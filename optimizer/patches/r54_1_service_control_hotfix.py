from pathlib import Path
import json, os, re

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# R54.1: Windows service Start is configuration owned by the Service Control
# Manager. R54 wrote HKLM\\SYSTEM\\CurrentControlSet\\Services\\*\\Start
# directly; protected service ACLs can reject that even when the user is an
# administrator, and rollback then fails through the same path. Route BOTH
# apply and restore through ChangeServiceConfig instead.
p=root/'src'/'MerzoOptimizer.Windows'/'Services'/'WindowsServiceAuditService.cs'
s=read(p)
old_apply='''            using var key = global::Microsoft.Win32.Registry.LocalMachine.OpenSubKey($@"SYSTEM\\CurrentControlSet\\Services\\{item.ServiceName}", writable: true)\n                ?? throw new InvalidOperationException("Не удалось открыть ключ службы для записи.");\n            key.SetValue("Start", 4, global::Microsoft.Win32.RegistryValueKind.DWord);'''
new_apply='''            SetServiceStartTypeViaScm(item.ServiceName, 4);'''
if old_apply not in s:
    raise SystemExit('R54.1 service apply registry-write anchor missing')
s=s.replace(old_apply,new_apply,1)

old_restore='''        using var key = global::Microsoft.Win32.Registry.LocalMachine.OpenSubKey($@"SYSTEM\\CurrentControlSet\\Services\\{state.ServiceName}", writable: true)\n            ?? throw new InvalidOperationException($"Служба {state.ServiceName} больше не найдена.");\n        key.SetValue("Start", state.StartValue, global::Microsoft.Win32.RegistryValueKind.DWord);'''
new_restore='''        SetServiceStartTypeViaScm(state.ServiceName, state.StartValue);'''
if old_restore not in s:
    raise SystemExit('R54.1 service restore registry-write anchor missing')
s=s.replace(old_restore,new_restore,1)

# Insert the SCM helper before the final class brace. No shell/free-form command
# is used: only advapi32 OpenSCManager/OpenService/ChangeServiceConfig.
helper=r'''
    private const uint ScManagerConnect = 0x0001;
    private const uint ServiceChangeConfig = 0x0002;
    private const uint ServiceNoChange = 0xFFFFFFFF;

    private static void SetServiceStartTypeViaScm(string serviceName, int startValue)
    {
        if (string.IsNullOrWhiteSpace(serviceName))
            throw new ArgumentException("Имя службы не задано.", nameof(serviceName));
        if (startValue is < 0 or > 4)
            throw new ArgumentOutOfRangeException(nameof(startValue), startValue, "Недопустимый тип запуска службы.");

        var scm = OpenSCManager(null, null, ScManagerConnect);
        if (scm == nint.Zero)
            throw new global::System.ComponentModel.Win32Exception(
                global::System.Runtime.InteropServices.Marshal.GetLastWin32Error(),
                "Не удалось открыть Service Control Manager.");
        try
        {
            var service = OpenService(scm, serviceName, ServiceChangeConfig);
            if (service == nint.Zero)
                throw new global::System.ComponentModel.Win32Exception(
                    global::System.Runtime.InteropServices.Marshal.GetLastWin32Error(),
                    $"Не удалось открыть службу {serviceName} через Service Control Manager.");
            try
            {
                if (!ChangeServiceConfig(
                        service,
                        ServiceNoChange,
                        checked((uint)startValue),
                        ServiceNoChange,
                        null,
                        null,
                        nint.Zero,
                        null,
                        null,
                        null,
                        null))
                {
                    throw new global::System.ComponentModel.Win32Exception(
                        global::System.Runtime.InteropServices.Marshal.GetLastWin32Error(),
                        $"Не удалось изменить тип запуска службы {serviceName} через Service Control Manager.");
                }
            }
            finally
            {
                CloseServiceHandle(service);
            }
        }
        finally
        {
            CloseServiceHandle(scm);
        }
    }

    [global::System.Runtime.InteropServices.DllImport("advapi32.dll", CharSet = global::System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
    private static extern nint OpenSCManager(string? machineName, string? databaseName, uint desiredAccess);

    [global::System.Runtime.InteropServices.DllImport("advapi32.dll", CharSet = global::System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
    private static extern nint OpenService(nint serviceManager, string serviceName, uint desiredAccess);

    [global::System.Runtime.InteropServices.DllImport("advapi32.dll", CharSet = global::System.Runtime.InteropServices.CharSet.Unicode, SetLastError = true)]
    [return: global::System.Runtime.InteropServices.MarshalAs(global::System.Runtime.InteropServices.UnmanagedType.Bool)]
    private static extern bool ChangeServiceConfig(
        nint service,
        uint serviceType,
        uint startType,
        uint errorControl,
        string? binaryPathName,
        string? loadOrderGroup,
        nint tagId,
        string? dependencies,
        string? serviceStartName,
        string? password,
        string? displayName);

    [global::System.Runtime.InteropServices.DllImport("advapi32.dll", SetLastError = true)]
    [return: global::System.Runtime.InteropServices.MarshalAs(global::System.Runtime.InteropServices.UnmanagedType.Bool)]
    private static extern bool CloseServiceHandle(nint serviceHandle);
'''
pos=s.rfind('\n}')
if pos < 0:
    raise SystemExit('R54.1 WindowsServiceAuditService final brace missing')
s=s[:pos]+helper+s[pos:]
write(p,s)

# Visible/product version: R54 updater now supports four-part tags end to end.
xaml=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xaml)
for old,new in [
    ('Production R54 · 0.1.54','Production R54.1 · 0.1.54.1'),
    ('Text="R54"','Text="R54.1"'),
    ('Production 0.1.54 · R53 GAME HOTFIX BRIDGE','Production 0.1.54.1 · R54 SERVICE CONTROL HOTFIX'),
]:
    if old not in x:
        raise SystemExit('R54.1 UI anchor missing: '+old)
    x=x.replace(old,new,1)
write(xaml,x)

iss=root/'installer'/'MerzoWindowsOptimizer.iss'
i=read(iss)
if '#define MyAppVersion "0.1.54"' in i:
    i=i.replace('#define MyAppVersion "0.1.54"','#define MyAppVersion "0.1.54.1"',1)
elif 'AppVersion=0.1.54' in i:
    i=i.replace('AppVersion=0.1.54','AppVersion=0.1.54.1',1)
else:
    raise SystemExit('R54.1 installer version anchor missing')
i=i.replace('0.1.54','0.1.54.1')
# Prevent accidental double revision if the literal replacement touched the new define.
i=i.replace('0.1.54.1.1','0.1.54.1')
write(iss,i)

projects=sorted((root/'src').glob('MerzoOptimizer.*/*.csproj'))
if len(projects)<5:
    raise SystemExit('R54.1 expected project set missing')
for cp in projects:
    t=read(cp)
    for label,target in [('AssemblyVersion','0.1.54.1'),('FileVersion','0.1.54.1'),('InformationalVersion','0.1.54.1')]:
        pat=rf'(<{label}>\s*)([^<]+?)(\s*</{label}>)'
        ms=list(re.finditer(pat,t))
        if not ms:
            raise SystemExit(f'R54.1 missing {label}: {cp.name}')
        vals={m.group(2).strip() for m in ms}
        if not vals <= {'0.1.54','0.1.54.0'}:
            raise SystemExit(f'R54.1 unexpected {label}: {cp.name}: {sorted(vals)}')
        t=re.sub(pat,lambda m:m.group(1)+target+m.group(3),t)
    write(cp,t)

# Fail closed on the screenshot regression. Read-only service registry access is
# still allowed for audit, but writable service-registry access is forbidden.
final=read(p)
for token in ('SetServiceStartTypeViaScm(item.ServiceName, 4);','SetServiceStartTypeViaScm(state.ServiceName, state.StartValue);','ChangeServiceConfig(','ServiceChangeConfig = 0x0002'):
    if token not in final:
        raise SystemExit('R54.1 SCM contract missing: '+token)
if re.search(r'CurrentControlSet\\\\Services.*writable:\s*true',final,re.I|re.S):
    raise SystemExit('R54.1 writable service registry path remains')
if 'key.SetValue("Start", 4' in final or 'key.SetValue("Start", state.StartValue' in final:
    raise SystemExit('R54.1 direct Start registry write remains')

(root/'R54_1_SERVICE_CONTROL_HOTFIX.marker').write_text(
    '0.1.54.1: service startup apply+Undo use SCM ChangeServiceConfig; direct writable Services\\Start registry path removed\n',
    encoding='utf-8')
print('R54.1 service control hotfix: OK')
