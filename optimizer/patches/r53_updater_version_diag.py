from pathlib import Path
import os

root=Path(os.environ['SOURCE_ROOT'])
p=root/'src'/'MerzoOptimizer.Windows'/'Updates'/'GitHubUpdateService.cs'
text=p.read_text(encoding='utf-8-sig')
lines=text.splitlines()
needles=('ParseTaggedVersion','Version.TryParse','Regex','LatestVersion','candidateTag','ReleaseTagPrefix')
print('R53_UPDATER_VERSION_DIAG_BEGIN')
seen=set()
for i,line in enumerate(lines):
    if any(n in line for n in needles):
        for j in range(max(0,i-8),min(len(lines),i+16)):
            if j in seen: continue
            seen.add(j)
            safe=lines[j].encode('ascii','backslashreplace').decode('ascii')
            print(f'{j+1:04d}: {safe}')
print('R53_UPDATER_VERSION_DIAG_END')
