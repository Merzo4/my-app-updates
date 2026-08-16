from pathlib import Path

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
    gate=r''' + "'''    foreach (var token in new[] { \"Header=\\\"Ход очистки\\\"\", \"SelectedCleanupTabIndex\", \"CleanupOperationSteps\", \"UpdateReleaseNotesText\", \"Что нового\" }) if (!xaml.Contains(token, StringComparison.Ordinal)) failures.Add($\"R28 UX missing: {token}\");\n    if (xaml.Contains(\"Header=\\\"Телеметрия\\\"\", StringComparison.Ordinal)) failures.Add(\"Telemetry must be integrated into profiles, not shown as a separate R28 tab.\");\n    if (!File.Exists(Path.Combine(AppContext.BaseDirectory, \"data\", \"release_notes.json\"))) failures.Add(\"R28 release_notes.json missing from payload.\");\n'''" + '''
    anchor_pos=q.find('Technical tweak IDs must stay hidden from user cards.')
    if anchor_pos < 0: raise SystemExit('SelfTest UI anchor missing')
    line_end=q.find('\\n', anchor_pos)
    if line_end < 0: line_end=len(q)
    q=q[:line_end+1]+gate+q[line_end+1:]'''

if old not in s:
    # Fallback targeted rewrite for slight formatting changes.
    start=s.find("ui_anchor='''")
    end=s.find("q=q.replace(ui_anchor,ui_anchor+gate,1)", start)
    if start < 0 or end < 0:
        raise SystemExit('R28 SelfTest block not found in patch script')
    end += len("q=q.replace(ui_anchor,ui_anchor+gate,1)")
    s=s[:start]+new+s[end:]
else:
    s=s.replace(old,new,1)

# Fold compile compatibility corrections into the patch before it generates C#.
s=s.replace('OnPropertyChanged(nameof(CleanupProgressText));','RaisePropertyChanged(nameof(CleanupProgressText));')
s=s.replace('result.SnapshotId?.ToString("N")[..8]', '(result.SnapshotId is Guid cleanupSnapshotId ? cleanupSnapshotId.ToString("N")[..8] : "—")')

patch.write_text(s,encoding='utf-8')
print('R28 patch compatibility rewrite: OK')
