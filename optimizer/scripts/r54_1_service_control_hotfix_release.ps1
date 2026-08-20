$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_r53_hotfix_bridge_release.ps1'
$original=Get-Content $base -Raw
$patched=$original

$oldChain="'r53_game_apply_hotfix.py','r53_version_finalize.py','r54_updater_bridge.py')"
$newChain="'r53_game_apply_hotfix.py','r53_version_finalize.py','r54_updater_bridge.py','r54_1_service_control_hotfix.py')"
if(($patched.Split($oldChain).Count-1)-ne1){throw 'R54.1 patch-chain anchor mismatch'}
$patched=$patched.Replace($oldChain,$newChain)

$old="`$text=`$text.Replace('0.1.53.1','0.1.54.0')"
$new="`$text=`$text.Replace('0.1.53.1','0.1.54.1')"
if(($patched.Split($old).Count-1)-ne1){throw 'R54.1 Convert version anchor mismatch'}
$patched=$patched.Replace($old,$new)

$old="`$text=`$text.Replace('Production R53.1','Production R54')"
$new="`$text=`$text.Replace('Production R53.1','Production R54.1')"
if(($patched.Split($old).Count-1)-ne1){throw 'R54.1 Convert title anchor mismatch'}
$patched=$patched.Replace($old,$new)

$old="`$text=`$text.Replace('R53 HOTFIX 1','R53 GAME HOTFIX BRIDGE')"
$new="`$text=`$text.Replace('R53 HOTFIX 1','R54 SERVICE CONTROL HOTFIX')"
if(($patched.Split($old).Count-1)-ne1){throw 'R54.1 Convert suffix anchor mismatch'}
$patched=$patched.Replace($old,$new)

$badgeOld=@'
$patchedV5=$patchedV5.Replace('Text="R53.1"','Text="R54"')
'@.Trim()
$badgeNew=@'
$patchedV5=$patchedV5.Replace('Text="R53.1"','Text="R54.1"')
'@.Trim()
if(($patched.Split($badgeOld).Count-1)-ne1){throw 'R54.1 V5 badge anchor mismatch'}
$patched=$patched.Replace($badgeOld,$badgeNew)

$buildCheckOld=@'
if(-not$patchedV1.Contains("-Version ''0.1.54.0''")){throw 'R54 bridge Build-Production version anchor missing'}
'@.Trim()
$buildCheckNew=@'
if(-not$patchedV1.Contains("-Version ''0.1.54.1''")){throw 'R54.1 Build-Production version anchor missing'}
'@.Trim()
if(($patched.Split($buildCheckOld).Count-1)-ne1){throw 'R54.1 R54-wrapper build self-check anchor mismatch'}
$patched=$patched.Replace($buildCheckOld,$buildCheckNew)

$dllCheckOld=@'
if(-not$patchedV1.Contains("if(`$v-ne'0.1.54.0')")){throw 'R54 bridge DLL version gate missing'}
'@.Trim()
$dllCheckNew=@'
if(-not$patchedV1.Contains("if(`$v-ne'0.1.54.1')")){throw 'R54.1 DLL version gate missing'}
'@.Trim()
if(($patched.Split($dllCheckOld).Count-1)-ne1){throw 'R54.1 R54-wrapper DLL self-check anchor mismatch'}
$patched=$patched.Replace($dllCheckOld,$dllCheckNew)

# R54 V2's intermediate identity gate intentionally stays R54. The R54.1
# product patch is executed later in V5 and the final outer gates require 54.1.
$distOld="if(`$version-ne'0.1.54.0')"
$distNew="if(`$version-ne'0.1.54.1')"
if(($patched.Split($distOld).Count-1)-ne1){throw 'R54.1 outer DLL version anchor mismatch'}
$patched=$patched.Replace($distOld,$distNew)

$uiOld=@'
if(-not$ui.Contains('Production R54 · 0.1.54')){throw 'R54 visible version missing'}
'@.Trim()
$uiNew=@'
if(-not$ui.Contains('Production R54.1 · 0.1.54.1')){throw 'R54.1 visible version missing'}
'@.Trim()
if(($patched.Split($uiOld).Count-1)-ne1){throw 'R54.1 outer visible version anchor mismatch'}
$patched=$patched.Replace($uiOld,$uiNew)

$navOld=@'
if(-not$ui.Contains('Text="R54"')){throw 'R54 navigation badge missing'}
'@.Trim()
$navNew=@'
if(-not$ui.Contains('Text="R54.1"')){throw 'R54.1 navigation badge missing'}
'@.Trim()
if(($patched.Split($navOld).Count-1)-ne1){throw 'R54.1 outer badge anchor mismatch'}
$patched=$patched.Replace($navOld,$navNew)

$issOld=@'
if(-not$i.Contains('#define MyAppVersion "0.1.54"') -and -not$i.Contains('AppVersion=0.1.54')){throw 'R54 Inno public version missing'}
'@.Trim()
$issNew=@'
if(-not$i.Contains('#define MyAppVersion "0.1.54.1"') -and -not$i.Contains('AppVersion=0.1.54.1')){throw 'R54.1 Inno public version missing'}
'@.Trim()
if(($patched.Split($issOld).Count-1)-ne1){throw 'R54.1 outer Inno anchor mismatch'}
$patched=$patched.Replace($issOld,$issNew)

try {
    Set-Content $base $patched -Encoding UTF8
    & $base
    if($LASTEXITCODE-ne0){throw "R54.1 inherited production gates failed: $LASTEXITCODE"}
    if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R54.1 SOURCE_ROOT missing'}
    $root=$env:SOURCE_ROOT

    $auditPath=Join-Path $root 'src\MerzoOptimizer.Windows\Services\WindowsServiceAuditService.cs'
    $restorePath=Join-Path $root 'src\MerzoOptimizer.Windows\Restore\WindowsRestoreService.cs'
    $helperPath=Join-Path $root 'src\MerzoOptimizer.Windows\Services\WindowsServiceStartTypeManager.cs'
    $xaml=Join-Path $root 'src\MerzoOptimizer.App\MainWindow.xaml'
    $iss=Join-Path $root 'installer\MerzoWindowsOptimizer.iss'
    foreach($p in @($auditPath,$restorePath,$helperPath,$xaml,$iss)){if(!(Test-Path $p)){throw "R54.1 final source missing: $p"}}
    $audit=Get-Content $auditPath -Raw
    $restore=Get-Content $restorePath -Raw
    $helper=Get-Content $helperPath -Raw
    $combined=$audit+"`n"+$restore+"`n"+$helper
    $ui=Get-Content $xaml -Raw
    $i=Get-Content $iss -Raw

    foreach($token in @(
        'WindowsServiceStartTypeManager.SetStartType(item.ServiceName, 4);',
        'WindowsServiceStartTypeManager.SetStartType(state.ServiceName, state.StartValue);',
        'ChangeServiceConfig(',
        'OpenSCManager(',
        'OpenService(',
        'ServiceChangeConfig = 0x0002'
    )){
        if(-not$combined.Contains($token)){throw "R54.1 SCM contract missing: $token"}
    }
    foreach($bad in @('key.SetValue("Start", 4','key.SetValue("Start", state.StartValue')){
        if($audit.Contains($bad) -or $restore.Contains($bad)){throw "R54.1 direct service Start registry write remains: $bad"}
    }
    if($audit -match 'CurrentControlSet\\Services.*writable:\s*true'){throw 'R54.1 writable service registry apply path remains'}
    if($restore -match 'CurrentControlSet\\Services.*writable:\s*true'){throw 'R54.1 writable service registry restore path remains'}
    if(!(Test-Path (Join-Path $root 'R54_1_SERVICE_CONTROL_HOTFIX.marker'))){throw 'R54.1 service hotfix marker missing'}
    if(-not$ui.Contains('Production R54.1 · 0.1.54.1') -or -not$ui.Contains('Text="R54.1"')){throw 'R54.1 visible identity missing'}
    if(-not$i.Contains('#define MyAppVersion "0.1.54.1"') -and -not$i.Contains('AppVersion=0.1.54.1')){throw 'R54.1 installer version missing'}

    $dist=Join-Path $root 'dist\app'
    foreach($n in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){
        $p=Join-Path $dist $n
        if(!(Test-Path $p)){throw "R54.1 missing $n"}
        $version=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString()
        if($version-ne'0.1.54.1'){throw "R54.1 $n version=$version"}
    }

    $notes=Join-Path $root 'dist\R53_RELEASE_NOTES.md'
    @'

## 0.1.54.1 — SERVICE CONTROL HOTFIX

- Исправлен фактический откат GAME на `Distributed Link Tracking Client`: `Requested registry access is not allowed`.
- Применение и snapshot Undo больше не записывают `HKLM\SYSTEM\CurrentControlSet\Services\<service>\Start` напрямую.
- Оба направления используют один штатный Windows Service Control Manager helper (`OpenSCManager` + `OpenService` + `ChangeServiceConfig`).
- Snapshot/Undo, service allow-list и запрет принудительного запуска восстановленной службы сохранены.
- R54 updater используется для доставки четырёхчастного hotfix `0.1.54.1` без обрезания revision.
'@ | Add-Content $notes -Encoding UTF8
    Write-Host 'R54_1_SERVICE_CONTROL_ALL_GATES_PASS'
}
finally {
    Set-Content $base $original -Encoding UTF8
}
