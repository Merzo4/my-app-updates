from pathlib import Path
import os
root=Path(os.environ['SOURCE_ROOT'])
p=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
s=p.read_text(encoding='utf-8-sig')
old='''<StackPanel Grid.Column="1" VerticalAlignment="Center"><TextBlock Text="Просто выбери уровень — Merzo сам соберёт только недостающие изменения" FontSize="11.4" FontWeight="SemiBold"/><TextBlock Text="Телеметрия отключается уже в ЛАЙТ. Defender / Windows Update / Store / IPv6 / pagefile сборки не отключают." Foreground="{StaticResource TextMuted}" FontSize="9.5"/></StackPanel>'''
new='''<StackPanel Grid.Column="1" VerticalAlignment="Center"><TextBlock Text="Просто выбери уровень — Merzo сам соберёт только недостающие изменения" FontSize="11.4" FontWeight="SemiBold"/><TextBlock Text="Телеметрия отключается уже в ЛАЙТ. Defender / Windows Update / Store / IPv6 / pagefile сборки не отключают." Foreground="{StaticResource TextMuted}" FontSize="9.5"/><TextBlock Text="ПРОВЕРКА СИСТЕМЫ ГОТОВА" Foreground="{StaticResource Accent}" FontSize="8.8" FontWeight="Bold" Margin="0,3,0,0"><TextBlock.Style><Style TargetType="TextBlock"><Setter Property="Visibility" Value="Collapsed"/><Style.Triggers><DataTrigger Binding="{Binding HasOptimizationScanResults, Mode=OneWay}" Value="True"><Setter Property="Visibility" Value="Visible"/></DataTrigger></Style.Triggers></Style></TextBlock.Style></TextBlock></StackPanel>'''
if s.count(old)!=1: raise SystemExit(f'R47 scan badge anchor count={s.count(old)}')
s=s.replace(old,new,1)
old_button='Command="{Binding SelectGamingExtremeCommand}" Click="OpenOptimization_Click" Content="Выбрать EXTREME"'
new_button='Command="{Binding SelectGamingExtremeCommand}" Click="OpenOptimization_Click" Content="Выбрать GAME EXTREME"'
if s.count(old_button)!=1: raise SystemExit(f'R47 expert extreme anchor count={s.count(old_button)}')
s=s.replace(old_button,new_button,1)
p.write_text(s,encoding='utf-8')
(root/'R47_FINALIZE.marker').write_text('R47 FINALIZE\nscan-ready OneWay badge + expert GAME EXTREME label\n',encoding='utf-8')
print('R47 finalize patch OK')