from pathlib import Path
import base64,zlib,os
here=Path(__file__).resolve().parent
payload=''.join((here/f'r31_payload.part{i}').read_text(encoding='utf-8').strip() for i in range(1,3))
exec(zlib.decompress(base64.b64decode(payload)), {'__name__':'__main__'})

# WPF temporary projects do not implicitly import System.IO.
root=Path(os.environ['SOURCE_ROOT'])
store=root/'src'/'MerzoOptimizer.App'/'Audit'/'AuditStateStore.cs'
s=store.read_text(encoding='utf-8-sig')
if 'using System.IO;' not in s:
    s='using System.IO;\n'+s
store.write_text(s,encoding='utf-8')

# ScheduledTaskItemViewModel exposes FullPath through Snapshot.
vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
v=vm.read_text(encoding='utf-8-sig')
v=v.replace('x.FullPath.Contains(pattern, StringComparison.OrdinalIgnoreCase)', 'x.Snapshot.FullPath.Contains(pattern, StringComparison.OrdinalIgnoreCase)')
vm.write_text(v,encoding='utf-8')
print('R31 compile compatibility: OK')
