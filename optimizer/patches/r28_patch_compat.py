from pathlib import Path
import os

patch=Path('optimizer/patches/r28_profiles_updates_cleanup_ux.py')
s=patch.read_text(encoding='utf-8-sig')

# The original R28 patch used a normal Python string for a C# line that itself
# contains escaped quotes. Python consumed the backslashes, so the exact
# SelfTest anchor could never match. Make the search robust instead of relying
# on that fragile literal.
old='''ui_anchor=''' + "'''    if (xaml.Contains(\"Text=\\\"{Binding Id, Mode=OneWay}\\\"\", StringComparison.Ordinal)) failures.Add(\"Technical tweak IDs must stay hidden from user cards.\");\\n'''" + '''
if 'R28 UX missing:' not in q:
    gate=''' + "'''    foreach (var token in new[] { \"Header=\\\\\\\"Ход очистки\\\\\\\"\", \"SelectedCleanupTabIndex\", \"CleanupOperationSteps\", \"UpdateReleaseNotesText\", \"Что нового\" }) if (!xaml.Contains(token, StringComparison.Ordinal)) failures.Add($\"R28 UX missing: {token}\");\\n    if (xaml.Contains(\"Header=\\\\\\\"Телеметрия\\\\\\\"\", StringComparison.Ordinal)) failures.Add(\"Telemetry must be integrated into profiles, not shown as a separate R28 tab.\");\\n    if (!File.Exists(Path.Combine(AppContext.BaseDirectory, \"data\", \"release_notes.json\"))) failures.Add(\"R28 release_notes.json missing from payload.\");\\n'''" + '''
    if ui_anchor not in q: raise SystemExit('SelfTest UI anchor missing')
    q=q.replace(ui_anchor,ui_anchor+gate,1)'''

new='''if 'R28 UX missing:' not in q:
    gate=r''' + "'''    foreach (var token in new[] { \"Header=\\\"Ход очистки\\\"\", \"SelectedCleanupTabIndex\", \"CleanupOperationSteps\", \"UpdateReleaseNotesText\", \"Что нового\" }) if (!xaml.Contains(token, StringComparison.Ordinal)) failures.Add($\"R28 UX missing: {token}\");\n    if (xaml.Contains(\"Header=\\\"Телеметрия\\\"\", StringComparison.Ordinal)) failures.Add(\"Telemetry must be integrated into profiles, not shown as a separate R28 tab.\");\n    if (!File.Exists(Path.Combine(repoRoot, \"data\", \"release_notes.json\"))) failures.Add(\"R28 release_notes.json missing from source data.\");\n'''" + '''
    anchor_pos=q.find('Technical tweak IDs must stay hidden from user cards.')
    if anchor_pos < 0: raise SystemExit('SelfTest UI anchor missing')
    line_end=q.find('\\n', anchor_pos)
    if line_end < 0: line_end=len(q)
    q=q[:line_end+1]+gate+q[line_end+1:]'''

if old not in s:
    start=s.find("ui_anchor='''")
    end=s.find("q=q.replace(ui_anchor,ui_anchor+gate,1)", start)
    if start < 0 or end < 0:
        raise SystemExit('R28 SelfTest block not found in patch script')
    end += len("q=q.replace(ui_anchor,ui_anchor+gate,1)")
    s=s[:start]+new+s[end:]
else:
    s=s.replace(old,new,1)

# Make any already-rewritten variant use the source tree rather than the
# SelfTest executable directory. Build-Production runs SelfTest before the
# payload is copied, so AppContext.BaseDirectory/data is intentionally absent.
s=s.replace('Path.Combine(AppContext.BaseDirectory, \\"data\\", \\"release_notes.json\\")', 'Path.Combine(repoRoot, \\"data\\", \\"release_notes.json\\")')
s=s.replace('R28 release_notes.json missing from payload.', 'R28 release_notes.json missing from source data.')

# Fold compile compatibility corrections into the patch before it generates C#.
s=s.replace('OnPropertyChanged(nameof(CleanupProgressText));','RaisePropertyChanged(nameof(CleanupProgressText));')
s=s.replace('result.SnapshotId?.ToString("N")[..8]', '(result.SnapshotId is Guid cleanupSnapshotId ? cleanupSnapshotId.ToString("N")[..8] : "—")')
patch.write_text(s,encoding='utf-8')

# The R24 updater's exact MessageBox block can vary across trusted-source
# revisions. Install a robust silent-start notification hook directly into the
# generated source before R26/R27/R28 continue patching it.
root=Path(os.environ['SOURCE_ROOT'])
vm=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
v=vm.read_text(encoding='utf-8-sig')
if 'ReleaseNotesWindow.ShowUpdateAvailable' not in v:
    method=v.find('    private async Task CheckUpdatesAsync(bool silent)')
    if method < 0:
        raise SystemExit('R28 update-check method missing')
    needle='            DownloadUpdateCommand.RaiseCanExecuteChanged();\n'
    pos=v.find(needle,method)
    if pos < 0:
        raise SystemExit('R28 update notification insertion point missing')
    pos += len(needle)
    hook='''            if (silent && _lastUpdateCheck is { Success: true, UpdateAvailable: true } startupUpdate && !string.Equals(_lastNotifiedUpdateVersion, startupUpdate.LatestVersion, StringComparison.OrdinalIgnoreCase))
            {
                _lastNotifiedUpdateVersion = startupUpdate.LatestVersion;
                global::MerzoOptimizer.App.ReleaseNotesWindow.ShowUpdateAvailable(Application.Current?.MainWindow, startupUpdate);
            }
'''
    v=v[:pos]+hook+v[pos:]
    vm.write_text(v,encoding='utf-8')

print('R28 patch compatibility rewrite: OK')
