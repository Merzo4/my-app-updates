$ErrorActionPreference='Stop'
$src=Get-Content '.\optimizer\scripts\r49_release.ps1' -Raw

# Move the entire proven R49 production pipeline to 0.1.50 first.
$src=$src.Replace('0.1.49','0.1.50')
$src=$src.Replace("'Production R49'","'Production R50'")
$src=$src.Replace("dist\\R49_RELEASE_NOTES.md","dist\\R50_RELEASE_NOTES.md")

# Exact cumulative patch chain: keep R49 finalization, then apply only the R50 UI reliability patch.
$old="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py')"
$new="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py','r50_ui_reliability.py')"
if(($src.Split($old).Count-1)-ne1){throw 'R50 patch-chain anchor mismatch'}
$src=$src.Replace($old,$new)

$oldGate="for marker in ['R49_CATALOG.marker','R49_RECOVERY_ONEDRIVE_INFRA.marker','R49_BUILD_INTEGRATION.marker']:"
$newGate="for marker in ['R49_CATALOG.marker','R49_RECOVERY_ONEDRIVE_INFRA.marker','R49_BUILD_INTEGRATION.marker','R49_FINALIZE.marker','R50_UI_RELIABILITY.marker']:"
if(($src.Split($oldGate).Count-1)-ne1){throw 'R50 marker-gate anchor mismatch'}
$src=$src.Replace($oldGate,$newGate)

# R49 V6 already proved this harness correction: a WPF Application must not shut down
# after the first hidden window closes when we probe both supported window sizes.
$oldHarness='[STAThread]static void Main(){var a=new App();a.InitializeComponent();foreach(var s in new[]{(1000d,600d),(920d,560d)})'
$newHarness='[STAThread]static void Main(){var a=new App();a.InitializeComponent();a.ShutdownMode=ShutdownMode.OnExplicitShutdown;foreach(var s in new[]{(1000d,600d),(920d,560d)})'
if(($src.Split($oldHarness).Count-1)-ne1){throw 'R50 WPF harness anchor mismatch'}
$src=$src.Replace($oldHarness,$newHarness)

# Keep the read-only network smoke API-correct.
$oldNet='var r=await n.DiagnoseAsync();Console.WriteLine("R49_DISPATCH_NETWORK_PASS "+r.Message);'
$newNet='var r=await n.DiagnoseAsync();if(r is null)throw new Exception("network snapshot null");Console.WriteLine("R50_DISPATCH_NETWORK_PASS");'
if(($src.Split($oldNet).Count-1)-ne1){throw 'R50 network smoke anchor mismatch'}
$src=$src.Replace($oldNet,$newNet)

# Make the OTA regression test a real previous client (0.1.49) looking for 0.1.50.
$oldOta='<Nullable>enable</Nullable></PropertyGroup><ItemGroup><ProjectReference Include="$wp" /></ItemGroup></Project>'
$newOta='<Nullable>enable</Nullable><AssemblyVersion>0.1.49.0</AssemblyVersion><FileVersion>0.1.49.0</FileVersion><InformationalVersion>0.1.49</InformationalVersion></PropertyGroup><ItemGroup><ProjectReference Include="$wp" /></ItemGroup></Project>'
if(($src.Split($oldOta).Count-1)-ne1){throw 'R50 OTA previous-client anchor mismatch'}
$src=$src.Replace($oldOta,$newOta)

# Add a regression gate for the exact screenshot bug: open Advanced on Builds,
# require a real viewport and require scrollable content at both supported sizes.
$oldLayout='t.SelectedIndex=2;w.UpdateLayout();var bar=N(w,"OptimizationApplyBar");if(bar is null||!Inside(bar,w))throw new Exception("build action bar overflow");w.Close();'
$newLayout='t.SelectedIndex=2;w.UpdateLayout();var bar=N(w,"OptimizationApplyBar");if(bar is null||!Inside(bar,w))throw new Exception("build action bar overflow");var exp=N(w,"BuildAdvancedExpander") as Expander;var scroll=N(w,"BuildAdvancedScroll") as ScrollViewer;if(exp is null||scroll is null)throw new Exception("build advanced controls missing");exp.IsExpanded=true;w.UpdateLayout();if(!Inside(exp,w)||scroll.ActualHeight<20||scroll.ViewportHeight<=0||scroll.ScrollableHeight<=0)throw new Exception($"build advanced scroll broken at {s}: h={scroll.ActualHeight} viewport={scroll.ViewportHeight} scroll={scroll.ScrollableHeight}");w.Close();'
if(($src.Split($oldLayout).Count-1)-ne1){throw 'R50 advanced-scroll gate anchor mismatch'}
$src=$src.Replace($oldLayout,$newLayout)

# Source-level fail closed checks for the exact fixes.
$needle="for t in ['Width=\"1000\" Height=\"600\"','MinWidth=\"920\" MinHeight=\"560\"','Production 0.1.50','Production R50','Сборки Windows'"
if(-not $src.Contains($needle)){throw 'R50 production identity gate anchor missing'}
$src=$src.Replace("'Сборки Windows','Экспертные инструменты','Установить сборку','OptimizationApplyBar','Recovery Package','OneDrive']:","'Сборки Windows','Экспертные инструменты','Установить сборку','OptimizationApplyBar','Recovery Package','OneDrive','BuildAdvancedExpander','BuildAdvancedScroll','MerzoExpanderStyle']:")

$tmp=Join-Path $env:RUNNER_TEMP 'r50_release_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp
if($LASTEXITCODE-ne0){throw "R50 expanded release script failed: $LASTEXITCODE"}

# Replace inherited R49 notes with the actual R50 changes after all gates succeed.
$notes=Join-Path $env:R49_ROOT 'dist\R50_RELEASE_NOTES.md'
@'
# R50 UI RELIABILITY

- Исправлен реальный R49-баг страницы «Сборки»: раскрытый блок «Дополнительно» больше не обрезается нижней границей окна. Весь экспертный контент получил собственную вертикальную прокрутку.
- Добавлен отдельный runtime-gate: «Дополнительно» принудительно раскрывается на 1000×600 и 920×560; тест требует существующий viewport и реальный scrollable range.
- Белые системные круглые стрелки Expander заменены компактными Merzo-chevron в тёмном стиле.
- Исправлена отображаемая версия в шапке: Production R50 · 0.1.50.
- Длинные CPU и Power Plan остаются компактными, но полный текст доступен по наведению.
- Полностью сохранены R49 ЛАЙТ/GAME/EXTREME, OneDrive preflight, Recovery Package, R46 security и R48 resilient OTA updater.
'@|Set-Content $notes -Encoding UTF8
Write-Host 'R50_UI_RELIABILITY_GATES_PASS'
