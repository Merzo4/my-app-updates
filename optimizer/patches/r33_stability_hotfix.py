from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])
version = '0.1.33'
assembly = '0.1.33.0'

# Stamp every project to one exact production version. Multiple PropertyGroups are intentional;
# replacing all version tags prevents an older conditional group from winning during publish.
for p in (root/'src').glob('*/**/*.csproj'):
    s = p.read_text(encoding='utf-8-sig')
    for tag, value in [
        ('Version', version), ('VersionPrefix', version), ('AssemblyVersion', assembly),
        ('FileVersion', assembly), ('InformationalVersion', version)
    ]:
        s = re.sub(fr'<{tag}>[^<]+</{tag}>', f'<{tag}>{value}</{tag}>', s)
    if '<Version>' not in s:
        insert = f'''\n  <PropertyGroup>\n    <Version>{version}</Version>\n    <VersionPrefix>{version}</VersionPrefix>\n    <AssemblyVersion>{assembly}</AssemblyVersion>\n    <FileVersion>{assembly}</FileVersion>\n    <InformationalVersion>{version}</InformationalVersion>\n  </PropertyGroup>\n'''
        s = s.replace('</Project>', insert + '</Project>')
    p.write_text(s, encoding='utf-8')

# Production UI branding + splash fallback.
xaml = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x = xaml.read_text(encoding='utf-8-sig')
x = re.sub(r'Production 0\.1\.\d+ · R\d+[^\"]*', 'Production 0.1.33 · R33 STABILITY RECOVERY', x)
x = re.sub(r'Production R\d+', 'Production R33', x)
x = re.sub(r'Production · v0\.1\.\d+', 'Production · v0.1.33', x)
xaml.write_text(x, encoding='utf-8')

appcs = root/'src'/'MerzoOptimizer.App'/'App.xaml.cs'
s = appcs.read_text(encoding='utf-8-sig')
s = re.sub(r'\? "0\.1\.\d+" : pendingVersion', '? "0.1.33" : pendingVersion', s)
appcs.write_text(s, encoding='utf-8')

vm = root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s = vm.read_text(encoding='utf-8-sig')
s = s.replace('версии 0.1.32', 'версии 0.1.33')
vm.write_text(s, encoding='utf-8')

# SelfTest branding. Keep the existing read-only safety tests, just make the production line explicit.
selftest = root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
s = selftest.read_text(encoding='utf-8-sig')
s = re.sub(r'Merzo Windows Optimizer — PRODUCTION R\d+[^\"\r\n]*SelfTest', 'Merzo Windows Optimizer — PRODUCTION R33 STABILITY RECOVERY SelfTest', s)
s = s.replace('PRODUCTION R32 PERFORMANCE SelfTest', 'PRODUCTION R33 STABILITY RECOVERY SelfTest')
selftest.write_text(s, encoding='utf-8')

# Release metadata.
notes = {
  'version': version,
  'title': 'R33 STABILITY RECOVERY',
  'summary': 'Emergency recovery after the R31 runtime TypeLoadException in the async dispatcher.',
  'added': [
    'Post-publish runtime smoke for AsyncOperationDispatcher.RunAsync<T> so the exact failure from R31 is caught before release.',
    'Recovery installer intended to install directly over a broken R31/R32 installation without uninstalling user data.',
    'Startup update notification from R32 remains enabled for all future versions.'
  ],
  'changed': [
    'Production protection is temporarily built without Obfuscar. Reliability takes priority until the generic async metadata issue is isolated.',
    'All application assemblies are hard-stamped to 0.1.33 to prevent mixed-version payloads.'
  ],
  'fixed': [
    "Fixed System.TypeLoadException: Could not load type 'b`1' from MerzoOptimizer.Core during audit/update operations.",
    'Audit and Update Center no longer depend on an obfuscated generic async state-machine that could be emitted with invalid metadata.',
    'Added release gate that actually calls both generic and non-generic dispatcher methods from the published payload.'
  ]
}
(root/'data'/'release_notes.json').write_text(json.dumps(notes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

rv = root/'release'/'version.json'
if rv.exists():
    try:
        obj = json.loads(rv.read_text(encoding='utf-8-sig'))
        if isinstance(obj, dict):
            for key in ('version','Version','app_version'):
                if key in obj: obj[key] = version
            rv.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    except Exception:
        pass

# Marker used by CI to prove the stability patch ran.
(root/'R33_STABILITY_RECOVERY.marker').write_text(
    'R33: no-obfuscation production build + published AsyncOperationDispatcher runtime smoke\n',
    encoding='utf-8')
print('R33 stability recovery patch: OK')
