from pathlib import Path
import os,re
root=Path(os.environ['SOURCE_ROOT'])

# R23 uses native WindowChrome. Remove the stale XAML event hook as well as the old method.
xaml=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=xaml.read_text(encoding='utf-8-sig')
x=re.sub(r'\s+MouseLeftButtonDown="TitleBar_MouseLeftButtonDown"', '', x)
xaml.write_text(x,encoding='utf-8')

# Some production source revisions expose an InstallUpdateCommand in addition to DownloadUpdateCommand.
# Route that legacy command into the new verified download/install flow.
vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s=vm.read_text(encoding='utf-8-sig')
if 'InstallUpdateAsync' in s and 'private Task InstallUpdateAsync()' not in s:
    marker='    private async Task DownloadUpdateAsync()\n'
    if marker not in s:
        raise SystemExit('DownloadUpdateAsync marker missing')
    s=s.replace(marker, '    private Task InstallUpdateAsync() => DownloadUpdateAsync();\n\n'+marker, 1)
vm.write_text(s,encoding='utf-8')

if 'MouseLeftButtonDown="TitleBar_MouseLeftButtonDown"' in xaml.read_text(encoding='utf-8'):
    raise SystemExit('Stale titlebar event hook remains')
final=vm.read_text(encoding='utf-8')
if 'InstallUpdateAsync' in final and 'private Task InstallUpdateAsync() => DownloadUpdateAsync();' not in final:
    raise SystemExit('Legacy InstallUpdateCommand is not bridged')
print('R24 compile compatibility patch: OK')
