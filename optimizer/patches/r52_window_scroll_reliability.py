from pathlib import Path
import json, os, re

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)

# ---- identity ----
x=x.replace('Merzo Windows Optimizer — Production 0.1.51 · R51 STABILITY + READABILITY','Merzo Windows Optimizer — Production 0.1.52 · R52 WINDOW + SCROLL RELIABILITY')
x=x.replace('Production R51 · 0.1.51','Production R52 · 0.1.52')
x=x.replace('<TextBlock Text="R51" Foreground="{StaticResource Accent}"','<TextBlock Text="R52" Foreground="{StaticResource Accent}"',1)

# ---- window-level handlers ----
wm=re.search(r'<Window\b.*?>',x,re.S)
if not wm: raise SystemExit('R52 Window root missing')
tag=wm.group(0)
for attr in ['SourceInitialized="OnMainWindowSourceInitialized"','PreviewMouseWheel="OnGlobalPreviewMouseWheel"']:
    if attr not in tag:
        tag=tag[:-1]+' '+attr+'>'
x=x[:wm.start()]+tag+x[wm.end():]

# ---- strengthen every important scroll host ----
def enrich_named_scroll(text,name):
    pat=rf'<ScrollViewer\b(?=[^>]*x:Name="{re.escape(name)}")[^>]*>'
    m=re.search(pat,text,re.S)
    if not m: raise SystemExit(f'R52 scroll host missing: {name}')
    t=m.group(0)
    attrs=[
        'VerticalScrollBarVisibility="Auto"',
        'HorizontalScrollBarVisibility="Disabled"',
        'CanContentScroll="False"',
        'PanningMode="VerticalOnly"',
        'IsDeferredScrollingEnabled="False"'
    ]
    for a in attrs:
        key=a.split('=',1)[0]
        t=re.sub(rf'\s+{re.escape(key)}="[^"]*"','',t)
        t=t[:-1]+' '+a+'>'
    return text[:m.start()]+t+text[m.end():]

x=enrich_named_scroll(x,'SidebarNavScroll')
x=enrich_named_scroll(x,'BuildAdvancedScroll')
if 'x:Name="OperationEventScroll"' in x:
    x=enrich_named_scroll(x,'OperationEventScroll')

# Give the sidebar expander a stable runtime name for the regression probe.
x=x.replace('<Expander Header="Экспертные инструменты" Style="{StaticResource MerzoExpanderStyle}"',
            '<Expander x:Name="SidebarExpertExpander" Header="Экспертные инструменты" Style="{StaticResource MerzoExpanderStyle}"',1)

write(xp,x)

# ---- code-behind: per-monitor work area maximize + global nested wheel routing ----
cp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml.cs'
c=read(cp)
if 'R52_WINDOW_SCROLL_BEGIN' not in c:
    insert=r'''

    // R52_WINDOW_SCROLL_BEGIN
    private const int WmGetMinMaxInfo = 0x0024;
    private const uint MonitorDefaultToNearest = 0x00000002;

    private void OnMainWindowSourceInitialized(object? sender, EventArgs e)
    {
        if (System.Windows.PresentationSource.FromVisual(this) is System.Windows.Interop.HwndSource source)
            source.AddHook(R52WindowProc);
    }

    private IntPtr R52WindowProc(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == WmGetMinMaxInfo)
        {
            ApplyMonitorWorkArea(hwnd, lParam);
            handled = true;
        }
        return IntPtr.Zero;
    }

    private static void ApplyMonitorWorkArea(IntPtr hwnd, IntPtr lParam)
    {
        if (lParam == IntPtr.Zero) return;
        var mmi = System.Runtime.InteropServices.Marshal.PtrToStructure<R52MinMaxInfo>(lParam);
        var monitor = R52MonitorFromWindow(hwnd, MonitorDefaultToNearest);
        if (monitor != IntPtr.Zero)
        {
            var info = new R52MonitorInfo
            {
                cbSize = System.Runtime.InteropServices.Marshal.SizeOf<R52MonitorInfo>()
            };
            if (R52GetMonitorInfo(monitor, ref info))
            {
                var work = info.rcWork;
                var area = info.rcMonitor;
                mmi.ptMaxPosition.x = work.left - area.left;
                mmi.ptMaxPosition.y = work.top - area.top;
                mmi.ptMaxSize.x = work.right - work.left;
                mmi.ptMaxSize.y = work.bottom - work.top;
                mmi.ptMaxTrackSize.x = mmi.ptMaxSize.x;
                mmi.ptMaxTrackSize.y = mmi.ptMaxSize.y;
            }
        }
        System.Runtime.InteropServices.Marshal.StructureToPtr(mmi, lParam, true);
    }

    private void OnGlobalPreviewMouseWheel(object sender, System.Windows.Input.MouseWheelEventArgs e)
    {
        if (e.Handled) return;
        System.Windows.DependencyObject? current = e.OriginalSource as System.Windows.DependencyObject;
        System.Windows.Controls.ScrollViewer? firstScrollable = null;

        while (current is not null)
        {
            if (current is System.Windows.Controls.ScrollViewer sv && sv.ScrollableHeight > 0.5)
            {
                firstScrollable ??= sv;
                var canMove = e.Delta > 0 ? sv.VerticalOffset > 0.5 : sv.VerticalOffset < sv.ScrollableHeight - 0.5;
                if (canMove)
                {
                    var next = Math.Clamp(sv.VerticalOffset - (e.Delta / 3.0), 0, sv.ScrollableHeight);
                    sv.ScrollToVerticalOffset(next);
                    e.Handled = true;
                    return;
                }
            }
            current = R52GetUiParent(current);
        }

        // If the pointer is over a child that consumed layout space but the nearest
        // viewer is currently at an edge, keep the event unhandled so an outer viewer
        // can still process it normally.
        _ = firstScrollable;
    }

    private static System.Windows.DependencyObject? R52GetUiParent(System.Windows.DependencyObject child)
    {
        if (child is System.Windows.ContentElement ce)
        {
            var parent = System.Windows.ContentOperations.GetParent(ce);
            if (parent is not null) return parent;
            if (ce is System.Windows.FrameworkContentElement fce) return fce.Parent;
            return null;
        }
        try { return System.Windows.Media.VisualTreeHelper.GetParent(child); }
        catch (InvalidOperationException) { return null; }
    }

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    private static extern IntPtr R52MonitorFromWindow(IntPtr hwnd, uint flags);

    [System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Auto)]
    [return: System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.Bool)]
    private static extern bool R52GetMonitorInfo(IntPtr monitor, ref R52MonitorInfo info);

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    private struct R52Point { public int x; public int y; }

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    private struct R52MinMaxInfo
    {
        public R52Point ptReserved;
        public R52Point ptMaxSize;
        public R52Point ptMaxPosition;
        public R52Point ptMinTrackSize;
        public R52Point ptMaxTrackSize;
    }

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
    private struct R52Rect { public int left; public int top; public int right; public int bottom; }

    [System.Runtime.InteropServices.StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential, CharSet = System.Runtime.InteropServices.CharSet.Auto)]
    private struct R52MonitorInfo
    {
        public int cbSize;
        public R52Rect rcMonitor;
        public R52Rect rcWork;
        public uint dwFlags;
    }
    // R52_WINDOW_SCROLL_END
'''
    pos=c.rfind('}')
    if pos<0: raise SystemExit('R52 MainWindow class closing brace missing')
    c=c[:pos]+insert+'\n'+c[pos:]
write(cp,c)

# ---- consistent assembly/version identity ----
for p in (root/'src').rglob('*.csproj'):
    s=read(p).replace('0.1.51.0','0.1.52.0').replace('0.1.51','0.1.52')
    write(p,s)
app=root/'src'/'MerzoOptimizer.App'/'App.xaml.cs'
s=read(app).replace('0.1.51','0.1.52').replace('[Crash][R51]','[Crash][R52]').replace('Production R51','Production R52')
write(app,s)

# ---- release notes ----
rp=root/'data'/'release_notes.json'
try:
    data=json.loads(read(rp))
    entry={
      'version':'0.1.52',
      'title':'R52 WINDOW + SCROLL RELIABILITY',
      'changes':[
        'Исправлена максимизация borderless WPF-окна: теперь используется рабочая область конкретного монитора, поэтому низ приложения не уходит под панель задач.',
        'Исправлена прокрутка раскрытых меню/Expander: колёсико маршрутизируется к ближайшему реально прокручиваемому контейнеру.',
        'SidebarNavScroll, Дополнительно и Ход событий получили явный физический scrolling без CanContentScroll-конфликтов.',
        'Сохранены R46 security, R48 OTA, R49 три сборки/Recovery/OneDrive, R50 UI reliability и R51 Widgets/readability.'
      ]
    }
    if isinstance(data,list):
        data=[e for e in data if not(isinstance(e,dict) and e.get('version')=='0.1.52')]
        data.insert(0,entry)
    elif isinstance(data,dict) and isinstance(data.get('releases'),list):
        data['releases']=[e for e in data['releases'] if not(isinstance(e,dict) and e.get('version')=='0.1.52')]
        data['releases'].insert(0,entry)
    elif isinstance(data,dict):
        data['version']='0.1.52';data['title']=entry['title'];data['changes']=entry['changes']
    write(rp,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
except Exception as ex:
    raise SystemExit(f'R52 release notes failed: {ex}')

(root/'R52_WINDOW_SCROLL_RELIABILITY.marker').write_text('R52 WINDOW + SCROLL RELIABILITY\nper-monitor work area maximize + global nested wheel routing\n',encoding='utf-8')
print('R52 window/scroll reliability patch: OK')
