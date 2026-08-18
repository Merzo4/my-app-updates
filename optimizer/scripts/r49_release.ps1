$ErrorActionPreference='Stop'
$Repo=(Resolve-Path '.').Path
$Work=Join-Path $Repo 'r49'
if(Test-Path $Work){Remove-Item $Work -Recurse -Force}

# Restore immutable trusted source.
$parts=Get-ChildItem (Join-Path $Repo 'optimizer/source-min/R21.part*')|Sort-Object Name
if($parts.Count-ne29){throw "Source parts missing: $($parts.Count)"}
$b=[Text.StringBuilder]::new();foreach($p in $parts){[void]$b.Append(((Get-Content $p.FullName -Raw)-replace '\s',''))}
$archive=Join-Path $Repo 'r49.tar.xz';[IO.File]::WriteAllBytes($archive,[Convert]::FromBase64String($b.ToString()))
$srcSha=(Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if($srcSha-ne'ce9ca7f8f44464c42165e0a79f3053062dfbe2e0df6b0b8517d1ac7510070d2d'){throw "Source SHA mismatch $srcSha"}
New-Item -ItemType Directory -Force $Work|Out-Null;tar -xf $archive -C $Work
$sln=Get-ChildItem $Work -Recurse -Filter MerzoWindowsOptimizer.sln|Select-Object -First 1
if(-not$sln){throw 'Solution missing'}
$root=$sln.Directory.FullName;$env:SOURCE_ROOT=$root

# Convert original transferable SelfTest feed contract to the production feed before cumulative patches.
$self=Join-Path $root 'src\MerzoOptimizer.SelfTest\Program.cs';$s=Get-Content $self -Raw
$s=$s.Replace('"releases/latest", "digest", "sha256:", "SHA256.HashDataAsync", "FixedTimeEquals"','"releases?per_page=50", "digest", "sha256:", "SHA256.HashDataAsync", "FixedTimeEquals"')
$old='if (!string.IsNullOrWhiteSpace(owner) || !string.IsNullOrWhiteSpace(repo)) failures.Add("Release feed should remain intentionally unconfigured in transferable DEV package.");'
$new='var prefix = root.TryGetProperty("release_tag_prefix", out var prefixEl) ? prefixEl.GetString() : null; var assetName = root.TryGetProperty("asset_name_contains", out var assetEl) ? assetEl.GetString() : null; if (!string.Equals(owner, "Merzo4", StringComparison.Ordinal) || !string.Equals(repo, "my-app-updates", StringComparison.Ordinal)) failures.Add("Production release feed must be Merzo4/my-app-updates."); if (!string.Equals(prefix, "mwo-v", StringComparison.Ordinal)) failures.Add("Production release tag prefix must be mwo-v."); if (!string.Equals(assetName, "MerzoWindowsOptimizerSetup-win-x64.exe", StringComparison.Ordinal)) failures.Add("Production installer asset name is incorrect.");'
if($s.Contains($old)){$s=$s.Replace($old,$new)}
Set-Content $self $s -Encoding UTF8

$patches=@(
'r24_update_center.py','r24_compile_fix.py','r26_ota_repair.py','r27_privacy_engine.py','r28_profiles_updates_cleanup_ux.py',
'r29_operation_center.py','r29_compile_fix.py','r30_major_update.py','r30_policy_fix.py','r31_audit_memory.py','r32_performance_engine.py',
'r33_stability_hotfix.py','r34_ultra_process_feedback.py','r34_task_extension.py','r35_readability_ui.py','r36_gaming_ui_polish.py',
'r37_operation_ui.py','r37_network_center.py','r37_finalize.py','r38_gaming_catalog.py','r38_gaming_network.py','r38_gaming_ui.py','r38_finalize.py',
'r39_gaming_build_catalog.py','r39_gaming_build_engine.py','r39_gaming_build_ui.py','r39_finalize.py','r40_network_binding_hotfix.py',
'r42_full_ui_rework.py','r42_window_contract_fix.py','r43_true_full_ui.py','r44_function_expansion.py','r44_finalize.py','r45_apply_selected_ux.py',
'r46_security_layout_hardening.py','r46_binding_finalize.py','r47_simple_builds.py','r47_finalize.py','r48_ota_reliability_wrapper.py',
'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py')
foreach($name in $patches){python (Join-Path $Repo "optimizer/patches/$name");if($LASTEXITCODE-ne0){throw "Patch failed: $name"}}

# R49 fail-closed source, UX and security gates.
@'
import os,json,re,xml.etree.ElementTree as ET
from pathlib import Path
r=Path(os.environ['SOURCE_ROOT'])
xp=r/'src/MerzoOptimizer.App/MainWindow.xaml';x=xp.read_text(encoding='utf-8-sig')
vm=(r/'src/MerzoOptimizer.App/ViewModels/MainWindowViewModel.cs').read_text(encoding='utf-8-sig')
app=(r/'src/MerzoOptimizer.App/App.xaml.cs').read_text(encoding='utf-8-sig')
u=(r/'src/MerzoOptimizer.Windows/Updates/GitHubUpdateService.cs').read_text(encoding='utf-8-sig')
b=(r/'src/MerzoOptimizer.Windows/Elevation/ElevatedOperationBroker.cs').read_text(encoding='utf-8-sig')
h=(r/'src/MerzoOptimizer.ElevatedHelper/Program.cs').read_text(encoding='utf-8-sig')
od=(r/'src/MerzoOptimizer.Windows/OneDrive/WindowsOneDriveOptimizationService.cs').read_text(encoding='utf-8-sig')
rp=(r/'src/MerzoOptimizer.Windows/Recovery/WindowsRecoveryPackageService.cs').read_text(encoding='utf-8-sig')

for t in ['Width="1000" Height="600"','MinWidth="920" MinHeight="560"','Production 0.1.49','Production R49','Сборки Windows','Экспертные инструменты','Установить сборку','OptimizationApplyBar','Recovery Package','OneDrive']:
    assert t in x,t
assert 'Телеметрия отключается уже в ЛАЙТ' not in x
for i in range(12): assert f'x:Name="PageRoot{i}"' in x,f'PageRoot{i}'
root=ET.parse(xp).getroot();ns='{http://schemas.microsoft.com/winfx/2006/xaml/presentation}';xn='{http://schemas.microsoft.com/winfx/2006/xaml}'
main=next(z for z in root.iter(ns+'TabControl') if z.attrib.get(xn+'Name')=='MainTabs');assert len([c for c in list(main) if c.tag==ns+'TabItem'])==12
required={'IsBusy','HasOptimizationScanResults','IsLightRecommended','IsStandardRecommended','DeepScanProgress','NetworkProgress','IsBalancedPowerActive','IsPerformancePowerActive','IsStartupUpdateNoticeVisible','UpdateProgress'};seen=set()
for e in root.iter():
    for val in e.attrib.values():
        if val.startswith('{Binding '):
            prop=val[len('{Binding '):].split(',',1)[0].split('}',1)[0].strip()
            if prop in required:
                seen.add(prop);assert 'Mode=OneWay' in val,(prop,val)
assert not(required-seen),('missing OneWay',sorted(required-seen))

tweaks=json.loads((r/'data/tweaks.json').read_text(encoding='utf-8-sig'))
by={t['id']:t for t in tweaks}
def ids(tag): return {t['id'] for t in tweaks if not t.get('scan_only',False) and tag in (t.get('profile_tags') or [])}
light,game,extreme=ids('merzo_light'),ids('merzo_game'),ids('merzo_extreme')
assert light < game < extreme,(len(light),len(game),len(extreme))
for q in ['explorer.launch_this_pc','explorer.classic_context_menu','onedrive.disable_sync','r49.onedrive.disable_startup','r49.start.hide_recently_added','r49.start.hide_personalized_sites','r49.privacy.disable_tailored_experiences','r49.delivery.disable_peer_downloads']:
    assert q in light,q
assert 'r49.power.disable_power_throttling' not in light and 'r49.power.disable_power_throttling' in game and 'r49.power.disable_power_throttling' in extreme
assert 'r49.gaming.disable_game_dvr' not in light and 'r49.gaming.disable_game_dvr' not in game and 'r49.gaming.disable_game_dvr' in extreme
lab=by['r49.lab.mpo_stutter_workaround'];assert 'gaming_build_lab' in lab.get('profile_tags',[]) and not(set(lab.get('profile_tags',[])) & {'merzo_light','merzo_game','merzo_extreme'})
for bad in ['performance.keep_defender_advisory','performance.keep_windows_update_advisory','performance.keep_ipv6_advisory','performance.keep_pagefile_advisory','performance.keep_timer_advisory','performance.keep_tcp_magic_advisory']:
    if bad in by: assert not(set(by[bad].get('profile_tags',[])) & {'merzo_light','merzo_game','merzo_extreme'}),bad

for t in ['OfficialOwner = "Merzo4"','OfficialRepository = "my-app-updates"','OfficialInstallerName = "MerzoWindowsOptimizerSetup-win-x64.exe"','FixedTimeShaEquals','IsOfficialReleaseAssetUrl','ResolveBestReleaseAsync','GetJsonWithRetryAsync','releases?per_page=20','matching-refs/tags','releases/tags/','tags?per_page=100','HttpStatusCode.GatewayTimeout','(HttpStatusCode)429']:
    assert t in u,t
for t in ['MERZO-ELEVATION/46','GetNamedPipeClientProcessId','--parent-pid','--nonce','RandomNumberGenerator']:
    assert t in b,t
for t in ['MERZO-ELEVATION/46','GetNamedPipeServerProcessId','--parent-pid','--nonce','ValidateSnapshotAsync','ValidateKnownServiceAsync','ValidateKnownTaskAsync','ValidateStartupDynamicTweak','CreateSystemRestorePoint','UninstallOneDrive','Checkpoint-Computer','Get-ComputerRestorePoint','OneDriveSetup.exe','/uninstall']:
    assert t in h,t
for t in ['IRecoveryPackageService','SystemRestorePointReady','CreateSystemRestorePoint','plannedOperations','CompleteAsync']:
    assert t in rp,t
for t in ['IOneDriveOptimizationService','HasConfiguredAccount','OneDriveSetup.exe','UninstallAsync']:
    assert t in od,t
assert 'Directory.Delete' not in od and 'File.Delete' not in od and 'Remove-Item' not in od
start=h.index('private static async Task<object> UninstallOneDriveAsync')
end=h.index('private static async Task<string> RunFixedPowerShellAsync',start)
odhelper=h[start:end]
for forbidden in ['Directory.Delete','File.Delete','Remove-Item','rmdir','del /']:
    assert forbidden not in odhelper,forbidden
assert 'Recovery Package preflight' in vm and 'oneDriveUninstallRequested' in vm and '_recoveryPackageService.CreateAsync' in vm
assert 'new WindowsRecoveryPackageService' in app and 'new WindowsOneDriveOptimizationService' in app
for marker in ['R49_CATALOG.marker','R49_RECOVERY_ONEDRIVE_INFRA.marker','R49_BUILD_INTEGRATION.marker']:
    assert (r/marker).exists(),marker
print(f'R49_SOURCE_SECURITY_PASS LIGHT={len(light)} GAME={len(game)} EXTREME={len(extreme)} TOTAL={len(tweaks)}')
'@|python
if($LASTEXITCODE-ne0){throw 'R49 source/security gate failed'}

foreach($p in Get-ChildItem (Join-Path $root 'src') -Recurse -Filter *.csproj){
    $z=Get-Content $p.FullName -Raw
    if($z-match'<AssemblyVersion>([^<]+)</AssemblyVersion>'-and$Matches[1]-ne'0.1.49.0'){throw "$($p.Name) assembly version $($Matches[1])"}
}

# Build-Production includes Core SelfTest. Obfuscation is intentionally disabled after R31 corruption.
Push-Location $root
try{& .\build\Build-Production.ps1 -Version '0.1.49' -SkipObfuscation;if($LASTEXITCODE-ne0){throw 'Production build failed'}}finally{Pop-Location}

dotnet run --project (Join-Path $root 'src\MerzoOptimizer.SelfTest\MerzoOptimizer.SelfTest.csproj') -c Release
if($LASTEXITCODE-ne0){throw 'SelfTest failed'}
$dist=Join-Path $root 'dist\app'
foreach($name in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){
    $p=Join-Path $dist $name;if(-not(Test-Path $p)){throw "Missing $name"}
    $v=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString();if($v-ne'0.1.49.0'){throw "$name version $v"}
}
if(Get-ChildItem $dist -Recurse -File|?{$_.Name-match'Obfuscar'}){throw 'Obfuscar artifact detected'}
foreach($f in Get-ChildItem (Join-Path $root 'src\MerzoOptimizer.App') -Recurse -Filter *.xaml|?{$_.FullName-notmatch'\\(bin|obj)\\'}){try{[xml](Get-Content $f.FullName -Raw)|Out-Null}catch{throw "Malformed XAML $($f.FullName): $($_.Exception.Message)"}}

# Runtime WPF layout probe for every top-level page at baseline and minimum contract.
$layout=Join-Path $env:RUNNER_TEMP 'r49-layout';New-Item -ItemType Directory -Force $layout|Out-Null
$ap=[Security.SecurityElement]::Escape((Join-Path $root 'src\MerzoOptimizer.App\MerzoOptimizer.App.csproj'))
@"
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup><ProjectReference Include="$ap" /></ItemGroup></Project>
"@|Set-Content (Join-Path $layout 'Layout.csproj') -Encoding UTF8
@'
using System.Windows;using System.Windows.Controls;using System.Windows.Media;using MerzoOptimizer.App;
internal static class Program{
static FrameworkElement N(DependencyObject p,string n){if(p is FrameworkElement f&&f.Name==n)return f;for(int i=0;i<VisualTreeHelper.GetChildrenCount(p);i++){var r=N(VisualTreeHelper.GetChild(p,i),n);if(r!=null)return r;}return null!;}
static bool Inside(FrameworkElement c,FrameworkElement a){var p=c.TransformToAncestor(a).Transform(new Point(0,0));return p.X>=-2&&p.Y>=-2&&p.X+c.ActualWidth<=a.ActualWidth+2&&p.Y+c.ActualHeight<=a.ActualHeight+2;}
[STAThread]static void Main(){var a=new App();a.InitializeComponent();foreach(var s in new[]{(1000d,600d),(920d,560d)}){var w=new MainWindow{Width=s.Item1,Height=s.Item2,Left=-20000,Top=-20000,ShowInTaskbar=false,ShowActivated=false};w.Show();w.UpdateLayout();var t=(TabControl)N(w,"MainTabs");var side=N(w,"SidebarProtectedModeCard");if(side is null||!Inside(side,w))throw new Exception("sidebar overflow");for(int i=0;i<12;i++){t.SelectedIndex=i;w.UpdateLayout();var r=N(w,$"PageRoot{i}");if(r is null||r.ActualWidth<1||r.ActualHeight<1||!Inside(r,w))throw new Exception($"PageRoot{i} overflow at {s}");}t.SelectedIndex=2;w.UpdateLayout();var bar=N(w,"OptimizationApplyBar");if(bar is null||!Inside(bar,w))throw new Exception("build action bar overflow");w.Close();}a.Shutdown();Console.WriteLine("R49_LAYOUT_12_PAGES_PASS");}}
'@|Set-Content (Join-Path $layout 'Program.cs') -Encoding UTF8
dotnet run --project (Join-Path $layout 'Layout.csproj') -c Release
if($LASTEXITCODE-ne0){throw 'R49 layout probe failed'}

# Dispatcher + read-only network diagnostic runtime smoke.
$smoke=Join-Path $env:RUNNER_TEMP 'r49-runtime';New-Item -ItemType Directory -Force $smoke|Out-Null
$core=[Security.SecurityElement]::Escape((Join-Path $dist 'MerzoOptimizer.Core.dll'));$win=[Security.SecurityElement]::Escape((Join-Path $dist 'MerzoOptimizer.Windows.dll'))
@"
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup><Reference Include="MerzoOptimizer.Core"><HintPath>$core</HintPath><Private>true</Private></Reference><Reference Include="MerzoOptimizer.Windows"><HintPath>$win</HintPath><Private>true</Private></Reference></ItemGroup></Project>
"@|Set-Content (Join-Path $smoke 'Smoke.csproj') -Encoding UTF8
@'
using MerzoOptimizer.Core.Dispatching;using MerzoOptimizer.Core.Network;using MerzoOptimizer.Windows.Elevation;using MerzoOptimizer.Windows.Network;
internal static class Program{static async Task Main(){using var d=new AsyncOperationDispatcher(2);var v=await d.RunAsync("r49",_=>Task.FromResult(49));if(v!=49)throw new Exception("dispatcher generic");await d.RunAsync("void",_=>Task.CompletedTask);var p=Path.Combine(Path.GetTempPath(),"mwo-r49-net-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(p);await using var b=new ElevatedOperationBroker(p,p,p);INetworkRepairService n=new WindowsNetworkRepairService(b);var r=await n.DiagnoseAsync();Console.WriteLine("R49_DISPATCH_NETWORK_PASS "+r.Message);}}
'@|Set-Content (Join-Path $smoke 'Program.cs') -Encoding UTF8
dotnet run --project (Join-Path $smoke 'Smoke.csproj') -c Release
if($LASTEXITCODE-ne0){throw 'Dispatcher/network smoke failed'}

# Deterministic updater regression: primary releases endpoint returns 504 three times; tag fallback must find R49.
$ota=Join-Path $env:RUNNER_TEMP 'r49-ota';New-Item -ItemType Directory -Force $ota|Out-Null
$wp=[Security.SecurityElement]::Escape((Join-Path $root 'src\MerzoOptimizer.Windows\MerzoOptimizer.Windows.csproj'))
@"
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><ProjectReference Include="$wp" /></ItemGroup></Project>
"@|Set-Content (Join-Path $ota 'Ota.csproj') -Encoding UTF8
@'
using System.Net;using System.Text;using MerzoOptimizer.Windows.Updates;
internal sealed class F:HttpMessageHandler{public int N;protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage q,CancellationToken c){var u=q.RequestUri!.AbsoluteUri;if(u.Contains("/releases?per_page=20")){N++;return R(HttpStatusCode.GatewayTimeout,"{}");}if(u.Contains("/git/matching-refs/tags/mwo-v"))return R(HttpStatusCode.OK,"[{\"ref\":\"refs/tags/mwo-v0.1.49\"}]");if(u.Contains("/releases/tags/mwo-v0.1.49")){var h=new string('a',64);return R(HttpStatusCode.OK,"{\"tag_name\":\"mwo-v0.1.49\",\"draft\":false,\"prerelease\":false,\"name\":\"R49\",\"assets\":[{\"name\":\"MerzoWindowsOptimizerSetup-win-x64.exe\",\"browser_download_url\":\"https://github.com/Merzo4/my-app-updates/releases/download/mwo-v0.1.49/MerzoWindowsOptimizerSetup-win-x64.exe\",\"digest\":\"sha256:"+h+"\",\"size\":12345},{\"name\":\"MerzoWindowsOptimizerSetup-win-x64.exe.sha256\",\"browser_download_url\":\"https://github.com/Merzo4/my-app-updates/releases/download/mwo-v0.1.49/MerzoWindowsOptimizerSetup-win-x64.exe.sha256\",\"size\":106}]}");}return R(HttpStatusCode.NotFound,"{}");}static Task<HttpResponseMessage> R(HttpStatusCode s,string j)=>Task.FromResult(new HttpResponseMessage(s){Content=new StringContent(j,Encoding.UTF8,"application/json")});}
internal static class Program{static async Task Main(){var dir=Path.Combine(Path.GetTempPath(),Guid.NewGuid().ToString("N"));Directory.CreateDirectory(dir);var sp=Path.Combine(dir,"update_settings.json");File.WriteAllText(sp,"{\"auto_check\":true,\"auto_download\":false,\"auto_install\":false,\"provider\":\"GitHub\",\"repository_owner\":\"Merzo4\",\"repository_name\":\"my-app-updates\",\"release_tag_prefix\":\"mwo-v\",\"asset_name_contains\":\"MerzoWindowsOptimizerSetup-win-x64.exe\",\"installer_silent_args\":\"/SILENT\"}");var f=new F();using var svc=new GitHubUpdateService(sp,Path.Combine(dir,"updates"),f);var r=await svc.CheckAsync();if(!r.Success||!r.UpdateAvailable||r.LatestVersion!="0.1.49"||f.N!=3)throw new Exception($"Fallback failed success={r.Success} latest={r.LatestVersion} calls={f.N} msg={r.Message}");Console.WriteLine("R49_504_FALLBACK_PASS");}}
'@|Set-Content (Join-Path $ota 'Program.cs') -Encoding UTF8
dotnet run --project (Join-Path $ota 'Ota.csproj') -c Release
if($LASTEXITCODE-ne0){throw 'R49 OTA fallback smoke failed'}

# Finished production EXE must remain alive; this catches startup/XAML/composition failures.
$exe=Join-Path $dist 'MerzoWindowsOptimizer.exe'
$proc=Start-Process $exe -WorkingDirectory $dist -PassThru;Start-Sleep 20
if($proc.HasExited){throw "Finished EXE exited $($proc.ExitCode)"}
Stop-Process -Id $proc.Id -Force

# Package exactly what will be released.
$zip=Join-Path $root 'dist\MerzoWindowsOptimizer-portable-win-x64.zip';if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path (Join-Path $dist '*') -DestinationPath $zip -CompressionLevel Optimal
$iscc=@('C:\Program Files (x86)\Inno Setup 6\ISCC.exe','C:\Program Files\Inno Setup 6\ISCC.exe')|?{Test-Path $_}|Select-Object -First 1
if(-not$iscc){throw 'ISCC missing'}
Push-Location $root;try{& $iscc '/DMyAppVersion=0.1.49' '.\installer\MerzoWindowsOptimizer.iss';if($LASTEXITCODE-ne0){throw 'Installer failed'}}finally{Pop-Location}
$installer=Join-Path $root 'dist\MerzoWindowsOptimizerSetup-win-x64.exe'
$ih=(Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant();$zh=(Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$ih  MerzoWindowsOptimizerSetup-win-x64.exe"|Set-Content "$installer.sha256" -Encoding ascii
"$zh  MerzoWindowsOptimizer-portable-win-x64.zip"|Set-Content "$zip.sha256" -Encoding ascii
if((Get-Content "$installer.sha256" -Raw)-notmatch[regex]::Escape($ih)){throw 'Installer sidecar mismatch'}
if((Get-Content "$zip.sha256" -Raw)-notmatch[regex]::Escape($zh)){throw 'Portable sidecar mismatch'}

$notes=Join-Path $root 'dist\R49_RELEASE_NOTES.md'
@'
# R49 PUBLIC READY — CLEAN / GAME / EXTREME

- ЛАЙТ: чистый Пуск, максимально доступное ограничение privacy/telemetry, меньше consumer-рекомендаций и P2P Delivery Optimization, Explorer UX и OneDrive preflight.
- OneDrive: если аккаунт не настроен, приложение может быть штатно удалено только после Recovery Package; пользовательские файлы и папки Merzo не удаляет. При активной настройке решение всегда подтверждает пользователь.
- GAME: всё из ЛАЙТ + существующий gaming/performance stack, Power Throttling off и Gaming Network SAFE.
- EXTREME: всё из GAME + Game DVR off, более жёсткие services/tasks и Gaming Network EXTREME. Перед запуском обязательны Recovery Package и подтверждённая System Restore protection; иначе EXTREME блокируется.
- LAB / скрытые исправления: экспериментальные symptom-specific твики отделены от публичных сборок и не выбираются автоматически.
- Сохранены R46 security model, Snapshot/Undo и R48 resilient updater с 5xx/timeout fallback.
- Defender, Windows Update, Microsoft Store, IPv6 и pagefile публичные сборки автоматически не отключают.
'@|Set-Content $notes -Encoding UTF8

"R49_ROOT=$root" >> $env:GITHUB_ENV
"R49_INSTALLER_SHA=$ih" >> $env:GITHUB_ENV
"R49_PORTABLE_SHA=$zh" >> $env:GITHUB_ENV
Write-Host "R49_BUILD_GATE_PASS"
Write-Host "R49_INSTALLER_SHA256=$ih"
Write-Host "R49_PORTABLE_SHA256=$zh"
