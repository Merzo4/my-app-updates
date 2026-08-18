from pathlib import Path
import os
root=Path(os.environ['SOURCE_ROOT'])
p=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml.cs'
s=p.read_text(encoding='utf-8-sig')

s=s.replace('[System.Runtime.InteropServices.DllImport("user32.dll")]\n    private static extern IntPtr R52MonitorFromWindow(IntPtr hwnd, uint flags);',
'''[System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint = "MonitorFromWindow")]\n    private static extern IntPtr R52MonitorFromWindow(IntPtr hwnd, uint flags);''')
s=s.replace('[System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Auto)]\n    [return: System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.Bool)]\n    private static extern bool R52GetMonitorInfo(IntPtr monitor, ref R52MonitorInfo info);',
'''[System.Runtime.InteropServices.DllImport("user32.dll", EntryPoint = "GetMonitorInfoW", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]\n    [return: System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.Bool)]\n    private static extern bool R52GetMonitorInfo(IntPtr monitor, ref R52MonitorInfo info);''')

old='''        // If the pointer is over a child that consumed layout space but the nearest\n        // viewer is currently at an edge, keep the event unhandled so an outer viewer\n        // can still process it normally.\n        _ = firstScrollable;\n    }\n\n    private static System.Windows.DependencyObject? R52GetUiParent'''
new='''        // Header/filler fallback: when the pointer is over the Expander header itself,\n        // it is not a descendant of the inner ScrollViewer. Route the wheel explicitly.\n        if (BuildAdvancedExpander is { IsExpanded: true, IsMouseOver: true } && R52TryScroll(BuildAdvancedScroll, e.Delta))\n        {\n            e.Handled = true;\n            return;\n        }\n        if (SidebarExpertExpander is { IsExpanded: true, IsMouseOver: true } && R52TryScroll(SidebarNavScroll, e.Delta))\n        {\n            e.Handled = true;\n            return;\n        }\n        _ = firstScrollable;\n    }\n\n    private static bool R52TryScroll(System.Windows.Controls.ScrollViewer? sv, int delta)\n    {\n        if (sv is null || sv.ScrollableHeight <= 0.5) return false;\n        var canMove = delta > 0 ? sv.VerticalOffset > 0.5 : sv.VerticalOffset < sv.ScrollableHeight - 0.5;\n        if (!canMove) return false;\n        var next = Math.Clamp(sv.VerticalOffset - (delta / 3.0), 0, sv.ScrollableHeight);\n        sv.ScrollToVerticalOffset(next);\n        return true;\n    }\n\n    private static System.Windows.DependencyObject? R52GetUiParent'''
if old not in s: raise SystemExit('R52 finalize wheel anchor missing')
s=s.replace(old,new,1)

for token in ['EntryPoint = "MonitorFromWindow"','EntryPoint = "GetMonitorInfoW"','R52TryScroll(BuildAdvancedScroll','R52TryScroll(SidebarNavScroll']:
    if token not in s: raise SystemExit('R52 finalize token missing: '+token)
p.write_text(s,encoding='utf-8')
(root/'R52_FINALIZE.marker').write_text('R52 FINALIZE\ncorrect Win32 entrypoints + Expander header wheel fallback\n',encoding='utf-8')
print('R52 finalize: OK')
