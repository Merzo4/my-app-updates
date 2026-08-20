from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p, s): p.parent.mkdir(parents=True, exist_ok=True); p.write_text(s, encoding='utf-8')

def setup_directive(text, key, value):
    pattern = rf'(?mi)^{re.escape(key)}\s*=.*$'
    replacement = f'{key}={value}'
    if re.search(pattern, text):
        return re.sub(pattern, lambda _m: replacement, text, count=1)
    m = re.search(r'(?mi)^\[Setup\]\s*$', text)
    if not m:
        raise SystemExit(f'R53 installer missing [Setup] for {key}')
    return text[:m.end()] + '\n' + replacement + text[m.end():]

# -----------------------------------------------------------------------------
# 1) Main shell always runs as the interactive user. Only ElevatedHelper may
#    cross the UAC boundary. This keeps Print Screen / Snipping Tool working
#    while the Merzo window is focused and prevents accidental always-admin UI.
# -----------------------------------------------------------------------------
app_dir = root/'src'/'MerzoOptimizer.App'
proj = app_dir/'MerzoOptimizer.App.csproj'
p = read(proj)
if '<ApplicationManifest>' in p:
    p = re.sub(r'<ApplicationManifest>[^<]*</ApplicationManifest>', '<ApplicationManifest>app.manifest</ApplicationManifest>', p, count=1)
else:
    m = re.search(r'</PropertyGroup>', p)
    if not m: raise SystemExit('R53 main app csproj PropertyGroup missing')
    p = p[:m.start()] + '  <ApplicationManifest>app.manifest</ApplicationManifest>\n' + p[m.start():]
write(proj, p)

manifest = '''<?xml version="1.0" encoding="utf-8"?>
<assembly manifestVersion="1.0" xmlns="urn:schemas-microsoft-com:asm.v1">
  <assemblyIdentity version="1.0.0.0" name="Merzo.Windows.Optimizer" />
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
write(app_dir/'app.manifest', manifest)

# Fail closed if the shell ever starts grabbing PrintScreen/global keyboard.
for source in app_dir.rglob('*.cs'):
    if any(x in source.parts for x in ('bin','obj')): continue
    text = read(source)
    for forbidden in ('RegisterHotKey(', 'SetWindowsHookEx', 'WH_KEYBOARD_LL', 'VK_SNAPSHOT', 'Key.PrintScreen'):
        if forbidden in text:
            raise SystemExit(f'R53 screenshot compatibility: forbidden global-key token {forbidden} in {source.name}')

# -----------------------------------------------------------------------------
# 2) OTA migration: an older Inno-installed copy outside Program Files is still
#    allowed to update, but Portable/DEV remains protected. After install, restart
#    the NEW Program Files executable first so an old copy cannot reopen.
# -----------------------------------------------------------------------------
vm = root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
v = read(vm)

# R26 used /VERYSILENT. R53 intentionally goes back to /SILENT so the user sees
# the branded file-replacement progress window, while wizard pages stay hidden.
args_pattern = r'(Arguments\s*=\s*")(/(?:SILENT|VERYSILENT)[^"]*)("\s*,)'
args_match = re.search(args_pattern, v)
if not args_match:
    raise SystemExit('R53 updater installer arguments block missing')
args = args_match.group(2).replace('/VERYSILENT', '/SILENT')
if '/MERZOUPDATE=1' not in args:
    args = args.rstrip() + ' /MERZOUPDATE=1'
v = v[:args_match.start()] + args_match.group(1) + args + args_match.group(3) + v[args_match.end():]

old_layout = '''        var baseDir = Path.GetFullPath(AppContext.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);\n        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);'''
new_layout = '''        var baseDir = Path.GetFullPath(AppContext.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);\n        // Legacy installed builds may live outside Program Files. Presence of the Inno\n        // uninstaller distinguishes them from Portable/DEV and allows one-time migration.\n        if (File.Exists(Path.Combine(baseDir, "unins000.exe"))) return true;\n        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);'''
if old_layout not in v and 'unins000.exe' not in v:
    raise SystemExit('R53 installed-layout migration anchor missing')
v = v.replace(old_layout, new_layout, 1)

old_restart = '''        var currentExe = Environment.ProcessPath ?? Path.Combine(AppContext.BaseDirectory, "MerzoWindowsOptimizer.exe");\n        var installer = Process.Start(new ProcessStartInfo'''
new_restart = '''        var currentExe = Environment.ProcessPath ?? Path.Combine(AppContext.BaseDirectory, "MerzoWindowsOptimizer.exe");\n        var programFiles = Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles);\n        var installedExe = string.IsNullOrWhiteSpace(programFiles)\n            ? currentExe\n            : Path.Combine(programFiles, "Merzo Windows Optimizer", "MerzoWindowsOptimizer.exe");\n        var installer = Process.Start(new ProcessStartInfo'''
if old_restart not in v and 'var installedExe = string.IsNullOrWhiteSpace(programFiles)' not in v:
    raise SystemExit('R53 updater restart anchor missing')
v = v.replace(old_restart, new_restart, 1)

# Replace the inherited restart-script body without depending on its historical
# escaping details. The new install path is preferred; old path is fallback only.
restart_pos = v.find('        var restartScript = Path.Combine(')
if restart_pos < 0:
    raise SystemExit('R53 restartScript declaration missing')
restart_line_end = v.find('\n', restart_pos)
if restart_line_end < 0:
    raise SystemExit('R53 restartScript line malformed')
restart_line_end += 1
filewrite_pos = v.find('        File.WriteAllText(restartScript, script);', restart_line_end)
if filewrite_pos < 0:
    raise SystemExit('R53 restartScript File.WriteAllText missing')
restart_body = '''        var escapedCurrentExe = currentExe.Replace("'", "''");\n        var escapedInstalledExe = installedExe.Replace("'", "''");\n        var script = $"$ErrorActionPreference='SilentlyContinue'`r`nWait-Process -Id {installer.Id}`r`nStart-Sleep -Milliseconds 1200`r`n$target='{escapedInstalledExe}'`r`nif (-not (Test-Path -LiteralPath $target)) {{ $target='{escapedCurrentExe}' }}`r`nif (Test-Path -LiteralPath $target) {{ Start-Process -FilePath $target }}`r`nRemove-Item -LiteralPath $PSCommandPath -Force`r`n";\n'''
v = v[:restart_line_end] + restart_body + v[filewrite_pos:]
write(vm, v)

# Keep the configured installer policy aligned with the visible branded OTA mode.
settings = root/'data'/'update_settings.json'
if settings.exists():
    cfg = json.loads(read(settings))
    silent = str(cfg.get('installer_silent_args') or '/SILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-')
    silent = silent.replace('/VERYSILENT', '/SILENT')
    if '/MERZOUPDATE=1' not in silent:
        silent = silent.rstrip() + ' /MERZOUPDATE=1'
    cfg['installer_silent_args'] = silent
    write(settings, json.dumps(cfg, ensure_ascii=False, indent=2)+'\n')

# -----------------------------------------------------------------------------
# 3) Real Windows installation: machine-wide Program Files destination.
#    UsePreviousAppDir=no intentionally migrates legacy installs that used an
#    earlier non-standard directory. User data remains in AppData, not {app}.
# -----------------------------------------------------------------------------
iss = root/'installer'/'MerzoWindowsOptimizer.iss'
s = read(iss)
for key, value in [
    ('DefaultDirName', r'{autopf}\Merzo Windows Optimizer'),
    ('DefaultGroupName', 'Merzo Windows Optimizer'),
    ('PrivilegesRequired', 'admin'),
    ('UsePreviousAppDir', 'no'),
    ('WizardStyle', 'modern'),
    ('DisableWelcomePage', 'no'),
    ('DisableProgramGroupPage', 'yes'),
    ('CloseApplications', 'yes'),
    ('RestartApplications', 'no'),
    ('UninstallDisplayName', 'Merzo Windows Optimizer'),
]:
    s = setup_directive(s, key, value)

# Brand the normal installer AND the visible /SILENT updater progress window.
brand_decl = r'''
// R53 MERZO PRODUCT INSTALLER THEME
var
  MerzoInstallBanner: TNewStaticText;

procedure MerzoApplyProductTheme; forward;
'''
brand_impl = r'''
procedure MerzoApplyProductTheme;
begin
  WizardForm.Caption := 'Merzo Windows Optimizer';
  WizardForm.Color := $00201712;
  WizardForm.MainPanel.Color := $00201712;
  WizardForm.WelcomePage.Color := $00201712;
  WizardForm.InnerPage.Color := $00201712;
  WizardForm.FinishedPage.Color := $00201712;

  WizardForm.PageNameLabel.Font.Color := clWhite;
  WizardForm.PageNameLabel.Font.Size := 12;
  WizardForm.PageNameLabel.Font.Style := [fsBold];
  WizardForm.PageDescriptionLabel.Font.Color := $00D8CEC5;
  WizardForm.WelcomeLabel1.Font.Color := clWhite;
  WizardForm.WelcomeLabel1.Font.Size := 18;
  WizardForm.WelcomeLabel1.Font.Style := [fsBold];
  WizardForm.WelcomeLabel1.Caption := 'MERZO WINDOWS OPTIMIZER';
  WizardForm.WelcomeLabel2.Font.Color := $00D8CEC5;
  WizardForm.WelcomeLabel2.Caption := 'Чистая Windows. GAME. EXTREME.' + #13#10 +
    'Snapshot → Apply → Verify → Log → Undo';
  WizardForm.FinishedHeadingLabel.Font.Color := clWhite;
  WizardForm.FinishedHeadingLabel.Font.Style := [fsBold];
  WizardForm.FinishedLabel.Font.Color := $00D8CEC5;
  WizardForm.StatusLabel.Font.Color := clWhite;
  WizardForm.FilenameLabel.Font.Color := $00BDB5AD;

  WizardForm.NextButton.Caption := 'Продолжить';
  WizardForm.BackButton.Caption := 'Назад';
  WizardForm.CancelButton.Caption := 'Отмена';

  MerzoInstallBanner := TNewStaticText.Create(WizardForm);
  MerzoInstallBanner.Parent := WizardForm.InstallingPage;
  MerzoInstallBanner.Left := 0;
  MerzoInstallBanner.Top := 0;
  MerzoInstallBanner.Width := WizardForm.InstallingPage.ClientWidth;
  MerzoInstallBanner.Height := ScaleY(34);
  MerzoInstallBanner.Font.Size := 11;
  MerzoInstallBanner.Font.Style := [fsBold];
  MerzoInstallBanner.Font.Color := $00FFCD40;

  if ExpandConstant('{param:MERZOUPDATE|0}') = '1' then
  begin
    WizardForm.Caption := 'Merzo Windows Optimizer · Обновление';
    MerzoInstallBanner.Caption := 'MERZO UPDATE · БЕЗОПАСНО ОБНОВЛЯЕМ ФАЙЛЫ';
    WizardForm.StatusLabel.Caption := 'Подготавливаем новую версию…';
  end
  else
    MerzoInstallBanner.Caption := 'MERZO INSTALL · PROTECTED SETUP';
end;
'''

if '// R53 MERZO PRODUCT INSTALLER THEME' not in s:
    if re.search(r'(?mi)^\[Code\]\s*$', s):
        m = re.search(r'(?mi)^\[Code\]\s*$', s)
        s = s[:m.end()] + '\n' + brand_decl + s[m.end():]
    else:
        s = s.rstrip() + '\n\n[Code]\n' + brand_decl

    # Hook into an existing InitializeWizard when present; otherwise add our own.
    init = re.search(r'(?is)(procedure\s+InitializeWizard\s*;\s*begin)', s)
    if init:
        s = s[:init.end()] + '\n  MerzoApplyProductTheme;' + s[init.end():]
        s = s.rstrip() + '\n\n' + brand_impl
    else:
        s = s.rstrip() + '\n\n' + brand_impl + '\nprocedure InitializeWizard;\nbegin\n  MerzoApplyProductTheme;\nend;\n'

write(iss, s)

# -----------------------------------------------------------------------------
# 4) Release notes + hard contract marker.
# -----------------------------------------------------------------------------
notes = root/'data'/'release_notes.json'
if notes.exists():
    try:
        data = json.loads(read(notes))
        extra = [
            'Установка теперь machine-wide в Program Files\\Merzo Windows Optimizer; старые Inno-установки мигрируют при обновлении.',
            'Основное окно закреплено как asInvoker: Print Screen/Snipping Tool совместимы; UAC используется только ElevatedHelper.',
            'Инсталлятор и окно OTA-обновления получили единый тёмный Merzo-дизайн и понятный прогресс обновления файлов.'
        ]
        for key in ('items','changes','notes'):
            if isinstance(data.get(key), list):
                for item in extra:
                    if item not in data[key]: data[key].append(item)
        write(notes, json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    except Exception:
        pass

(root/'R53_PRODUCT_INSTALL_BRANDING.marker').write_text(
    'R53 Program Files + asInvoker screenshot compatibility + branded visible install/update\n',
    encoding='utf-8')
print('R53 product install/branding patch: OK')
