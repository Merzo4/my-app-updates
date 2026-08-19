import os
import pathlib
import re

root = pathlib.Path(os.environ['MERZO_SRC'])
p = root / 'src' / 'MerzoStream.Foundation' / 'Services' / 'LocalPlayerServer.cs'
text = p.read_text(encoding='utf-8-sig')
pattern = re.compile(r'    private const string PlayerHtml = """\n.*?\n""";\n\n    private const string MusicHtml = """', re.S)
replacement = '''    private const string PlayerHtml = """
<!doctype html><html><head><meta charset="utf-8"><style>html,body,#p{margin:0;width:100%;height:100%;background:transparent!important;overflow:hidden}iframe{border:0;background:transparent!important}body.idle #p{visibility:hidden!important;opacity:0!important;pointer-events:none}</style></head><body class="idle"><div id="p"></div><script src="https://www.youtube.com/iframe_api"></script><script>
// protected 0.1.0e player transport restored + later blank/clear safety retained
let player=null,last='',rev=-1,generation=-1,preview=new URLSearchParams(location.search).get('preview')==='1',fails=0;
function blank(){document.body.classList.add('idle');try{player?.stopVideo?.();player?.clearVideo?.()}catch{}last=''}
function post(state,error=''){if(!player||!last)return;const actual=String(player.getVideoData?.()?.video_id||last||'');fetch('/player-event',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({state,position:Number(player.getCurrentTime?.()||0),duration:Number(player.getDuration?.()||0),error,generation,video_id:actual})}).catch(()=>{})}
window.onYouTubeIframeAPIReady=()=>{player=new YT.Player('p',{width:'100%',height:'100%',playerVars:{autoplay:1,controls:1,rel:0,playsinline:1},events:{onReady:()=>{if(last)player.playVideo()},onStateChange:e=>{if(e.data===YT.PlayerState.PLAYING)post('playing');else if(e.data===YT.PlayerState.PAUSED)post('paused');else if(e.data===YT.PlayerState.ENDED)post('ended')},onError:e=>post('error',String(e.data))}})};
async function tick(){try{const s=await (await fetch('/state',{cache:'no-store'})).json();fails=0;const idle=!s.video_id||!!s.stopped;document.body.classList.toggle('idle',idle);if(!player){if(idle)blank();return}const nextGen=Number(s.generation??-1);if(nextGen!==generation)generation=nextGen;if(idle){if(last){player.stopVideo();player.clearVideo?.();last=''}return}if(s.video_id&&s.video_id!==last){last=s.video_id;player.loadVideoById({videoId:last,startSeconds:Number(s.position||0)});player.setVolume(preview?0:Number(s.volume||30))}if(s.revision!==rev){rev=s.revision;player.setVolume(preview?0:Number(s.volume||30));if(s.paused)player.pauseVideo();else player.playVideo();const delta=Math.abs(Number(player.getCurrentTime?.()||0)-Number(s.position||0));if(delta>2.5)player.seekTo(Number(s.position||0),true)}}catch{if(++fails>=2)blank()}}setInterval(tick,300);setInterval(()=>{if(player&&last)post(player.getPlayerState?.()===1?'playing':'heartbeat')},1200);
</script></body></html>
""";

    private const string MusicHtml = """'''
new_text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit(f'0.1.0r player finalize failed: PlayerHtml block matches={count}')
for forbidden in ('youtube-nocookie.com', 'startup-timeout', 'loadDeadline'):
    player_block = new_text[new_text.index('private const string PlayerHtml'):new_text.index('private const string MusicHtml')]
    if forbidden in player_block:
        raise SystemExit(f'0.1.0r forbidden player experiment remains: {forbidden}')
for required in ('background:transparent!important', 'function blank()', 'protected 0.1.0e player transport restored', 'player.clearVideo'):
    player_block = new_text[new_text.index('private const string PlayerHtml'):new_text.index('private const string MusicHtml')]
    if required not in player_block:
        raise SystemExit(f'0.1.0r protected player invariant missing: {required}')
p.write_text(new_text, encoding='utf-8')
print('0.1.0r HYBRID PROTECTED PLAYER FINALIZE PASS')
