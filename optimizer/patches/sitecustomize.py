# Temporary R37 patch-chain compatibility hook.
# Python imports sitecustomize automatically from the script directory.  Once
# R36 has materialized MainWindow.xaml, give its existing Gaming nav entry a
# stable x:Name so r37_network_center.py can clone the exact approved style.
from pathlib import Path
import os,re
try:
    root=os.environ.get('SOURCE_ROOT')
    if root:
        p=Path(root)/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
        if p.exists():
            s=p.read_text(encoding='utf-8-sig')
            if 'x:Name="GamingDevNav"' not in s:
                m=re.search(r'<RadioButton\b[^>]*Click="GamingDev_Click"[^>]*/>',s,re.S)
                if m:
                    tag=m.group(0).replace('<RadioButton','<RadioButton x:Name="GamingDevNav"',1)
                    p.write_text(s[:m.start()]+tag+s[m.end():],encoding='utf-8')
except Exception:
    # Never break unrelated historical patch scripts; the R37 patch itself has
    # a strict anchor and will fail clearly if this preparation was impossible.
    pass
