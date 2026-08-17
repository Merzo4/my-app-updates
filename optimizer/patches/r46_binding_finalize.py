from pathlib import Path
import json, os
root=Path(os.environ['SOURCE_ROOT'])
p=root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml'
s=p.read_text(encoding='utf-8-sig')
replacements={
    '{Binding IsBusy}':'{Binding IsBusy, Mode=OneWay}',
    '{Binding HasOptimizationScanResults}':'{Binding HasOptimizationScanResults, Mode=OneWay}',
    '{Binding IsLightRecommended}':'{Binding IsLightRecommended, Mode=OneWay}',
    '{Binding IsStandardRecommended}':'{Binding IsStandardRecommended, Mode=OneWay}',
    '{Binding DeepScanProgress, StringFormat={}{0:0}%}':'{Binding DeepScanProgress, Mode=OneWay, StringFormat={}{0:0}%}',
    '{Binding NetworkProgress, StringFormat={}{0:0}%}':'{Binding NetworkProgress, Mode=OneWay, StringFormat={}{0:0}%}',
    '{Binding IsBalancedPowerActive}':'{Binding IsBalancedPowerActive, Mode=OneWay}',
    '{Binding IsPerformancePowerActive}':'{Binding IsPerformancePowerActive, Mode=OneWay}',
    '{Binding IsStartupUpdateNoticeVisible}':'{Binding IsStartupUpdateNoticeVisible, Mode=OneWay}',
}
for old,new in replacements.items():
    count=s.count(old)
    if count!=1: raise SystemExit(f'R46 binding finalize anchor count {count}: {old}')
    s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
helper=root/'src'/'MerzoOptimizer.ElevatedHelper'/'Program.cs'
h=helper.read_text(encoding='utf-8-sig')
old_name='IsValidDynamicStartupTweak'
new_name='ValidateStartupDynamicTweak'
if h.count(old_name)!=2: raise SystemExit(f'R46 helper validation rename count {h.count(old_name)}')
h=h.replace(old_name,new_name)
helper.write_text(h,encoding='utf-8')
settings_path=root/'data'/'update_settings.json'
cfg=json.loads(settings_path.read_text(encoding='utf-8-sig'))
if cfg.get('repository_owner')!='Merzo4' or cfg.get('repository_name')!='my-app-updates': raise SystemExit('R46 update feed aliases refused: non-official repository')
cfg['owner']=cfg['repository_owner']; cfg['repo']=cfg['repository_name']
settings_path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('R46 explicit OneWay bindings + helper validation naming + official feed aliases finalize: OK')
