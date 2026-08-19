import os
import pathlib

root = pathlib.Path(os.environ['MERZO_SRC'])
p = root / 'SELFTEST_PURE_DOTNET_STATIC.ps1'
text = p.read_text(encoding='utf-8-sig')
old = '''Check ($media.Contains('PROTECTED MEDIA RECOVERY 0.1.0r') -and $ui.Contains("api('media_add_test',q)") -and -not $ui.Contains("const r=await api('media_search',q);")) '0.1.0r protected Media request path regressed' '''.strip()
new = '''Check ($ui.Contains("api('media_add_test',q)") -and -not $ui.Contains("const r=await api('media_search',q);")) '0.1.0r protected Media request path regressed' '''.strip()
if old in text:
    text = text.replace(old, new, 1)
elif new not in text:
    raise SystemExit('0.1.0r R2 stale Media selftest assertion not found')
p.write_text(text, encoding='utf-8')
print('0.1.0r R2 STATIC SELFTEST STALE MARKER FIX PASS')
