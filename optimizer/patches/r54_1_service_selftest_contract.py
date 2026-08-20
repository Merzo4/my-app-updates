from pathlib import Path
import os

root=Path(os.environ['SOURCE_ROOT'])
p=root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
s=p.read_text(encoding='utf-8-sig')

anchor='''    var cleanup = File.ReadAllText(Path.Combine(repoRoot, required[5]));'''
insert='''    var cleanup = File.ReadAllText(Path.Combine(repoRoot, required[5]));\n    var serviceScmPath = Path.Combine(repoRoot, "src", "MerzoOptimizer.Windows", "Services", "WindowsServiceStartTypeManager.cs");\n    if (!File.Exists(serviceScmPath)) failures.Add("Service SCM helper missing.");\n    var serviceScm = File.Exists(serviceScmPath) ? File.ReadAllText(serviceScmPath) : string.Empty;'''
if s.count(anchor)!=1:
    raise SystemExit(f'R54.1 SelfTest SCM helper anchor count={s.count(anchor)}')
s=s.replace(anchor,insert,1)

old='''    if (!services.Contains("Start\\\", 4", StringComparison.Ordinal) || !services.Contains("RestoreAsync", StringComparison.Ordinal)) failures.Add("Service Disable/Restore contract incomplete.");'''
new='''    if (!services.Contains("WindowsServiceStartTypeManager.SetStartType(item.ServiceName, 4)", StringComparison.Ordinal) ||\n        !services.Contains("RestoreAsync", StringComparison.Ordinal) ||\n        !restore.Contains("WindowsServiceStartTypeManager.SetStartType(state.ServiceName, state.StartValue)", StringComparison.Ordinal) ||\n        !serviceScm.Contains("ChangeServiceConfig(", StringComparison.Ordinal) ||\n        !serviceScm.Contains("ServiceChangeConfig = 0x0002", StringComparison.Ordinal) ||\n        !serviceScm.Contains("OpenSCManager(", StringComparison.Ordinal) ||\n        !serviceScm.Contains("OpenService(", StringComparison.Ordinal))\n        failures.Add("Service Disable/Restore SCM contract incomplete.");\n    if (services.Contains("key.SetValue(\\\"Start\\\", 4", StringComparison.Ordinal) ||\n        restore.Contains("key.SetValue(\\\"Start\\\", state.StartValue", StringComparison.Ordinal))\n        failures.Add("Direct service Start registry writes must stay removed from apply/restore paths.");'''
if s.count(old)!=1:
    raise SystemExit(f'R54.1 SelfTest legacy service contract anchor count={s.count(old)}')
s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
print('R54.1 service SelfTest SCM contract: OK')
