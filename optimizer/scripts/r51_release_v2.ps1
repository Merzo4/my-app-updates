$ErrorActionPreference='Stop'
$src=Get-Content '.\optimizer\scripts\r50_release.ps1' -Raw

# Promote the proven R50 pipeline to R51 without renaming the retained R50 patch.
$needle="`$src=`$src.Replace('0.1.49','0.1.50')"
$replacement="`$src=`$src.Replace('0.1.49','0.1.51')"
if(($src.Split($needle).Count-1)-ne1){throw 'R51 version promotion anchor mismatch'}
$src=$src.Replace($needle,$replacement)
$src=$src.Replace('Production R50','Production R51')
$src=$src.Replace('R50_RELEASE_NOTES.md','R51_RELEASE_NOTES.md')

$old="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py','r50_ui_reliability.py')"
$new="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py','r50_ui_reliability.py','r51_widgets_operation_readability.py')"
if(($src.Split($old).Count-1)-ne1){throw 'R51 patch-chain anchor mismatch'}
$src=$src.Replace($old,$new)

$oldGate="'R49_FINALIZE.marker','R50_UI_RELIABILITY.marker']:"
$newGate="'R49_FINALIZE.marker','R50_UI_RELIABILITY.marker','R51_STABILITY_READABILITY.marker']:"
if(($src.Split($oldGate).Count-1)-ne1){throw 'R51 marker gate anchor mismatch'}
$src=$src.Replace($oldGate,$newGate)

# Immediate previous-client OTA smoke: installed R50 must discover R51.
$oldPrev='<AssemblyVersion>0.1.49.0</AssemblyVersion><FileVersion>0.1.49.0</FileVersion><InformationalVersion>0.1.49</InformationalVersion>'
$newPrev='<AssemblyVersion>0.1.50.0</AssemblyVersion><FileVersion>0.1.50.0</FileVersion><InformationalVersion>0.1.50</InformationalVersion>'
if(($src.Split($oldPrev).Count-1)-ne1){throw 'R51 OTA previous-client anchor mismatch'}
$src=$src.Replace($oldPrev,$newPrev)
$src=$src.Replace('R50_DISPATCH_NETWORK_PASS','R51_DISPATCH_NETWORK_PASS')
$src=$src.Replace("Write-Host 'R50_UI_RELIABILITY_GATES_PASS'","Write-Host 'R51_BASE_GATES_PASS'")

$tmp=Join-Path $env:RUNNER_TEMP 'r51_release_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp
if($LASTEXITCODE-ne0){throw "R51 expanded release script failed: $LASTEXITCODE"}
if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R51 SOURCE_ROOT missing'}

# Exact regression gates for the screenshot failure and Operation Center readability.
@'
import json, os, pathlib
root=pathlib.Path(os.environ['SOURCE_ROOT'])
tweaks=json.loads((root/'data'/'tweaks.json').read_text(encoding='utf-8-sig'))
byid={t.get('id'):t for t in tweaks}
w=byid.get('ui.disable_widgets')
assert w is not None
assert w.get('requires_admin') is False, 'automatic Widgets rule still requires admin'
acts=w.get('registry_actions') or []
assert len(acts)==1
assert acts[0].get('hive')=='CurrentUser'
assert acts[0].get('key_path')==r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced'
assert acts[0].get('value_name')=='TaskbarDa' and acts[0].get('integer_value')==0
p=byid.get('ui.disable_widgets_device_policy')
assert p is not None and p.get('requires_admin') is True
assert not ({'merzo_light','merzo_game','merzo_extreme'} & set(p.get('profile_tags') or []))

x=(root/'src'/'MerzoOptimizer.App'/'MainWindow.xaml').read_text(encoding='utf-8-sig')
for token in ['x:Name="OperationCenterRoot"','x:Name="OperationEventScroll"','Text="Ход событий"','FontSize="13.4"','FontSize="12.3"','Production R51 · 0.1.51']:
    assert token in x, 'readability token missing: '+token
sec=x[x.index('<TabItem Header="Ход работы"'):]
sec=sec[:sec.index('</TabItem>')]
assert 'Text="✓"' not in sec, 'legacy hard-coded success icon still present'
print('R51_WIDGETS_AND_READABILITY_SOURCE_PASS')
'@ | python -
if($LASTEXITCODE-ne0){throw 'R51 widgets/readability source gate failed'}

# Runtime ACL smoke for the automatic per-user Widgets route.
$smoke='HKCU:\Software\MerzoWindowsOptimizer\R51WidgetAclSmoke'
try {
    New-Item -Path $smoke -Force | Out-Null
    New-ItemProperty -Path $smoke -Name TaskbarDa -PropertyType DWord -Value 0 -Force | Out-Null
    if((Get-ItemProperty -Path $smoke -Name TaskbarDa).TaskbarDa-ne0){throw 'HKCU widget ACL verify failed'}
    Write-Host 'R51_WIDGETS_HKCU_RUNTIME_PASS'
} finally {
    Remove-Item $smoke -Recurse -Force -ErrorAction SilentlyContinue
}

# Ensure packaged portable contains the fixed rule, not stale R50 data.
$portable=Join-Path $env:SOURCE_ROOT 'dist\MerzoWindowsOptimizer-portable-win-x64.zip'
if(!(Test-Path $portable)){throw 'R51 portable missing'}
$check=Join-Path $env:RUNNER_TEMP 'r51_portable_check'
Remove-Item $check -Recurse -Force -ErrorAction SilentlyContinue
Expand-Archive $portable $check -Force
$env:R51_PORTABLE_CHECK=$check
@'
import json, os, pathlib
root=pathlib.Path(os.environ['R51_PORTABLE_CHECK'])
data=json.loads((root/'data'/'tweaks.json').read_text(encoding='utf-8-sig'))
w=next(t for t in data if t.get('id')=='ui.disable_widgets')
assert w['requires_admin'] is False
assert w['registry_actions'][0]['hive']=='CurrentUser'
assert w['registry_actions'][0]['value_name']=='TaskbarDa'
print('R51_PACKAGED_WIDGETS_PASS')
'@ | python -
if($LASTEXITCODE-ne0){throw 'R51 packaged Widgets gate failed'}

$notes=Join-Path $env:SOURCE_ROOT 'dist\R51_RELEASE_NOTES.md'
@'
# R51 STABILITY + READABILITY

- Исправлен сбой GAME/LIGHT/EXTREME на шаге «Отключить Widgets»: автоматические сборки больше не зависят от HKLM Dsh policy key, который на кастомных Windows может вернуть UnauthorizedAccessException.
- Автоматический Widgets-твик теперь использует безопасную per-user настройку TaskbarDa=0. Строгая device policy сохранена только в экспертном LAB.
- Переработан «Ход работы»: текущая операция крупнее, выше контраст, крупный процент, Snapshot → Apply → Verify → Log → Undo читается сразу.
- «Ход событий» получил FontSize 12.3, LineHeight 18, отдельную вертикальную прокрутку и легенду ✓ / → / ⚠ / ✕.
- Убрана ложная зелёная галочка, которая раньше рисовалась у каждой строки независимо от результата.
- Сохранены R46 security, R48 OTA, R49 LIGHT/GAME/EXTREME + Recovery/OneDrive и R50 UI reliability.
'@ | Set-Content $notes -Encoding UTF8

Write-Host 'R51_STABILITY_READABILITY_GATES_PASS'
