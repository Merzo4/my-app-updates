param(
  [Parameter(Mandatory=$true)][string]$Dll,
  [Parameter(Mandatory=$true)][string]$SettingsPath,
  [Parameter(Mandatory=$true)][string]$UpdateDirectory,
  [Parameter(Mandatory=$true)][string]$ExpectedVersion
)
$ErrorActionPreference='Stop'
$dllPath=(Resolve-Path $Dll).Path
$settings=(Resolve-Path $SettingsPath).Path
$work=Join-Path $env:TEMP ('r54-real-updater-host-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $work | Out-Null
try {
  $hostCsproj=Join-Path $work 'R54UpdaterHost.csproj'
  @"
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net10.0-windows10.0.19041.0</TargetFramework>
    <AssemblyVersion>0.1.54.0</AssemblyVersion>
    <FileVersion>0.1.54.0</FileVersion>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>enable</Nullable>
  </PropertyGroup>
  <ItemGroup>
    <Reference Include="MerzoOptimizer.Windows"><HintPath>$dllPath</HintPath><Private>true</Private></Reference>
  </ItemGroup>
</Project>
"@ | Set-Content $hostCsproj -Encoding UTF8
  @'
using System.Reflection;

var dll=Path.GetFullPath(args[0]);
var settings=Path.GetFullPath(args[1]);
var updateDir=Path.GetFullPath(args[2]);
var expected=args[3];
var asm=Assembly.LoadFrom(dll);
var type=asm.GetTypes().First(t=>t.FullName!.EndsWith("GitHubUpdateService",StringComparison.Ordinal));
var ctors=type.GetConstructors();
object? service=null;
foreach(var c in ctors){
  var p=c.GetParameters();
  if(p.Length==3 && p[0].ParameterType==typeof(string) && p[1].ParameterType==typeof(string)){
    object? third=p[2].ParameterType.IsValueType?Activator.CreateInstance(p[2].ParameterType):null;
    try{service=c.Invoke(new object?[]{settings,updateDir,third});break;}catch{}
  }
}
if(service is null) throw new Exception("R54 GitHubUpdateService constructor not found");

MethodInfo? check=null;
object?[]? checkArgs=null;
foreach(var m in type.GetMethods().Where(m=>m.Name=="CheckAsync")){
  var ps=m.GetParameters();
  if(ps.Length==0){check=m;checkArgs=Array.Empty<object?>();break;}
  if(ps.Length==1 && ps[0].ParameterType==typeof(CancellationToken)){check=m;checkArgs=new object?[]{CancellationToken.None};break;}
}
if(check is null || checkArgs is null) throw new Exception("Compatible CheckAsync overload missing");
Console.WriteLine($"R54_REAL_CHECK_SIGNATURE params={check.GetParameters().Length}");
var checkTask=(Task)check.Invoke(service,checkArgs)!;
await checkTask;
var result=checkTask.GetType().GetProperty("Result")!.GetValue(checkTask)!;
string S(string n)=>result.GetType().GetProperty(n)?.GetValue(result)?.ToString()??"";
bool B(string n)=>result.GetType().GetProperty(n)?.GetValue(result) is bool b && b;
Console.WriteLine($"R54_REAL_CHECK success={B("Success")} configured={B("IsConfigured")} available={B("UpdateAvailable")} current={S("CurrentVersion")} latest={S("LatestVersion")}");
Console.WriteLine($"R54_REAL_ASSET={S("AssetUrl")}");
Console.WriteLine($"R54_REAL_CHECKSUM={S("ChecksumUrl")}");
if(!B("Success")||!B("IsConfigured")||!B("UpdateAvailable")) throw new Exception("R54 CheckAsync did not expose an update");
if(S("LatestVersion")!=expected) throw new Exception($"R54 latest version mismatch: {S("LatestVersion")} != {expected}");
if(!S("AssetUrl").Contains($"/releases/download/mwo-v{expected}/MerzoWindowsOptimizerSetup-win-x64.exe",StringComparison.Ordinal)) throw new Exception("R54 asset URL mismatch");
if(!S("ChecksumUrl").Contains($"/releases/download/mwo-v{expected}/MerzoWindowsOptimizerSetup-win-x64.exe.sha256",StringComparison.Ordinal)) throw new Exception("R54 checksum URL mismatch");
MethodInfo? download=null;
object?[]? da=null;
foreach(var m in type.GetMethods().Where(m=>m.Name=="DownloadAsync")){
  var ps=m.GetParameters();
  if(ps.Length==1 && ps[0].ParameterType.IsInstanceOfType(result)){download=m;da=new[]{result};break;}
  if(ps.Length==2 && ps[0].ParameterType.IsInstanceOfType(result) && ps[1].ParameterType==typeof(CancellationToken)){download=m;da=new object?[]{result,CancellationToken.None};break;}
}
if(download is null || da is null) throw new Exception("Compatible DownloadAsync overload missing");
Console.WriteLine($"R54_REAL_DOWNLOAD_SIGNATURE params={download.GetParameters().Length}");
var dt=(Task)download.Invoke(service,da)!;
await dt;
var dr=dt.GetType().GetProperty("Result")!.GetValue(dt)!;
string DS(string n)=>dr.GetType().GetProperty(n)?.GetValue(dr)?.ToString()??"";
bool DB(string n)=>dr.GetType().GetProperty(n)?.GetValue(dr) is bool b && b;
Console.WriteLine($"R54_REAL_DOWNLOAD_RESULT success={DB("Success")} file={DS("FilePath")} verifiedSha={DS("VerifiedSha256")} message={DS("Message")}");
if(!DB("Success")) throw new Exception("R54 DownloadAsync failed: "+DS("Message"));
var file=DS("FilePath");
if(!File.Exists(file)) throw new Exception("R54 downloaded installer missing");
if(string.IsNullOrWhiteSpace(DS("VerifiedSha256"))) throw new Exception("R54 DownloadAsync did not report verified SHA");
Console.WriteLine($"R54_REAL_DOWNLOAD_PASS path={file} sha={DS("VerifiedSha256")} latest={S("LatestVersion")}");
'@ | Set-Content (Join-Path $work 'Program.cs') -Encoding UTF8
  dotnet run --project $hostCsproj --configuration Release -- $dllPath $settings $UpdateDirectory $ExpectedVersion
  if($LASTEXITCODE-ne0){throw "R54 updater host failed: $LASTEXITCODE"}
}
finally {Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue}
