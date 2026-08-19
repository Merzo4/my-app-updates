$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_1_service_control_hotfix_release.ps1'
$original=Get-Content $base -Raw
$patched=$original

$oldLiteral='$newChain="''r53_game_apply_hotfix.py'',''r53_version_finalize.py'',''r54_updater_bridge.py'',''r54_1_service_control_hotfix.py'')"'
$newLiteral='$newChain="''r53_game_apply_hotfix.py'',''r53_version_finalize.py'',''r54_updater_bridge.py'',''r54_1_service_control_hotfix.py'',''r54_1_service_selftest_contract.py'',''r54_2_onedrive_resilience.py'',''r54_2_version_finalize.py'')"'
if(($patched.Split($oldLiteral).Count-1)-ne1){throw 'R54.2 patch-chain anchor mismatch'}
$patched=$patched.Replace($oldLiteral,$newLiteral)

# Adapt only the outer R54.1 release controller identity. Patch filenames and
# R54_1 markers use underscores and remain unchanged.
$patched=$patched.Replace('0.1.54.1','0.1.54.2')
$patched=$patched.Replace('R54.1','R54.2')
$patched=$patched.Replace('R54_1_SERVICE_CONTROL_ALL_GATES_PASS','R54_2_INHERITED_SERVICE_GATES_PASS')

try {
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
    if($h -match 'process\.ExitCode\s*!=\s*0[\s\S]{0,120}throw'){throw 'R54.2 non-zero OneDriveSetup exit remains package-fatal'}
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
}
