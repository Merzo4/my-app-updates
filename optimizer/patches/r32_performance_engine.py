from pathlib import Path
import base64,zlib,json,os
here=Path(__file__).resolve().parent
payload=''.join((here/f'r32_payload.part{i}').read_text(encoding='utf-8').strip() for i in range(1,3))
src=zlib.decompress(base64.b64decode(payload)).decode('utf-8')
old="x=replace_once(x,tail,notice,'main window tail')"
new="""if tail in x:\n    x=x.replace(tail,notice,1)\nelse:\n    # R31 final appends its own overlays after MainTabs. Insert R32 notice immediately before the root Grid close, independent of whitespace.\n    window_pos=x.rfind('</Window>')\n    grid_pos=x.rfind('</Grid>',0,window_pos)\n    if window_pos < 0 or grid_pos < 0:\n        raise SystemExit('R32 anchor missing: main window root elements')\n    overlay_start=notice.find('        <!-- R32')\n    overlay_end=notice.rfind('    </Grid>\\n</Window>')\n    if overlay_start < 0 or overlay_end < 0:\n        raise SystemExit('R32 internal notice template invalid')\n    overlay=notice[overlay_start:overlay_end]\n    x=x[:grid_pos]+overlay+x[grid_pos:]"""
if old not in src:
    raise SystemExit('R32 compatibility rewrite anchor missing')
src=src.replace(old,new,1)
exec(compile(src,'r32_payload','exec'), {'__name__':'__main__'})

# R32 diagnostic anti-myth rules are read-only markers. SelfTest requires every catalog item
# to describe a concrete registry state, while security markers must not belong to apply profiles.
root=Path(os.environ['SOURCE_ROOT'])
tp=root/'data'/'tweaks.json'
tweaks=json.loads(tp.read_text(encoding='utf-8-sig'))
checks={
 'performance.keep_sysmain_advisory': ('LocalMachine',r'SYSTEM\CurrentControlSet\Services\SysMain','Start',2),
 'performance.keep_pagefile_advisory': ('LocalMachine',r'SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management','DisablePagingExecutive',0),
 'performance.keep_defender_advisory': ('LocalMachine',r'SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection','DisableRealtimeMonitoring',0),
 'performance.keep_windows_update_advisory': ('LocalMachine',r'SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU','NoAutoUpdate',0),
 'performance.keep_ipv6_advisory': ('LocalMachine',r'SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters','DisabledComponents',0),
 'performance.keep_timer_advisory': ('LocalMachine',r'SYSTEM\CurrentControlSet\Control\Session Manager\kernel','GlobalTimerResolutionRequests',0),
 'performance.keep_tcp_magic_advisory': ('LocalMachine',r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile','NetworkThrottlingIndex',10),
}
for item in tweaks:
    if item.get('id') in checks:
        hive,key,name,value=checks[item['id']]
        item['profile_tags']=[]
        item['registry_actions']=[{'hive':hive,'key_path':key,'value_name':name,'value_type':'DWord','integer_value':value}]
tp.write_text(json.dumps(tweaks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('R32 anti-myth scan-only compatibility: OK')
