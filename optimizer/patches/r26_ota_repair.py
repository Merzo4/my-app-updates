from pathlib import Path
import os,re,json

root=Path(os.environ['SOURCE_ROOT'])
VERSION='0.1.26'
RUNTIME='0.1.26.0'

# Hard-stamp the actual WPF assembly. The previous release package was named
# 0.1.25, but its app assembly still reported 0.1.21.
proj=root/'src'/'MerzoOptimizer.App'/'MerzoOptimizer.App.csproj'
p=proj.read_text(encoding='utf-8-sig')
p=re.sub(r'\s*<!-- MERZO_R26_VERSION_BEGIN -->.*?<!-- MERZO_R26_VERSION_END -->\s*','\n',p,flags=re.S)
stamp=f'''\n  <!-- MERZO_R26_VERSION_BEGIN -->
  <PropertyGroup>
    <Version>{VERSION}</Version>
    <VersionPrefix>{VERSION}</VersionPrefix>
    <AssemblyVersion>{RUNTIME}</AssemblyVersion>
    <FileVersion>{RUNTIME}</FileVersion>
    <InformationalVersion>{VERSION}</InformationalVersion>
  </PropertyGroup>
  <!-- MERZO_R26_VERSION_END -->\n'''
if '</Project>' not in p: raise SystemExit('Project end tag missing')
p=p.replace('</Project>',stamp+'</Project>',1)
proj.write_text(p,encoding='utf-8')

# Replace legacy visible R21/R24/R25 identity structurally instead of relying on
# one exact old string.
xaml=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=xaml.read_text(encoding='utf-8-sig')
x=re.sub(r'(<Window\b[^>]*\bTitle=")[^"]*(")',rf'\1Merzo Windows Optimizer — Production {VERSION} · R26 OTA REPAIR\2',x,count=1,flags=re.S)
x=re.sub(r'Production\s+R\d+','Production R26',x)
x=re.sub(r'Production\s+0\.1\.\d+(?:\s*·\s*ONLINE UPDATE TEST)?',f'Production {VERSION}',x)
x=re.sub(r'v0\.1\.\d+',f'v{VERSION}',x)
x=x.replace('ONLINE UPDATE TEST ✓','OTA REPAIR ✓').replace('ONLINE UPDATE TEST','OTA REPAIR')
if 'Production R26' not in x:
    x=x.replace('Merzo Windows Optimizer','Merzo Windows Optimizer · Production R26',1)
xaml.write_text(x,encoding='utf-8')

# Harden the updater launch. SHA-256 verification remains upstream in the
# existing UpdateService and is not weakened here.
vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s=vm.read_text(encoding='utf-8-sig')
s=re.sub(r'Arguments\s*=\s*"/(?:SILENT|VERYSILENT)[^"]*"\s*,',
         'Arguments = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-",',
         s,count=1)
old=r"var script = \$\"\$ErrorActionPreference='SilentlyContinue'.*?Remove-Item -LiteralPath \$PSCommandPath -Force`r`n\";"
new='''var script = $"$ErrorActionPreference='SilentlyContinue'`r`nWait-Process -Id {installer.Id}`r`nStart-Sleep -Milliseconds 1500`r`nfor($i=0;$i -lt 12;$i++) {{ if(Get-Process -Name 'MerzoWindowsOptimizer' -ErrorAction SilentlyContinue) {{ break }}; if(Test-Path -LiteralPath '{escapedExe}') {{ Start-Process -FilePath '{escapedExe}'; Start-Sleep -Milliseconds 700; if(Get-Process -Name 'MerzoWindowsOptimizer' -ErrorAction SilentlyContinue) {{ break }} }}; Start-Sleep -Seconds 1 }}`r`nRemove-Item -LiteralPath $PSCommandPath -Force`r`n";'''
s=re.sub(old,lambda m:new,s,count=1,flags=re.S)
if '/RESTARTAPPLICATIONS' not in s: raise SystemExit('Restart flags missing')
vm.write_text(s,encoding='utf-8')

# Primary silent-OTA relaunch is handled by Inno itself, so update success no
# longer depends only on a PowerShell fallback script.
iss=root/'installer'/'MerzoWindowsOptimizer.iss'
i=iss.read_text(encoding='utf-8-sig')
marker='; MERZO_R26_SILENT_RELAUNCH'
line='Filename: "{app}\\MerzoWindowsOptimizer.exe"; WorkingDir: "{app}"; Flags: nowait runasoriginaluser; Check: WizardSilent; StatusMsg: "Launching Merzo Windows Optimizer..."'
if 'MERZO_R26_SILENT_RELAUNCH' not in i:
    block=marker+'\n'+line
    m=re.search(r'(?mi)^\[Run\]\s*$',i)
    if m: i=i[:m.end()]+'\n'+block+i[m.end():]
    else: i=i.rstrip()+'\n\n[Run]\n'+block+'\n'
iss.write_text(i,encoding='utf-8')

# Keep the production feed explicit.
settings=root/'data'/'update_settings.json'
j=json.loads(settings.read_text(encoding='utf-8-sig'))
j.update({
  'auto_check':True,
  'auto_download':True,
  'auto_install':True,
  'provider':'GitHub',
  'repository_owner':'Merzo4',
  'repository_name':'my-app-updates',
  'release_tag_prefix':'mwo-v',
  'asset_name_contains':'MerzoWindowsOptimizerSetup-win-x64.exe',
  'installer_silent_args':'/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
})
settings.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Consistency marker for the self-test output.
st=root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
if st.exists():
    q=st.read_text(encoding='utf-8-sig')
    q=re.sub(r'PRODUCTION R\d+ SelfTest','PRODUCTION R26 SelfTest',q)
    q=q.replace('SCAN FIRST + LITE BUILD SelfTest R20','PRODUCTION R26 SelfTest')
    st.write_text(q,encoding='utf-8')

# Source-level gates.
fx=xaml.read_text(encoding='utf-8')
fv=vm.read_text(encoding='utf-8')
fi=iss.read_text(encoding='utf-8')
for token in ['Production R26',VERSION]:
    if token not in fx: raise SystemExit(f'Visible identity missing: {token}')
for token in ['LaunchVerifiedInstallerAndRestart','/RESTARTAPPLICATIONS']:
    if token not in fv: raise SystemExit(f'Updater contract missing: {token}')
if 'MERZO_R26_SILENT_RELAUNCH' not in fi: raise SystemExit('Silent relaunch missing')
print('R26 OTA/version repair patch: OK')
