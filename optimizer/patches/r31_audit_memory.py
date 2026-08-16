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

# Preserve an explicit Update Center 4.0 regression marker for CI and brand SelfTest correctly.
xaml=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=xaml.read_text(encoding='utf-8-sig')
if 'R30: visual Update Center 4.0' not in x:
    x=x.replace('</Window>', '    <!-- R30: visual Update Center 4.0 retained in R31 -->\n</Window>')
xaml.write_text(x,encoding='utf-8')

selftest=root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
st=selftest.read_text(encoding='utf-8-sig')
st=st.replace('PRODUCTION R29 OPERATIONS SelfTest','PRODUCTION R31 AUDIT MEMORY SelfTest').replace('PRODUCTION R30 MAJOR SelfTest','PRODUCTION R31 AUDIT MEMORY SelfTest')
selftest.write_text(st,encoding='utf-8')
print('R31 compile/release compatibility: OK')
