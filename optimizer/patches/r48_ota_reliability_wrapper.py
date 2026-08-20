from pathlib import Path
import os

p=Path(__file__).with_name('r48_ota_reliability.py')
s=p.read_text(encoding='utf-8')
old="expected='046f883dbbbcdac5a3ed1a674f7c2f87c36c07a0dfb2d9b6de73cd9fa566434a'"
new="expected='fce7c1ab1d6224ee7490ef615b8ae1d1458427f428c58fa302f65603e2565191'"
if s.count(old)!=1:
    raise SystemExit('R48 wrapper baseline anchor mismatch')
s=s.replace(old,new,1)
exec(compile(s,str(p),'exec'))

# R48 intentionally replaces the single fragile releases?per_page=50 path
# with retry + a smaller releases list + two tag-based fallback paths.
root=Path(os.environ['SOURCE_ROOT'])
st=root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
t=st.read_text(encoding='utf-8-sig')
old_test='foreach (var token in new[] { "releases?per_page=50", "digest", "sha256:", "SHA256.HashDataAsync", "FixedTimeEquals" }) if (!source.Contains(token, StringComparison.Ordinal)) failures.Add($"Verified updater requirement missing: {token}");'
new_test='foreach (var token in new[] { "releases?per_page=20", "matching-refs/tags", "releases/tags/", "tags?per_page=100", "GetJsonWithRetryAsync", "HttpStatusCode.GatewayTimeout", "digest", "sha256:", "SHA256.HashDataAsync", "FixedTimeEquals" }) if (!source.Contains(token, StringComparison.Ordinal)) failures.Add($"R48 resilient updater requirement missing: {token}");'
if t.count(old_test)!=1:
    raise SystemExit(f'R48 SelfTest updater anchor count={t.count(old_test)}')
st.write_text(t.replace(old_test,new_test,1),encoding='utf-8')
(root/'R48_SELFTEST_FINALIZE.marker').write_text('R48 resilient updater SelfTest\n',encoding='utf-8')
print('R48 updater + SelfTest wrapper: OK')
