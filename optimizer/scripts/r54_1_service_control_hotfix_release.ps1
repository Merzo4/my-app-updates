$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_r53_hotfix_bridge_release.ps1'
$original=Get-Content $base -Raw
$patched=$original

# Extend the exact already-green R54 patch chain by one patch only.
$oldChain="'r53_game_apply_hotfix.py','r53_version_finalize.py','r54_updater_bridge.py')"
$newChain="'r53_game_apply_hotfix.py','r53_version_finalize.py','r54_updater_bridge.py','r54_1_service_control_hotfix.py')"
if(($patched.Split($oldChain).Count-1)-ne1){throw 'R54.1 patch-chain anchor mismatch'}
$patched=$patched.Replace($oldChain,$newChain)

# R54.1 is the first four-part release delivered by the fixed R54 updater.
# Transform inherited R53.1 build/gate expectations to 0.1.54.1 instead of the
# R54 bridge's 0.1.54.0, while leaving three-part R54 bridge parser tests intact.
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

# V5 has a standalone navigation badge normalization after generic conversion.
$patched=$patched.Replace("`$patchedV5=`$patchedV5.Replace('Text=\"R53.1\"','Text=\"R54\"')",
                           "`$patchedV5=`$patchedV5.Replace('Text=\"R53.1\"','Text=\"R54.1\"')")

# Outer final gates must inspect the finished 54.1 source/artifact.
$patched=$patched.Replace("if(`$version-ne'0.1.54.0')","if(`$version-ne'0.1.54.1')")
$patched=$patched.Replace("if(-not`$ui.Contains('Production R54 · 0.1.54')){throw 'R54 visible version missing'}",
                           "if(-not`$ui.Contains('Production R54.1 · 0.1.54.1')){throw 'R54.1 visible version missing'}")
$patched=$patched.Replace("if(-not`$ui.Contains('Text=\"R54\"')){throw 'R54 navigation badge missing'}",
                           "if(-not`$ui.Contains('Text=\"R54.1\"')){throw 'R54.1 navigation badge missing'}")
$patched=$patched.Replace("if(-not`$i.Contains('#define MyAppVersion \"0.1.54\"') -and -not`$i.Contains('AppVersion=0.1.54')){throw 'R54 Inno public version missing'}",
                           "if(-not`$i.Contains('#define MyAppVersion \"0.1.54.1\"') -and -not`$i.Contains('AppVersion=0.1.54.1')){throw 'R54.1 Inno public version missing'}")

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
