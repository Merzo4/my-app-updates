using System.ComponentModel;
using System.Diagnostics;
using System.IO.Pipes;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Win32.SafeHandles;
using MerzoOptimizer.Core.Elevation;

namespace MerzoOptimizer.Windows.Elevation;

public sealed class ElevationDeniedException : Exception
{
    public ElevationDeniedException(string message, Exception? inner = null) : base(message, inner) { }
}

public sealed class ElevatedOperationBroker : IAsyncDisposable
{
    private const string Protocol = "MERZO-ELEVATION/46";
    private const int MaximumRequestChars = 128 * 1024;
    private const int MaximumResponseChars = 256 * 1024;

    private static readonly JsonSerializerOptions JsonOptions = ElevationJson.CreateOptions();
    private readonly SemaphoreSlim _gate = new(1, 1);
    private NamedPipeServerStream? _pipe;
    private StreamReader? _reader;
    private StreamWriter? _writer;
    private Process? _helperProcess;
    private readonly string _snapshotDirectory;
    private readonly string _logDirectory;
    private readonly string _backupDirectory;
    private bool _disposed;

    public ElevatedOperationBroker(string snapshotDirectory, string logDirectory, string backupDirectory)
    {
        _snapshotDirectory = Path.GetFullPath(snapshotDirectory);
        _logDirectory = Path.GetFullPath(logDirectory);
        _backupDirectory = Path.GetFullPath(backupDirectory);
    }

    public bool IsHelperActive => _helperProcess is { HasExited: false } && _pipe is { IsConnected: true };

    public async Task<T> ExecuteAsync<T>(ElevatedOperationRequest request, CancellationToken cancellationToken = default)
    {
        if (_disposed) throw new ObjectDisposedException(nameof(ElevatedOperationBroker));
        await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            await EnsureConnectedAsync(cancellationToken).ConfigureAwait(false);
            var normalized = request with { RequestId = Guid.NewGuid().ToString("N") };
            var line = JsonSerializer.Serialize(normalized, JsonOptions);
            if (line.Length > MaximumRequestChars)
                throw new InvalidDataException("Elevated request exceeded the safe protocol limit.");

            await _writer!.WriteLineAsync(line).ConfigureAwait(false);
            var responseLine = await _reader!.ReadLineAsync(cancellationToken).ConfigureAwait(false);
            if (responseLine is null)
                throw new IOException("Elevated helper unexpectedly disconnected.");
            if (responseLine.Length > MaximumResponseChars)
                throw new InvalidDataException("Elevated helper response exceeded the safe protocol limit.");

            var response = JsonSerializer.Deserialize<ElevatedOperationResponse>(responseLine, JsonOptions)
                ?? throw new InvalidDataException("Elevated helper returned an empty response.");

            if (!string.Equals(response.RequestId, normalized.RequestId, StringComparison.Ordinal))
                throw new InvalidDataException("Elevated helper response id does not match the request.");
            if (!response.Success)
                throw new ElevationDeniedException(response.Error ?? "Elevated operation failed.");
            if (string.IsNullOrWhiteSpace(response.ResultJson))
                throw new InvalidDataException("Elevated helper returned no result payload.");

            return JsonSerializer.Deserialize<T>(response.ResultJson, JsonOptions)
                ?? throw new InvalidDataException($"Could not deserialize elevated result as {typeof(T).Name}.");
        }
        catch (Exception ex) when (ex is IOException or InvalidDataException)
        {
            TryTerminateHelper();
            ResetConnection();
            throw;
        }
        finally
        {
            _gate.Release();
        }
    }

    private async Task EnsureConnectedAsync(CancellationToken cancellationToken)
    {
        if (IsHelperActive)
            return;

        ResetConnection();
        var pipeName = $"MerzoOptimizer-{Environment.ProcessId}-{Guid.NewGuid():N}";
        var nonce = Convert.ToHexString(RandomNumberGenerator.GetBytes(32)).ToLowerInvariant();
        _pipe = new NamedPipeServerStream(
            pipeName,
            PipeDirection.InOut,
            1,
            PipeTransmissionMode.Byte,
            PipeOptions.Asynchronous | PipeOptions.CurrentUserOnly,
            8192,
            8192);

        var helperPath = ResolveHelperPath();
        ValidateHelperBinary(helperPath);

        try
        {
            var psi = new ProcessStartInfo
            {
                FileName = helperPath,
                Arguments = $"--pipe {pipeName} --parent-pid {Environment.ProcessId} --nonce {nonce} --snapshot-b64 {EncodeArg(_snapshotDirectory)} --log-b64 {EncodeArg(_logDirectory)} --backup-b64 {EncodeArg(_backupDirectory)}",
                UseShellExecute = true,
                Verb = "runas",
                WorkingDirectory = Path.GetDirectoryName(helperPath) ?? AppContext.BaseDirectory,
                WindowStyle = ProcessWindowStyle.Hidden
            };
            _helperProcess = Process.Start(psi) ?? throw new InvalidOperationException("Could not start elevated helper.");
        }
        catch (Win32Exception ex) when (ex.NativeErrorCode == 1223)
        {
            ResetConnection();
            throw new ElevationDeniedException("Запрос UAC отменён. Merzo ничего не изменил.", ex);
        }
        catch
        {
            ResetConnection();
            throw;
        }

        using var connectCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        connectCts.CancelAfter(TimeSpan.FromSeconds(20));
        try
        {
            await _pipe.WaitForConnectionAsync(connectCts.Token).ConfigureAwait(false);
            VerifyConnectedHelperProcess();

            _reader = new StreamReader(_pipe, new UTF8Encoding(false), detectEncodingFromByteOrderMarks: false, bufferSize: 8192, leaveOpen: true);
            _writer = new StreamWriter(_pipe, new UTF8Encoding(false), bufferSize: 8192, leaveOpen: true) { AutoFlush = true };

            using var handshakeCts = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            handshakeCts.CancelAfter(TimeSpan.FromSeconds(5));
            var hello = await _reader.ReadLineAsync(handshakeCts.Token).ConfigureAwait(false);
            var expectedHello = $"{Protocol} HELLO {nonce}";
            if (!string.Equals(hello, expectedHello, StringComparison.Ordinal))
                throw new InvalidDataException("Elevated helper handshake failed.");
            await _writer.WriteLineAsync($"{Protocol} OK {nonce}").ConfigureAwait(false);
        }
        catch (Exception ex) when (ex is not ElevationDeniedException)
        {
            TryTerminateHelper();
            ResetConnection();
            throw new ElevationDeniedException("Не удалось подтвердить защищённый UAC-helper. Изменение не выполнено.", ex);
        }
    }

    private void VerifyConnectedHelperProcess()
    {
        if (_pipe is null || _helperProcess is null || _helperProcess.HasExited)
            throw new InvalidDataException("Elevated helper process is unavailable.");
        if (!GetNamedPipeClientProcessId(_pipe.SafePipeHandle, out var clientPid))
            throw new IOException($"Windows не вернула PID UAC-helper (Win32 {Marshal.GetLastWin32Error()}).");
        if (clientPid != (uint)_helperProcess.Id)
            throw new InvalidDataException("Named pipe was connected by an unexpected process. Connection rejected.");
    }

    private static void ValidateHelperBinary(string helperPath)
    {
        if (!File.Exists(helperPath))
            throw new FileNotFoundException("Merzo elevated helper was not found. Rebuild the full solution.", helperPath);

        var fullHelper = Path.GetFullPath(helperPath);
        var besideApp = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "MerzoOptimizer.ElevatedHelper.exe"));
        if (IsInstalledLayout() && !fullHelper.Equals(besideApp, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Production отказался запускать UAC-helper вне каталога приложения.");

        var appPath = Environment.ProcessPath;
        if (string.IsNullOrWhiteSpace(appPath) || !File.Exists(appPath))
            throw new InvalidDataException("Не удалось подтвердить основной EXE перед UAC.");

        var appVersion = FileVersionInfo.GetVersionInfo(appPath).FileVersion ?? string.Empty;
        var helperVersion = FileVersionInfo.GetVersionInfo(fullHelper).FileVersion ?? string.Empty;
        if (string.IsNullOrWhiteSpace(appVersion) || !string.Equals(appVersion, helperVersion, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Версия UAC-helper не совпадает с версией основного приложения.");
    }

    private static string ResolveHelperPath()
    {
        var besideApp = Path.Combine(AppContext.BaseDirectory, "MerzoOptimizer.ElevatedHelper.exe");
        if (File.Exists(besideApp))
            return besideApp;

        foreach (var configuration in new[] { "Release", "Debug" })
        {
            var dev = Path.GetFullPath(Path.Combine(
                AppContext.BaseDirectory,
                "..", "..", "..", "..",
                "MerzoOptimizer.ElevatedHelper", "bin", configuration, "net10.0-windows",
                "MerzoOptimizer.ElevatedHelper.exe"));
            if (File.Exists(dev))
                return dev;
        }

        return besideApp;
    }

    private static string EncodeArg(string value) => Convert.ToBase64String(Encoding.UTF8.GetBytes(value));

    private static bool IsInstalledLayout()
    {
        var baseDir = Path.GetFullPath(AppContext.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar);
        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);
        var programFilesX86 = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86);
        return (!string.IsNullOrWhiteSpace(programFiles) && baseDir.StartsWith(programFiles, StringComparison.OrdinalIgnoreCase)) ||
               (!string.IsNullOrWhiteSpace(programFilesX86) && baseDir.StartsWith(programFilesX86, StringComparison.OrdinalIgnoreCase));
    }

    private void ResetConnection()
    {
        try { _writer?.Dispose(); } catch { }
        try { _reader?.Dispose(); } catch { }
        try { _pipe?.Dispose(); } catch { }
        _writer = null;
        _reader = null;
        _pipe = null;
        if (_helperProcess is { HasExited: true })
        {
            _helperProcess.Dispose();
            _helperProcess = null;
        }
    }

    private void TryTerminateHelper()
    {
        try
        {
            if (_helperProcess is { HasExited: false })
                _helperProcess.Kill(entireProcessTree: true);
        }
        catch { }
    }

    public async ValueTask DisposeAsync()
    {
        if (_disposed) return;
        _disposed = true;

        await _gate.WaitAsync().ConfigureAwait(false);
        try
        {
            if (IsHelperActive)
            {
                try
                {
                    var request = new ElevatedOperationRequest
                    {
                        RequestId = Guid.NewGuid().ToString("N"),
                        Kind = ElevatedOperationKind.Shutdown
                    };
                    await _writer!.WriteLineAsync(JsonSerializer.Serialize(request, JsonOptions)).ConfigureAwait(false);
                }
                catch { }
            }
            TryTerminateHelper();
            ResetConnection();
            _helperProcess?.Dispose();
            _helperProcess = null;
        }
        finally
        {
            _gate.Release();
            _gate.Dispose();
        }
    }

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetNamedPipeClientProcessId(SafePipeHandle Pipe, out uint ClientProcessId);
}
