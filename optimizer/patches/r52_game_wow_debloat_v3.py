from pathlib import Path

p=Path(__file__).with_name('r52_game_wow_debloat.py')
s=p.read_text(encoding='utf-8')

old="    private static async Task<string> RunFixedPowerShellAsync(string script, TimeSpan timeout)\\n"
new="    private static async Task<string> RunFixedPowerShellAsync(string script, TimeSpan timeoutValue)\\n"
if old not in s: raise SystemExit('R52 GAME V3 helper anchor source missing')
s=s.replace(old,new,1)

old='''final_anchor=\'\'\'            Stage2StatusText = gamingBuild\\n                ? $"Gaming Build применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count} · Network: {gamingNetworkMode}."\'\'\''''
new='''final_anchor=\'\'\'            Stage2StatusText = gamingBuild\\n                ? $"Gaming Build применён: {done} шагов · Snapshot: {appliedSnapshotIds.Count} · Network: {gamingNetworkMode} · Recovery: {(recoveryPackage?.Success == true ? "готов" : "Snapshot/Undo")}."\'\'\''''
if old not in s: raise SystemExit('R52 GAME V3 final-status source anchor missing')
s=s.replace(old,new,1)

# Keep Recovery information in the new final status as well. Double quotes are
# intentionally NOT backslash-escaped here: this text becomes real C# code.
old='''? $"Gaming Build применён: {done} шагов · Appx удалено {gamingDebloatRemoved} · процессы {processCountBefore} → {processCountAfter} сейчас · Snapshot: {appliedSnapshotIds.Count} · Network: {gamingNetworkMode}. После перезагрузки выполните повторный аудит для финального результата."'''
new='''? $"Gaming Build применён: {done} шагов · Appx удалено {gamingDebloatRemoved} · процессы {processCountBefore} → {processCountAfter} сейчас · Snapshot: {appliedSnapshotIds.Count} · Network: {gamingNetworkMode} · Recovery: {(recoveryPackage?.Success == true ? "готов" : "Snapshot/Undo")}. После перезагрузки выполните повторный аудит для финального результата."'''
if old not in s: raise SystemExit('R52 GAME V3 final-new source anchor missing')
s=s.replace(old,new,1)

exec(compile(s,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
print('R52 GAME WOW V3 exact-R51 wrapper: OK')
