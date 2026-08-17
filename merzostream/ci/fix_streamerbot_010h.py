import os, pathlib
p=pathlib.Path(os.environ['MERZO_SRC'])/'src'/'MerzoStream.Foundation'/'Services'/'StreamerBotService.cs'
s=p.read_text(encoding='utf-8')
old='actions = actions.Select(ToWireAction).ToArray(),'
new='actions = actions.Select(x => ToWireAction(x)).ToArray(),'
if old not in s:
    if new in s:
        print('STREAMERBOT FIX ALREADY PRESENT')
    else:
        raise SystemExit('Expected StreamerBotService Select expression not found')
else:
    p.write_text(s.replace(old,new,1),encoding='utf-8')
    print('STREAMERBOT SELECT FIX APPLIED')
