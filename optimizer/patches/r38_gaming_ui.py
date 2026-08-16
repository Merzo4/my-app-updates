from pathlib import Path
import os

root = Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p, s): p.write_text(s, encoding='utf-8')
def rep(s, old, new, label):
    if old not in s:
        raise SystemExit(f'R38 gaming UI anchor missing: {label}')
    return s.replace(old, new, 1)

# ViewModel: profile selectors are nested presets and still only select cards.
p = root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s = read(p)
s = rep(s,
'''        SelectGamingProfileCommand = new AsyncRelayCommand(() => SelectNamedCategoryPresetAsync("GAMING", new[] { "Gaming" }, safeOnly: false), () => !IsStage2Busy);
        SelectDeveloperProfileCommand = new AsyncRelayCommand(() => SelectNamedCategoryPresetAsync("DEVELOPER", new[] { "Developer", "Explorer", "Edge" }, safeOnly: false), () => !IsStage2Busy);''',
'''        SelectGamingProfileCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("gaming_safe", "GAMING SAFE"), () => !IsStage2Busy);
        SelectGamingPerformanceCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("gaming_performance", "GAMING PERFORMANCE"), () => !IsStage2Busy);
        SelectGamingExtremeCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("gaming_extreme", "GAMING EXTREME"), () => !IsStage2Busy);
        SelectGamingLabCommand = new AsyncRelayCommand(() => SelectGamingTaggedPresetAsync("gaming_lab", "GAMING LAB"), () => !IsStage2Busy);
        SelectDeveloperProfileCommand = new AsyncRelayCommand(() => SelectNamedCategoryPresetAsync("DEVELOPER", new[] { "Developer", "Explorer", "Edge" }, safeOnly: false), () => !IsStage2Busy);''', 'command init')
s = rep(s,
'''    public AsyncRelayCommand SelectGamingProfileCommand { get; }
    public AsyncRelayCommand SelectDeveloperProfileCommand { get; }''',
'''    public AsyncRelayCommand SelectGamingProfileCommand { get; }
    public AsyncRelayCommand SelectGamingPerformanceCommand { get; }
    public AsyncRelayCommand SelectGamingExtremeCommand { get; }
    public AsyncRelayCommand SelectGamingLabCommand { get; }
    public AsyncRelayCommand SelectDeveloperProfileCommand { get; }''', 'command properties')
s = rep(s,
'''            SelectGamingProfileCommand.RaiseCanExecuteChanged();
            SelectDeveloperProfileCommand.RaiseCanExecuteChanged();''',
'''            SelectGamingProfileCommand.RaiseCanExecuteChanged();
            SelectGamingPerformanceCommand.RaiseCanExecuteChanged();
            SelectGamingExtremeCommand.RaiseCanExecuteChanged();
            SelectGamingLabCommand.RaiseCanExecuteChanged();
            SelectDeveloperProfileCommand.RaiseCanExecuteChanged();''', 'busy refresh')

anchor = '    private async Task SelectNamedCategoryPresetAsync(string title, IReadOnlyCollection<string> categories, bool safeOnly)'
method = r'''    private Task SelectGamingTaggedPresetAsync(string tag, string title)
    {
        _selectedProfileTag = tag;
        foreach (var card in SafeTweaks)
        {
            var match = card.Definition.ProfileTags?.Contains(tag, StringComparer.OrdinalIgnoreCase) == true;
            card.IsSelected = match && !card.Definition.ScanOnly && card.IsSupported && !card.IsApplied;
        }
        RefreshSelectedTweaks();
        var selected = SafeTweaks.Count(static x => x.IsSelected);
        var safe = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Safe);
        var balanced = SafeTweaks.Count(static x => x.IsSelected && x.Definition.Risk == TweakRisk.Balanced);
        SelectedOptimizationTabIndex = 2;
        SelectedTweaksText = selected == 0
            ? $"{title}: новых неприменённых настроек нет"
            : $"{title} · Выбрано: {selected} · SAFE: {safe} · BALANCED/EXPERIMENTAL: {balanced}";
        Stage2StatusText = selected == 0
            ? $"{title}: настройки уже применены или не поддерживаются на этом ПК."
            : $"{title}: выбрано {selected}. Проверьте список. Применение пойдёт через Snapshot → Apply → Verify → Undo.";
        return Task.CompletedTask;
    }

'''
if anchor not in s:
    raise SystemExit('R38 gaming selector method anchor missing')
s = s.replace(anchor, method + anchor, 1)
write(p, s)

# Replace the old two-card Gaming page with a dense four-level Gaming Boost UI.
p = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
s = read(p)
start_marker = '            <!-- R31: Gaming / Developer Center -->'
end_marker = '            <!-- Compact power center with explicit active plan -->'
a = s.find(start_marker)
b = s.find(end_marker, a + 1)
if a < 0 or b < 0:
    raise SystemExit('R38 gaming page boundaries missing')
page = r'''            <!-- R38: Gaming Boost / Extreme Performance -->
            <TabItem>
                <Grid Margin="11,8,11,9">
                    <Grid.RowDefinitions><RowDefinition Height="45"/><RowDefinition Height="172"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                    <Grid Grid.Row="0">
                        <StackPanel>
                            <TextBlock Style="{StaticResource PageTitle}" Text="Gaming Boost / Developer"/>
                            <TextBlock Text="От SAFE до LAB: больше производительности и меньше фоновой нагрузки, но все изменения сначала показываются и остаются обратимыми." Foreground="{StaticResource TextMuted}" FontSize="10.4"/>
                        </StackPanel>
                    </Grid>
                    <UniformGrid Grid.Row="1" Columns="3" Margin="0,4,0,7">
                        <Border Style="{StaticResource PresetCardBorder}" Margin="0,0,5,0" Padding="10,8">
                            <Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                                <StackPanel><TextBlock Text="SAFE GAMING" FontSize="13.2" FontWeight="SemiBold"/><TextBlock Text="Базовые игровые настройки без спорных системных изменений." Foreground="{StaticResource TextSecondary}" FontSize="9.8" TextWrapping="Wrap" Margin="0,3,0,0"/></StackPanel>
                                <TextBlock Grid.Row="1" Text="Game Mode, контроль DVR и уже проверенные Gaming-настройки." Foreground="{StaticResource TextMuted}" FontSize="9.4" TextWrapping="Wrap" Margin="0,7,0,4"/>
                                <Button Grid.Row="2" Style="{StaticResource CompactSecondaryButton}" Command="{Binding SelectGamingProfileCommand}" Click="OpenOptimization_Click" Content="Выбрать SAFE" HorizontalAlignment="Left"/>
                            </Grid>
                        </Border>
                        <Border Style="{StaticResource PresetCardBorder}" Margin="5,0" Padding="10,8" BorderBrush="#315E59">
                            <Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                                <StackPanel><TextBlock Text="PERFORMANCE" FontSize="13.2" FontWeight="SemiBold"/><TextBlock Text="Gaming + Performance + безопасная разгрузка процессов." Foreground="{StaticResource TextSecondary}" FontSize="9.8" TextWrapping="Wrap" Margin="0,3,0,0"/></StackPanel>
                                <TextBlock Grid.Row="1" Text="Для игрового ПК на каждый день. Более жёстко, но без LAB-настроек scheduler/HAGS." Foreground="{StaticResource TextMuted}" FontSize="9.4" TextWrapping="Wrap" Margin="0,7,0,4"/>
                                <Button Grid.Row="2" Style="{StaticResource CompactPrimaryButton}" Command="{Binding SelectGamingPerformanceCommand}" Click="OpenOptimization_Click" Content="Выбрать PERFORMANCE" HorizontalAlignment="Left"/>
                            </Grid>
                        </Border>
                        <Border Style="{StaticResource PresetCardBorder}" Margin="5,0,0,0" Padding="10,8" Background="#191519" BorderBrush="#6B4A51">
                            <Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                                <StackPanel><StackPanel Orientation="Horizontal"><TextBlock Text="EXTREME" FontSize="13.2" FontWeight="SemiBold"/><Border Background="#3B2026" CornerRadius="8" Padding="5,1" Margin="7,0,0,0"><TextBlock Text="АГРЕССИВНО" Foreground="#D89098" FontSize="8.7" FontWeight="Bold"/></Border></StackPanel><TextBlock Text="PERFORMANCE + агрессивная разгрузка фоновой Windows." Foreground="{StaticResource TextSecondary}" FontSize="9.8" TextWrapping="Wrap" Margin="0,3,0,0"/></StackPanel>
                                <TextBlock Grid.Row="1" Text="Для пользователей, которым важнее отклик/FPS, чем лишние фоновые функции Windows." Foreground="#BFA3A8" FontSize="9.4" TextWrapping="Wrap" Margin="0,7,0,4"/>
                                <Button Grid.Row="2" Style="{StaticResource CompactSecondaryButton}" Command="{Binding SelectGamingExtremeCommand}" Click="OpenOptimization_Click" Content="Выбрать EXTREME" HorizontalAlignment="Left"/>
                            </Grid>
                        </Border>
                    </UniformGrid>
                    <Grid Grid.Row="2"><Grid.ColumnDefinitions><ColumnDefinition Width="1.15*"/><ColumnDefinition Width="7"/><ColumnDefinition Width="0.85*"/></Grid.ColumnDefinitions>
                        <Border Grid.Column="0" Background="#18151B" BorderBrush="#644D72" BorderThickness="1" CornerRadius="9" Padding="10,8">
                            <Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                                <StackPanel Orientation="Horizontal"><TextBlock Text="LAB MODE" FontSize="13" FontWeight="SemiBold"/><Border Background="#33243C" CornerRadius="9" Padding="6,2" Margin="7,0,0,0"><TextBlock Text="EXPERIMENTAL" Foreground="#C59AD6" FontSize="8.8" FontWeight="Bold"/></Border></StackPanel>
                                <TextBlock Grid.Row="1" Text="EXTREME + спорные, но обратимые scheduler/GPU/MMCSS-настройки. Здесь нет обещания «+500% FPS»: сравнивайте реальные показатели до/после." Foreground="{StaticResource TextSecondary}" FontSize="9.7" TextWrapping="Wrap" Margin="0,5,0,5"/>
                                <TextBlock Grid.Row="2" Text="В LAB могут войти HAGS, foreground scheduler bias и MMCSS 10%. Defender, Windows Update, Store, IPv6 и pagefile не отключаются." Foreground="#B99CC3" FontSize="9.3" TextWrapping="Wrap"/>
                                <StackPanel Grid.Row="3" Orientation="Horizontal" Margin="0,8,0,0"><Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding SelectGamingLabCommand}" Click="OpenOptimization_Click" Content="Выбрать LAB"/><Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding ApplyGamingNetworkExtremeCommand}" Content="Network EXTREME" Margin="6,0,0,0"/></StackPanel>
                            </Grid>
                        </Border>
                        <Border Grid.Column="2" Style="{StaticResource CardBorder}" Padding="10,8">
                            <Grid><Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                                <TextBlock Text="Developer" FontSize="13" FontWeight="SemiBold"/>
                                <TextBlock Grid.Row="1" Text="Long Paths, PowerShell privacy, Explorer и Edge-настройки для рабочей среды." Foreground="{StaticResource TextSecondary}" FontSize="9.7" TextWrapping="Wrap" Margin="0,5,0,0"/>
                                <TextBlock Grid.Row="2" Text="Gaming Network SAFE можно применить отдельно: RSS Enabled + TCP Auto-Tuning Normal." Foreground="{StaticResource TextMuted}" FontSize="9.4" TextWrapping="Wrap" Margin="0,7,0,0"/>
                                <StackPanel Grid.Row="3" Margin="0,8,0,0"><Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding SelectDeveloperProfileCommand}" Click="OpenOptimization_Click" Content="Developer-твики" HorizontalAlignment="Left"/><Button Style="{StaticResource CompactSecondaryButton}" Command="{Binding ApplyGamingNetworkSafeCommand}" Content="Network SAFE" HorizontalAlignment="Left" Margin="0,5,0,0"/></StackPanel>
                            </Grid>
                        </Border>
                    </Grid>
                </Grid>
            </TabItem>

'''
s = s[:a] + page + s[b:]
write(p, s)
print('R38 Gaming Boost UI patch: OK')
