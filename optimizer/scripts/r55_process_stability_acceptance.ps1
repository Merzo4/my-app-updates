param(
  [Parameter(Mandatory=$true)][string]$SourceRoot
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$core=Join-Path $SourceRoot 'src\MerzoOptimizer.Core\MerzoOptimizer.Core.csproj'
$win=Join-Path $SourceRoot 'src\MerzoOptimizer.Windows\MerzoOptimizer.Windows.csproj'
if(!(Test-Path $core) -or !(Test-Path $win)){throw 'R55 acceptance project references missing'}

$work=Join-Path $env:RUNNER_TEMP 'r55-process-acceptance'
Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
New-Item $work -ItemType Directory -Force | Out-Null
$csproj=@"
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0-windows</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <ProjectReference Include="$core" />
    <ProjectReference Include="$win" />
  </ItemGroup>
</Project>
"@
Set-Content (Join-Path $work 'R55Acceptance.csproj') $csproj -Encoding UTF8

$program=@'
using System.Diagnostics;
using Microsoft.Win32;
using MerzoOptimizer.Core.Audit;
using MerzoOptimizer.Windows.Processes;

var tempDir = Path.Combine(Path.GetTempPath(), "MerzoR55Synthetic");
Directory.CreateDirectory(tempDir);
var synthetic = Path.Combine(tempDir, "MerzoR55Synthetic.exe");
File.Copy(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "ping.exe"), synthetic, true);
const string valueName = "MerzoR55SyntheticDelayed";
Process? child = null;
try
{
    using (var run = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run"))
        run!.SetValue(valueName, $"\"{synthetic}\" 127.0.0.1 -n 20", RegistryValueKind.String);

    var delayed = Task.Run(async () =>
    {
        await Task.Delay(800);
        child = Process.Start(new ProcessStartInfo(synthetic, "127.0.0.1 -n 20") { UseShellExecute = false, CreateNoWindow = true });
    });

    var analyzer = new WindowsProcessStabilityAnalyzer();
    var options = new ProcessStabilityAuditOptions([TimeSpan.Zero, TimeSpan.FromSeconds(2), TimeSpan.FromSeconds(4)]);
    var points = new List<string>();
    var progress = new Progress<ProcessStabilityProgress>(p => points.Add($"{p.SampleIndex}:{p.ProcessCount}"));
    var report = await analyzer.RunAsync(options, progress, CancellationToken.None);
    await delayed;

    var row = report.Deltas.FirstOrDefault(x => x.FamilyName.Equals("MerzoR55Synthetic", StringComparison.OrdinalIgnoreCase));
    if (row is null) throw new Exception("synthetic delayed family was not detected");
    if (row.AddedPeak < 1) throw new Exception($"synthetic AddedPeak={row.AddedPeak}");
    if (!row.Source.StartsWith("Автозагрузка:", StringComparison.Ordinal)) throw new Exception($"synthetic source={row.Source}");
    if (row.Classification is not ("Проверить" or "Необязательный")) throw new Exception($"synthetic classification={row.Classification}");

    var svchost = report.Samples.SelectMany(x => x.Families).FirstOrDefault(x => x.FamilyName.Equals("svchost", StringComparison.OrdinalIgnoreCase));
    if (svchost is null) throw new Exception("svchost baseline evidence missing");
    if (svchost.Classification != "Не трогать") throw new Exception($"svchost classification={svchost.Classification}");

    if (report.Samples.Count != 3) throw new Exception($"samples={report.Samples.Count}");
    if (report.PeakCount < report.BaselineCount) throw new Exception("invalid peak count");
    Console.WriteLine($"R55_SYNTHETIC_DELAYED_PASS family={row.FamilyName} added={row.AddedPeak} source={row.Source} class={row.Classification}");
    Console.WriteLine($"R55_PROTECTED_SYSTEM_PASS family={svchost.FamilyName} class={svchost.Classification}");
    Console.WriteLine($"R55_SAMPLE_CURVE_PASS baseline={report.BaselineCount} final={report.FinalCount} peak={report.PeakCount} samples={report.Samples.Count}");
    Console.WriteLine("R55_PROCESS_STABILITY_ACCEPTANCE_PASS");
}
finally
{
    try { child?.Kill(entireProcessTree: true); } catch { }
    try { child?.Dispose(); } catch { }
    try { using var run = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run", writable: true); run?.DeleteValue(valueName, false); } catch { }
    try { File.Delete(synthetic); Directory.Delete(tempDir, false); } catch { }
}
'@
Set-Content (Join-Path $work 'Program.cs') $program -Encoding UTF8
Push-Location $work
try {
  dotnet run -c Release --project .\R55Acceptance.csproj
  if($LASTEXITCODE-ne0){throw "R55 acceptance exit=$LASTEXITCODE"}
}
finally { Pop-Location }
