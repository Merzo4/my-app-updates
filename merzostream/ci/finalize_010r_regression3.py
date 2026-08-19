import os, pathlib, re
root=pathlib.Path(os.environ['MERZO_SRC'])

# 1. Restore the actual 0.1.0e primary YouTube search path for REAL queue additions.
# New preview/search UI may keep richer parser, but AddTest/AddExternal use the old
# videoRenderer-only search + old relevance/official score that was proven on the user's PC.
media_path=root/'src/MerzoStream.Foundation/Services/MediaQueueService.cs'
media=media_path.read_text(encoding='utf-8-sig')
resolve_rx=re.compile(r'    private async Task<MediaItem\?> ResolveAsync\(string query, CancellationToken ct\)\n    \{.*?\n    \}\n\n    private async Task<\(string title, string channel\)> OEmbedAsync',re.S)
resolve='''    private async Task<MediaItem?> ResolveAsync(string query, CancellationToken ct)
    {
        var direct = ExtractVideoId(query);
        if (!string.IsNullOrWhiteSpace(direct))
        {
            var meta = await OEmbedAsync(direct, ct);
            return new MediaItem { VideoId = direct, Title = meta.title.Length > 0 ? meta.title : query, OriginalQuery = query };
        }

        // RECOVERY R3: exact proven 0.1.0e primary search/ranking path.
        // Important: this intentionally does not use the later recursive ytInitialData
        // candidate collector for the REAL queue, because that pulled unrelated shelves/shorts.
        var candidates = await SearchPrimaryLegacyAsync(query, ct);
        var ranked = candidates
            .Select(x => new { x.id, x.title, x.channel, score = ScorePrimaryLegacy(query, x.title, x.channel) })
            .OrderByDescending(x => x.score)
            .ToArray();
        if (ranked.Length == 0 || string.IsNullOrWhiteSpace(ranked[0].id)) return null;
        var best = ranked[0];
        var item = new MediaItem { VideoId = best.id, Title = best.title, OriginalQuery = query };
        var floor = best.score - 260;
        item.Fallbacks = ranked.Skip(1).Where(x => x.score >= floor).Take(6).Select(x => new MediaFallback(x.id, x.title, x.channel)).ToList();
        return item;
    }

    private async Task<List<(string id, string title, string channel)>> SearchPrimaryLegacyAsync(string query, CancellationToken ct)
    {
        using var req = new HttpRequestMessage(HttpMethod.Get, "https://www.youtube.com/results?search_query=" + Uri.EscapeDataString(query));
        req.Headers.UserAgent.ParseAdd("Mozilla/5.0 MerzoStream/0.1");
        using var resp = await _http.SendAsync(req, ct); resp.EnsureSuccessStatusCode();
        var html = await resp.Content.ReadAsStringAsync(ct);
        var rx = new Regex(@"""videoRenderer"":\{""videoId"":""(?<id>[A-Za-z0-9_-]{11})"".*?""title"":\{""runs"":\[\{""text"":""(?<title>(?:\\.|[^""])*)"".*?""ownerText"":\{""runs"":\[\{""text"":""(?<channel>(?:\\.|[^""])*)""", RegexOptions.Singleline);
        var list = new List<(string, string, string)>(); var seen = new HashSet<string>();
        foreach (Match m in rx.Matches(html))
        {
            var id = m.Groups["id"].Value; if (!seen.Add(id)) continue;
            var title = UnescapeJson(m.Groups["title"].Value); var channel = UnescapeJson(m.Groups["channel"].Value);
            if (title.Length == 0) continue; list.Add((id, title, channel)); if (list.Count >= 30) break;
        }
        return list;
    }

    private static double ScorePrimaryLegacy(string query, string title, string channel)
    {
        static string N(string s) => Regex.Replace((s ?? "").ToLowerInvariant().Replace('ё', 'е'), @"[^\p{L}\p{N}]+", " ").Trim();
        var q = N(query); var t = N(title); var c = N(channel); if (q.Length == 0) return 0;
        var tokens = q.Split(' ', StringSplitOptions.RemoveEmptyEntries); var titleWords = t.Split(' ', StringSplitOptions.RemoveEmptyEntries).ToHashSet(); var combined = (t + " " + c).Split(' ', StringSplitOptions.RemoveEmptyEntries).ToHashSet();
        double score = 0;
        if (t == q) score += 760; else if (t.Contains(q, StringComparison.Ordinal)) score += 520;
        var matched = tokens.Count(combined.Contains); var titleMatched = tokens.Count(titleWords.Contains);
        score += (double)matched / tokens.Length * 245 + (double)titleMatched / tokens.Length * 95;
        if (matched == tokens.Length) score += 185; else if (tokens.Length >= 2) score -= 300 + (tokens.Length - matched) * 220;
        if (t.StartsWith(q, StringComparison.Ordinal)) score += 70;
        var all = " " + t + " " + c + " ";
        foreach (var p in new[] { " official music video ", " official video ", " официальный клип ", " премьера клипа ", " music video " }) if (all.Contains(p, StringComparison.Ordinal)) score += 300;
        foreach (var p in new[] { " remix ", " cover ", " караоке ", " live ", " reaction ", " концерт ", " выступление " }) if (all.Contains(p, StringComparison.Ordinal) && !q.Contains(p.Trim(), StringComparison.Ordinal)) score -= 350;
        return score;
    }

    private async Task<(string title, string channel)> OEmbedAsync'''
media,n=resolve_rx.subn(lambda _: resolve,media,count=1)
if n!=1: raise SystemExit(f'R3 Resolve replacement failed {n}')

# Heartbeat is diagnostic only. Never convert a non-playing YouTube state into "playing".
old='''                case "playing":
                case "heartbeat":
                    _playbackStatus = "playing"; _paused = false; _stopped = false;
                    break;'''
new='''                case "playing":
                    _playbackStatus = "playing"; _paused = false; _stopped = false;
                    break;
                case "heartbeat":
                    // RECOVERY R3: heartbeat proves the page is alive, not that video is playing.
                    break;'''
if old not in media: raise SystemExit('R3 heartbeat switch anchor missing')
media=media.replace(old,new,1)
media_path.write_text(media,encoding='utf-8')

# 2. Restore the actual 0.1.0e PlayerHtml, byte-for-byte in behavior.
player_path=root/'src/MerzoStream.Foundation/Services/LocalPlayerServer.cs'
player=player_path.read_text(encoding='utf-8-sig')
rx=re.compile(r'    private const string PlayerHtml = """\n.*?\n""";\n\n    private const string ChatHtml = """',re.S)
block='''    private const string PlayerHtml = """
<!doctype html><html><head><meta charset="utf-8"><style>html,body,#p{margin:0;width:100%;height:100%;background:#000;overflow:hidden}iframe{border:0}</style></head><body><div id="p"></div><script src="https://www.youtube.com/iframe_api"></script><script>
// RECOVERY R3: actual 0.1.0e player transport restored.
let player=null,last='',rev=-1,generation=-1,preview=new URLSearchParams(location.search).get('preview')==='1';
function post(state,error=''){if(!player||!last)return;const actual=String(player.getVideoData?.()?.video_id||last||'');fetch('/player-event',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({state,position:Number(player.getCurrentTime?.()||0),duration:Number(player.getDuration?.()||0),error,generation,video_id:actual})}).catch(()=>{})}
window.onYouTubeIframeAPIReady=()=>{player=new YT.Player('p',{width:'100%',height:'100%',playerVars:{autoplay:1,controls:1,rel:0,playsinline:1},events:{onStateChange:e=>{if(e.data===YT.PlayerState.PLAYING)post('playing');else if(e.data===YT.PlayerState.PAUSED)post('paused');else if(e.data===YT.PlayerState.ENDED)post('ended')},onError:e=>post('error',String(e.data))}})};
async function tick(){try{const s=await (await fetch('/state',{cache:'no-store'})).json();if(!player)return;const nextGen=Number(s.generation??-1);if(nextGen!==generation)generation=nextGen;if(s.video_id&&s.video_id!==last){last=s.video_id;player.loadVideoById({videoId:last,startSeconds:Number(s.position||0)});player.setVolume(Number(s.volume||30));if(preview)player.setVolume(0)}if(s.revision!==rev){rev=s.revision;player.setVolume(preview?0:Number(s.volume||30));if(s.stopped||!s.video_id){player.stopVideo();if(!s.video_id){player.clearVideo?.();last=''}}else if(s.paused)player.pauseVideo();else player.playVideo();if(s.video_id){const delta=Math.abs(Number(player.getCurrentTime?.()||0)-Number(s.position||0));if(delta>2.5)player.seekTo(Number(s.position||0),true)}}}catch{}}setInterval(tick,300);setInterval(()=>{if(player&&last)post(player.getPlayerState?.()===1?'playing':'heartbeat')},1200);
</script></body></html>
""";

    private const string ChatHtml = """'''
player,n=rx.subn(lambda _: block,player,count=1)
if n!=1: raise SystemExit(f'R3 PlayerHtml replacement failed {n}')
player_path.write_text(player,encoding='utf-8')

# 3. Restore persistent preview iframe lifecycle from 0.1.0e.
app_path=root/'ui/web/app.js'
app=app_path.read_text(encoding='utf-8-sig')
old="""  const preview=$('#mediaPreview'),empty=$('#mediaPreviewEmpty');if(preview){const hasActive=!!cur&&!stopped;const previewUrl=rt.running&&hasActive?`http://127.0.0.1:${rt.port||5000}/player?preview=1&g=${Number(player.generation||0)}`:'';if(previewUrl&&previewUrl!==mediaPreviewUrl){mediaPreviewUrl=previewUrl;preview.src=previewUrl;preview.classList.add('visible');empty?.classList.add('hidden')}else if(!previewUrl){mediaPreviewUrl='';preview.src='about:blank';preview.classList.remove('visible');empty?.classList.remove('hidden')}}"""
new="""  const preview=$('#mediaPreview'),empty=$('#mediaPreviewEmpty');if(preview){const previewUrl=rt.running?`http://127.0.0.1:${rt.port||5000}/player?preview=1`:'';if(previewUrl&&previewUrl!==mediaPreviewUrl){mediaPreviewUrl=previewUrl;preview.src=previewUrl;preview.classList.add('visible');empty?.classList.add('hidden')}else if(!previewUrl&&mediaPreviewUrl){mediaPreviewUrl='';preview.removeAttribute('src');preview.classList.remove('visible');empty?.classList.remove('hidden')}}"""
if old not in app: raise SystemExit('R3 preview lifecycle anchor missing')
app=app.replace(old,new,1)
app_path.write_text(app,encoding='utf-8')

# 4. Update static selftest: actual e transport + persistent iframe + legacy primary resolver + no false heartbeat.
st_path=root/'SELFTEST_PURE_DOTNET_STATIC.ps1'
st=st_path.read_text(encoding='utf-8-sig')
insert="""
  Check ($media.Contains('SearchPrimaryLegacyAsync') -and $media.Contains('ScorePrimaryLegacy') -and $media.Contains('videoRenderer') -and $media.Contains('case \"heartbeat\":') -and $media.Contains('heartbeat proves the page is alive')) '0.1.0r R3 proven primary search / truthful heartbeat missing'
  Check ($localPlayer.Contains('actual 0.1.0e player transport restored') -and $localPlayer.Contains('setInterval(tick,300)') -and $localPlayer.Contains('background:#000') -and -not $localPlayer.Contains('body.idle #p')) '0.1.0r R3 actual 0.1.0e player transport missing'
  Check ($ui.Contains('/player?preview=1`') -and -not $ui.Contains('/player?preview=1&g=') -and -not $ui.Contains('const hasActive=!!cur&&!stopped')) '0.1.0r R3 persistent preview iframe lifecycle missing'
"""
anchor="  Check ($ui.Contains('e.textContent!==next')) '0.1.0r R2 stable label update guard missing'\n"
if insert.strip() not in st:
    if anchor not in st: raise SystemExit('R3 selftest anchor missing')
    st=st.replace(anchor,anchor+insert,1)
st_path.write_text(st,encoding='utf-8')

notes=root/'RELEASE_NOTES_0.1.0r.md'
t=notes.read_text(encoding='utf-8-sig')
if 'RECOVERY R3 — actual old Media transport' not in t:
    t+='''\n## RECOVERY R3 — actual old Media transport\n\n- Restored the actual 0.1.0e persistent internal player iframe and PlayerHtml lifecycle.\n- Real queue additions use the proven 0.1.0e `videoRenderer` search/ranking path; richer recursive search remains preview-only.\n- Heartbeat no longer lies that a video is playing; only real `YT.PlayerState.PLAYING` sets playing state.\n'''
    notes.write_text(t,encoding='utf-8')

# invariants
m=media_path.read_text(encoding='utf-8')
p=player_path.read_text(encoding='utf-8')
a=app_path.read_text(encoding='utf-8')
for x in ['SearchPrimaryLegacyAsync','ScorePrimaryLegacy','heartbeat proves the page is alive']:
    if x not in m: raise SystemExit('missing '+x)
for x in ['actual 0.1.0e player transport restored','setInterval(tick,300)','background:#000']:
    if x not in p: raise SystemExit('missing '+x)
for x in ['body.idle #p','startup-timeout','youtube-nocookie.com']:
    if x in p: raise SystemExit('forbidden '+x)
if '/player?preview=1&g=' in a or 'const hasActive=!!cur&&!stopped' in a: raise SystemExit('preview remount still present')
print('0.1.0r RECOVERY R3 FINALIZE PASS: actual e player + persistent iframe + legacy primary search + truthful heartbeat')
