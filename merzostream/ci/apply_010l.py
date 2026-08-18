import json, os
from pathlib import Path
root=Path(os.environ['MERZO_SRC'])

def rw(rel, fn):
    p=root/rel
    if not p.exists(): raise SystemExit(f'missing {rel}')
    t=p.read_text(encoding='utf-8-sig')
    u=fn(t)
    if u==t: raise SystemExit(f'no change for {rel}')
    p.write_text(u,encoding='utf-8',newline='\n')

def repl(rel,a,b):
    def f(t):
        if a not in t: raise SystemExit(f'marker missing in {rel}: {a[:80]}')
        return t.replace(a,b)
    rw(rel,f)

version_files=['ui/web/app_info.json','ui/web/concept.css','ui/web/styles.css','ui/web/splash.html','ui/web/concept.js','ui/web/index.html','release/GITHUB_ACTIONS_MERZOSTREAM_RUNTIME.yml','content/app_info.json','08_BUILD_BRANDED_SETUP.ps1','tools/MerzoStream.Foundation.SelfTest/Program.cs','SELFTEST_PURE_DOTNET_STATIC.ps1','src/MerzoStream.Foundation/Services/UpdateService.cs','src/MerzoStream.Setup/Program.cs','src/MerzoStream.Host/DotNetBackend.cs','src/MerzoStream.Host/MainForm.cs','06_BUILD_RUNTIME_RELEASE.ps1']
for rel in version_files:
    p=root/rel;t=p.read_text(encoding='utf-8-sig')
    if '0.1.0k' not in t and rel not in ('ui/web/index.html',): raise SystemExit(f'0.1.0k version marker missing in {rel}')
    t=t.replace('0.1.0k','0.1.0l').replace('010k-r1','010l-r1')
    p.write_text(t,encoding='utf-8',newline='\n')

repl('ui/web/index.html','<button class="account-pill" data-open="accounts"><span id="accountBadge">○ GitHub</span></button>','<button aria-label="GitHub — состояние неизвестно" class="account-pill integration-pill service-tooltip" data-open="accounts" data-tooltip="GitHub — состояние неизвестно" id="githubPill" title="GitHub — состояние неизвестно"><i></i><span id="accountBadge">GitHub —</span></button>')
repl('ui/web/index.html','<p>Streamer.bot + OAuth JSON</p><b data-account-status="youtube">Проверка…</b></div><div class="account-actions"><button class="ghost small" id="chooseYoutubeSecret">OAuth JSON</button>','<p>Авторизация YouTube / Streamer.bot</p><b data-account-status="youtube">Проверка…</b></div><div class="account-actions">')

repl('ui/web/app.js',"function renderCloudLocal(c){const connected=!!c.connected_local, unlocked=!!c.unlocked_local, login=c.login||'';setText('#accountBadge',connected?`✓ ${login?'@'+login:'GitHub'}`:'○ GitHub');setText('#cloudHeadline'", "function renderCloudLocal(c){const connected=!!c.connected_local, unlocked=!!c.unlocked_local, login=c.login||'';setText('#accountBadge',connected?'GitHub ✓':'GitHub —');const pill=$('#githubPill');if(pill){pill.classList.remove('ready','warning','error');if(connected)pill.classList.add(unlocked?'ready':'warning');setServiceTooltip(pill,connected?`GitHub — подключён${login?' • @'+login:''}${unlocked?' • Cloud готов':' • Cloud требует внимания'}`:'GitHub — не подключён')}setText('#cloudHeadline'")
repl('ui/web/app.js',"$('#chooseYoutubeSecret').onclick=async()=>{const r=await api('youtube_choose_client_secret');if(r.ok){toast(r.message);refreshAccounts()}else if(!r.cancelled)toast(r.message,true)};","const chooseYoutubeSecret=$('#chooseYoutubeSecret');if(chooseYoutubeSecret)chooseYoutubeSecret.onclick=async()=>{const r=await api('youtube_choose_client_secret');if(r.ok){toast(r.message);refreshAccounts()}else if(!r.cancelled)toast(r.message,true)};")

p=root/'ui/web/concept.css';t=p.read_text(encoding='utf-8')
wrong='.live-pill:nth-child(2){border-color:rgba(255,40,105,.45)!important;color:#ff789e!important}'
if wrong not in t: raise SystemExit('hard-coded Streamer.bot red rule missing')
t=t.replace(wrong,'')
t+='''\n/* 0.1.0l — top service indicators follow real service state; no hard-coded Streamer.bot red. */\n.top-actions .integration-pill{border-color:rgba(93,150,181,.26)!important;color:#a8bac6!important;box-shadow:none!important;background:#07121e!important}\n.top-actions .integration-pill>i{width:8px!important;height:8px!important;border-radius:50%!important;background:#607888!important;box-shadow:none!important;flex:0 0 auto!important}\n.top-actions .integration-pill.ready{border-color:rgba(35,223,126,.62)!important;color:#7df0b7!important;box-shadow:0 0 14px rgba(35,223,126,.12)!important;background:rgba(7,35,29,.82)!important}\n.top-actions .integration-pill.ready>i{background:#23df7e!important;box-shadow:0 0 10px rgba(35,223,126,.75)!important}\n.top-actions .integration-pill.warning{border-color:rgba(255,176,50,.60)!important;color:#ffc86f!important;box-shadow:0 0 14px rgba(255,176,50,.10)!important;background:rgba(39,29,10,.78)!important}\n.top-actions .integration-pill.warning>i{background:#ffb032!important;box-shadow:0 0 10px rgba(255,176,50,.72)!important}\n.top-actions .integration-pill.error{border-color:rgba(255,72,104,.62)!important;color:#ff8ca2!important;box-shadow:0 0 14px rgba(255,72,104,.11)!important;background:rgba(42,10,19,.78)!important}\n.top-actions .integration-pill.error>i{background:#ff4868!important;box-shadow:0 0 10px rgba(255,72,104,.72)!important}\n'''
p.write_text(t,encoding='utf-8',newline='\n')

p=root/'ui/web/styles.css';t=p.read_text(encoding='utf-8')
t+='''\n/* 0.1.0l top service status fallback */\n.account-pill.integration-pill i{width:7px;height:7px;border-radius:50%;background:#49616f;flex:0 0 auto}\n.account-pill.integration-pill.ready{border-color:rgba(86,230,165,.36);color:#a8e9ce}.account-pill.integration-pill.ready i{background:var(--success);box-shadow:0 0 10px rgba(86,230,165,.6)}\n.account-pill.integration-pill.warning{border-color:rgba(245,200,107,.34);color:#e5c987}.account-pill.integration-pill.warning i{background:var(--warn);box-shadow:0 0 9px rgba(245,200,107,.45)}\n.account-pill.integration-pill.error{border-color:rgba(255,107,129,.34);color:#e99aab}.account-pill.integration-pill.error i{background:var(--danger);box-shadow:0 0 9px rgba(255,107,129,.45)}\n'''
p.write_text(t,encoding='utf-8',newline='\n')

for rel in ('content/app_info.json','ui/web/app_info.json'):
    p=root/rel;d=json.loads(p.read_text(encoding='utf-8'))
    d['version']='0.1.0l';d['build']='0.1.0l • LIVE STATUS COLORS + ACCOUNT UX';d['window_title']='MerzoStream Suite - Pure .NET 0.1.0l';d['sidebar_subtitle']='SUITE - PURE .NET 0.1.0l'
    d['release_notes']=['Top bar: OBS / Streamer.bot / GitHub border and glow follow actual service state.','Removed hard-coded red Streamer.bot border.','GitHub is now the same live-status pill as OBS and Streamer.bot.','YouTube Account Center no longer asks normal users for OAuth JSON.','Update Center/OTA logic is unchanged.']+d.get('release_notes',[])
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

notes='''# MerzoStream Suite 0.1.0l\n\n- OBS / Streamer.bot / GitHub top indicators now share one real state-color contract.\n- Healthy: green; degraded/attention: amber; error: red; offline/unknown: neutral.\n- Removed the legacy hard-coded red border from Streamer.bot.\n- GitHub now has its own live status dot and matching border/glow.\n- YouTube Account Center no longer exposes OAuth JSON in the normal user flow.\n- Update Center/OTA is unchanged.\n'''
(root/'RELEASE_NOTES_0.1.0l.md').write_text(notes,encoding='utf-8',newline='\n')

p=root/'SELFTEST_PURE_DOTNET_STATIC.ps1';t=p.read_text(encoding='utf-8')
needle='  Write-Host ("PURE DOTNET 0.1.0l STATIC SELFTEST PASS`nchecks=$checks") -ForegroundColor Green'
extra="  Check ($css.Contains('top service indicators follow real service state') -and -not $css.Contains('.live-pill:nth-child(2){')) 'top service pill dynamic color authority missing'\n  Check ($html.Contains('id=\"githubPill\"') -and -not $html.Contains('id=\"chooseYoutubeSecret\"')) 'GitHub status pill or YouTube account UX fix missing'\n"
if needle not in t: raise SystemExit('selftest insertion marker missing')
t=t.replace(needle,extra+needle)
p.write_text(t,encoding='utf-8',newline='\n')
print('0.1.0l APPLY PASS')
