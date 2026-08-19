$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_1_service_control_hotfix_release.ps1'
$original=Get-Content $base -Raw
$patched=$original
$onePatch='.\optimizer\patches\r54_2_onedrive_resilience.py'
$onePatchOriginal=Get-Content $onePatch -Raw
$onePatchPatched=$onePatchOriginal
$r53v1='.\optimizer\scripts\r53_release_v1.ps1'
$r53v1Original=Get-Content $r53v1 -Raw
$r53v1Patched=$r53v1Original
$r52v2='.\optimizer\scripts\r52_game_release_v2.ps1'
$r52v2Original=Get-Content $r52v2 -Raw
$r52v2Patched=$r52v2Original

$oldLiteral='$newChain="''r53_game_apply_hotfix.py'',''r53_version_finalize.py'',''r54_updater_bridge.py'',''r54_1_service_control_hotfix.py'')"'
$newLiteral='$newChain="''r53_game_apply_hotfix.py'',''r53_version_finalize.py'',''r54_updater_bridge.py'',''r54_1_service_control_hotfix.py'',''r54_1_service_selftest_contract.py'',''r54_2_onedrive_resilience.py'',''r54_2_version_finalize.py'')"'
if(($patched.Split($oldLiteral).Count-1)-ne1){throw 'R54.2 patch-chain anchor mismatch'}
$patched=$patched.Replace($oldLiteral,$newLiteral)

# The initial patch contained a gate that matched unrelated helper processes.
$legacyGate="    'if (process.ExitCode != 0)\n            throw',"
$scopedGate="    'OneDriveSetup /uninstall завершился с кодом',"
if(($onePatchPatched.Split($legacyGate).Count-1)-ne1){throw 'R54.2 OneDrive gate-scope anchor mismatch'}
$onePatchPatched=$onePatchPatched.Replace($legacyGate,$scopedGate)

# Deep R52 V2 source/security gate is generated before later R53/R54 wrappers.
# Change ONLY the suffix token in its exact gate list. Product title promotion
# still follows the normal R52 -> R53 -> R54.1 -> R54.2 chain.
$r52GateOld="'Production R52 · 0.1.52','SourceInitialized=\"OnMainWindowSourceInitialized\"','PreviewMouseWheel=\"OnGlobalPreviewMouseWheel\"','BuildAdvancedScroll','SidebarExpertExpander','OperationEventScroll','R52 GAME WOW + UI RELIABILITY'"
$r52GateNew="'Production R52 · 0.1.52','SourceInitialized=\"OnMainWindowSourceInitialized\"','PreviewMouseWheel=\"OnGlobalPreviewMouseWheel\"','BuildAdvancedScroll','SidebarExpertExpander','OperationEventScroll','R54.2 ONEDRIVE + GAME RELIABILITY'"
if(($r52v2Patched.Split($r52GateOld).Count-1)-ne1){throw 'R54.2 deep R52 suffix-gate anchor mismatch'}
$r52v2Patched=$r52v2Patched.Replace($r52GateOld,$r52GateNew)

# R53 outer source gate also carries the old suffix independently.
$gateOld="'Production R53.1 · 0.1.53.1','R53 HOTFIX 1','BuildAdvancedScroll','SidebarNavScroll'"
$gateNew="'Production R53.1 · 0.1.53.1','R54.2 ONEDRIVE + GAME RELIABILITY','BuildAdvancedScroll','SidebarNavScroll'"
if(($r53v1Patched.Split($gateOld).Count-1)-ne1){throw 'R54.2 inherited R53 suffix-gate anchor mismatch'}
$r53v1Patched=$r53v1Patched.Replace($gateOld,$gateNew)

# Adapt only the outer R54.1 controller identity.
$patched=$patched.Replace('0.1.54.1','0.1.54.2')
$patched=$patched.Replace('R54.1','R54.2')
$patched=$patched.Replace('R54_1_SERVICE_CONTROL_ALL_GATES_PASS','R54_2_INHERITED_SERVICE_GATES_PASS')

try {
    Set-Content $onePatch $onePatchPatched -Encoding UTF8
    Set-Content $r52v2 $r52v2Patched -Encoding UTF8
    Set-Content $r53v1 $r53v1Patched -Encoding UTF8
    Set-Content $base $patched -Encoding UTF8
    & $base
    if($LASTEXITCODE-ne0){throw "R54.2 inherited production gates failed: $LASTEXITCODE"}
    if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R54.2 SOURCE_ROOT missing'}
    $root=$env:SOURCE_ROOT

    $one=Join-Path $root 'src\MerzoOptimizer.Windows\OneDrive\WindowsOneDriveOptimizationService.cs'
    $helper=Join-Path $root 'src\MerzoOptimizer.ElevatedHelper\Program.cs'
    $vm=Join-Path $root 'src\MerzoOptimizer.App\ViewModels\MainWindowViewModel.cs'
    $ui=Join-Path $root 'src\MerzoOptimizer.App\MainWindow.xaml'
    $iss=Join-Path $root 'installer\MerzoWindowsOptimizer.iss'
    foreach($p in @($one,$helper,$vm,$ui,$iss)){if(!(Test-Path $p)){throw "R54.2 final source missing: $p"}}
    $o=Get-Content $one -Raw
    $h=Get-Content $helper -Raw
    $v=Get-Content $vm -Raw
    $x=Get-Content $ui -Raw
    $i=Get-Content $iss -Raw

    if($o.Contains('KnownInstallPaths().Any(File.Exists)')){throw 'R54.2 stale OneDriveSetup install detection remains'}
    if(-not$o.Contains('KnownClientPaths().Any(File.Exists)')){throw 'R54.2 client-only OneDrive detection missing'}
    if($h.Contains('OneDriveSetup /uninstall завершился с кодом')){throw 'R54.2 legacy OneDriveSetup fatal-exit message remains'}
    foreach($token in @('setup leftovers ignored','OneDrive оставлен; пакет продолжен','OneDrive не удалён; необязательный шаг пропущен, пакет продолжен.','OneDrive не настроен')){
        if(-not(($o+"`n"+$h+"`n"+$v).Contains($token))){throw "R54.2 OneDrive contract missing: $token"}
    }
    if(-not$x.Contains('Production R54.2 · 0.1.54.2') -or -not$x.Contains('Text="R54.2"')){throw 'R54.2 visible identity missing'}
    if(-not$i.Contains('#define MyAppVersion "0.1.54.2"') -and -not$i.Contains('AppVersion=0.1.54.2')){throw 'R54.2 installer identity missing'}
    if(!(Test-Path (Join-Path $root 'R54_2_ONEDRIVE_RESILIENCE.marker'))){throw 'R54.2 OneDrive marker missing'}
    if(!(Test-Path (Join-Path $root 'R54_2_VERSION_FINAL.marker'))){throw 'R54.2 version marker missing'}

    $dist=Join-Path $root 'dist\app'
    foreach($n in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){
        $p=Join-Path $dist $n
        if(!(Test-Path $p)){throw "R54.2 missing $n"}
        $version=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString()
        if($version-ne'0.1.54.2'){throw "R54.2 $n version=$version"}
    }

    Write-Host 'R54_2_ONEDRIVE_GAME_RELIABILITY_ALL_GATES_PASS'
}
finally {
    Set-Content $base $original -Encoding UTF8
    Set-Content $onePatch $onePatchOriginal -Encoding UTF8
    Set-Content $r52v2 $r52v2Original -Encoding UTF8
    Set-Content $r53v1 $r53v1Original -Encoding UTF8
}
