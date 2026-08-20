$ErrorActionPreference='Stop'
$src=Get-Content '.\optimizer\scripts\r52_release.ps1' -Raw

# Add GAME WOW after the already-built R52 window/scroll fix, before build/gates run.
$old="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py','r50_ui_reliability.py','r51_widgets_operation_readability.py','r52_window_scroll_reliability.py')"
$new="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py','r50_ui_reliability.py','r51_widgets_operation_readability.py','r52_window_scroll_reliability.py','r52_game_wow_debloat.py')"
if(($src.Split($old).Count-1)-ne1){throw 'R52 GAME patch-chain anchor mismatch'}
$src=$src.Replace($old,$new)

$oldMarker="'R49_FINALIZE.marker','R50_UI_RELIABILITY.marker','R51_STABILITY_READABILITY.marker','R52_WINDOW_SCROLL_RELIABILITY.marker']:"
$newMarker="'R49_FINALIZE.marker','R50_UI_RELIABILITY.marker','R51_STABILITY_READABILITY.marker','R52_WINDOW_SCROLL_RELIABILITY.marker','R52_GAME_WOW.marker']:"
if(($src.Split($oldMarker).Count-1)-ne1){throw 'R52 GAME marker anchor mismatch'}
$src=$src.Replace($oldMarker,$newMarker)

$tmp=Join-Path $env:RUNNER_TEMP 'r52_game_release_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp
if($LASTEXITCODE-ne0){throw "R52 base/window pipeline failed: $LASTEXITCODE"}
if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R52 SOURCE_ROOT missing'}

# GAME WOW safety and product gates.
@'
import json, os, pathlib
r=pathlib.Path(os.environ['SOURCE_ROOT'])
vm=(r/'src/MerzoOptimizer.App/ViewModels/MainWindowViewModel.cs').read_text(encoding='utf-8-sig')
h=(r/'src/MerzoOptimizer.ElevatedHelper/Program.cs').read_text(encoding='utf-8-sig')
g=(r/'src/MerzoOptimizer.Windows/Gaming/WindowsGamingDebloatService.cs').read_text(encoding='utf-8-sig')
core=(r/'src/MerzoOptimizer.Core/Elevation/ElevationModels.cs').read_text(encoding='utf-8-sig')
x=(r/'src/MerzoOptimizer.App/MainWindow.xaml').read_text(encoding='utf-8-sig')
for t in ['GamingDebloat','Gaming Debloat','processCountBefore','processCountAfter','gamingDebloatRemoved','90–120']:
    assert t in vm,t
assert 'GamingDebloat' in core
for t in ['GamingDebloatAsync','Remove-AppxPackage','Microsoft.MicrosoftSolitaireCollection','Microsoft.OutlookForWindows','Microsoft.YourPhone']:
    assert t in h,t
for t in ['IGamingDebloatService','InspectAsync','XboxGamingInstalled','LightTargets','GameTargets','ExtremeTargets']:
    assert t in g,t
for forbidden in ['Remove-AppxProvisionedPackage','-AllUsers','Microsoft.WindowsStore','Microsoft.WindowsCalculator','Microsoft.WindowsNotepad','Microsoft.Paint','Microsoft.Windows.Photos','Microsoft.ScreenSketch','Microsoft.SecHealthUI','Microsoft.DesktopAppInstaller']:
    assert forbidden.lower() not in h.lower(), 'protected/destructive token in helper: '+forbidden
forbidden_cmd=['Directory.Delete','File.Delete','Remove-Item','rd /s','rmdir']
for t in forbidden_cmd: assert t not in h[h.index('GamingDebloatAsync'):h.index('RunFixedPowerShellAsync',h.index('GamingDebloatAsync'))],t
items=json.loads((r/'data/tweaks.json').read_text(encoding='utf-8-sig'))
for item in items:
    tags=set(item.get('profile_tags') or [])
    if 'process_aggressive' in tags and not item.get('scan_only'):
        assert 'merzo_game' in tags, 'GAME missing process_aggressive '+item.get('id','?')
for fid in ['performance.keep_defender_advisory','performance.keep_windows_update_advisory','performance.keep_ipv6_advisory','performance.keep_pagefile_advisory','performance.keep_timer_advisory','performance.keep_tcp_magic_advisory']:
    item=next((z for z in items if z.get('id')==fid),None)
    if item: assert not({'merzo_light','merzo_game','merzo_extreme'} & set(item.get('profile_tags') or [])),fid
assert 'R52 GAME WOW + UI RELIABILITY' in x
assert (r/'R52_GAME_WOW.marker').exists()
print('R52_GAME_WOW_SOURCE_PASS')
'@ | python -
if($LASTEXITCODE-ne0){throw 'R52 GAME source/safety gate failed'}

# Read-only Appx inspection on the clean runner. Mutation is intentionally not invoked in CI.
$probe=Join-Path $env:RUNNER_TEMP 'r52-game-probe';Remove-Item $probe -Recurse -Force -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force $probe|Out-Null
$win=[Security.SecurityElement]::Escape((Join-Path $env:SOURCE_ROOT 'src\MerzoOptimizer.Windows\MerzoOptimizer.Windows.csproj'))
@"
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup><ProjectReference Include="$win" /></ItemGroup></Project>
"@|Set-Content (Join-Path $probe 'Probe.csproj') -Encoding UTF8
@'
using MerzoOptimizer.Windows.Gaming;using MerzoOptimizer.Windows.Elevation;
internal static class Program{static async Task Main(){await using var broker=new ElevatedOperationBroker(AppContext.BaseDirectory);var svc=new WindowsGamingDebloatService(broker);foreach(var mode in new[]{"LIGHT","GAME","EXTREME"}){var r=await svc.InspectAsync(mode);if(r.RemovableCount<0)throw new Exception();Console.WriteLine($"{mode} removable={r.RemovableCount} xbox={r.XboxGamingInstalled}");}Console.WriteLine("R52_GAME_DEBLOAT_READONLY_PASS");}}
'@|Set-Content (Join-Path $probe 'Program.cs') -Encoding UTF8
dotnet run --project (Join-Path $probe 'Probe.csproj') -c Release
if($LASTEXITCODE-ne0){throw 'R52 GAME read-only Appx probe failed'}

# Build output must really contain R52 assemblies and the new service.
$dist=Join-Path $env:SOURCE_ROOT 'dist\app'
foreach($name in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){
 $p=Join-Path $dist $name;if(!(Test-Path $p)){throw "Missing $name"};$v=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString();if($v-ne'0.1.52.0'){throw "$name stale $v"}
}
if(!(Test-Path (Join-Path $env:SOURCE_ROOT 'src\MerzoOptimizer.Windows\Gaming\WindowsGamingDebloatService.cs'))){throw 'Gaming Debloat service missing'}

$notes=Join-Path $env:SOURCE_ROOT 'dist\R52_RELEASE_NOTES.md'
@'
# R52 GAME WOW + UI RELIABILITY

- GAME 2.0 теперь делает реальный Gaming Debloat, а не только audit: удаляет фиксированный allow-list Microsoft consumer Appx текущего пользователя. Пользовательские Win32-программы и защищённые системные приложения не затрагиваются.
- ЛАЙТ очищает очевидный consumer-bloat; GAME дополнительно убирает Outlook(new), consumer Teams, Phone Link, People/Maps/Cortana при наличии; EXTREME расширяет список.
- GAME включает reviewed process_aggressive rules и больше известных фоновых источников. Xbox-службы отключаются только если Xbox/Game Pass не обнаружен.
- Перед Appx removal обязателен Recovery Package/System Restore; без него destructive-этап LIGHT/GAME пропускается, EXTREME блокируется.
- Результат показывает реальное число процессов ДО → ПОСЛЕ. Ориентир GAME ~90–120 после reboot на чистой Windows — цель, а не обещание: драйверы/антивирус/используемые функции влияют на итог.
- Исправлены два общих UI-регресса: максимизация уважает taskbar/work area, а раскрытые Expander/экспертные области реально прокручиваются.
- Сохранены R46 security, R48 OTA, R49 Recovery/OneDrive, R50 UI reliability и R51 Widgets/readability.
'@|Set-Content $notes -Encoding UTF8

Write-Host 'R52_GAME_WOW_ALL_GATES_PASS'
