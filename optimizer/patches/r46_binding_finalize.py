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
updater=root/'src'/'MerzoOptimizer.Windows'/'Updates'/'GitHubUpdateService.cs'
u=updater.read_text(encoding='utf-8-sig')
old='''        if (!HasOfficialProductionConfiguration() || !ValidateDownloadMetadata(update, out var metadataError))\n            return new UpdateDownloadResult { Success = false, Message = metadataError ?? "Метаданные обновления отклонены." };\n'''
new='''        string? metadataError = null;\n        if (!HasOfficialProductionConfiguration())\n            return new UpdateDownloadResult { Success = false, Message = "Конфигурация обновлений не является официальной." };\n        if (!ValidateDownloadMetadata(update, out metadataError))\n            return new UpdateDownloadResult { Success = false, Message = metadataError ?? "Метаданные обновления отклонены." };\n'''
if u.count(old)!=1: raise SystemExit(f'R46 updater definite-assignment anchor count {u.count(old)}')
u=u.replace(old,new,1)
updater.write_text(u,encoding='utf-8')
selftest=root/'src'/'MerzoOptimizer.SelfTest'/'Program.cs'
st=selftest.read_text(encoding='utf-8-sig')
old_test='''    if (!xaml.Contains("MinWidth=\\"880\\" MinHeight=\\"520\\"", StringComparison.Ordinal)) failures.Add("Approved minimum window must remain 880x520.");'''
new_test='''    if (!xaml.Contains("MinWidth=\\"920\\" MinHeight=\\"560\\"", StringComparison.Ordinal)) failures.Add("R46 safe minimum window must remain 920x560.");'''
if st.count(old_test)!=1: raise SystemExit(f'R46 minimum-window selftest anchor count {st.count(old_test)}')
st=st.replace(old_test,new_test,1)
selftest.write_text(st,encoding='utf-8')
print('R46 OneWay/helper/feed/updater/minimum-window SelfTest finalize: OK')
