import os, pathlib
root=pathlib.Path(os.environ['MERZO_SRC'])
p=root/'SELFTEST_PURE_DOTNET_STATIC.ps1'
t=p.read_text(encoding='utf-8-sig')
pairs=[
("  Check (-not $resolveBlock.Contains('officialCandidates') -and $resolveBlock.Contains('var candidates = await SearchAsync(query, ct);')) '0.1.0r R2 primary Media resolver is not the pre-regression one-query path'",
 "  Check ($resolveBlock.Contains('SearchPrimaryLegacyAsync(query, ct)') -and -not $resolveBlock.Contains('var candidates = await SearchAsync(query, ct);')) '0.1.0r R3 real queue resolver is not the proven 0.1.0e path'"),
("  Check ($localPlayer.Contains('setInterval(tick,250)') -and -not $localPlayer.Contains('onReady:()=>{if(last)player.playVideo()}')) '0.1.0r R2 player timing/event path is not restored to 0.1.0m'",
 "  Check ($localPlayer.Contains('setInterval(tick,300)') -and $localPlayer.Contains('actual 0.1.0e player transport restored') -and -not $localPlayer.Contains('body.idle #p')) '0.1.0r R3 actual 0.1.0e player timing/lifecycle missing'"),
("  Check (-not $localPlayer.Contains('startup-timeout') -and -not $localPlayer.Contains('youtube-nocookie.com') -and $localPlayer.Contains('protected 0.1.0e player transport restored')) '0.1.0r protected Media player transport regressed'",
 "  Check (-not $localPlayer.Contains('startup-timeout') -and -not $localPlayer.Contains('youtube-nocookie.com') -and $localPlayer.Contains('actual 0.1.0e player transport restored')) '0.1.0r R3 Media player transport regressed'")]
for old,new in pairs:
    if old in t: t=t.replace(old,new,1)
    elif new not in t: raise SystemExit('R3 selftest migration anchor missing: '+old[:90])
p.write_text(t,encoding='utf-8')
print('0.1.0r R3 SELFTEST MIGRATION PASS')
