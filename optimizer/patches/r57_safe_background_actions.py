from pathlib import Path
import os,re

root=Path(os.environ['SOURCE_ROOT'])
def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8')
def once(text,old,new,label):
    c=text.count(old)
    if c!=1: raise SystemExit(f'R57 anchor {label} count={c}')
    return text.replace(old,new,1)

# R57 deliberately does NOT create a second Windows mutation engine. It only
# bridges confirmed process families to already-reviewed tweak IDs. Actual
# mutation remains in the existing Snapshot -> Apply -> Verify -> Undo path.

# -----------------------------------------------------------------------------
# 1) Process intelligence model: expose management guidance + reviewed tweak IDs.
# -----------------------------------------------------------------------------
models=root/'src'/'MerzoOptimizer.Core'/'Audit'/'ProcessStabilityModels.cs'
m=read(models)
old_family='''public sealed record ProcessStabilityFamilySnapshot(\n    string FamilyName,\n    int Count,\n    IReadOnlyList<int> Pids,\n    IReadOnlyList<string> Paths,\n    string Source,\n    string Classification,\n    string Recommendation,\n    string Evidence);'''
new_family='''public sealed record ProcessStabilityFamilySnapshot(\n    string FamilyName,\n    int Count,\n    IReadOnlyList<int> Pids,\n    IReadOnlyList<string> Paths,\n    string Source,\n    string Classification,\n    string Recommendation,\n    string Evidence,\n    string Management,\n    IReadOnlyList<string> SafeTweakIds);'''
m=once(m,old_family,new_family,'family-management-fields')
write(models,m)

an=root/'src'/'MerzoOptimizer.Windows'/'Processes'/'WindowsProcessStabilityAnalyzer.cs'
a=read(an)
a=once(a,
'''        return new ProcessStabilityFamilySnapshot(family, items.Count, items.Select(static x => x.Pid).OrderBy(static x => x).ToArray(),\n            paths, source, classification, recommendation, evidence);''',
'''        var management = ResolveSafeManagement(family, classification);\n        return new ProcessStabilityFamilySnapshot(family, items.Count, items.Select(static x => x.Pid).OrderBy(static x => x).ToArray(),\n            paths, source, classification, recommendation, evidence, management.Hint, management.TweakIds);''','family-return-management')
helper=r'''    private static (string Hint, IReadOnlyList<string> TweakIds) ResolveSafeManagement(string family, string classification)
    {
        if (classification is "Не трогать" or "Драйвер / оставить")
            return ("Не трогать", Array.Empty<string>());

        if (string.Equals(family, "Edge", StringComparison.OrdinalIgnoreCase))
            return ("Можно подготовить SAFE: Startup Boost + background mode", new[] { "r34.edge.disable_startup_boost", "r34.edge.disable_background_mode" });
        if (string.Equals(family, "chrome", StringComparison.OrdinalIgnoreCase))
            return ("Можно подготовить SAFE: background mode Chrome", new[] { "browser.chrome.disable_background_mode" });
        if (string.Equals(family, "Widgets", StringComparison.OrdinalIgnoreCase))
            return ("Можно подготовить SAFE: отключение Widgets policy", new[] { "r34.widgets.disable_widgets_policy" });
        if (string.Equals(family, "WebView2", StringComparison.OrdinalIgnoreCase))
            return ("Только проверить владельца WebView2 — общий runtime автоматически не отключается", Array.Empty<string>());
        if (string.Equals(family, "OneDrive", StringComparison.OrdinalIgnoreCase))
            return ("Управлять через отдельный OneDrive/Автозагрузка сценарий; из аудита не удалять", Array.Empty<string>());

        return classification == "Необязательный"
            ? ("Проверить Автозагрузку; автоматического действия для этого источника нет", Array.Empty<string>())
            : ("Только проверить источник", Array.Empty<string>());
    }

'''
anchor='''    private static SourceInventory BuildSourceInventory()\n    {'''
a=once(a,anchor,helper+anchor,'management-helper')
write(an,a)

# -----------------------------------------------------------------------------
# 2) ViewModel: one safe action = select existing reviewed tweaks only.
# -----------------------------------------------------------------------------
vm_path=root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
v=read(vm_path)
v=once(v,
'''        RunProcessStabilityAuditCommand = new AsyncRelayCommand(RunProcessStabilityAuditAsync);\n        CancelProcessStabilityAuditCommand = new AsyncRelayCommand(CancelProcessStabilityAuditAsync);''',
'''        RunProcessStabilityAuditCommand = new AsyncRelayCommand(RunProcessStabilityAuditAsync);\n        CancelProcessStabilityAuditCommand = new AsyncRelayCommand(CancelProcessStabilityAuditAsync);\n        PrepareDetectedSafeBackgroundActionsCommand = new AsyncRelayCommand(PrepareDetectedSafeBackgroundActionsAsync, () => !IsStage2Busy);''','command-ctor')
v=once(v,
'''    public AsyncRelayCommand RunProcessStabilityAuditCommand { get; }\n    public AsyncRelayCommand CancelProcessStabilityAuditCommand { get; }''',
'''    public AsyncRelayCommand RunProcessStabilityAuditCommand { get; }\n    public AsyncRelayCommand CancelProcessStabilityAuditCommand { get; }\n    public AsyncRelayCommand PrepareDetectedSafeBackgroundActionsCommand { get; }''','command-property')
method=r'''    private Task PrepareDetectedSafeBackgroundActionsAsync()
    {
        if (_disposed || IsStage2Busy) return Task.CompletedTask;

        var ids = ProcessStabilityFinalRows
            .SelectMany(static x => x.SafeTweakIds)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToHashSet(StringComparer.OrdinalIgnoreCase);
        if (ids.Count == 0)
        {
            ProcessReductionStatusText = "R57: в постоянном фоне нет источников, для которых существует проверенное SAFE-действие. Ничего не выбрано и не изменено.";
            return Task.CompletedTask;
        }

        var added = 0;
        foreach (var card in SafeTweaks)
        {
            if (!ids.Contains(card.Definition.Id) || card.Definition.ScanOnly || !card.IsSupported || card.IsApplied || card.IsSelected) continue;
            card.IsSelected = true;
            added++;
        }

        var totalSelected = SafeTweaks.Count(static x => x.IsSelected);
        ProcessReductionStatusText = added > 0
            ? $"R57: добавлено {added} SAFE-действий из фактического постоянного фона. Всего выбрано {totalSelected}. Ничего ещё не применено — проверьте список «Выбранное»."
            : "R57: подходящие SAFE-действия уже применены или уже находятся в списке «Выбранное». Windows не изменялась.";
        SelectedOptimizationTabIndex = 3;
        return Task.CompletedTask;
    }

'''
anchor='''    private Task CancelProcessStabilityAuditAsync()\n    {'''
v=once(v,anchor,method+anchor,'prepare-safe-method')
# Keep command state coherent with the existing Stage2 busy state.
raise='''            SelectProcessLiteCommand.RaiseCanExecuteChanged();'''
if raise in v and 'PrepareDetectedSafeBackgroundActionsCommand.RaiseCanExecuteChanged();' not in v:
    v=v.replace(raise,raise+'\n            PrepareDetectedSafeBackgroundActionsCommand.RaiseCanExecuteChanged();',1)
write(vm_path,v)

# -----------------------------------------------------------------------------
# 3) UI: permanent background gets a non-destructive management bridge.
# -----------------------------------------------------------------------------
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)
old='''            <TabItem Header="Постоянный фон" Style="{StaticResource SubTabItem}">\n                <Border Style="{StaticResource R43PageCard}" Margin="0,5,0,0"><DataGrid ItemsSource="{Binding ProcessStabilityFinalRows}" AutoGenerateColumns="False" IsReadOnly="True" BorderThickness="0"><DataGrid.Columns>\n                    <DataGridTextColumn Header="Семейство" Binding="{Binding FamilyName, Mode=OneWay}" Width="135"/><DataGridTextColumn Header="15 мин" Binding="{Binding Count, Mode=OneWay}" Width="60"/><DataGridTextColumn Header="Источник" Binding="{Binding Source, Mode=OneWay}" Width="195"/><DataGridTextColumn Header="Решение" Binding="{Binding Classification, Mode=OneWay}" Width="115"/><DataGridTextColumn Header="Почему" Binding="{Binding Recommendation, Mode=OneWay}" Width="*"/>\n                </DataGrid.Columns></DataGrid></Border>\n            </TabItem>'''
new='''            <TabItem Header="Постоянный фон" Style="{StaticResource SubTabItem}">\n                <Grid Margin="0,5,0,0">\n                    <Grid.RowDefinitions><RowDefinition Height="46"/><RowDefinition Height="*"/></Grid.RowDefinitions>\n                    <Border Grid.Row="0" Style="{StaticResource R43HeroCard}" Padding="10,6" Margin="0,0,0,6">\n                        <Grid><Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>\n                            <StackPanel VerticalAlignment="Center"><TextBlock Text="R57 SAFE BACKGROUND ACTIONS" Style="{StaticResource R43SectionLabel}"/><TextBlock Text="Только уже проверенные обратимые правила. Службы, драйверы, задачи и неизвестные источники из этой таблицы автоматически не отключаются." Foreground="{StaticResource TextMuted}" FontSize="9" TextTrimming="CharacterEllipsis"/></StackPanel>\n                            <Button Grid.Column="1" Style="{StaticResource CompactPrimaryButton}" Command="{Binding PrepareDetectedSafeBackgroundActionsCommand}" Click="OpenOptimization_Click" Content="Подготовить SAFE действия" MinWidth="170" VerticalAlignment="Center"/>\n                        </Grid>\n                    </Border>\n                    <Border Grid.Row="1" Style="{StaticResource R43PageCard}"><DataGrid ItemsSource="{Binding ProcessStabilityFinalRows}" AutoGenerateColumns="False" IsReadOnly="True" BorderThickness="0"><DataGrid.Columns>\n                        <DataGridTextColumn Header="Семейство" Binding="{Binding FamilyName, Mode=OneWay}" Width="120"/><DataGridTextColumn Header="15 мин" Binding="{Binding Count, Mode=OneWay}" Width="58"/><DataGridTextColumn Header="Источник" Binding="{Binding Source, Mode=OneWay}" Width="170"/><DataGridTextColumn Header="Класс" Binding="{Binding Classification, Mode=OneWay}" Width="105"/><DataGridTextColumn Header="Управление" Binding="{Binding Management, Mode=OneWay}" Width="260"/><DataGridTextColumn Header="Почему" Binding="{Binding Recommendation, Mode=OneWay}" Width="*"/>\n                    </DataGrid.Columns></DataGrid></Border>\n                </Grid>\n            </TabItem>'''
x=once(x,old,new,'permanent-background-ui')
x=once(x,'Production R56 · 0.1.56','Production R57 · 0.1.57','visible-version')
x=once(x,'Text="R56"','Text="R57"','sidebar-version')
x=once(x,'Production 0.1.56 · R56 BASELINE PROCESS INTELLIGENCE','Production 0.1.57 · R57 SAFE BACKGROUND ACTIONS','window-title')
write(xp,x)

# -----------------------------------------------------------------------------
# 4) Versioning. Existing mutation contracts are intentionally unchanged.
# -----------------------------------------------------------------------------
projects=sorted((root/'src').glob('MerzoOptimizer.*/*.csproj'))
if len(projects)<5: raise SystemExit('R57 project set missing')
for cp in projects:
    t=read(cp)
    for label,value in {'Version':'0.1.57','VersionPrefix':'0.1.57','AssemblyVersion':'0.1.57.0','FileVersion':'0.1.57.0','InformationalVersion':'0.1.57'}.items():
        pat=rf'(<{label}>\s*)([^<]+?)(\s*</{label}>)'
        if re.search(pat,t): t=re.sub(pat,lambda mm:mm.group(1)+value+mm.group(3),t)
    write(cp,t)

iss=root/'installer'/'MerzoWindowsOptimizer.iss'
i=read(iss)
if '0.1.56' not in i: raise SystemExit('R57 installer R56 anchor missing')
i=i.replace('0.1.56','0.1.57')
write(iss,i)

notes=root/'dist'/'R53_RELEASE_NOTES.md'
if notes.exists():
    n=read(notes)
    add='''\n\n## 0.1.57 — Safe Background Actions\n- «Постоянный фон» теперь показывает, как именно можно управлять найденным источником.\n- Edge, Chrome и Widgets сопоставляются только с уже проверенными SAFE-правилами из существующего каталога.\n- Кнопка «Подготовить SAFE действия» лишь добавляет подходящие правила в «Выбранное»; Windows в этот момент не меняется.\n- Применение по-прежнему идёт через стандартный Snapshot → Apply → Verify → Undo/Restore.\n- WebView2 неизвестного владельца, OneDrive, службы, драйверы, scheduled tasks и неподтверждённые процессы автоматически не отключаются.\n'''
    if '## 0.1.57 — Safe Background Actions' not in n: n+=add
    write(notes,n)

(root/'R57_SAFE_BACKGROUND_ACTIONS.marker').write_text('0.1.57 / diagnostic-to-reviewed-tweak bridge / selection only / no new mutation engine\n',encoding='utf-8')
print('R57_SAFE_BACKGROUND_ACTIONS_PATCH_PASS')
