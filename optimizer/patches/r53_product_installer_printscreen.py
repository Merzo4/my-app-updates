from pathlib import Path
import os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(p):
    return p.read_text(encoding='utf-8-sig')

def write(p, s):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding='utf-8')

# -----------------------------------------------------------------------------
# R53 PRODUCT POLISH
# 1. The application itself MUST stay non-elevated so Print Screen / Snipping
#    Tool work while the Merzo window is active. Only ElevatedHelper gets UAC.
# 2. Installer is machine-wide and installs to Program Files like a normal app.
# 3. The same Inno installer UI is used by OTA upgrades, so styling it also
#    replaces the ugly file-replacement/update window.
# -----------------------------------------------------------------------------

# --- Main app execution level: force asInvoker --------------------------------
app_dir = root / 'src' / 'MerzoOptimizer.App'
manifest = app_dir / 'app.manifest'
manifest_text = '''<?xml version="1.0" encoding="utf-8"?>
<assembly manifestVersion="1.0" xmlns="urn:schemas-microsoft-com:asm.v1">
  <assemblyIdentity version="1.0.0.0" name="MerzoWindowsOptimizer.app"/>
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
      <requestedPrivileges>
        <requestedExecutionLevel level="asInvoker" uiAccess="false" />
      </requestedPrivileges>
    </security>
  </trustInfo>
  <compatibility xmlns="urn:schemas-microsoft-com:compatibility.v1">
    <application>
      <supportedOS Id="{8e0f7a12-bfb3-4fe8-b9a5-48fd50a15a9a}" />
    </application>
  </compatibility>
</assembly>
'''
write(manifest, manifest_text)

app_csproj = app_dir / 'MerzoOptimizer.App.csproj'
cs = read(app_csproj)
if '<ApplicationManifest>' in cs:
    cs = re.sub(r'<ApplicationManifest>.*?</ApplicationManifest>', '<ApplicationManifest>app.manifest</ApplicationManifest>', cs, count=1, flags=re.S)
else:
    pg = cs.find('</PropertyGroup>')
    if pg < 0:
        raise SystemExit('R53 product polish: App csproj PropertyGroup missing')
    cs = cs[:pg] + '  <ApplicationManifest>app.manifest</ApplicationManifest>\n' + cs[pg:]
write(app_csproj, cs)

# Defensive gate: never allow the GUI project to request permanent admin.
for p in [app_csproj, manifest]:
    t = read(p).lower()
    if 'requireadministrator' in t or 'highestavailable' in t:
        raise SystemExit(f'R53 product polish: elevated GUI forbidden in {p.name}')

# --- Installer: Program Files + machine scope + dark branded wizard -----------
iss_files = [p for p in root.rglob('*.iss') if 'obj' not in p.parts and 'bin' not in p.parts]
if not iss_files:
    raise SystemExit('R53 product polish: no Inno Setup .iss found in production source')

BRAND_CODE = r'''

// R53_MERZO_BRANDED_INSTALLER_BEGIN
procedure R53ApplyMerzoTheme;
begin
  WizardForm.Color := $00181614;
  WizardForm.MainPanel.Color := $00181614;
  WizardForm.InnerPage.Color := $00181614;
  WizardForm.OuterNotebook.Color := $00181614;
  WizardForm.WelcomeLabel1.Font.Color := $00F6F7F9;
  WizardForm.WelcomeLabel2.Font.Color := $00B7C0CA;
  WizardForm.FinishedHeadingLabel.Font.Color := $00F6F7F9;
  WizardForm.FinishedLabel.Font.Color := $00B7C0CA;
  WizardForm.PageNameLabel.Font.Color := $00F6F7F9;
  WizardForm.PageDescriptionLabel.Font.Color := $00B7C0CA;
  WizardForm.StatusLabel.Font.Color := $00D7DEE7;
  WizardForm.FilenameLabel.Font.Color := $009DA9B6;
  WizardForm.NextButton.Caption := 'Далее';
  WizardForm.CancelButton.Caption := 'Отмена';
end;

procedure R53ProductPolishInitializeWizard;
begin
  R53ApplyMerzoTheme;
  WizardForm.Caption := 'Merzo Windows Optimizer';
end;
// R53_MERZO_BRANDED_INSTALLER_END
'''

for p in iss_files:
    s = read(p)
    if '[Setup]' not in s:
        continue

    # Genuine machine-wide installation location.
    if re.search(r'^DefaultDirName=.*$', s, flags=re.M):
        s = re.sub(r'^DefaultDirName=.*$', r'DefaultDirName={autopf}\\Merzo Windows Optimizer', s, count=1, flags=re.M)
    else:
        s = s.replace('[Setup]', '[Setup]\nDefaultDirName={autopf}\\Merzo Windows Optimizer', 1)

    directives = {
        'PrivilegesRequired': 'admin',
        'PrivilegesRequiredOverridesAllowed': 'dialog',
        'WizardStyle': 'modern',
        'DisableProgramGroupPage': 'yes',
        'UninstallDisplayName': 'Merzo Windows Optimizer',
    }
    for key, value in directives.items():
        pat = rf'^{re.escape(key)}=.*$'
        if re.search(pat, s, flags=re.M):
            s = re.sub(pat, f'{key}={value}', s, count=1, flags=re.M)
        else:
            s = s.replace('[Setup]', f'[Setup]\n{key}={value}', 1)

    # Make upgrades behave as real upgrades, not parallel installs.
    if not re.search(r'^UsePreviousAppDir=', s, flags=re.M):
        s = s.replace('[Setup]', '[Setup]\nUsePreviousAppDir=yes', 1)
    if not re.search(r'^CloseApplications=', s, flags=re.M):
        s = s.replace('[Setup]', '[Setup]\nCloseApplications=yes', 1)
    if not re.search(r'^RestartApplications=', s, flags=re.M):
        s = s.replace('[Setup]', '[Setup]\nRestartApplications=yes', 1)

    # Dark modern file-copy/update experience. Inno calls InitializeWizard only
    # once, so if an existing one is present we inject the theme call into it.
    if 'R53_MERZO_BRANDED_INSTALLER_BEGIN' not in s:
        if '[Code]' not in s:
            s += '\n[Code]\n'
        if re.search(r'procedure\s+InitializeWizard\s*;', s, flags=re.I):
            # Keep existing logic and call our theme routine at its start.
            s += BRAND_CODE.replace('procedure R53ProductPolishInitializeWizard;\nbegin\n  R53ApplyMerzoTheme;\n  WizardForm.Caption := \'Merzo Windows Optimizer\';\nend;\n', '')
            s = re.sub(
                r'(procedure\s+InitializeWizard\s*;\s*begin)',
                r"\1\n  R53ApplyMerzoTheme;\n  WizardForm.Caption := 'Merzo Windows Optimizer';",
                s,
                count=1,
                flags=re.I,
            )
        else:
            s += BRAND_CODE
            s += "\nprocedure InitializeWizard;\nbegin\n  R53ProductPolishInitializeWizard;\nend;\n"

    write(p, s)

# --- OTA updater: ensure installer is not launched in a way that elevates app --
# We intentionally do NOT weaken update SHA/digest validation. Product polish is
# limited to launch/UI/install location behavior.
for p in root.rglob('*.cs'):
    if 'bin' in p.parts or 'obj' in p.parts:
        continue
    low = p.name.lower()
    if low in {'app.xaml.cs', 'mainwindow.xaml.cs'} or 'update' in low:
        txt = read(p)
        if 'requireAdministrator' in txt:
            raise SystemExit(f'R53 product polish: permanent GUI elevation token in {p}')

(root / 'R53_PRODUCT_INSTALLER_PRINTSCREEN.marker').write_text(
    'ProgramFiles=1\nMainAppAsInvoker=1\nBrandedInstaller=1\nBrandedUpgradeWindow=1\n',
    encoding='utf-8'
)
print(f'R53_PRODUCT_INSTALLER_PRINTSCREEN_PASS iss={len(iss_files)}')
