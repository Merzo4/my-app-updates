from pathlib import Path
import os, re

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# R54.1: service startup configuration belongs to Windows Service Control
# Manager. R54 wrote HKLM\SYSTEM\CurrentControlSet\Services\*\Start directly
# both when applying and when restoring a snapshot. Protected service ACLs can
# reject that registry write and then make rollback fail through the same path.
# Route both directions through one SCM helper.
audit=root/'src'/'MerzoOptimizer.Windows'/'Services'/'WindowsServiceAuditService.cs'
a=read(audit)
old_apply='''            using var key = global::Microsoft.Win32.Registry.LocalMachine.OpenSubKey($@"SYSTEM\\CurrentControlSet\\Services\\{item.ServiceName}", writable: true)\n                ?? throw new InvalidOperationException("Не удалось открыть ключ службы для записи.");\n            key.SetValue("Start", 4, global::Microsoft.Win32.RegistryValueKind.DWord);'''
new_apply='''            WindowsServiceStartTypeManager.SetStartType(item.ServiceName, 4);'''
if old_apply not in a:
    raise SystemExit('R54.1 service apply registry-write anchor missing')
a=a.replace(old_apply,new_apply,1)
write(audit,a)

restore=root/'src'/'MerzoOptimizer.Windows'/'Restore'/'WindowsRestoreService.cs'
r=read(restore)
old_restore='''        using var key = global::Microsoft.Win32.Registry.LocalMachine.OpenSubKey($@"SYSTEM\\CurrentControlSet\\Services\\{state.ServiceName}", writable: true)\n            ?? throw new InvalidOperationException($"Служба {state.ServiceName} больше не найдена.");\n        key.SetValue("Start", state.StartValue, global::Microsoft.Win32.RegistryValueKind.DWord);'''
new_restore='''        global::MerzoOptimizer.Windows.Services.WindowsServiceStartTypeManager.SetStartType(state.ServiceName, state.StartValue);'''
if old_restore not in r:
    raise SystemExit('R54.1 service restore registry-write anchor missing')
r=r.replace(old_restore,new_restore,1)
write(restore,r)

helper_path=root/'src'/'MerzoOptimizer.Windows'/'Services'/'WindowsServiceStartTypeManager.cs'
if helper_path.exists():
    raise SystemExit('R54.1 SCM helper unexpectedly already exists')
helper=r'''namespace MerzoOptimizer.Windows.Services;

internal static class WindowsServiceStartTypeManager
{
    private const uint ScManagerConnect = 0x0001;
    private const uint ServiceChangeConfig = 0x0002;
    private const uint ServiceNoChange = 0xFFFFFFFF;

    internal static void SetStartType(string serviceName, int startValue)
    {
        if (string.IsNullOrWhiteSpace(serviceName))
            throw new ArgumentException("Имя службы не задано.", nameof(serviceName));
        if (startValue is < 0 or > 4)
            throw new ArgumentOutOfRangeException(nameof(startValue), startValue, "Недопустимый тип запуска службы.");

        var scm = OpenSCManager(null, null, ScManagerConnect);
        if (scm == nint.Zero)
            throw CreateWin32("Не удалось открыть Service Control Manager.");

        try
        {
            var service = OpenService(scm, serviceName, ServiceChangeConfig);
            if (service == nint.Zero)
                throw CreateWin32($"Не удалось открыть службу {serviceName} через Service Control Manager.");

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
                    throw CreateWin32($"Не удалось изменить тип запуска службы {serviceName} через Service Control Manager.");
                }
            }
            finally
            {
                _ = CloseServiceHandle(service);
            }
        }
        finally
        {
            _ = CloseServiceHandle(scm);
        }
    }

    private static global::System.ComponentModel.Win32Exception CreateWin32(string message) =>
        new(global::System.Runtime.InteropServices.Marshal.GetLastWin32Error(), message);

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
}
'''
write(helper_path,helper)

# Visible/product version: installed R54 updater already proved four-part release
# discovery/download, so this hotfix may use exact 0.1.54.1.
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
i=i.replace('0.1.54','0.1.54.1').replace('0.1.54.1.1','0.1.54.1')
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

# Fail closed on the exact screenshot regression. Service registry is still
# read-only for audit; no service apply/Undo path may open it writable or set
# Start directly.
a_final=read(audit)
r_final=read(restore)
h_final=read(helper_path)
for token in (
    'WindowsServiceStartTypeManager.SetStartType(item.ServiceName, 4);',
    'WindowsServiceStartTypeManager.SetStartType(state.ServiceName, state.StartValue);',
    'ChangeServiceConfig(',
    'ServiceChangeConfig = 0x0002',
    'OpenSCManager(',
    'OpenService('
):
    hay=(a_final+'\n'+r_final+'\n'+h_final)
    if token not in hay:
        raise SystemExit('R54.1 SCM contract missing: '+token)
for label,text in [('apply',a_final),('restore',r_final)]:
    if re.search(r'CurrentControlSet\\Services.*writable:\s*true',text,re.I|re.S):
        raise SystemExit(f'R54.1 writable service registry path remains in {label}')
    if 'key.SetValue("Start"' in text:
        raise SystemExit(f'R54.1 direct service Start registry write remains in {label}')

(root/'R54_1_SERVICE_CONTROL_HOTFIX.marker').write_text(
    '0.1.54.1: service startup apply and snapshot Undo use shared SCM ChangeServiceConfig; direct writable Services\\Start paths removed\n',
    encoding='utf-8')
print('R54.1 service control hotfix: OK')
