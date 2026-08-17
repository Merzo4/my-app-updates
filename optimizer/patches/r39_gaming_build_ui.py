from pathlib import Path
import os

root = Path(os.environ['SOURCE_ROOT'])
p = root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x = p.read_text(encoding='utf-8-sig')

# Put Gaming Build directly beside the four main optimization profiles.
needle = 'Command="{Binding SelectLightProfileCommand}"'
pos = x.find(needle)
if pos < 0:
    raise SystemExit('R39 main profile command anchor missing')
ug_start = x.rfind('<UniformGrid', 0, pos)
ug_open_end = x.find('>', ug_start)
ug_end = x.find('</UniformGrid>', pos)
if ug_start < 0 or ug_open_end < 0 or ug_end < 0:
    raise SystemExit('R39 main profile UniformGrid missing')
open_tag = x[ug_start:ug_open_end+1]
if 'Columns="4"' in open_tag:
    x = x[:ug_start] + open_tag.replace('Columns="4"','Columns="5"',1) + x[ug_open_end+1:]
    delta = len(open_tag.replace('Columns="4"','Columns="5"',1)) - len(open_tag)
    ug_end += delta

card = r'''
                        <Border Style="{StaticResource PresetCardBorder}" Margin="4,0,0,0" Padding="9,7" BorderBrush="#3D716B" Background="#10201F">
                            <Grid>
                                <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                                <StackPanel>
                                    <StackPanel Orientation="Horizontal"><TextBlock Text="GAME BUILD" FontSize="12.6" FontWeight="SemiBold"/><Border Background="#173733" CornerRadius="8" Padding="5,1" Margin="5,0,0,0"><TextBlock Text="NEW" Foreground="#6BCABE" FontSize="8.5" FontWeight="Bold"/></Border></StackPanel>
                                    <TextBlock Text="Игровая Windows одним профилем" Foreground="{StaticResource Accent}" FontSize="9.3" FontWeight="SemiBold" Margin="0,2,0,0"/>
                                </StackPanel>
                                <TextBlock Grid.Row="1" Text="Твики + снижение фоновых процессов + службы/задачи + Gaming Network. По умолчанию PERFORMANCE; SAFE / EXTREME / LAB доступны в Gaming Boost." Foreground="{StaticResource TextSecondary}" FontSize="9.2" TextWrapping="Wrap" Margin="0,5,0,4"/>
                                <Button Grid.Row="2" Style="{StaticResource CompactPrimaryButton}" Command="{Binding SelectGamingPerformanceCommand}" Click="OpenOptimization_Click" Content="GAME PERFORMANCE" HorizontalAlignment="Stretch"/>
                            </Grid>
                        </Border>
'''
ug_end = x.find('</UniformGrid>', pos)
x = x[:ug_end] + card + x[ug_end:]

# Make the dedicated Gaming page explain that it now controls full build profiles.
x = x.replace('Text="Gaming Boost / Developer"', 'Text="Gaming Build / Developer"', 1)
x = x.replace('От SAFE до LAB: больше производительности и меньше фоновой нагрузки, но все изменения сначала показываются и остаются обратимыми.',
              'Игровая сборка Windows: системные твики, источники фоновых процессов, службы/задачи и сеть объединены в один план. SAFE → PERFORMANCE → EXTREME → LAB.', 1)
x = x.replace('Базовые игровые настройки без спорных системных изменений.', 'Игровая база + безопасная разгрузка + Gaming Network SAFE.', 1)
x = x.replace('Gaming + Performance + безопасная разгрузка процессов.', 'Игровые/Performance твики + фоновые процессы/службы + Gaming Network SAFE.', 1)
x = x.replace('PERFORMANCE + агрессивная разгрузка фоновой Windows.', 'PERFORMANCE + агрессивная разгрузка Windows + Gaming Network EXTREME.', 1)
x = x.replace('EXTREME + спорные, но обратимые scheduler/GPU/MMCSS-настройки. Здесь нет обещания «+500% FPS»: сравнивайте реальные показатели до/после.',
              'EXTREME + экспериментальные scheduler/GPU/MMCSS-настройки и дополнительные условные службы. Сравнивайте FPS, frametime и фоновые процессы до/после.', 1)
x = x.replace('Content="Выбрать SAFE"', 'Content="GAME SAFE"', 1)
x = x.replace('Content="Выбрать PERFORMANCE"', 'Content="GAME PERFORMANCE"', 1)
x = x.replace('Content="Выбрать EXTREME"', 'Content="GAME EXTREME"', 1)
x = x.replace('Content="Выбрать LAB"', 'Content="GAME LAB"', 1)

p.write_text(x, encoding='utf-8')

# The selected-plan summary must state that services/tasks/network are executed only after confirmation.
p = root/'src'/'MerzoOptimizer.App'/'ViewModels'/'MainWindowViewModel.cs'
s = p.read_text(encoding='utf-8-sig')
old = 'Stage2StatusText = selected == 0\n            ? $"{title}: настройки уже применены или не поддерживаются на этом ПК."\n            : $"{title}: выбрано {selected}. Проверьте список. Применение пойдёт через Snapshot → Apply → Verify → Undo.";'
new = 'Stage2StatusText = selected == 0\n            ? $"{title}: Registry/Policy уже настроены; при применении Gaming Build всё равно будут проверены его службы/задачи и сеть."\n            : $"{title}: выбрано {selected} Registry/Policy. После подтверждения Merzo также проверит подходящие службы/задачи и Gaming Network. Всё выполняется по этапам с Snapshot/Undo.";'
if old not in s:
    raise SystemExit('R39 gaming selection status anchor missing')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('R39 Gaming Build UI integration: OK')
