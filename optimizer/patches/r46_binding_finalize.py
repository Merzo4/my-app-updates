from pathlib import Path
import os
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
print('R46 explicit OneWay binding finalize: OK')
