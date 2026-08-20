from pathlib import Path
import json, os, re

root=Path(os.environ['SOURCE_ROOT'])

def read(p): return p.read_text(encoding='utf-8-sig')
def write(p,s): p.write_text(s,encoding='utf-8')

# -----------------------------------------------------------------------------
# 1) Widgets: R50 used the documented device policy under HKLM. On customized
#    Windows installations that policy key can have a restrictive ACL, which
#    produced UnauthorizedAccessException and correctly triggered package rollback.
#    Normal LIGHT/GAME/EXTREME must not depend on such a machine-policy ACL.
# -----------------------------------------------------------------------------
tp=root/'data'/'tweaks.json'
tweaks=json.loads(read(tp))
byid={t.get('id'):t for t in tweaks}
wid=byid.get('ui.disable_widgets')
if wid is None:
    raise SystemExit('R51 ui.disable_widgets missing')

wid['name']='Убрать Widgets с панели задач'
wid['category']='Windows UX'
wid['risk']='Safe'
wid['requires_admin']=False
wid['requires_restart']=False
wid['description']='Безопасно убирает точку входа Widgets из панели задач текущего пользователя. Не зависит от защищённого HKLM policy key и не может сорвать установку всей сборки из-за ACL.'
wid['expected_effect']='Кнопка Widgets исчезает с панели задач. Дополнительное ограничение фоновой активности выполняется другими privacy/background правилами сборки.'
wid['source_note']='Windows per-user taskbar setting. R51 intentionally avoids mandatory HKLM Dsh mutation in automatic profiles.'
wid['registry_actions']=[{
    'hive':'CurrentUser',
    'key_path':'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
    'value_name':'TaskbarDa',
    'value_type':'DWord',
    'integer_value':0
}]
wid['min_windows_build']=22000

# Keep the real device policy available to experts/LAB, but never auto-select it
# in LIGHT/GAME/EXTREME because a custom ACL must not abort the whole package.
policy_id='ui.disable_widgets_device_policy'
if policy_id not in byid:
    tweaks.append({
        'id':policy_id,
        'name':'Widgets — машинная политика (эксперт)',
        'category':'LAB / Windows UX',
        'risk':'Balanced',
        'requires_admin':True,
        'requires_restart':False,
        'description':'Полностью запрещает Widgets на уровне устройства через документированную NewsAndInterests policy. На кастомных Windows доступ к HKLM\\SOFTWARE\\Policies\\Microsoft\\Dsh может быть ограничен, поэтому правило не входит в автоматические сборки.',
        'expected_effect':'При доступной политике Widgets запрещаются на уровне устройства. Если ACL системы запрещает запись — правило следует оставить неприменённым, а автоматические сборки используют безопасный per-user вариант.',
        'source_note':'Microsoft NewsAndInterests/AllowNewsAndInterests device policy.',
        'profile_tags':['gaming_lab'],
        'registry_actions':[{
            'hive':'LocalMachine',
            'key_path':'SOFTWARE\\Policies\\Microsoft\\Dsh',
            'value_name':'AllowNewsAndInterests',
            'value_type':'DWord',
            'integer_value':0
        }],
        'min_windows_build':22000
    })
else:
    pol=byid[policy_id]
    pol['profile_tags']=[x for x in pol.get('profile_tags',[]) if x not in ('merzo_light','merzo_game','merzo_extreme')]

write(tp,json.dumps(tweaks,ensure_ascii=False,indent=2)+'\n')

# -----------------------------------------------------------------------------
# 2) Operation Center readability. Replace the legacy R37 tab. It had small,
#    muted text and a hard-coded green check icon on EVERY event row, even for
#    warnings/errors. R51 shows the real event prefix and makes current work
#    readable without increasing the application window itself.
# -----------------------------------------------------------------------------
xp=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
x=read(xp)
start=x.find('<TabItem Header="Ход работы"')
if start < 0:
    raise SystemExit('R51 operation tab start missing')
end=x.find('</TabItem>',start)
if end < 0:
    raise SystemExit('R51 operation tab end missing')
end += len('</TabItem>')

new_tab=r'''<TabItem Header="Ход работы" Style="{StaticResource SubTabItem}">
                                <Grid x:Name="OperationCenterRoot" Margin="0,6,0,0" MinHeight="330">
                                    <Grid.RowDefinitions><RowDefinition Height="168"/><RowDefinition Height="*"/></Grid.RowDefinitions>

                                    <Border Grid.Row="0" Background="#0E1A21" BorderBrush="#34756D" BorderThickness="1" CornerRadius="11" Padding="14,11" Margin="0,0,0,8">
                                        <Grid>
                                            <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/><RowDefinition Height="Auto"/></Grid.RowDefinitions>
                                            <Grid Grid.Row="0">
                                                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                                                <StackPanel>
                                                    <TextBlock Text="Ход выполнения" FontSize="16.5" FontWeight="SemiBold" Foreground="#F1F7F7"/>
                                                    <TextBlock Text="Текущая операция и реальный журнал изменений" Foreground="#9EB8B6" FontSize="11" Margin="0,2,0,0"/>
                                                </StackPanel>
                                                <Border Grid.Column="1" Background="#173A35" BorderBrush="#3A8278" BorderThickness="1" CornerRadius="12" Padding="11,5" VerticalAlignment="Center">
                                                    <TextBlock Text="{Binding DeepScanProgress, Mode=OneWay, StringFormat={}{0:0}%}" Foreground="#7AD2C6" FontSize="14" FontWeight="Bold"/>
                                                </Border>
                                            </Grid>

                                            <Border Grid.Row="1" Background="#13232B" CornerRadius="8" Padding="10,7" Margin="0,9,0,0">
                                                <StackPanel>
                                                    <TextBlock Text="СЕЙЧАС" Foreground="#72C9BE" FontSize="10.2" FontWeight="Bold"/>
                                                    <TextBlock Text="{Binding DeepScanStatusText, Mode=OneWay}" Foreground="#F0F6F6" FontSize="13.4" FontWeight="SemiBold" TextWrapping="Wrap" LineHeight="19" Margin="0,2,0,0"/>
                                                </StackPanel>
                                            </Border>

                                            <ProgressBar Grid.Row="2" Value="{Binding DeepScanProgress, Mode=OneWay}" Maximum="100" Height="8" Margin="0,9,0,6"/>

                                            <Grid Grid.Row="3">
                                                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                                                <TextBlock Text="{Binding Stage2StatusText, Mode=OneWay}" Foreground="#B7CDCB" FontSize="10.8" TextWrapping="Wrap" VerticalAlignment="Center"/>
                                                <TextBlock Grid.Column="1" Text="Snapshot → Apply → Verify → Log → Undo" Foreground="#7EA29F" FontSize="10.2" Margin="12,0,0,0" VerticalAlignment="Center"/>
                                            </Grid>
                                        </Grid>
                                    </Border>

                                    <Border Grid.Row="1" Background="#0B1218" BorderBrush="#273A43" BorderThickness="1" CornerRadius="11" Padding="10,9">
                                        <Grid>
                                            <Grid.RowDefinitions><RowDefinition Height="34"/><RowDefinition Height="*"/></Grid.RowDefinitions>
                                            <Grid Grid.Row="0">
                                                <Grid.ColumnDefinitions><ColumnDefinition Width="*"/><ColumnDefinition Width="Auto"/></Grid.ColumnDefinitions>
                                                <StackPanel Orientation="Horizontal" VerticalAlignment="Center">
                                                    <TextBlock Text="Ход событий" FontSize="13.8" FontWeight="SemiBold" Foreground="#F0F6F6"/>
                                                    <Border Background="#173A35" BorderBrush="#306D66" BorderThickness="1" CornerRadius="8" Padding="7,2" Margin="9,0,0,0"><TextBlock Text="LIVE" Foreground="#72C9BE" FontSize="9.8" FontWeight="Bold"/></Border>
                                                </StackPanel>
                                                <TextBlock Grid.Column="1" Text="✓ готово   → выполняется   ⚠ предупреждение   ✕ ошибка" Foreground="#A7BCBA" FontSize="10.2" VerticalAlignment="Center"/>
                                            </Grid>

                                            <ScrollViewer x:Name="OperationEventScroll" Grid.Row="1" VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled" CanContentScroll="False" Padding="0,3,2,0">
                                                <ItemsControl ItemsSource="{Binding DeepScanSteps}">
                                                    <ItemsControl.ItemTemplate>
                                                        <DataTemplate>
                                                            <Border Background="#101A21" BorderBrush="#29404A" BorderThickness="1" CornerRadius="8" Padding="11,8" Margin="0,0,0,6">
                                                                <Grid>
                                                                    <Grid.ColumnDefinitions><ColumnDefinition Width="4"/><ColumnDefinition Width="*"/></Grid.ColumnDefinitions>
                                                                    <Border Background="#3C8279" CornerRadius="2" Margin="0,1,0,1"/>
                                                                    <TextBlock Grid.Column="1" Text="{Binding}" FontSize="12.3" LineHeight="18" Foreground="#E4EEEE" TextWrapping="Wrap" Margin="10,0,2,0"/>
                                                                </Grid>
                                                            </Border>
                                                        </DataTemplate>
                                                    </ItemsControl.ItemTemplate>
                                                </ItemsControl>
                                            </ScrollViewer>
                                        </Grid>
                                    </Border>
                                </Grid>
                            </TabItem>'''

x=x[:start]+new_tab+x[end:]

# Production identity for the next OTA build.
x=x.replace('Merzo Windows Optimizer — Production 0.1.50 · R50 UI RELIABILITY','Merzo Windows Optimizer — Production 0.1.51 · R51 STABILITY + READABILITY')
x=x.replace('Production R50 · 0.1.50','Production R51 · 0.1.51')
x=x.replace('<TextBlock Text="R50" Foreground="{StaticResource Accent}"','<TextBlock Text="R51" Foreground="{StaticResource Accent}"',1)
write(xp,x)

# Stamp every project consistently.
for p in (root/'src').rglob('*.csproj'):
    s=read(p)
    s=s.replace('0.1.50.0','0.1.51.0').replace('0.1.50','0.1.51')
    write(p,s)

app=root/'src'/'MerzoOptimizer.App'/'App.xaml.cs'
s=read(app).replace('0.1.50','0.1.51').replace('[Crash][R50]','[Crash][R51]').replace('Production R50','Production R51')
write(app,s)

sp=root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
s=read(sp).replace('PRODUCTION R50 UI RELIABILITY','PRODUCTION R51 STABILITY + READABILITY')
write(sp,s)

# Release Center entry.
rp=root/'data'/'release_notes.json'
try:
    data=json.loads(read(rp))
    entry={
        'version':'0.1.51',
        'title':'R51 STABILITY + READABILITY',
        'changes':[
            'Исправлен сбой GAME/LIGHT/EXTREME на шаге Widgets: автоматические сборки больше не зависят от защищённого HKLM Dsh policy key.',
            'Widgets в автоматических сборках теперь убираются через безопасную per-user настройку TaskbarDa; строгая device-policy оставлена только в экспертном LAB.',
            'Полностью переработан Ход работы: крупнее текущая операция, выше контраст, крупный процент и читаемый журнал событий.',
            'Убрана ложная зелёная галочка у каждой строки журнала — теперь виден реальный префикс ✓ / → / ⚠ / ✕.',
            'R48 OTA, R49 Recovery/OneDrive/три сборки и R50 UI reliability сохранены.'
        ]
    }
    if isinstance(data,list):
        data=[e for e in data if not (isinstance(e,dict) and e.get('version')=='0.1.51')]
        data.insert(0,entry)
    elif isinstance(data,dict) and isinstance(data.get('releases'),list):
        data['releases']=[e for e in data['releases'] if not (isinstance(e,dict) and e.get('version')=='0.1.51')]
        data['releases'].insert(0,entry)
    elif isinstance(data,dict):
        data['version']='0.1.51'; data['title']='R51 STABILITY + READABILITY'; data['changes']=entry['changes']
    write(rp,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
except Exception as ex:
    raise SystemExit(f'R51 release notes failed: {ex}')

(root/'R51_STABILITY_READABILITY.marker').write_text(
    'R51 STABILITY + READABILITY\nWidgets automatic-profile ACL fix + readable Operation Center\n',encoding='utf-8')

print('R51 widgets/readability patch: OK')
