from pathlib import Path
import json, os, re

root=Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# Version labels and all assemblies.
for p in [root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml', root/'src'/'MerzoOptimizer.App'/'App.xaml.cs', root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs']:
    s=read(p)
    s=s.replace('Production R36','Production R37').replace('v0.1.36','v0.1.37').replace('0.1.36 / Production R36','0.1.37 / Production R37')
    s=s.replace('MerzoDiagnostics-R36-','MerzoDiagnostics-R37-').replace('[Crash][R36]','[Crash][R37]').replace('[Merzo R36]','[Merzo R37]')
    # Splash fallback literal.
    s=s.replace('"0.1.36" : pendingVersion','"0.1.37" : pendingVersion')
    write(p,s)

for csproj in (root/'src').rglob('*.csproj'):
    s=read(csproj)
    s=re.sub(r'<Version>[^<]+</Version>','<Version>0.1.37</Version>',s)
    s=re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>','<AssemblyVersion>0.1.37.0</AssemblyVersion>',s)
    s=re.sub(r'<FileVersion>[^<]+</FileVersion>','<FileVersion>0.1.37.0</FileVersion>',s)
    s=re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>','<InformationalVersion>0.1.37</InformationalVersion>',s)
    write(csproj,s)

notes={
  'version':'0.1.37',
  'title':'R37 OPERATION CENTER & NETWORK REPAIR',
  'summary':'Единый тёмный стиль всех диалогов, наглядный живой ход системных операций и полноценный Repair / Network Center.',
  'added':[
    'Merzo Dialogs: собственные тёмные диалоги подтверждения, результата, предупреждения и ошибки вместо белых системных MessageBox.',
    'Operation Center: крупный прогресс, текущий этап, LIVE-список действий и понятная цепочка Snapshot → Apply → Verify → Log → Undo.',
    'Repair / Network: активный адаптер, IPv4, шлюз, DNS, DHCP, скорость соединения, тест шлюза и DNS-разрешения.',
    'Безопасные сетевые repair-команды через allow-listed UAC-helper: Flush DNS, Renew DHCP, Winsock reset, TCP/IP reset и пошаговое комплексное восстановление.'
  ],
  'changed':[
    'После запуска выбранного набора Merzo автоматически открывает «Ход работы», чтобы применение не происходило визуально в пустоте.',
    'Итоги применения, очистки, восстановления, питания, обновлений и аварийные уведомления теперь используют единый стиль программы.',
    'Repair / Network стал реальной страницей вместо заглушки в левой навигации.'
  ],
  'fixed':[
    'Убраны белые нативные окна Windows внутри обычного рабочего интерфейса Merzo.',
    'Исправлена слабая визуализация применения профиля: ход реальной операции теперь виден до завершения.',
    'Сетевой Repair не использует сомнительные ping/TCP-хаки: IPv6, MTU, TCP autotuning, Wi-Fi/VPN профили и пароли не удаляются и не отключаются.'
  ]
}
write(root/'data'/'release_notes.json',json.dumps(notes,ensure_ascii=False,indent=2)+'\n')
(root/'R37_OPERATION_NETWORK.marker').write_text('R37 OPERATION CENTER + THEMED DIALOGS + NETWORK REPAIR\n',encoding='utf-8')
print('R37 finalize patch: OK')
