$ErrorActionPreference='Stop'
$src=Get-Content '.\optimizer\scripts\r52_game_release_v2.ps1' -Raw

# R53 builds on the complete R51 pipeline + R52 window/scroll + corrected GAME WOW
# patch, then adds the R53 process/Clean Start layer before any build/test step.
$prev='<AssemblyVersion>0.1.51.0</AssemblyVersion><FileVersion>0.1.51.0</FileVersion><InformationalVersion>0.1.51</InformationalVersion>'
$prevPlaceholder='<AssemblyVersion>__R53_PREV__.0</AssemblyVersion><FileVersion>__R53_PREV__.0</FileVersion><InformationalVersion>__R53_PREV__</InformationalVersion>'
if(($src.Split($prev).Count-1)-ne1){throw 'R53 previous-client anchor mismatch'}
$src=$src.Replace($prev,$prevPlaceholder)
$src=$src.Replace('0.1.52','0.1.53')

# R53 Hotfix 1 is a four-part Windows/file version (0.1.53.1). The inherited
# R52 -> R51 -> R50 -> R49 generator promotes the old 0.1.49 source by a
# three-part string replacement, which naturally produces 0.1.53.0. Normalize
# only current-version checks/build arguments to .1 while the previous-client
# placeholder is still protected, so OTA smoke remains exactly 0.1.52.0.
$src=$src.Replace('0.1.53.0','0.1.53.1')
$src=$src.Replace("'Production R53 · 0.1.53'","'Production R53.1 · 0.1.53.1'")

# The deepest R50 step later reads pristine R49 and performs the actual
# 0.1.49 -> 0.1.53 promotion. Extend that generated replacement with a second,
# exact .53.0 -> .53.1 normalization and pass 0.1.53.1 to Build-Production.
$deepOld=@'
$replacement="`$src=`$src.Replace('0.1.49','0.1.53')"
'@.Trim()
$deepNew=@'
$replacement="`$src=`$src.Replace('0.1.49','0.1.53');`$src=`$src.Replace('0.1.53.0','0.1.53.1');`$src=`$src.Replace('-Version ''0.1.53''','-Version ''0.1.53.1''')"
'@.Trim()
if(($src.Split($deepOld).Count-1)-ne1){throw 'R53 HF1 deep version promotion anchor mismatch'}
$src=$src.Replace($deepOld,$deepNew)

$src=$src.Replace('__R53_PREV__','0.1.52')
$src=$src.Replace('Production R52','Production R53')
$src=$src.Replace('R52_RELEASE_NOTES.md','R53_RELEASE_NOTES.md')
$src=$src.Replace('R52 GAME WOW + UI RELIABILITY','R53 PROCESS + CLEAN START')

# Normalize the inherited R52 process target BEFORE the old script is written
# through generated PowerShell/UTF-8 layers. Match any single dash/mojibake
# separator instead of depending on one Unicode code point. This prevents the
# legacy source gate from turning 90-120 into 90�120 on hosted runners.
$src=[regex]::Replace($src,'90[^0-9\r\n]{1,4}120','80-100')

# R46 hardened ElevatedOperationBroker from one string to three string arguments.
# R52's read-only probe predates that constructor. It never executes an elevated
# operation, so three local probe directories are sufficient and keep the old
# regression gate meaningful without weakening production broker validation.
$oldProbe='new ElevatedOperationBroker(AppContext.BaseDirectory)'
$newProbe='new ElevatedOperationBroker(AppContext.BaseDirectory, AppContext.BaseDirectory, AppContext.BaseDirectory)'
if(($src.Split($oldProbe).Count-1)-ne1){throw 'R53 inherited broker probe anchor mismatch'}
$src=$src.Replace($oldProbe,$newProbe)

$old="'r52_window_scroll_reliability.py','r52_game_wow_debloat.py')"
$new="'r52_window_scroll_reliability.py','r52_game_wow_debloat_v3.py','r53_process_start_debloat.py')"
if(($src.Split($old).Count-1)-ne1){throw 'R53 patch-chain anchor mismatch'}
$src=$src.Replace($old,$new)

# R52/R51 keep their own marker checks. R53 has an explicit post-build marker
# gate below, avoiding a brittle textual dependency on the inherited marker list.

# Keep internal gate names unique so logs are easy to audit.
$src=$src.Replace('R52_V2_GAME_UI_SOURCE_PASS','R53_BASE_GAME_UI_SOURCE_PASS')
$src=$src.Replace('R52_V2_MAXIMIZE_SCROLL_PASS','R53_MAXIMIZE_SCROLL_PASS')
$src=$src.Replace('R52_V2_DEBLOAT_READONLY_PASS','R53_DEBLOAT_READONLY_PASS')
$src=$src.Replace('R52_V2_GAME_WOW_ALL_GATES_PASS','R53_BASE_GATES_PASS')

$tmp=Join-Path $env:RUNNER_TEMP 'r53_release_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp
if($LASTEXITCODE-ne0){throw "R53 expanded production pipeline failed: $LASTEXITCODE"}
if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R53 SOURCE_ROOT missing'}

# Exact R53/R53.1 source/security gates.
@'
import json, os, pathlib, re
r=pathlib.Path(os.environ['SOURCE_ROOT'])
vm=(r/'src/MerzoOptimizer.App/ViewModels/MainWindowViewModel.cs').read_text(encoding='utf-8-sig')
x=(r/'src/MerzoOptimizer.App/MainWindow.xaml').read_text(encoding='utf-8-sig')
g=(r/'src/MerzoOptimizer.Windows/Gaming/WindowsGamingDebloatService.cs').read_text(encoding='utf-8-sig')
h=(r/'src/MerzoOptimizer.ElevatedHelper/Program.cs').read_text(encoding='utf-8-sig')
items=json.loads((r/'data/tweaks.json').read_text(encoding='utf-8-sig'))
services=json.loads((r/'data/service_rules.json').read_text(encoding='utf-8-sig'))
byid={z.get('id'):z for z in items}

# UI identity/layout belongs in XAML. Process target text is runtime/reporting
# state and is validated in the ViewModel plus the dedicated R53 ASCII gate.
for t in ['Production R53.1 · 0.1.53.1','R53 PROCESS + CLEAN START','BuildAdvancedScroll','SidebarNavScroll']:
    assert t in x,t
for t in ['processTargetText','80-100','60-80','gamingDebloatRemoved','processCountBefore','processCountAfter','WalletService','TrkWks','WSearch','SysMain']:
    assert t in vm,t
assert '\\"готов\\"' not in vm, 'escaped quote regression returned to generated C#'
for tid in ['r53.start.hide_recent_documents','r53.start.disable_web_search_suggestions','r53.process.service_host_density']:
    assert tid in byid,tid
pd=byid['r53.process.service_host_density']
assert pd.get('risk')=='Advanced' and pd.get('requires_restart') is True
assert {'merzo_game','merzo_extreme'} <= set(pd.get('profile_tags') or [])
a=pd['registry_actions'][0]
assert a['hive']=='LocalMachine' and a['value_name']=='SvcHostSplitThresholdInKB' and a['integer_value']==67108864

svc={str(s.get('service_name','')).lower():s for s in services}
for name in ['walletservice','trkwks','lfsvc','wmpnetworksvc','wsearch','sysmain']:
    assert name in svc,name

for token in ['Microsoft.PowerAutomateDesktop','MicrosoftCorporationII.QuickAssist','XboxOptionalTargets','Microsoft.GamingApp','Microsoft.XboxApp']:
    assert token in g,token
for token in ['$hasXbox','$xboxOptional','Microsoft.XboxGamingOverlay','Microsoft.PowerAutomateDesktop','Microsoft.WindowsSoundRecorder','Microsoft.Todos']:
    assert token in h,token

# Never allow public GAME/EXTREME to cross critical boundaries.
for forbidden in ['Microsoft.WindowsStore','Microsoft.WindowsCalculator','Microsoft.WindowsNotepad','Microsoft.Paint','Microsoft.Windows.Photos','Microsoft.ScreenSketch','Microsoft.SecHealthUI','Microsoft.DesktopAppInstaller']:
    assert forbidden.lower() not in h.lower(),forbidden
for forbidden in ['Remove-AppxProvisionedPackage','-AllUsers']:
    assert forbidden.lower() not in h.lower(),forbidden
for fid in ['performance.keep_defender_advisory','performance.keep_windows_update_advisory','performance.keep_ipv6_advisory','performance.keep_pagefile_advisory','performance.keep_timer_advisory','performance.keep_tcp_magic_advisory']:
    z=byid.get(fid)
    if z: assert not ({'merzo_light','merzo_game','merzo_extreme'} & set(z.get('profile_tags') or [])),fid
assert (r/'R53_PROCESS_CLEAN_START.marker').exists()
assert (r/'R53_GAME_APPLY_HOTFIX.marker').exists()
print('R53_PROCESS_START_DEBLOAT_SOURCE_PASS')
'@ | python -
if($LASTEXITCODE-ne0){throw 'R53 source/security gate failed'}

# Packaged data must contain the new public behavior, not only generated source.
$portable=Join-Path $env:SOURCE_ROOT 'dist\MerzoWindowsOptimizer-portable-win-x64.zip'
if(!(Test-Path $portable)){throw 'R53 portable missing'}
$check=Join-Path $env:RUNNER_TEMP 'r53_portable_check'
Remove-Item $check -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive $portable $check -Force
$env:R53_PORTABLE_CHECK=$check
@'
import json, os, pathlib
r=pathlib.Path(os.environ['R53_PORTABLE_CHECK'])
items=json.loads((r/'data/tweaks.json').read_text(encoding='utf-8-sig'))
ids={z.get('id') for z in items}
for tid in ['r53.start.hide_recent_documents','r53.start.disable_web_search_suggestions','r53.process.service_host_density']:
    assert tid in ids,tid
print('R53_PACKAGED_PROCESS_START_PASS')
'@ | python -
if($LASTEXITCODE-ne0){throw 'R53 packaged data gate failed'}

# Re-check exact finished binary version.
$dist=Join-Path $env:SOURCE_ROOT 'dist\app'
foreach($n in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){
    $p=Join-Path $dist $n
    if(!(Test-Path $p)){throw "R53 missing $n"}
    $v=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString()
    if($v-ne'0.1.53.1'){throw "R53 HF1 $n version=$v"}
}

$notes=Join-Path $env:SOURCE_ROOT 'dist\R53_RELEASE_NOTES.md'
@'
# R53 PROCESS + CLEAN START

- GAME: целевой диапазон после перезагрузки и 2–3 минут простоя — 80-100 процессов. EXTREME: 60-80. Это ориентиры, а не искусственно подделываемые числа.
- Добавлен Process Density: часть Service Host снова группируется, что реально уменьшает количество отдельных svchost. Это не выдаётся за самостоятельный FPS-твик и может снижать изоляцию служб; Snapshot/Undo обязателен.
- Чистый Пуск усилен: недавние документы и web suggestions отключаются; consumer recommendations/silent installs остаются выключенными. Пользовательские закрепления программа не стирает.
- GAME Debloat реально удаляет allow-listed consumer Appx текущего пользователя. Добавлены Outlook(new), consumer Teams, Phone Link, People/Maps/Cortana, Dev Home, Power Automate Desktop и Quick Assist при наличии.
- Xbox/Game Bar части удаляются только если Xbox app/Game Pass не обнаружены. При установленном Xbox/Game Pass его стек сохраняется.
- EXTREME дополнительно чистит media/Family/ToDo consumer Appx и может отключить WSearch/SysMain/geolocation/media-sharing с явным риском и Recovery Package.
- Microsoft Store, Calculator, Notepad, Paint, Photos, Snipping Tool, Defender, Windows Update, IPv6 и pagefile не входят в destructive-allow-list.
- Сохранены R52 work-area/maximize + scroll fixes, R51 Widgets/readability, R49 Recovery/OneDrive и R48 OTA security.
'@ | Set-Content $notes -Encoding UTF8
Write-Host 'R53_PROCESS_CLEAN_START_ALL_GATES_PASS'