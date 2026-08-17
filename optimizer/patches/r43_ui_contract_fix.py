from pathlib import Path
import os

root=Path(os.environ['SOURCE_ROOT'])
p=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
s=p.read_text(encoding='utf-8-sig')

def rep(old,new,label):
    global s
    if old not in s:
        raise SystemExit('R43 UI contract anchor missing: '+label)
    s=s.replace(old,new,1)

rep(
'<StackPanel Grid.Column="1" VerticalAlignment="Center"><StackPanel Orientation="Horizontal"><TextBlock Text="Рекомендация: " Foreground="{StaticResource TextSecondary}" FontSize="10.8"/><TextBlock Text="{Binding RecommendedProfileTitle, Mode=OneWay}" Foreground="{StaticResource Accent}" FontSize="13.2" FontWeight="SemiBold"/></StackPanel><TextBlock Text="{Binding RecommendedProfileReason, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.6" TextTrimming="CharacterEllipsis" Margin="0,2,10,0"/></StackPanel>',
'<StackPanel Grid.Column="1" VerticalAlignment="Center"><StackPanel Orientation="Horizontal"><TextBlock Text="Рекомендация: " Foreground="{StaticResource TextSecondary}" FontSize="10.8"/><TextBlock Text="{Binding RecommendedProfileTitle, Mode=OneWay}" Foreground="{StaticResource Accent}" FontSize="13.2" FontWeight="SemiBold"/><TextBlock Text="СКАН ГОТОВ" Foreground="{StaticResource Accent}" FontSize="8.8" FontWeight="Bold" Margin="7,2,0,0"><TextBlock.Style><Style TargetType="TextBlock"><Setter Property="Visibility" Value="Collapsed"/><Style.Triggers><DataTrigger Binding="{Binding HasOptimizationScanResults}" Value="True"><Setter Property="Visibility" Value="Visible"/></DataTrigger></Style.Triggers></Style></TextBlock.Style></TextBlock></StackPanel><TextBlock Text="{Binding RecommendedProfileReason, Mode=OneWay}" Foreground="{StaticResource TextMuted}" FontSize="9.6" TextTrimming="CharacterEllipsis" Margin="0,2,10,0"/></StackPanel>',
'optimization scan state')

rep(
'<TextBlock Text="LIGHT" FontSize="15" FontWeight="SemiBold"/><TextBlock Text="Безопасная база"',
'<StackPanel Orientation="Horizontal"><TextBlock Text="LIGHT" FontSize="15" FontWeight="SemiBold"/><TextBlock Text="РЕКОМЕНДУЕТСЯ" Foreground="{StaticResource Accent}" FontSize="8.6" FontWeight="Bold" Margin="7,3,0,0"><TextBlock.Style><Style TargetType="TextBlock"><Setter Property="Visibility" Value="Collapsed"/><Style.Triggers><DataTrigger Binding="{Binding IsLightRecommended}" Value="True"><Setter Property="Visibility" Value="Visible"/></DataTrigger></Style.Triggers></Style></TextBlock.Style></TextBlock></StackPanel><TextBlock Text="Безопасная база"',
'LIGHT recommendation state')

rep(
'<TextBlock Text="STANDARD" FontSize="15" FontWeight="SemiBold"/><TextBlock Text="Баланс скорости и совместимости"',
'<StackPanel Orientation="Horizontal"><TextBlock Text="STANDARD" FontSize="15" FontWeight="SemiBold"/><TextBlock Text="РЕКОМЕНДУЕТСЯ" Foreground="{StaticResource Accent}" FontSize="8.6" FontWeight="Bold" Margin="7,3,0,0"><TextBlock.Style><Style TargetType="TextBlock"><Setter Property="Visibility" Value="Collapsed"/><Style.Triggers><DataTrigger Binding="{Binding IsStandardRecommended}" Value="True"><Setter Property="Visibility" Value="Visible"/></DataTrigger></Style.Triggers></Style></TextBlock.Style></TextBlock></StackPanel><TextBlock Text="Баланс скорости и совместимости"',
'STANDARD recommendation state')

rep(
'<ItemsControl.ItemsPanel><ItemsPanelTemplate><UniformGrid Columns="2"/></ItemsPanelTemplate></ItemsControl.ItemsPanel><ItemsControl.ItemTemplate><DataTemplate><Border Style="{StaticResource R43PageCard}" Margin="0,0,7,7" Padding="10,8">',
'<ItemsControl.ItemsPanel><ItemsPanelTemplate><WrapPanel/></ItemsPanelTemplate></ItemsControl.ItemsPanel><ItemsControl.ItemTemplate><DataTemplate><Border Width="360" Style="{StaticResource R43PageCard}" Margin="0,0,7,7" Padding="10,8">',
'cleanup responsive cards')

rep(
'<StackPanel><TextBlock Text="Сбалансированный" FontSize="13" FontWeight="SemiBold"/><TextBlock Text="Повседневная работа и экономичность."',
'<StackPanel><StackPanel Orientation="Horizontal"><TextBlock Text="Сбалансированный" FontSize="13" FontWeight="SemiBold"/><TextBlock Text="АКТИВЕН" Foreground="{StaticResource Accent}" FontSize="8.8" FontWeight="Bold" Margin="7,3,0,0"><TextBlock.Style><Style TargetType="TextBlock"><Setter Property="Visibility" Value="Collapsed"/><Style.Triggers><DataTrigger Binding="{Binding IsBalancedPowerActive}" Value="True"><Setter Property="Visibility" Value="Visible"/></DataTrigger></Style.Triggers></Style></TextBlock.Style></TextBlock></StackPanel><TextBlock Text="Повседневная работа и экономичность."',
'balanced active state')

rep(
'<StackPanel><TextBlock Text="Высокая производительность" FontSize="13" FontWeight="SemiBold"/><TextBlock Text="Для ПК от сети. Возможны больший нагрев и расход энергии."',
'<StackPanel><StackPanel Orientation="Horizontal"><TextBlock Text="Высокая производительность" FontSize="13" FontWeight="SemiBold"/><TextBlock Text="АКТИВЕН" Foreground="{StaticResource Warning}" FontSize="8.8" FontWeight="Bold" Margin="7,3,0,0"><TextBlock.Style><Style TargetType="TextBlock"><Setter Property="Visibility" Value="Collapsed"/><Style.Triggers><DataTrigger Binding="{Binding IsPerformancePowerActive}" Value="True"><Setter Property="Visibility" Value="Visible"/></DataTrigger></Style.Triggers></Style></TextBlock.Style></TextBlock></StackPanel><TextBlock Text="Для ПК от сети. Возможны больший нагрев и расход энергии."',
'performance active state')

rep('Text="Все доступные схемы Windows"','Text="Все схемы Windows"','power schemes label')

p.write_text(s,encoding='utf-8')
(root/'R43_UI_CONTRACT_FIX.marker').write_text('R43 UI CONTRACT FIX\n',encoding='utf-8')
print('R43 UI contract fix: OK')
