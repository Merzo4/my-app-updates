$ErrorActionPreference='Stop'
$src=Get-Content '.\optimizer\scripts\r51_release_v2.ps1' -Raw

# Promote proven R51 chain to R52.
$src=$src.Replace("`$replacement=\"`$src=`$src.Replace('0.1.49','0.1.51')\"","`$replacement=\"`$src=`$src.Replace('0.1.49','0.1.52')\"")
$src=$src.Replace("`$src=`$src.Replace('Production R50','Production R51')","`$src=`$src.Replace('Production R50','Production R52')")
$src=$src.Replace('R51_RELEASE_NOTES.md','R52_RELEASE_NOTES.md')

$old="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py','r50_ui_reliability.py','r51_widgets_operation_readability.py')"
$new="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py','r50_ui_reliability.py','r51_widgets_operation_readability.py','r52_window_scroll_reliability.py')"
if(($src.Split($old).Count-1)-ne1){throw 'R52 patch-chain anchor mismatch'}
$src=$src.Replace($old,$new)

$oldGate="'R49_FINALIZE.marker','R50_UI_RELIABILITY.marker','R51_STABILITY_READABILITY.marker']:"
$newGate="'R49_FINALIZE.marker','R50_UI_RELIABILITY.marker','R51_STABILITY_READABILITY.marker','R52_WINDOW_SCROLL_RELIABILITY.marker']:"
if(($src.Split($oldGate).Count-1)-ne1){throw 'R52 marker anchor mismatch'}
$src=$src.Replace($oldGate,$newGate)

# Previous-client OTA smoke must be installed R51 looking for R52.
$src=$src.Replace('<AssemblyVersion>0.1.50.0</AssemblyVersion><FileVersion>0.1.50.0</FileVersion><InformationalVersion>0.1.50</InformationalVersion>',
                  '<AssemblyVersion>0.1.51.0</AssemblyVersion><FileVersion>0.1.51.0</FileVersion><InformationalVersion>0.1.51</InformationalVersion>')
$src=$src.Replace('R51_DISPATCH_NETWORK_PASS','R52_DISPATCH_NETWORK_PASS')
$src=$src.Replace("Write-Host 'R51_STABILITY_READABILITY_GATES_PASS'","Write-Host 'R52_BASE_GATES_PASS'")

$tmp=Join-Path $env:RUNNER_TEMP 'r52_release_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp
if($LASTEXITCODE-ne0){throw "R52 expanded production pipeline failed: $LASTEXITCODE"}
if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R52 SOURCE_ROOT missing'}

# Source-level regression contract.
@'
import os,pathlib,re
r=pathlib.Path(os.environ['SOURCE_ROOT'])
x=(r/'src/MerzoOptimizer.App/MainWindow.xaml').read_text(encoding='utf-8-sig')
c=(r/'src/MerzoOptimizer.App/MainWindow.xaml.cs').read_text(encoding='utf-8-sig')
for token in ['Production R52 · 0.1.52','SourceInitialized="OnMainWindowSourceInitialized"','PreviewMouseWheel="OnGlobalPreviewMouseWheel"','x:Name="SidebarExpertExpander"','x:Name="SidebarNavScroll"','x:Name="BuildAdvancedScroll"']:
    assert token in x, token
for name in ['SidebarNavScroll','BuildAdvancedScroll','OperationEventScroll']:
    m=re.search(r'<ScrollViewer\b(?=[^>]*x:Name="'+re.escape(name)+r'")[^>]*>',x,re.S)
    assert m, name
    t=m.group(0)
    for a in ['VerticalScrollBarVisibility="Auto"','CanContentScroll="False"','PanningMode="VerticalOnly"','IsDeferredScrollingEnabled="False"']:
        assert a in t,(name,a)
for token in ['R52_WINDOW_SCROLL_BEGIN','WmGetMinMaxInfo','R52MonitorFromWindow','R52GetMonitorInfo','ApplyMonitorWorkArea','OnGlobalPreviewMouseWheel','ScrollToVerticalOffset','R52GetUiParent']:
    assert token in c,token
print('R52_WINDOW_SCROLL_SOURCE_PASS')
'@ | python -
if($LASTEXITCODE-ne0){throw 'R52 source regression gate failed'}

# Real WPF regression: expand, scroll, maximize, and keep all pages inside the working area.
$test=Join-Path $env:RUNNER_TEMP 'r52-window-scroll-test'
Remove-Item $test -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $test|Out-Null
$app=[Security.SecurityElement]::Escape((Join-Path $env:SOURCE_ROOT 'src\MerzoOptimizer.App\MerzoOptimizer.App.csproj'))
@"
<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><UseWPF>true</UseWPF><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><ProjectReference Include="$app" /></ItemGroup></Project>
"@ | Set-Content (Join-Path $test 'Test.csproj') -Encoding UTF8
@'
using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Interop;
using System.Windows.Media;
using MerzoOptimizer.App;

internal static class Program
{
    static FrameworkElement N(DependencyObject p,string n){if(p is FrameworkElement f&&f.Name==n)return f;for(int i=0;i<VisualTreeHelper.GetChildrenCount(p);i++){var r=N(VisualTreeHelper.GetChild(p,i),n);if(r!=null)return r;}return null!;}
    static bool Inside(FrameworkElement c,FrameworkElement a){var p=c.TransformToAncestor(a).Transform(new Point(0,0));return p.X>=-3&&p.Y>=-3&&p.X+c.ActualWidth<=a.ActualWidth+3&&p.Y+c.ActualHeight<=a.ActualHeight+3;}
    [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr hWnd,out RECT r);
    [DllImport("user32.dll")] static extern IntPtr MonitorFromWindow(IntPtr hWnd,uint flags);
    [DllImport("user32.dll")] static extern bool GetMonitorInfo(IntPtr h,ref MI i);
    [StructLayout(LayoutKind.Sequential)] struct RECT{public int left,top,right,bottom;}
    [StructLayout(LayoutKind.Sequential)] struct MI{public int cbSize;public RECT monitor,work;public uint flags;}

    [STAThread] static void Main()
    {
        var a=new App();a.InitializeComponent();a.ShutdownMode=ShutdownMode.OnExplicitShutdown;
        var w=new MainWindow{Width=920,Height=560,Left=100,Top=100,ShowInTaskbar=false,ShowActivated=false};
        w.Show();w.UpdateLayout();
        var tabs=(TabControl)N(w,"MainTabs");

        // Sidebar expander must create a real scrolling range at minimum size when needed.
        var sideExp=(Expander)N(w,"SidebarExpertExpander");var side=(ScrollViewer)N(w,"SidebarNavScroll");
        sideExp.IsExpanded=true;w.UpdateLayout();
        if(side.ScrollableHeight>0.5){side.ScrollToVerticalOffset(Math.Min(60,side.ScrollableHeight));w.UpdateLayout();if(side.VerticalOffset<=0.1)throw new Exception("sidebar expanded scrolling does not move");}

        // Builds advanced menu must definitely be scrollable and movable at minimum contract.
        tabs.SelectedIndex=2;w.UpdateLayout();
        var exp=(Expander)N(w,"BuildAdvancedExpander");exp.IsExpanded=true;w.UpdateLayout();
        var sv=(ScrollViewer)N(w,"BuildAdvancedScroll");
        if(sv.ScrollableHeight<=0.5)throw new Exception($"BuildAdvancedScroll has no scrolling range: {sv.ScrollableHeight}");
        sv.ScrollToVerticalOffset(Math.Min(80,sv.ScrollableHeight));w.UpdateLayout();
        if(sv.VerticalOffset<=0.1)throw new Exception("BuildAdvancedScroll offset did not move");

        // Maximize must respect the current monitor work area instead of covering taskbar.
        w.WindowState=WindowState.Maximized;w.UpdateLayout();
        var hwnd=new WindowInteropHelper(w).Handle;if(hwnd==IntPtr.Zero)throw new Exception("window hwnd missing");
        if(!GetWindowRect(hwnd,out var wr))throw new Exception("GetWindowRect failed");
        var mon=MonitorFromWindow(hwnd,2);var mi=new MI{cbSize=Marshal.SizeOf<MI>()};if(mon==IntPtr.Zero||!GetMonitorInfo(mon,ref mi))throw new Exception("monitor info failed");
        if(wr.left<mi.work.left-3||wr.top<mi.work.top-3||wr.right>mi.work.right+3||wr.bottom>mi.work.bottom+3)
            throw new Exception($"maximized window outside work area: window={wr.left},{wr.top},{wr.right},{wr.bottom} work={mi.work.left},{mi.work.top},{mi.work.right},{mi.work.bottom}");

        for(int i=0;i<12;i++){tabs.SelectedIndex=i;w.UpdateLayout();var page=N(w,$"PageRoot{i}");if(page is null||page.ActualWidth<1||page.ActualHeight<1||!Inside(page,w))throw new Exception($"PageRoot{i} overflow maximized");}
        w.Close();a.Shutdown();Console.WriteLine("R52_MAXIMIZE_SCROLL_RUNTIME_PASS");
    }
}
'@ | Set-Content (Join-Path $test 'Program.cs') -Encoding UTF8

dotnet run --project (Join-Path $test 'Test.csproj') -c Release
if($LASTEXITCODE-ne0){throw 'R52 maximize/scroll runtime gate failed'}

$notes=Join-Path $env:SOURCE_ROOT 'dist\R52_RELEASE_NOTES.md'
@'
# R52 WINDOW + SCROLL RELIABILITY

- Исправлено разворачивание на полный экран: borderless WPF-окно теперь учитывает рабочую область текущего монитора и не уходит под панель задач.
- Исправлена прокрутка при раскрытых меню/Expander: глобальный PreviewMouseWheel направляет колесо к ближайшему ScrollViewer, который реально может прокручиваться.
- Sidebar «Экспертные инструменты», «Сборки → Дополнительно» и «Ход событий» используют физическую прокрутку CanContentScroll=False + PanningMode=VerticalOnly.
- Добавлен runtime-gate: реально раскрывает меню, меняет VerticalOffset, максимизирует окно и проверяет все 12 PageRoot относительно monitor work area.
- R46 security, R48 OTA, R49 LIGHT/GAME/EXTREME + Recovery/OneDrive, R50 UI reliability и R51 Widgets/readability сохранены.
'@ | Set-Content $notes -Encoding UTF8
Write-Host 'R52_WINDOW_SCROLL_GATES_PASS'
