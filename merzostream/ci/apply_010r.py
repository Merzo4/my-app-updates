import base64, hashlib, lzma, os, pathlib, subprocess

root = pathlib.Path(os.environ['MERZO_SRC'])
tmp = pathlib.Path(os.environ.get('RUNNER_TEMP', str(root.parent)))
CHUNK_SHAS = [
    '606e10fdc2cdfe4b6b20385be19cf6b5b2cdec969406255df345657162b21053',
    '37017d459847bdcf36db2e8ea110ea33d8287306c0119da684d5661a14787e7e',
    '58f19611697aeae7a2a2ece3d0624433e9b7f7de75cd596f45f68a70819f7068',
]
XZ_SHA = '017999221d52c582fc667ac3f9adb4253cde7fbe875d7744aa6bfb085a95a1cc'
RAW_SHA = '26ad5886e14eb164f7482fea607eee937b68712cdb0b69ca72e3a5fc657a9b45'

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def replace_text(rel, pairs):
    p = root / rel
    text = p.read_text(encoding='utf-8-sig')
    for old, new in pairs:
        if old not in text:
            raise SystemExit(f'0.1.0r finalize missing expected text in {rel}: {old[:100]}')
        text = text.replace(old, new)
    p.write_text(text, encoding='utf-8')

parts_dir = pathlib.Path(__file__).resolve().parent / '010r-b64'
encoded = []
for i, expected in enumerate(CHUNK_SHAS):
    p = parts_dir / f'chunk{i:02d}.txt'
    raw = p.read_bytes().strip()
    actual = sha(raw)
    if actual != expected:
        raise SystemExit(f'0.1.0r {p.name} SHA mismatch: {actual} != {expected}')
    encoded.append(raw.decode('ascii'))

xz = base64.urlsafe_b64decode(''.join(encoded))
if sha(xz) != XZ_SHA:
    raise SystemExit(f'0.1.0r XZ SHA mismatch: {sha(xz)} != {XZ_SHA}')
patch = lzma.decompress(xz)
if sha(patch) != RAW_SHA:
    raise SystemExit(f'0.1.0r raw SHA mismatch: {sha(patch)} != {RAW_SHA}')

patch_path = tmp / 'merzostream-010r.patch'
patch_path.write_bytes(patch)
subprocess.run(['git', 'apply', '--check', '--binary', str(patch_path)], cwd=root, check=True)
subprocess.run(['git', 'apply', '--binary', str(patch_path)], cwd=root, check=True)
print('0.1.0r RECOVERY PATCH PASS', RAW_SHA, 'xz', XZ_SHA, 'chunks', len(CHUNK_SHAS))

# Finalize the recovery identity everywhere. This deliberately happens after the q->r
# binary/text recovery patch so the built runtime cannot identify itself as q internally.
replace_text('src/MerzoStream.Setup/Program.cs', [
    ('private const string Version = "0.1.0q"', 'private const string Version = "0.1.0r"'),
    ('MerzoStream Suite 0.1.0q установлен', 'MerzoStream Suite 0.1.0r установлен'),
])
replace_text('src/MerzoStream.Foundation/Services/UpdateService.cs', [
    ('MerzoStreamSuite-PureDotNet-Update/0.1.0q', 'MerzoStreamSuite-PureDotNet-Update/0.1.0r'),
])
replace_text('src/MerzoStream.Foundation/Services/DonationAlertsService.cs', [
    ('MerzoStreamSuite/0.1.0q', 'MerzoStreamSuite/0.1.0r'),
])
replace_text('src/MerzoStream.Host/MainForm.cs', [
    ("setSplashVersion('0.1.0q')", "setSplashVersion('0.1.0r')"),
    ('0.1.0q owns the title bar', '0.1.0r keeps the recovered title bar'),
])
replace_text('src/MerzoStream.Host/DotNetBackend.cs', [
    ('public const string DevVersion = "0.1.0q"', 'public const string DevVersion = "0.1.0r"'),
    ('0.1.0q • FIELD FIX • MEDIA + VK LOGIN + BRAND + CHROME • PURE .NET', '0.1.0r • RECOVERY • PROTECTED MEDIA + VK LOGIN • PURE .NET'),
])
replace_text('ui/web/index.html', [('010q-r1', '010r-recovery1')])
replace_text('ui/web/splash.html', [('0.1.0q', '0.1.0r')])
replace_text('ui/web/app_info.json', [
    ('Pure .NET 0.1.0q', 'Pure .NET 0.1.0r'),
    ('PURE .NET 0.1.0q', 'PURE .NET 0.1.0r'),
])
replace_text('content/app_info.json', [
    ('Pure .NET 0.1.0q', 'Pure .NET 0.1.0r'),
    ('PURE .NET 0.1.0q', 'PURE .NET 0.1.0r'),
])
replace_text('06_BUILD_RUNTIME_RELEASE.ps1', [("$Version='0.1.0q'", "$Version='0.1.0r'")])
replace_text('08_BUILD_BRANDED_SETUP.ps1', [("$Version='0.1.0q'", "$Version='0.1.0r'")])
replace_text('tools/MerzoStream.Foundation.SelfTest/Program.cs', [('0.1.0q', '0.1.0r')])

# The q selftest encoded the q experiment as a requirement. Recovery changes that
# requirement into a non-regression assertion for the previously protected player path.
selftest = root / 'SELFTEST_PURE_DOTNET_STATIC.ps1'
st = selftest.read_text(encoding='utf-8-sig')
for old, new in [
    ('RELEASE_NOTES_0.1.0q.md', 'RELEASE_NOTES_0.1.0r.md'),
    ("setSplashVersion('0.1.0q')", "setSplashVersion('0.1.0r')"),
    ('public const string DevVersion = "0.1.0q"', 'public const string DevVersion = "0.1.0r"'),
    ('backend version is not 0.1.0q', 'backend version is not 0.1.0r'),
    ('MerzoStreamSuite-PureDotNet-Update/0.1.0q', 'MerzoStreamSuite-PureDotNet-Update/0.1.0r'),
    ('concept.css?v=010q-r1', 'concept.css?v=010r-recovery1'),
    ("$splash.Contains('0.1.0q')", "$splash.Contains('0.1.0r')"),
    ("String(v||'0.1.0q')", "String(v||'0.1.0r')"),
    ('private const string Version = "0.1.0q"', 'private const string Version = "0.1.0r"'),
    ("[string]`$Version='0.1.0q'", "[string]`$Version='0.1.0r'"),
    ("$appInfo.version -eq '0.1.0q'", "$appInfo.version -eq '0.1.0r'"),
    ('PURE DOTNET 0.1.0q STATIC SELFTEST PASS', 'PURE DOTNET 0.1.0r RECOVERY STATIC SELFTEST PASS'),
    ('PURE DOTNET 0.1.0q STATIC SELFTEST FAIL', 'PURE DOTNET 0.1.0r RECOVERY STATIC SELFTEST FAIL'),
]:
    if old not in st:
        raise SystemExit(f'0.1.0r static finalize missing expected text: {old}')
    st = st.replace(old, new)
old_watchdog = "Check ($localPlayer.Contains('startup-timeout') -and $localPlayer.Contains('loadDeadline')) '0.1.0q Media player startup watchdog missing'"
new_watchdog = "Check (-not $localPlayer.Contains('startup-timeout') -and -not $localPlayer.Contains('youtube-nocookie.com') -and $localPlayer.Contains('protected 0.1.0e player transport restored')) '0.1.0r protected Media player transport regressed'\n  Check ($media.Contains('PROTECTED MEDIA RECOVERY 0.1.0r') -and $ui.Contains(\"api('media_add_test',q)\") -and -not $ui.Contains(\"const r=await api('media_search',q);\")) '0.1.0r protected Media request path regressed'"
if old_watchdog not in st:
    raise SystemExit('0.1.0r static finalize missing q watchdog assertion')
st = st.replace(old_watchdog, new_watchdog)
old_vk = "Check ($vkAuth.Contains('VkAuthWebView2_v2') -and $vkAuth.Contains('sessionStorage') -and $vkAuth.Contains('NavigationCompleted') -and -not $backend.Contains('developer_gate=true')) 'user-facing VK login diagnostics/session capture regression'"
new_vk = "Check ($vkAuth.Contains('Path.Combine(AppPaths.DataDirectory(), \"WebView2\")') -and $vkAuth.Contains('WaitAsync(TimeSpan.FromSeconds(15))') -and $vkAuth.Contains('sessionStorage') -and $vkAuth.Contains('NavigationCompleted') -and -not $vkAuth.Contains('VkAuthWebView2_v2') -and -not $backend.Contains('developer_gate=true')) '0.1.0r VK shared WebView2 recovery regressed'"
if old_vk not in st:
    raise SystemExit('0.1.0r static finalize missing q VK assertion')
st = st.replace(old_vk, new_vk)
selftest.write_text(st, encoding='utf-8')
print('0.1.0r VERSION + SELFTEST FINALIZE PASS')

# Merge the old direct YouTube player transport with the later proven blank/clear safety.
# This intentionally avoids q's nocookie/startup-watchdog experiment while preserving
# transparent empty state and stale-video suppression after Skip/Clear.
finalizer = pathlib.Path(__file__).resolve().with_name('finalize_010r_player.py')
subprocess.run(['python', str(finalizer)], check=True)
