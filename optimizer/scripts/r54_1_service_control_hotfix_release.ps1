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

# R54 wrapper validates its generated R53 scripts before executing them. Those
# checks must follow the new 54.1 target too; they are runner assertions only.
$buildCheckOld=@'
if(-not$patchedV1.Contains("-Version ''0.1.54.0''")){throw 'R54 bridge Build-Production version anchor missing'}
'@.Trim()
$buildCheckNew=@'
if(-not$patchedV1.Contains("-Version ''0.1.54.1''")){throw 'R54.1 Build-Production version anchor missing'}
'@.Trim()
if(($patched.Split($buildCheckOld).Count-1)-ne1){throw 'R54.1 R54-wrapper build self-check anchor mismatch'}
$patched=$patched.Replace($buildCheckOld,$buildCheckNew)

$dllCheckOld=@'
if(-not$patchedV1.Contains("if($v-ne'0.1.54.0')")){throw 'R54 bridge DLL version gate missing'}
'@.Trim()
$dllCheckNew=@'
if(-not$patchedV1.Contains("if($v-ne'0.1.54.1')")){throw 'R54.1 DLL version gate missing'}
'@.Trim()
if(($patched.Split($dllCheckOld).Count-1)-ne1){throw 'R54.1 R54-wrapper DLL self-check anchor mismatch'}
$patched=$patched.Replace($dllCheckOld,$dllCheckNew)

$v2CheckOld=@'
if(-not$patchedV2.Contains("'Production R54 · 0.1.54'")){throw 'R54 bridge V2 exact title anchor missing after conversion'}
'@.Trim()
$v2CheckNew=@'
if(-not$patchedV2.Contains("'Production R54.1 · 0.1.54.1'")){throw 'R54.1 V2 exact title anchor missing after conversion'}
'@.Trim()
if(($patched.Split($v2CheckOld).Count-1)-ne1){throw 'R54.1 R54-wrapper V2 title self-check anchor mismatch'}
$patched=$patched.Replace($v2CheckOld,$v2CheckNew)

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

    $svc=Join-Path $root 'src\MerzoOptimizer.Windows\Services\WindowsServiceAuditService.cs'
    $xaml=Join-Path $root 'src\MerzoOptimizer.App\MainWindow.xaml'
    $iss=Join-Path $root 'installer\MerzoWindowsOptimizer.iss'
    foreach($p in @($svc,$xaml,$iss)){if(!(Test-Path $p)){throw "R54.1 final source missing: $p"}}
    $s=Get-Content $svc -Raw
    $ui=Get-Content $xaml -Raw
    $i=Get-Content $iss -Raw

    foreach($token in @('SetServiceStartTypeViaScm(item.ServiceName, 4);','SetServiceStartTypeViaScm(state.ServiceName, state.StartValue);','ChangeServiceConfig(','OpenSCManager(','OpenService(','ServiceChangeConfig = 0x0002')){
        if(-not$s.Contains($token)){throw "R54.1 SCM contract missing: $token"}
    }
    foreach($bad in @('key.SetValue("Start", 4','key.SetValue("Start", state.StartValue')){
        if($s.Contains($bad)){throw "R54.1 direct service Start registry write remains: $bad"}
    }
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

- Исправлен следующий фактический откат GAME: Distributed Link Tracking Client мог вернуть `Requested registry access is not allowed`.
- Причина: применение и Undo меняли `HKLM\SYSTEM\CurrentControlSet\Services\<service>\Start` прямой записью реестра. Некоторые службы защищают этот ключ отдельным ACL даже для администратора.
- Изменение типа запуска и восстановление теперь выполняются через штатный Windows Service Control Manager (`ChangeServiceConfig`). Прямой writable-доступ к `Services\...\Start` из service execution path удалён.
- Snapshot/Undo, allow-list служб и запрет принудительного запуска восстановленной службы сохранены.
- R54 updater используется как первая проверка доставки четырёхчастного hotfix `0.1.54.1` без обрезания revision.
'@ | Add-Content $notes -Encoding UTF8
    Write-Host 'R54_1_SERVICE_CONTROL_ALL_GATES_PASS'
}
finally {
    Set-Content $base $original -Encoding UTF8
}
