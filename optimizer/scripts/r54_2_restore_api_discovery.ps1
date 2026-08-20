param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$artifact=(Resolve-Path $ArtifactDir).Path
$zip=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip' | Select-Object -First 1
if(!$zip){throw 'R54.2 restore discovery portable zip missing'}
$work=Join-Path $env:RUNNER_TEMP ('mwo-r542-restore-api-'+[guid]::NewGuid().ToString('N'))
$app=Join-Path $work 'app';New-Item -ItemType Directory -Force $app|Out-Null;Expand-Archive $zip.FullName $app -Force
$probe=Join-Path $work 'probe';New-Item -ItemType Directory -Force $probe|Out-Null
@'
<Project Sdk="Microsoft.NET.Sdk">
<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup>
</Project>
'@|Set-Content (Join-Path $probe 'Probe.csproj') -Encoding UTF8
@'
using System.Reflection;
var root=Path.GetFullPath(args[0]);
var win=Assembly.LoadFrom(Path.Combine(root,"MerzoOptimizer.Windows.dll"));
var core=Assembly.LoadFrom(Path.Combine(root,"MerzoOptimizer.Core.dll"));
string[] needles={"WindowsRestoreService","ElevationAwareRestoreService","WindowsSnapshotService","ElevatedOperationBroker","IRestoreService","ISnapshotService"};
foreach(var needle in needles){
  var types=win.GetTypes().Concat(core.GetTypes()).Where(t=>t.Name.Equals(needle,StringComparison.Ordinal)).ToArray();
  foreach(var t in types){
    Console.WriteLine($"R542_TYPE {t.FullName}");
    foreach(var c in t.GetConstructors(BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance))
      Console.WriteLine("R542_CTOR "+t.Name+"("+string.Join(",",c.GetParameters().Select(p=>$"{p.ParameterType.FullName} {p.Name}"))+")");
    foreach(var m in t.GetMethods(BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.DeclaredOnly).Where(m=>m.Name.Contains("Restore",StringComparison.OrdinalIgnoreCase)||m.Name.Contains("List",StringComparison.OrdinalIgnoreCase)||m.Name.Contains("Get",StringComparison.OrdinalIgnoreCase)||m.Name.Contains("Mark",StringComparison.OrdinalIgnoreCase)))
      Console.WriteLine("R542_METHOD "+t.Name+"."+m.Name+"("+string.Join(",",m.GetParameters().Select(p=>$"{p.ParameterType.FullName} {p.Name}"))+") -> "+m.ReturnType.FullName);
  }
}
'@|Set-Content (Join-Path $probe 'Program.cs') -Encoding UTF8
dotnet run --project (Join-Path $probe 'Probe.csproj') -c Release -- $app
if($LASTEXITCODE-ne0){throw 'R54.2 restore reflection probe failed'}
Write-Host 'R54_2_RESTORE_API_DISCOVERY_PASS'
