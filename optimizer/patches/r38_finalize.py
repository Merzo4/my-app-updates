from pathlib import Path
import json, os, re

root = Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p, s): p.write_text(s, encoding='utf-8')

# Visible version labels and diagnostics.
for p in [root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml', root/'src'/'MerzoOptimizer.App'/'App.xaml.cs', root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs']:
    s = read(p)
    s = s.replace('Production R37', 'Production R38').replace('v0.1.37', 'v0.1.38')
    s = s.replace('0.1.37 / Production R37', '0.1.38 / Production R38')
    s = s.replace('MerzoDiagnostics-R37-', 'MerzoDiagnostics-R38-').replace('[Crash][R37]', '[Crash][R38]').replace('[Merzo R37]', '[Merzo R38]')
    s = s.replace('"0.1.37" : pendingVersion', '"0.1.38" : pendingVersion')
    write(p, s)

for csproj in (root/'src').rglob('*.csproj'):
    s = read(csproj)
    s = re.sub(r'<Version>[^<]+</Version>', '<Version>0.1.38</Version>', s)
    s = re.sub(r'<AssemblyVersion>[^<]+</AssemblyVersion>', '<AssemblyVersion>0.1.38.0</AssemblyVersion>', s)
    s = re.sub(r'<FileVersion>[^<]+</FileVersion>', '<FileVersion>0.1.38.0</FileVersion>', s)
    s = re.sub(r'<InformationalVersion>[^<]+</InformationalVersion>', '<InformationalVersion>0.1.38</InformationalVersion>', s)
    write(csproj, s)

notes = {
  'version': '0.1.38',
  'title': 'R38 GAMING BOOST & EXTREME PERFORMANCE',
  'summary': 'Четыре уровня Gaming-профиля, experimental/LAB-настройки и отдельный Gaming Network с сохранением baseline адаптера.',
  'added': [
    'Gaming Boost: SAFE, PERFORMANCE, EXTREME и LAB — вложенные уровни от обычных игровых настроек до агрессивных экспериментальных.',
    'Gaming Network SAFE: RSS Enabled + TCP Auto-Tuning Normal без принудительного перезапуска сетевого адаптера.',
    'Gaming Network EXTREME: baseline адаптера + попытка low-latency настройки RSC, энергосбережения и Interrupt Moderation только если драйвер это поддерживает.',
    'Restore Gaming Network: возврат сохранённых параметров адаптера после EXTREME.',
    'Новые экспериментальные карточки: Game Mode, DisableUserPresenceQos, MMCSS SystemResponsiveness 10%, foreground scheduler bias и HAGS LAB.'
  ],
  'changed': [
    'Gaming / Developer переработан в компактный Gaming Boost Center с понятным уровнем риска.',
    'Все Gaming-профили сначала только выбирают действия; применение остаётся через Snapshot → Apply → Verify → Undo.',
    'Repair / Network дополнен отдельным Gaming Network блоком.'
  ],
  'safety': [
    'EXTREME/LAB помечены как экспериментальные: результат зависит от CPU, GPU, игры и драйвера.',
    'Defender, Windows Update, Microsoft Store, IPv6 и pagefile не отключаются.',
    'Gaming Network не принимает произвольные команды из UI: elevated helper использует фиксированный allow-list.',
    'Production остаётся без Obfuscar; dispatcher runtime smoke обязателен.'
  ]
}
write(root/'data'/'release_notes.json', json.dumps(notes, ensure_ascii=False, indent=2) + '\n')
(root/'R38_GAMING_EXTREME.marker').write_text('R38 GAMING BOOST + EXTREME PERFORMANCE + GAMING NETWORK\n', encoding='utf-8')
print('R38 finalize patch: OK')
