from pathlib import Path
import os

root=Path(os.environ['SOURCE_ROOT'])
store=root/'src'/'MerzoOptimizer.App'/'Audit'/'AuditStateStore.cs'
s=store.read_text(encoding='utf-8-sig')
if 'using System.IO;' not in s:
    s='using System.IO;\n'+s
store.write_text(s,encoding='utf-8')

vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
v=vm.read_text(encoding='utf-8-sig')
v=v.replace('x.FullPath.Contains(pattern, StringComparison.OrdinalIgnoreCase)', 'x.Snapshot.FullPath.Contains(pattern, StringComparison.OrdinalIgnoreCase)')
vm.write_text(v,encoding='utf-8')

if 'using System.IO;' not in store.read_text(encoding='utf-8'):
    raise SystemExit('AuditStateStore System.IO fix missing')
if 'x.FullPath.Contains(pattern' in vm.read_text(encoding='utf-8'):
    raise SystemExit('Scheduled task FullPath fix missing')
print('R31 compile fixes: OK')
