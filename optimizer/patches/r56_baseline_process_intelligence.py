from pathlib import Path
import os,re

root=Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8')
def once(text,old,new,label):
    c=text.count(old)
    if c!=1: raise SystemExit(f'R56 anchor {label} count={c}')
    return text.replace(old,new,1)

# R56 is intentionally diagnostic/read-only. It does NOT add any process kill,
# service disable, task disable or registry mutation. The existing GAME allow-list
# remains unchanged.

an=root/'src'/'MerzoOptimizer.Windows'/'Processes'/'WindowsProcessStabilityAnalyzer.cs'
a=read(an)
a=once(a,
'''        "SecurityHealthService", "SecurityHealthSystray", "MsMpEng", "NisSrv", "WmiPrvSE"\n    };''',
'''        "SecurityHealthService", "SecurityHealthSystray", "MsMpEng", "NisSrv", "WmiPrvSE",\n        "SearchIndexer", "SearchProtocolHost", "SearchFilterHost", "sppsvc", "TiWorker", "MoUsoCoreWorker",\n        "UsoClient", "TextInputHost", "ApplicationFrameHost", "Taskmgr"\n    };''','protected-windows-families')
a=once(a,
'''        "NVDisplay.Container", "nvcontainer", "RadeonSoftware", "AMDRSServ", "atiesrxx", "atieclxx",\n        "igfxCUIService", "igfxEM", "RtkAudUService", "RtkAudioService"''',
'''        "NVDisplay.Container", "nvcontainer", "RadeonSoftware", "AMDRSServ", "AMDRSSrcExt", "atiesrxx", "atieclxx",\n        "igfxCUIService", "igfxEM", "RtkAudUService", "RtkAudioService"''','amd-driver-family')
write(an,a)

vm_path=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
vm=read(vm_path)
vm=once(vm,
'''    public ObservableCollection<ProcessStabilityDelta> ProcessStabilityRows { get; } = [];\n''',
'''    public ObservableCollection<ProcessStabilityDelta> ProcessStabilityRows { get; } = [];\n    public ObservableCollection<ProcessStabilityFamilySnapshot> ProcessStabilityFinalRows { get; } = [];\n''','final-rows-collection')
vm=once(vm,
'''        ProcessStabilityRows.Clear();\n        ProcessStabilityStatusText = "Снимаю базовый список процессов…";''',
'''        ProcessStabilityRows.Clear();\n        ProcessStabilityFinalRows.Clear();\n        ProcessStabilityStatusText = "Снимаю базовый список процессов…";''','final-rows-clear')
vm=once(vm,
'''            foreach (var row in report.Deltas) ProcessStabilityRows.Add(row);\n            ProcessStabilityTimelineText = string.Join("  →  ", report.Samples.Select(s => $"{FormatProcessStabilityOffset(s.Elapsed)}: {s.ProcessCount}"));\n            ProcessStabilitySummaryText = $"Старт: {report.BaselineCount} → 15 мин: {report.FinalCount} · пик: {report.PeakCount} (+{report.AddedAtPeak}) · проверить/необязательных: {report.ReviewAddedCount} · системных/драйверных новых: {report.ProtectedAddedCount}.";\n            ProcessReductionStatusText = report.ReviewAddedCount > 0\n                ? $"R55 нашёл {report.ReviewAddedCount} поздно появляющихся процессов для проверки. Неизвестные источники автоматически не отключаются."\n                : "R55 не нашёл подтверждённых необязательных источников роста; системные процессы не трогаем.";''',
'''            foreach (var row in report.Deltas) ProcessStabilityRows.Add(row);\n            var finalSample = report.Samples.Last();\n            foreach (var row in finalSample.Families\n                         .Where(static x => x.Count > 0)\n                         .OrderBy(static x => x.Classification == "Необязательный" ? 0 : x.Classification == "Проверить" ? 1 : 2)\n                         .ThenByDescending(static x => x.Count)\n                         .ThenBy(static x => x.FamilyName, StringComparer.OrdinalIgnoreCase))\n                ProcessStabilityFinalRows.Add(row);\n            ProcessStabilityTimelineText = string.Join("  →  ", report.Samples.Select(s => $"{FormatProcessStabilityOffset(s.Elapsed)}: {s.ProcessCount}"));\n            ProcessStabilitySummaryText = $"Живой аудит: старт {report.BaselineCount} → 15 мин {report.FinalCount} · пик {report.PeakCount} (+{report.AddedAtPeak}) · проверить/необязательных новых: {report.ReviewAddedCount} · системных/драйверных новых: {report.ProtectedAddedCount}.";\n            ProcessReductionStatusText = report.ReviewAddedCount > 0\n                ? $"R56: {report.ReviewAddedCount} поздних процессов требуют проверки. Постоянный фон смотрите отдельно; неизвестные источники автоматически не отключаются."\n                : "R56: подтверждённого необязательного роста нет. Постоянный фон показан отдельно; системные процессы и драйверы не трогаем.";''','report-final-rows')
vm=once(vm,
'''        PerformanceProcessSummaryText = $"Процессов: {snapshot.ProcessCount} · пользовательских: {snapshot.UserProcessCount} · в TOP-{snapshot.TopProcesses.Count} кандидатов на фоновую разгрузку: {backgroundCandidates}.";''',
'''        PerformanceProcessSummaryText = $"Сохранённый Smart Audit: процессов {snapshot.ProcessCount} · пользовательских {snapshot.UserProcessCount} · TOP-{snapshot.TopProcesses.Count}, кандидатов на фоновую разгрузку: {backgroundCandidates}. Это не живой счётчик 15-минутного аудита.";''','saved-smart-audit-label')
write(vm_path,vm)

xaml_path=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xaml_path)
final_tab='''            <TabItem Header="Постоянный фон" Style="{StaticResource SubTabItem}">\n                <Border Style="{StaticResource R43PageCard}" Margin="0,5,0,0"><DataGrid ItemsSource="{Binding ProcessStabilityFinalRows}" AutoGenerateColumns="False" IsReadOnly="True" BorderThickness="0"><DataGrid.Columns>\n                    <DataGridTextColumn Header="Семейство" Binding="{Binding FamilyName, Mode=OneWay}" Width="135"/><DataGridTextColumn Header="15 мин" Binding="{Binding Count, Mode=OneWay}" Width="60"/><DataGridTextColumn Header="Источник" Binding="{Binding Source, Mode=OneWay}" Width="195"/><DataGridTextColumn Header="Решение" Binding="{Binding Classification, Mode=OneWay}" Width="115"/><DataGridTextColumn Header="Почему" Binding="{Binding Recommendation, Mode=OneWay}" Width="*"/>\n                </DataGrid.Columns></DataGrid></Border>\n            </TabItem>\n'''
anchor='''            <TabItem Header="Текущий TOP" Style="{StaticResource SubTabItem}">'''
if final_tab not in x:
    x=once(x,anchor,final_tab+anchor,'final-background-tab')
# R55.1 identities are the exact starting point for R56.
x=once(x,'Production R55.1 · 0.1.55.1','Production R56 · 0.1.56','visible-version')
x=once(x,'Text="R55.1"','Text="R56"','sidebar-version')
x=once(x,'Production 0.1.55.1 · R55.1 STARTUP BINDING HOTFIX','Production 0.1.56 · R56 BASELINE PROCESS INTELLIGENCE','window-title')
write(xaml_path,x)

# Advance every production assembly/package to 0.1.56.
projects=sorted((root/'src').glob('MerzoOptimizer.*/*.csproj'))
if len(projects)<5: raise SystemExit('R56 project set missing')
for cp in projects:
    t=read(cp)
    for label,value in {'Version':'0.1.56','VersionPrefix':'0.1.56','AssemblyVersion':'0.1.56.0','FileVersion':'0.1.56.0','InformationalVersion':'0.1.56'}.items():
        pat=rf'(<{label}>\s*)([^<]+?)(\s*</{label}>)'
        if re.search(pat,t): t=re.sub(pat,lambda m:m.group(1)+value+m.group(3),t)
    for required in ('AssemblyVersion','FileVersion','InformationalVersion'):
        if f'<{required}>' not in t: raise SystemExit(f'R56 missing {required}: {cp.name}')
    write(cp,t)

iss=root/'installer'/'MerzoWindowsOptimizer.iss'
i=read(iss)
if '0.1.55.1' not in i: raise SystemExit('R56 installer R55.1 anchor missing')
i=i.replace('0.1.55.1','0.1.56')
write(iss,i)

notes=root/'dist'/'R53_RELEASE_NOTES.md'
if notes.exists():
    n=read(notes)
    add='''\n\n## 0.1.56 — Baseline Process Intelligence\n- 15-минутный аудит теперь явно отделён от сохранённого Smart Audit: старый snapshot больше не выглядит как текущий live-счётчик.\n- Добавлена вкладка «Постоянный фон»: показывает семейства процессов, реально оставшиеся к 15-й минуте.\n- Уточнена безопасная классификация Windows Search, Software Protection, Update/host компонентов и Task Manager.\n- AMDRSSrcExt распознаётся как компонент AMD/драйвера и не предлагается как обычный сторонний кандидат.\n- Правила GAME, сервисные allow-list и Snapshot/Undo не расширялись. R56 ничего нового автоматически не отключает.\n'''
    if '## 0.1.56 — Baseline Process Intelligence' not in n: n+=add
    write(notes,n)

(root/'R56_BASELINE_PROCESS_INTELLIGENCE.marker').write_text('0.1.56 / live-vs-saved clarity / final baseline rows / classification only / no new mutations\n',encoding='utf-8')
print('R56_BASELINE_PROCESS_INTELLIGENCE_PASS')
