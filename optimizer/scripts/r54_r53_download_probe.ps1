param(
  [Parameter(Mandatory=$true)][string]$Dll,
  [Parameter(Mandatory=$true)][string]$SettingsPath,
  [Parameter(Mandatory=$true)][string]$UpdateDirectory,
  [string]$ExpectedVersion='0.1.54'
)
$ErrorActionPreference='Stop'

if(!(Test-Path $Dll)){throw "R53 updater DLL missing: $Dll"}
if(!(Test-Path $SettingsPath)){throw "Settings missing: $SettingsPath"}
Remove-Item $UpdateDirectory -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $UpdateDirectory | Out-Null

# Public R53 uses Assembly.GetEntryAssembly() to determine CurrentVersion.
# Loading it inside pwsh would make CurrentVersion=PowerShell (7.x), which is not
# the real application path and makes DownloadAsync correctly refuse download.
# Run the exact installed R53 updater DLL inside a tiny versioned EXE whose entry
# assembly is 0.1.53.0 — the same version as the real installed R53 app.
$hostRoot=Join-Path $env:TEMP ('mwo-r53-real-updater-host-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $hostRoot | Out-Null
$project=Join-Path $hostRoot 'R53UpdaterHost.csproj'
$program=Join-Path $hostRoot 'Program.cs'
@'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0-windows</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
    <AssemblyVersion>0.1.53.0</AssemblyVersion>
    <FileVersion>0.1.53.0</FileVersion>
    <InformationalVersion>0.1.53</InformationalVersion>
  </PropertyGroup>
</Project>
'@ | Set-Content $project -Encoding UTF8
@'
using System.Reflection;
using System.Security.Cryptography;

internal static class Program
{
    private static object? P(object o, string name) => o.GetType().GetProperty(name)?.GetValue(o);
    private static string S(object o, string name) => Convert.ToString(P(o, name)) ?? "";
    private static bool B(object o, string name) => Convert.ToBoolean(P(o, name));

    private static async Task<object> AwaitResult(object taskObject)
    {
        var task = (Task)taskObject;
        await task.ConfigureAwait(false);
        return task.GetType().GetProperty("Result")?.GetValue(task)
            ?? throw new InvalidOperationException("Task result missing");
    }

    public static async Task<int> Main(string[] args)
    {
        if (args.Length != 4) throw new ArgumentException("Expected: dll settings updateDir expectedVersion");
        var dll = Path.GetFullPath(args[0]);
        var settingsPath = Path.GetFullPath(args[1]);
        var updateDir = Path.GetFullPath(args[2]);
        var expectedVersion = args[3];
        var dllDir = Path.GetDirectoryName(dll)!;
        Directory.SetCurrentDirectory(dllDir);
        Directory.CreateDirectory(updateDir);

        AppDomain.CurrentDomain.AssemblyResolve += (_, e) =>
        {
            var candidate = Path.Combine(dllDir, new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(candidate) ? Assembly.LoadFrom(candidate) : null;
        };

        var asm = Assembly.LoadFrom(dll);
        var type = asm.GetTypes().FirstOrDefault(t => t.FullName?.EndsWith("GitHubUpdateService", StringComparison.Ordinal) == true)
            ?? throw new InvalidOperationException("GitHubUpdateService missing");
        var ctor = type.GetConstructors().FirstOrDefault(c => c.GetParameters().Length == 3)
            ?? throw new InvalidOperationException("R53 updater constructor missing");
        var names = string.Join(',', ctor.GetParameters().Select(p => p.Name));
        if (names != "settingsPath,updateDirectory,handler")
            throw new InvalidOperationException("Unexpected R53 updater constructor: " + names);

        using var handler = new HttpClientHandler();
        var svc = ctor.Invoke(new object?[] { settingsPath, updateDir, handler });
        try
        {
            var checkMethod = type.GetMethods().FirstOrDefault(m =>
                m.Name == "CheckAsync" && m.GetParameters().Length == 1 &&
                m.GetParameters()[0].ParameterType == typeof(CancellationToken))
                ?? throw new InvalidOperationException("R53 CheckAsync missing");
            var check = await AwaitResult(checkMethod.Invoke(svc, new object?[] { CancellationToken.None })!);
            var success = B(check, "Success");
            var configured = B(check, "Configured");
            var updateAvailable = B(check, "UpdateAvailable");
            var current = S(check, "CurrentVersion");
            var latest = S(check, "LatestVersion");
            var assetUrl = S(check, "AssetUrl");
            var checksumUrl = S(check, "ChecksumUrl");
            Console.WriteLine($"R53_REAL_CHECK success={success} configured={configured} available={updateAvailable} current={current} latest={latest}");
            Console.WriteLine("R53_REAL_ASSET=" + assetUrl);
            Console.WriteLine("R53_REAL_CHECKSUM=" + checksumUrl);
            if (!success || !configured) throw new InvalidOperationException("R53 CheckAsync failed: " + S(check, "Message"));
            if (current != "0.1.53") throw new InvalidOperationException("R53 test-host CurrentVersion mismatch: " + current);
            if (!updateAvailable) throw new InvalidOperationException("R53 did not mark R54 as available in real 0.1.53 host");
            if (latest != expectedVersion) throw new InvalidOperationException("R53 LatestVersion mismatch: " + latest);
            var expectedTag = "mwo-v" + expectedVersion;
            var expectedInstallerSuffix = $"/releases/download/{expectedTag}/MerzoWindowsOptimizerSetup-win-x64.exe";
            if (!assetUrl.EndsWith(expectedInstallerSuffix, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("R53 selected wrong installer URL: " + assetUrl);
            if (!checksumUrl.EndsWith(expectedInstallerSuffix + ".sha256", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException("R53 selected wrong checksum URL: " + checksumUrl);

            var downloadMethod = type.GetMethods().FirstOrDefault(m =>
                m.Name == "DownloadAsync" && m.GetParameters().Length == 2 &&
                m.GetParameters()[1].ParameterType == typeof(CancellationToken))
                ?? throw new InvalidOperationException("R53 DownloadAsync(check,cancellationToken) missing");
            var download = await AwaitResult(downloadMethod.Invoke(svc, new object?[] { check, CancellationToken.None })!);
            var downloadSuccess = B(download, "Success");
            var filePath = S(download, "FilePath");
            var verifiedSha = S(download, "VerifiedSha256");
            Console.WriteLine($"R53_REAL_DOWNLOAD_RESULT success={downloadSuccess} file={filePath} verifiedSha={verifiedSha} message={S(download,"Message")}");
            if (!downloadSuccess) throw new InvalidOperationException("R53 DownloadAsync returned Success=false");
            if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath))
                filePath = Directory.EnumerateFiles(updateDir, "MerzoWindowsOptimizerSetup-win-x64.exe", SearchOption.AllDirectories).FirstOrDefault() ?? "";
            if (string.IsNullOrWhiteSpace(filePath) || !File.Exists(filePath))
                throw new InvalidOperationException("R53 DownloadAsync did not create official installer");
            var hash = Convert.ToHexString(await SHA256.HashDataAsync(File.OpenRead(filePath))).ToLowerInvariant();
            if (!string.IsNullOrWhiteSpace(verifiedSha) && !string.Equals(verifiedSha, hash, StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException($"R53 VerifiedSha256 mismatch: result={verifiedSha} file={hash}");
            Console.WriteLine($"R53_REAL_DOWNLOAD_PASS path={filePath} sha={hash} latest={expectedVersion}");
            return 0;
        }
        finally
        {
            if (svc is IDisposable disposable) disposable.Dispose();
        }
    }
}
'@ | Set-Content $program -Encoding UTF8

try {
  $output=& dotnet run --project $project -c Release -- $Dll $SettingsPath $UpdateDirectory $ExpectedVersion 2>&1
  $exit=$LASTEXITCODE
  $text=($output | ForEach-Object {[string]$_}) -join "`n"
  Write-Host $text
  if($exit-ne0){throw "Versioned R53 updater host failed with exit $exit"}
  if($text-notmatch'R53_REAL_DOWNLOAD_PASS'){throw 'Versioned R53 updater host did not confirm download'}
}
finally {
  Remove-Item $hostRoot -Recurse -Force -ErrorAction SilentlyContinue
}
