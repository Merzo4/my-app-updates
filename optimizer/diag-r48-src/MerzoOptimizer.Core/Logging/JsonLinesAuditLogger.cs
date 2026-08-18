using System.Text.Json;

namespace MerzoOptimizer.Core.Logging;

public sealed class JsonLinesAuditLogger : IAuditLogger
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = false
    };

    private readonly SemaphoreSlim _writeLock = new(1, 1);

    public JsonLinesAuditLogger(string? logDirectory = null)
    {
        LogDirectory = logDirectory ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "MerzoWindowsOptimizer",
            "logs");

        Directory.CreateDirectory(LogDirectory);
    }

    public string LogDirectory { get; }

    public async Task WriteAsync(AuditLogEntry entry, CancellationToken cancellationToken = default)
    {
        var filePath = Path.Combine(LogDirectory, $"audit-{DateTime.Now:yyyyMMdd}.jsonl");
        var line = JsonSerializer.Serialize(entry, JsonOptions) + Environment.NewLine;

        await _writeLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            await File.AppendAllTextAsync(filePath, line, cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _writeLock.Release();
        }
    }
}
