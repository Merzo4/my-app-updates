$ErrorActionPreference='Stop'
$src=Get-Content '.\optimizer\scripts\r51_release_v2.ps1' -Raw

$old=@'
$replacement="`$src=`$src.Replace('0.1.49','0.1.51')"
'@.Trim()
$new=@'
$replacement="`$src=`$src.Replace('0.1.49','0.1.52')"
'@.Trim()
if(($src.Split($old).Count-1)-ne1){throw 'R52 V2 version promotion anchor mismatch'}
$src=$src.Replace($old,$new)

$old=@'
$src=$src.Replace('Production R50','Production R51')
'@.Trim()
$new=@'
$src=$src.Replace('Production R50','Production R52')
'@.Trim()
if(($src.Split($old).Count-1)-ne1){throw 'R52 V2 production label anchor mismatch'}
$src=$src.Replace($old,$new)

$old=@'
$src=$src.Replace('R50_RELEASE_NOTES.md','R51_RELEASE_NOTES.md')
'@.Trim()
$new=@'
$src=$src.Replace('R50_RELEASE_NOTES.md','R52_RELEASE_NOTES.md')
'@.Trim()
if(($src.Split($old).Count-1)-ne1){throw 'R52 V2 notes anchor mismatch'}
$src=$src.Replace($old,$new)

$old="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py','r50_ui_reliability.py','r51_widgets_operation_readability.py')"
$new="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py','r50_ui_reliability.py','r51_widgets_operation_readability.py','r52_window_scroll_reliability.py','r52_game_wow_debloat.py')"
if(($src.Split($old).Count-1)-ne1){throw 'R52 V2 patch chain anchor mismatch'}
$src=$src.Replace($old,$new)

$old="'R49_FINALIZE.marker','R50_UI_RELIABILITY.marker','R51_STABILITY_READABILITY.marker']:"
$new="'R49_FINALIZE.marker','R50_UI_RELIABILITY.marker','R51_STABILITY_READABILITY.marker','R52_WINDOW_SCROLL_RELIABILITY.marker','R52_GAME_WOW.marker']:"
if(($src.Split($old).Count-1)-ne1){throw 'R52 V2 marker anchor mismatch'}
$src=$src.Replace($old,$new)

$old=@'
$newPrev='<AssemblyVersion>0.1.50.0</AssemblyVersion><FileVersion>0.1.50.0</FileVersion><InformationalVersion>0.1.50</InformationalVersion>'
'@.Trim()
$new=@'
$newPrev='<AssemblyVersion>0.1.51.0</AssemblyVersion><FileVersion>0.1.51.0</FileVersion><InformationalVersion>0.1.51</InformationalVersion>'
'@.Trim()
if(($src.Split($old).Count-1)-ne1){throw 'R52 V2 previous client anchor mismatch'}
$src=$src.Replace($old,$new)

$src=$src.Replace('R51_DISPATCH_NETWORK_PASS','R52_DISPATCH_NETWORK_PASS')
$src=$src.Replace('R51_BASE_GATES_PASS','R52_BASE_GATES_PASS')
$src=$src.Replace("'Production R51 · 0.1.51'","'Production R52 · 0.1.52'")
$src=$src.Replace('dist\R51_RELEASE_NOTES.md','dist\R52_RELEASE_NOTES.md')
$src=$src.Replace("Write-Host 'R51_STABILITY_READABILITY_GATES_PASS'","Write-Host 'R52_BASE_PLUS_R51_GATES_PASS'")

$tmp=Join-Path $env:RUNNER_TEMP 'r52_game_release_v2_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp
if($LASTEXITCODE-ne0){throw "R52 V2 cumulative production pipeline failed: $LASTEXITCODE"}
if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R52 V2 SOURCE_ROOT missing'}

# R52 exact source/security gates.
@'
import json, os, pathlib, re
r=pathlib.Path(os.environ['SOURCE_ROOT'])
x=(r/'src/MerzoOptimizer.App/MainWindow.xaml').read_text(encoding='utf-8-sig')
c=(r/'src/MerzoOptimizer.App/MainWindow.xaml.cs').read_text(encoding='utf-8-sig')
vm=(r/'src/MerzoOptimizer.App/ViewModels/MainWindowViewModel.cs').read_text(encoding='utf-8-sig')
core=(r/'src/MerzoOptimizer.Core/Elevation/ElevationModels.cs').read_text(encoding='utf-8-sig')
h=(r/'src/MerzoOptimizer.ElevatedHelper/Program.cs').read_text(encoding='utf-8-sig')
g=(r/'src/MerzoOptimizer.Windows/Gaming/WindowsGamingDebloatService.cs').read_text(encoding='utf-8-sig')

for t in ['Production R52 · 0.1.52','SourceInitialized="OnMainWindowSourceInitialized"','PreviewMouseWheel="OnGlobalPreviewMouseWheel"','BuildAdvancedScroll','SidebarExpertExpander','OperationEventScroll','R52 GAME WOW + UI RELIABILITY']:
    assert t in x,t
for t in ['R52_WINDOW_SCROLL_BEGIN','WmGetMinMaxInfo','R52MonitorFromWindow','R52GetMonitorInfo','ApplyMonitorWorkArea','OnGlobalPreviewMouseWheel','ScrollToVerticalOffset']:
    assert t in c,t
for t in ['GamingDebloat','Gaming Debloat','processCountBefore','processCountAfter','gamingDebloatRemoved','90–120']:
    assert t in vm,t
assert 'GamingDebloat' in core
for t in ['GamingDebloatAsync','Remove-AppxPackage','Microsoft.MicrosoftSolitaireCollection','Microsoft.OutlookForWindows','Microsoft.YourPhone']:
    assert t in h,t
for t in ['IGamingDebloatService','InspectAsync','XboxGamingInstalled','LightTargets','GameTargets','ExtremeTargets']:
    assert t in g,t

for forbidden in ['Remove-AppxProvisionedPackage','-AllUsers','Microsoft.WindowsStore','Microsoft.WindowsCalculator','Microsoft.WindowsNotepad','Microsoft.Paint','Microsoft.Windows.Photos','Microsoft.ScreenSketch','Microsoft.SecHealthUI','Microsoft.DesktopAppInstaller']:
    assert forbidden.lower() not in h.lower(), 'protected/destructive helper token: '+forbidden
segment=h[h.index('GamingDebloatAsync'):h.index('RunFixedPowerShellAsync',h.index('GamingDebloatAsync'))]
for forbidden in ['Directory.Delete','File.Delete','Remove-Item','rmdir','rd /s']:
    assert forbidden not in segment,forbidden

items=json.loads((r/'data/tweaks.json').read_text(encoding='utf-8-sig'))
for item in items:
    tags=set(item.get('profile_tags') or [])
    if 'process_aggressive' in tags and not item.get('scan_only'):
        assert 'merzo_game' in tags,'GAME missing process_aggressive '+item.get('id','?')
for fid in ['performance.keep_defender_advisory','performance.keep_windows_update_advisory','performance.keep_ipv6_advisory','performance.keep_pagefile_advisory','performance.keep_timer_advisory','performance.keep_tcp_magic_advisory']:
    item=next((z for z in items if z.get('id')==fid),None)
    if item: assert not({'merzo_light','merzo_game','merzo_extreme'} & set(item.get('profile_tags') or [])),fid
for marker in ['R52_WINDOW_SCROLL_RELIABILITY.marker','R52_GAME_WOW.marker']:
    assert (r/marker).exists(),marker
print('R52_V2_GAME_UI_SOURCE_PASS')
'@ | python -
if($LASTEXITCODE-ne0){throw 'R52 V2 source/security gates failed'}

# WPF runtime: expand+scroll both areas and maximize inside real monitor work area.
$test=Join-Path $env:RUNNER_TEMP 'r52-v2-ui';Remove-Item $test -Recurse -Force -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force $test|Out-Null
$app=[Security.SecurityElement]::Escape((Join-Path $env:SOURCE_ROOT 'src\MerzoOptimizer.App\MerzoOptimizer.App.csproj'))
@"
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><ProjectReference Include="$app" /></ItemGroup></Project>
"@|Set-Content (Join-Path $test 'Test.csproj') -Encoding UTF8
@'
using System.Runtime.InteropServices;using System.Windows;using System.Windows.Controls;using System.Windows.Interop;using System.Windows.Media;using MerzoOptimizer.App;
internal static class Program{
 static FrameworkElement N(DependencyObject p,string n){if(p is FrameworkElement f&&f.Name==n)return f;for(int i=0;i<VisualTreeHelper.GetChildrenCount(p);i++){var r=N(VisualTreeHelper.GetChild(p,i),n);if(r!=null)return r;}return null!;}
 [DllImport("user32.dll")]static extern bool GetWindowRect(IntPtr h,out RECT r);[DllImport("user32.dll")]static extern IntPtr MonitorFromWindow(IntPtr h,uint f);[DllImport("user32.dll")]static extern bool GetMonitorInfo(IntPtr h,ref MI i);[StructLayout(LayoutKind.Sequential)]struct RECT{public int l,t,r,b;}[StructLayout(LayoutKind.Sequential)]struct MI{public int cb;public RECT mon,work;public uint flags;}
 [STAThread]static void Main(){var a=new App{ShutdownMode=ShutdownMode.OnExplicitShutdown};a.InitializeComponent();var w=new MainWindow{Width=920,Height=560,Left=60,Top=60,ShowInTaskbar=false};w.Show();w.UpdateLayout();var tabs=(TabControl)N(w,"MainTabs");
 tabs.SelectedIndex=2;w.UpdateLayout();var exp=(Expander)N(w,"BuildAdvancedExpander");exp.IsExpanded=true;w.UpdateLayout();var sv=(ScrollViewer)N(w,"BuildAdvancedScroll");if(sv.ScrollableHeight<=0.5)throw new Exception("advanced no range");sv.ScrollToVerticalOffset(Math.Min(80,sv.ScrollableHeight));w.UpdateLayout();if(sv.VerticalOffset<=0.1)throw new Exception("advanced offset");
 var se=(Expander)N(w,"SidebarExpertExpander");se.IsExpanded=true;w.UpdateLayout();var ss=(ScrollViewer)N(w,"SidebarNavScroll");if(ss.ScrollableHeight>0.5){ss.ScrollToVerticalOffset(Math.Min(60,ss.ScrollableHeight));w.UpdateLayout();if(ss.VerticalOffset<=0.1)throw new Exception("sidebar offset");}
 w.WindowState=WindowState.Maximized;w.UpdateLayout();var hwnd=new WindowInteropHelper(w).Handle;if(!GetWindowRect(hwnd,out var wr))throw new Exception("window rect");var mon=MonitorFromWindow(hwnd,2);var mi=new MI{cb=Marshal.SizeOf<MI>()};if(mon==IntPtr.Zero||!GetMonitorInfo(mon,ref mi))throw new Exception("monitor info");if(wr.l<mi.work.l-3||wr.t<mi.work.t-3||wr.r>mi.work.r+3||wr.b>mi.work.b+3)throw new Exception($"outside work area {wr.l},{wr.t},{wr.r},{wr.b} vs {mi.work.l},{mi.work.t},{mi.work.r},{mi.work.b}");
 for(int i=0;i<12;i++){tabs.SelectedIndex=i;w.UpdateLayout();var p=N(w,$"PageRoot{i}");var pt=p.TransformToAncestor(w).Transform(new Point());if(pt.Y+p.ActualHeight>w.ActualHeight+3)throw new Exception($"page {i} bottom overflow");}w.Close();a.Shutdown();Console.WriteLine("R52_V2_MAXIMIZE_SCROLL_PASS");}}
'@|Set-Content (Join-Path $test 'Program.cs') -Encoding UTF8
dotnet run --project (Join-Path $test 'Test.csproj') -c Release
if($LASTEXITCODE-ne0){throw 'R52 V2 maximize/scroll gate failed'}

# Read-only Appx inspect: prove service runs without invoking mutation.
$probe=Join-Path $env:RUNNER_TEMP 'r52-v2-debloat';Remove-Item $probe -Recurse -Force -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force $probe|Out-Null
$win=[Security.SecurityElement]::Escape((Join-Path $env:SOURCE_ROOT 'src\MerzoOptimizer.Windows\MerzoOptimizer.Windows.csproj'))
@"
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings></PropertyGroup><ItemGroup><ProjectReference Include="$win" /></ItemGroup></Project>
"@|Set-Content (Join-Path $probe 'Probe.csproj') -Encoding UTF8
@'
using MerzoOptimizer.Windows.Gaming;using MerzoOptimizer.Windows.Elevation;
internal static class Program{static async Task Main(){await using var b=new ElevatedOperationBroker(AppContext.BaseDirectory);var s=new WindowsGamingDebloatService(b);foreach(var m in new[]{"LIGHT","GAME","EXTREME"}){var r=await s.InspectAsync(m);if(r.RemovableCount<0)throw new Exception();Console.WriteLine($"{m}: {r.RemovableCount}; xbox={r.XboxGamingInstalled}");}Console.WriteLine("R52_V2_DEBLOAT_READONLY_PASS");}}
'@|Set-Content (Join-Path $probe 'Program.cs') -Encoding UTF8
dotnet run --project (Join-Path $probe 'Probe.csproj') -c Release
if($LASTEXITCODE-ne0){throw 'R52 V2 read-only debloat gate failed'}

# Final packaged binary identity.
$dist=Join-Path $env:SOURCE_ROOT 'dist\app';foreach($n in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){$p=Join-Path $dist $n;if(!(Test-Path $p)){throw "missing $n"};$v=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString();if($v-ne'0.1.52.0'){throw "$n version $v"}}

$notes=Join-Path $env:SOURCE_ROOT 'dist\R52_RELEASE_NOTES.md'
@'
# R52 GAME WOW + UI RELIABILITY

- GAME 2.0 выполняет реальный allow-listed Gaming Debloat: Microsoft consumer Appx удаляются для текущего пользователя; Win32-программы и защищённые системные приложения не затрагиваются.
- LIGHT чистит очевидный consumer-bloat; GAME дополнительно убирает Outlook(new), consumer Teams, Phone Link, People/Maps/Cortana при наличии; EXTREME расширяет список.
- GAME включает reviewed process_aggressive rules и дополнительные известные фоновые источники. Xbox-службы сохраняются, если обнаружен Xbox/Game Pass.
- Перед Appx removal обязателен Recovery Package/System Restore. При его отсутствии destructive-этап LIGHT/GAME пропускается; EXTREME блокируется.
- После применения отображается реальное число процессов ДО → ПОСЛЕ; цель GAME ~90–120 после reboot на чистой Windows не является гарантией.
- Максимизация учитывает monitor work area/taskbar; раскрытые Expander и экспертные области реально прокручиваются.
- Сохранены R46 security, R48 OTA, R49 Recovery/OneDrive, R50 UI reliability и R51 Widgets/readability.
'@|Set-Content $notes -Encoding UTF8
Write-Host 'R52_V2_GAME_WOW_ALL_GATES_PASS'
