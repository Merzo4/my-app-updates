import os
import pathlib
import re

root = pathlib.Path(os.environ['MERZO_SRC'])

# 1) Restore the exact primary Media resolver behavior from 0.1.0m.
media_path = root / 'src' / 'MerzoStream.Foundation' / 'Services' / 'MediaQueueService.cs'
media = media_path.read_text(encoding='utf-8-sig')
resolve_rx = re.compile(r'    private async Task<MediaItem\?> ResolveAsync\(string query, CancellationToken ct\)\n    \{.*?\n    \}\n\n    private async Task<\(string title, string channel\)> OEmbedAsync', re.S)
resolve_replacement = '''    private async Task<MediaItem?> ResolveAsync(string query, CancellationToken ct)
    {
        var direct = ExtractVideoId(query);
        if (!string.IsNullOrWhiteSpace(direct))
        {
            var meta = await OEmbedAsync(direct, ct);
            return new MediaItem { VideoId = direct, Title = meta.title.Length > 0 ? meta.title : query, OriginalQuery = query };
        }

        // RECOVERY R2: exact primary search path from the last pre-regression build.
        // Do NOT silently add a second "официальный клип" query here: that changed
        // the winning result for short literal requests such as "Само собой".
        var candidates = await SearchAsync(query, ct);
        var ranked = candidates
            .Select(x => new { x.Id, x.Title, x.Channel, x.Views, x.Verified, x.Official, score = Score(query, x.Title, x.Channel, x.Views, x.Verified, x.Official) })
            .OrderByDescending(x => x.score)
            .ThenByDescending(x => x.Views)
            .ToArray();
        if (ranked.Length == 0 || string.IsNullOrWhiteSpace(ranked[0].Id)) return null;
        var best = ranked[0];
        var item = new MediaItem { VideoId = best.Id, Title = best.Title, OriginalQuery = query };
        var floor = best.score - 360;
        item.Fallbacks = ranked.Skip(1).Where(x => x.score >= floor).Take(8).Select(x => new MediaFallback(x.Id, x.Title, x.Channel)).ToList();
        return item;
    }

    private async Task<(string title, string channel)> OEmbedAsync'''
media, count = resolve_rx.subn(resolve_replacement, media, count=1)
if count != 1:
    raise SystemExit(f'0.1.0r R2 ResolveAsync replacement failed: {count}')
old_penalty = '''                                  " tik tok ", " tiktok ", " shorts ", " dance ", " танец ", " fan edit ", " edit ", " amv ", " meme " })'''
new_penalty = '''                                  " tik tok ", " tiktok ", " shorts " })'''
if old_penalty not in media:
    raise SystemExit('0.1.0r R2 score penalty anchor missing')
media = media.replace(old_penalty, new_penalty, 1)
media_path.write_text(media, encoding='utf-8')

# 2) Restore the exact player timing/event shape used in 0.1.0m.
player_path = root / 'src' / 'MerzoStream.Foundation' / 'Services' / 'LocalPlayerServer.cs'
player = player_path.read_text(encoding='utf-8-sig')
old_ready = "events:{onReady:()=>{if(last)player.playVideo()},onStateChange:"
new_ready = "events:{onStateChange:"
if old_ready not in player:
    raise SystemExit('0.1.0r R2 player onReady anchor missing')
player = player.replace(old_ready, new_ready, 1)
if 'setInterval(tick,300)' not in player:
    raise SystemExit('0.1.0r R2 player 300ms anchor missing')
player = player.replace('setInterval(tick,300)', 'setInterval(tick,250)', 1)
player = player.replace('// protected 0.1.0e player transport restored + later blank/clear safety retained', '// protected 0.1.0e player transport restored • RECOVERY R2 exact 0.1.0m timing + blank/clear safety')
player_path.write_text(player, encoding='utf-8')

# 3) Native title bar must own a real layout row instead of overlaying WebView by 34 px.
main_path = root / 'src' / 'MerzoStream.Host' / 'MainForm.cs'
main = main_path.read_text(encoding='utf-8-sig')
fields_old = '''    private readonly Button _closeButton = ChromeButton("×", true);\n    private DotNetBackend? _backend;'''
fields_new = '''    private readonly Button _closeButton = ChromeButton("×", true);\n    private readonly Panel _contentHost = new() { Dock = DockStyle.Fill, Margin = Padding.Empty, Padding = Padding.Empty, BackColor = Color.FromArgb(7, 11, 18) };\n    private readonly TableLayoutPanel _rootLayout = new() { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 2, Margin = Padding.Empty, Padding = Padding.Empty, BackColor = Color.FromArgb(7, 11, 18) };\n    private DotNetBackend? _backend;'''
if fields_old not in main:
    raise SystemExit('0.1.0r R2 MainForm fields anchor missing')
main = main.replace(fields_old, fields_new, 1)
controls_old = '''        _nativeStatus.Visible = false;\n        InitializeCustomChrome();\n        Controls.Add(_webView);\n        Controls.Add(_nativeStatus);\n        Controls.Add(_titleBar);\n        _titleBar.BringToFront();\n        Shown += async (_, _) => await StartHostAsync();'''
controls_new = '''        _nativeStatus.Visible = false;\n        InitializeCustomChrome();\n\n        // RECOVERY R2: title bar and WebView live in separate rows.\n        // The previous BringToFront + Dock.Top combination physically covered the\n        // first 34 px of the web UI and clipped page titles/top controls.\n        _rootLayout.RowStyles.Add(new RowStyle(SizeType.Absolute, 0));\n        _rootLayout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));\n        _titleBar.Dock = DockStyle.Fill;\n        _contentHost.Controls.Add(_webView);\n        _contentHost.Controls.Add(_nativeStatus);\n        _rootLayout.Controls.Add(_titleBar, 0, 0);\n        _rootLayout.Controls.Add(_contentHost, 0, 1);\n        Controls.Add(_rootLayout);\n        Shown += async (_, _) => await StartHostAsync();'''
if controls_old not in main:
    raise SystemExit('0.1.0r R2 MainForm control layout anchor missing')
main = main.replace(controls_old, controls_new, 1)
ready_old = '''            _titleBar.Visible = true;\n            _titleBar.BringToFront();\n            ApplyDarkWindowChrome();'''
ready_new = '''            _rootLayout.RowStyles[0].Height = 34;\n            _titleBar.Visible = true;\n            _rootLayout.PerformLayout();\n            ApplyDarkWindowChrome();'''
if ready_old not in main:
    raise SystemExit('0.1.0r R2 MainForm ready chrome anchor missing')
main = main.replace(ready_old, ready_new, 1)
main_path.write_text(main, encoding='utf-8')

# 4) Do not rewrite unchanged labels during polling; this removes the visible title flicker.
app_path = root / 'ui' / 'web' / 'app.js'
app = app_path.read_text(encoding='utf-8-sig')
settext_old = "function setText(sel,text){const e=$(sel);if(e)e.textContent=text}"
settext_new = "function setText(sel,text){const e=$(sel);if(!e)return;const next=String(text??'');if(e.textContent!==next)e.textContent=next}"
if settext_old not in app:
    raise SystemExit('0.1.0r R2 setText anchor missing')
app = app.replace(settext_old, settext_new, 1)
app_path.write_text(app, encoding='utf-8')

# 5) Extend the static acceptance test with the exact regressions seen on the user's PC.
selftest_path = root / 'SELFTEST_PURE_DOTNET_STATIC.ps1'
selftest = selftest_path.read_text(encoding='utf-8-sig')
needle = "  Check ($main.Contains('_titleBar') -and $main.Contains('WM_NCHITTEST') -and -not $main.Contains('FormBorderStyle.Sizable')) '0.1.0q custom dark window chrome missing or native titlebar restored'"
resolver_signature = 'private async Task<(string title, string channel)> OEmbedAsync'
r2_checks = f'''  Check ($main.Contains('TableLayoutPanel _rootLayout') -and $main.Contains('_rootLayout.RowStyles[0].Height = 34') -and $main.Contains('_rootLayout.Controls.Add(_contentHost, 0, 1)') -and -not $main.Contains('_titleBar.BringToFront();')) '0.1.0r R2 titlebar still overlays WebView'\n  $resolveStart=$media.IndexOf('ResolveAsync'); $resolveEnd=$media.IndexOf('{resolver_signature}',$resolveStart); $resolveBlock=$media.Substring($resolveStart,$resolveEnd-$resolveStart)\n  Check (-not $resolveBlock.Contains('officialCandidates') -and $resolveBlock.Contains('var candidates = await SearchAsync(query, ct);')) '0.1.0r R2 primary Media resolver is not the pre-regression one-query path'\n  Check ($localPlayer.Contains('setInterval(tick,250)') -and -not $localPlayer.Contains('onReady:()=>{{if(last)player.playVideo()}}')) '0.1.0r R2 player timing/event path is not restored to 0.1.0m'\n  Check ($ui.Contains('e.textContent!==next')) '0.1.0r R2 stable label update guard missing'\n'''
if r2_checks.strip() not in selftest:
    if needle not in selftest:
        raise SystemExit('0.1.0r R2 selftest injection anchor missing')
    selftest = selftest.replace(needle, r2_checks + needle, 1)
    selftest_path.write_text(selftest, encoding='utf-8')

# 6) Make the recovery build self-identifying in release notes without changing app version.
notes_path = root / 'RELEASE_NOTES_0.1.0r.md'
notes = notes_path.read_text(encoding='utf-8-sig')
marker = '\n## RECOVERY R2 — protected regression restoration\n'
if marker.strip() not in notes:
    notes += marker + '''\n- Primary Media resolver restored to the exact 0.1.0m one-query path; hidden `официальный клип` second search removed from real requests.\n- Local YouTube player event/timing path restored to 0.1.0m while retaining stale-video blank/clear protection.\n- Custom title bar moved into its own WinForms layout row; it no longer overlays the WebView.\n- Repeated polling no longer rewrites unchanged labels, removing Media title flicker.\n'''
    notes_path.write_text(notes, encoding='utf-8')

# Final invariants. Use the next method signature as the boundary; OEmbedAsync is also
# called inside ResolveAsync for direct URLs, so searching for the bare token is wrong.
media_check = media_path.read_text(encoding='utf-8')
resolve_start = media_check.index('ResolveAsync')
resolve_end = media_check.index(resolver_signature, resolve_start)
resolve_block = media_check[resolve_start:resolve_end]
if 'officialCandidates' in resolve_block or 'var candidates = await SearchAsync(query, ct);' not in resolve_block:
    raise SystemExit('0.1.0r R2 primary resolver is not the exact one-query path')
player_check = player_path.read_text(encoding='utf-8')
player_block = player_check[player_check.index('private const string PlayerHtml'):player_check.index('private const string ChatHtml')]
for required in ('setInterval(tick,250)', 'function blank()', 'player.clearVideo', 'protected 0.1.0e player transport restored'):
    if required not in player_block:
        raise SystemExit(f'0.1.0r R2 player invariant missing: {required}')
for forbidden in ('onReady:()=>{if(last)player.playVideo()}', 'youtube-nocookie.com', 'startup-timeout'):
    if forbidden in player_block:
        raise SystemExit(f'0.1.0r R2 player regression remains: {forbidden}')
main_check = main_path.read_text(encoding='utf-8')
for required in ('TableLayoutPanel _rootLayout', '_rootLayout.RowStyles[0].Height = 34', '_rootLayout.Controls.Add(_contentHost, 0, 1)'):
    if required not in main_check:
        raise SystemExit(f'0.1.0r R2 chrome invariant missing: {required}')
if '_titleBar.BringToFront();' in main_check:
    raise SystemExit('0.1.0r R2 titlebar overlay call still present')
if 'e.textContent!==next' not in app_path.read_text(encoding='utf-8'):
    raise SystemExit('0.1.0r R2 stable setText invariant missing')

print('0.1.0r RECOVERY R2 FINALIZE PASS: exact m resolver/player + non-overlay chrome + stable labels + regression tests')
