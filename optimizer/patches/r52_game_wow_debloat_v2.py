from pathlib import Path

p=Path(__file__).with_name('r52_game_wow_debloat.py')
s=p.read_text(encoding='utf-8')
old="    private static async Task<string> RunFixedPowerShellAsync(string script, TimeSpan timeout)\\n"
new="    private static async Task<string> RunFixedPowerShellAsync(string script, TimeSpan timeoutValue)\\n"
if old not in s:
    raise SystemExit('R52 GAME WOW V2 helper anchor source not found')
s=s.replace(old,new,1)
code=compile(s,str(p),'exec')
exec(code,{'__name__':'__main__','__file__':str(p)})
print('R52 GAME WOW V2 helper-anchor wrapper: OK')
