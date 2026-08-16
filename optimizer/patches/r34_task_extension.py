from pathlib import Path
import json, os
root=Path(os.environ['SOURCE_ROOT'])
p=root/'data'/'task_rules.json'
tasks=json.loads(p.read_text(encoding='utf-8-sig'))
existing={str(x.get('pattern','')).lower() for x in tasks}
extra=[
 (r'\\Microsoft\\Windows\\Work Folders\\','BALANCED','Можно отключать только если корпоративные Work Folders не используются.'),
 (r'\\Microsoft\\Windows\\Workplace Join\\','BALANCED','Не трогать на Entra ID/Azure AD/корпоративных ПК; на обычном локальном домашнем ПК это условный кандидат.'),
 (r'\\Microsoft\\Windows\\Bluetooth\\','BALANCED','Можно отключать Bluetooth-задачи только на ПК без Bluetooth-устройств и сценариев.'),
]
for pattern,risk,recommendation in extra:
    if pattern.lower() not in existing:
        tasks.append({'pattern':pattern,'risk':risk,'recommendation':recommendation})
        existing.add(pattern.lower())
p.write_text(json.dumps(tasks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

# Cumulative-build navigation compatibility. R37 promotes the old
# "Repair / Network" placeholder to a real navigation item. Keep an invisible
# self-closing copy of the approved NavRadioButton contract so the later R37
# patch can clone style/GroupName without changing the visible R34-R36 UI.
xaml=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
if xaml.exists():
    s=xaml.read_text(encoding='utf-8-sig')
    placeholder='<TextBlock Text="Repair / Network" Foreground="{StaticResource TextMuted}" FontSize="10" Margin="7,4"/>'
    if placeholder not in s:
        placeholder='<TextBlock Text="Repair / Network" Foreground="{StaticResource TextMuted}" FontSize="11.2" Margin="7,4"/>'
    marker='R37_NETWORK_NAV_TEMPLATE'
    if placeholder in s and marker not in s:
        template='<!-- R37_NETWORK_NAV_TEMPLATE <RadioButton x:Name="GamingDevNav" GroupName="MainNav" Style="{StaticResource NavRadioButton}" Click="GamingDev_Click" Content="Gaming / Developer"/> -->\n                    '
        s=s.replace(placeholder,template+placeholder,1)
    # r37_network_center searches for the first exact Text="Питание" and uses
    # it to locate the Power TabItem. The sidebar label appears earlier, so keep
    # its visible text identical while making its XAML literal unambiguous.
    s=s.replace('Text="Питание"','Text="Питание "',1)
    xaml.write_text(s,encoding='utf-8')
print('R34 task extension OK tasks=',len(tasks))
