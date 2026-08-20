$ErrorActionPreference='Stop'
$env:R52_TEMPLATE=(Resolve-Path '.\optimizer\scripts\r51_release_v2.ps1').Path
$env:R52_TMP=(Join-Path $env:RUNNER_TEMP 'r52_from_r51.ps1')
@'
import os
from pathlib import Path
src=Path(os.environ['R52_TEMPLATE']).read_text(encoding='utf-8-sig')
repls=[
("0.1.49','0.1.51","0.1.49','0.1.52"),
("Production R50','Production R51","Production R50','Production R52"),
('R51_RELEASE_NOTES.md','R52_RELEASE_NOTES.md'),
("'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py','r50_ui_reliability.py','r51_widgets_operation_readability.py')",
 "'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py','r50_ui_reliability.py','r51_widgets_operation_readability.py','r52_window_scroll_reliability.py','r52_finalize.py')"),
("'R49_FINALIZE.marker','R50_UI_RELIABILITY.marker','R51_STABILITY_READABILITY.marker']:",
 "'R49_FINALIZE.marker','R50_UI_RELIABILITY.marker','R51_STABILITY_READABILITY.marker','R52_WINDOW_SCROLL_RELIABILITY.marker','R52_FINALIZE.marker']:"),
('<AssemblyVersion>0.1.50.0</AssemblyVersion><FileVersion>0.1.50.0</FileVersion><InformationalVersion>0.1.50</InformationalVersion>',
 '<AssemblyVersion>0.1.51.0</AssemblyVersion><FileVersion>0.1.51.0</FileVersion><InformationalVersion>0.1.51</InformationalVersion>'),
('Production R51 · 0.1.51','Production R52 · 0.1.52'),
('R51_DISPATCH_NETWORK_PASS','R52_DISPATCH_NETWORK_PASS'),
("Write-Host 'R51_STABILITY_READABILITY_GATES_PASS'","Write-Host 'R52_BASE_GATES_PASS'")
]
for old,new in repls:
    if old not in src:
        raise SystemExit('R52 V3 template anchor missing: '+old[:100])
    src=src.replace(old,new,1)
Path(os.environ['R52_TMP']).write_text(src,encoding='utf-8')
print('R52 V3 template prepared')
'@ | python -
if($LASTEXITCODE-ne0){throw 'R52 V3 template preparation failed'}
& $env:R52_TMP
if($LASTEXITCODE-ne0){throw "R52 V3 base pipeline failed: $LASTEXITCODE"}
if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R52 SOURCE_ROOT missing'}

@'
import os,pathlib,re
r=pathlib.Path(os.environ['SOURCE_ROOT'])
x=(r/'src/MerzoOptimizer.App/MainWindow.xaml').read_text(encoding='utf-8-sig')
c=(r/'src/MerzoOptimizer.App/MainWindow.xaml.cs').read_text(encoding='utf-8-sig')
for token in ['Production R52 · 0.1.52','SourceInitialized="OnMainWindowSourceInitialized"','PreviewMouseWheel="OnGlobalPreviewMouseWheel"','x:Name="SidebarExpertExpander"','x:Name="SidebarNavScroll"','x:Name="BuildAdvancedScroll"']:
    assert token in x,token
for name in ['SidebarNavScroll','BuildAdvancedScroll','OperationEventScroll']:
    m=re.search(r'<ScrollViewer\b(?=[^>]*x:Name="'+re.escape(name)+r'")[^>]*>',x,re.S);assert m,name
    t=m.group(0)
    for a in ['VerticalScrollBarVisibility="Auto"','CanContentScroll="False"','PanningMode="VerticalOnly"','IsDeferredScrollingEnabled="False"']:
        assert a in t,(name,a)
for token in ['R52_WINDOW_SCROLL_BEGIN','EntryPoint = "MonitorFromWindow"','EntryPoint = "GetMonitorInfoW"','ApplyMonitorWorkArea','OnGlobalPreviewMouseWheel','R52TryScroll(BuildAdvancedScroll','R52TryScroll(SidebarNavScroll']:
    assert token in c,token
for marker in ['R52_WINDOW_SCROLL_RELIABILITY.marker','R52_FINALIZE.marker']:
    assert (r/marker).exists(),marker
print('R52_V3_SOURCE_PASS')
'@ | python -
if($LASTEXITCODE-ne0){throw 'R52 V3 source gate failed'}

$test=Join-Path $env:RUNNER_TEMP 'r52-v3-runtime'
Remove-Item $test -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $test|Out-Null
$app=[Security.SecurityElement]::Escape((Join-Path $env:SOURCE_ROOT 'src\MerzoOptimizer.App\MerzoOptimizer.App.csproj'))
@"
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><ProjectReference Include="$app" /></ItemGroup></Project>
"@|Set-Content (Join-Path $test 'Test.csproj') -Encoding UTF8
@'
using System.Runtime.InteropServices;using System.Windows;using System.Windows.Controls;using System.Windows.Interop;using System.Windows.Media;using MerzoOptimizer.App;
internal static class Program{
static FrameworkElement N(DependencyObject p,string n){if(p is FrameworkElement f&&f.Name==n)return f;for(int i=0;i<VisualTreeHelper.GetChildrenCount(p);i++){var r=N(VisualTreeHelper.GetChild(p,i),n);if(r!=null)return r;}return null!;}
static bool Inside(FrameworkElement c,FrameworkElement a){var p=c.TransformToAncestor(a).Transform(new Point(0,0));return p.X>=-3&&p.Y>=-3&&p.X+c.ActualWidth<=a.ActualWidth+3&&p.Y+c.ActualHeight<=a.ActualHeight+3;}
[DllImport("user32.dll")]static extern bool GetWindowRect(IntPtr h,out RECT r);[DllImport("user32.dll")]static extern IntPtr MonitorFromWindow(IntPtr h,uint f);[DllImport("user32.dll",EntryPoint="GetMonitorInfoW",CharSet=CharSet.Unicode)]static extern bool GetMonitorInfo(IntPtr h,ref MI i);
[StructLayout(LayoutKind.Sequential)]struct RECT{public int l,t,r,b;}[StructLayout(LayoutKind.Sequential)]struct MI{public int cb;public RECT monitor,work;public uint flags;}
[STAThread]static void Main(){var a=new App();a.InitializeComponent();a.ShutdownMode=ShutdownMode.OnExplicitShutdown;var w=new MainWindow{Width=920,Height=560,Left=100,Top=100,ShowInTaskbar=false,ShowActivated=false};w.Show();w.UpdateLayout();var tabs=(TabControl)N(w,"MainTabs");
var se=(Expander)N(w,"SidebarExpertExpander");var ss=(ScrollViewer)N(w,"SidebarNavScroll");se.IsExpanded=true;w.UpdateLayout();if(ss.ScrollableHeight>0.5){ss.ScrollToVerticalOffset(Math.Min(50,ss.ScrollableHeight));w.UpdateLayout();if(ss.VerticalOffset<=0.1)throw new Exception("sidebar scroll offset stuck");}
tabs.SelectedIndex=2;w.UpdateLayout();var be=(Expander)N(w,"BuildAdvancedExpander");be.IsExpanded=true;w.UpdateLayout();var bs=(ScrollViewer)N(w,"BuildAdvancedScroll");if(bs.ScrollableHeight<=0.5)throw new Exception("build advanced has no scroll range");bs.ScrollToVerticalOffset(Math.Min(70,bs.ScrollableHeight));w.UpdateLayout();if(bs.VerticalOffset<=0.1)throw new Exception("build advanced scroll offset stuck");
w.WindowState=WindowState.Maximized;w.UpdateLayout();var hwnd=new WindowInteropHelper(w).Handle;if(!GetWindowRect(hwnd,out var wr))throw new Exception("window rect failed");var mon=MonitorFromWindow(hwnd,2);var mi=new MI{cb=Marshal.SizeOf<MI>()};if(mon==IntPtr.Zero||!GetMonitorInfo(mon,ref mi))throw new Exception("monitor info failed");if(wr.l<mi.work.l-4||wr.t<mi.work.t-4||wr.r>mi.work.r+4||wr.b>mi.work.b+4)throw new Exception($"maximized outside work area {wr.l},{wr.t},{wr.r},{wr.b} vs {mi.work.l},{mi.work.t},{mi.work.r},{mi.work.b}");
for(int i=0;i<12;i++){tabs.SelectedIndex=i;w.UpdateLayout();var p=N(w,$"PageRoot{i}");if(p is null||p.ActualWidth<1||p.ActualHeight<1||!Inside(p,w))throw new Exception($"PageRoot{i} overflow maximized");}w.Close();a.Shutdown();Console.WriteLine("R52_V3_MAXIMIZE_SCROLL_PASS");}}
'@|Set-Content (Join-Path $test 'Program.cs') -Encoding UTF8
dotnet run --project (Join-Path $test 'Test.csproj') -c Release
if($LASTEXITCODE-ne0){throw 'R52 V3 runtime maximize/scroll failed'}

$notes=Join-Path $env:SOURCE_ROOT 'dist\R52_RELEASE_NOTES.md'
@'
# R52 WINDOW + SCROLL RELIABILITY
- Максимизация учитывает рабочую область текущего монитора и не перекрывает панель задач.
- Раскрытые Expander/меню прокручиваются колёсиком и ползунком; колесо маршрутизируется в ближайший доступный ScrollViewer.
- Заголовки «Экспертные инструменты» и «Дополнительно» тоже умеют направлять колесо в свой раскрытый контент.
- Runtime gate реально меняет VerticalOffset, максимизирует окно и проверяет все 12 страниц.
- R46 security, R48 OTA, R49 LIGHT/GAME/EXTREME/Recovery/OneDrive, R50 UI и R51 Widgets/readability сохранены.
'@|Set-Content $notes -Encoding UTF8
Write-Host 'R52_V3_ALL_GATES_PASS'
