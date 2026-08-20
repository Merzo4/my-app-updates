$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$controller='.\optimizer\scripts\r54_2_onedrive_game_reliability_release.ps1'
$deepBase='.\optimizer\scripts\r49_release.ps1'
if(!(Test-Path $controller)){throw 'R55 inherited R54.2 controller missing'}
if(!(Test-Path $deepBase)){throw 'R55 inherited R49 production base missing'}
$original=Get-Content $controller -Raw
$patched=$original
$deepOriginal=Get-Content $deepBase -Raw
$deepPatched=$deepOriginal

# R50+ controllers were designed as cumulative version wrappers and progressively
# rewrite the R49 version. R55 adds its finalizer before the inherited R49
# source/build gates, so the deep gate and Build-Production version must agree
# with the final R55 identity instead of stopping at the previous R54 value.
if(($deepPatched.Split('0.1.49').Count-1)-lt3){throw 'R55 deep R49 version anchors missing'}
$deepPatched=$deepPatched.Replace('0.1.49','0.1.55')

# Inject R55 immediately after the exact R54.2 finalizer in the inherited patch chain.
$chainNeedle="''r54_2_version_finalize.py'')"
$chainReplacement="''r54_2_version_finalize.py'',''r55_process_stability.py'',''r55_version_finalize.py'')"
if(($patched.Split($chainNeedle).Count-1)-ne1){throw 'R55 patch-chain anchor mismatch'}
$patched=$patched.Replace($chainNeedle,$chainReplacement)

# The inherited controller still contributes the exact R54.2 reliability patches,
# but build/version gates validate the new cumulative feature release.
$versionLine='$patched=$patched.Replace(''0.1.54.1'',''0.1.54.2'')'
$versionNew='$patched=$patched.Replace(''0.1.54.1'',''0.1.55'')'
if(($patched.Split($versionLine).Count-1)-ne1){throw 'R55 inherited build-version anchor mismatch'}
$patched=$patched.Replace($versionLine,$versionNew)

$releaseLine='$patched=$patched.Replace(''R54.1'',''R54.2'')'
$releaseNew='$patched=$patched.Replace(''R54.1'',''R55'')'
if(($patched.Split($releaseLine).Count-1)-ne1){throw 'R55 inherited release-label anchor mismatch'}
$patched=$patched.Replace($releaseLine,$releaseNew)

# Promote only validation/identity literals inside the controller; keep R54.2
# patch filenames and recovery markers intact as inherited evidence.
$patched=$patched.Replace('Production R54.2 · 0.1.54.2','Production R55 · 0.1.55')
$patched=$patched.Replace('Text=\"R54.2\"','Text=\"R55\"')
$patched=$patched.Replace('#define MyAppVersion \"0.1.54.2\"','#define MyAppVersion \"0.1.55\"')
$patched=$patched.Replace('AppVersion=0.1.54.2','AppVersion=0.1.55')
$patched=$patched.Replace("version-ne'0.1.54.2'","version-ne'0.1.55.0'")
$patched=$patched.Replace('R54.2 ONEDRIVE + GAME RELIABILITY','R55 PROCESS STABILITY')

try {
    Set-Content $deepBase $deepPatched -Encoding UTF8
    Set-Content $controller $patched -Encoding UTF8
    & $controller
    if($LASTEXITCODE -ne 0){throw "R55 inherited production controller failed: $LASTEXITCODE"}

    if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R55 SOURCE_ROOT missing'}
    $root=$env:SOURCE_ROOT
    foreach($rel in @('R55_PROCESS_STABILITY.marker','R55_VERSION_FINAL.marker','src\MerzoOptimizer.Core\Audit\ProcessStabilityModels.cs','src\MerzoOptimizer.Windows\Processes\WindowsProcessStabilityAnalyzer.cs')){
        if(!(Test-Path (Join-Path $root $rel))){throw "R55 output missing: $rel"}
    }
    $x=Get-Content (Join-Path $root 'src\MerzoOptimizer.App\MainWindow.xaml') -Raw
    $v=Get-Content (Join-Path $root 'src\MerzoOptimizer.App\ViewModels\MainWindowViewModel.cs') -Raw
    foreach($token in @('Production R55 · 0.1.55','R55 PROCESS STABILITY','Аудит 15 минут','ProcessStabilityRows')){
        if(-not(($x+"`n"+$v).Contains($token))){throw "R55 UI/VM contract missing: $token"}
    }
    $a=Get-Content (Join-Path $root 'src\MerzoOptimizer.Windows\Processes\WindowsProcessStabilityAnalyzer.cs') -Raw
    foreach($token in @('ProcessStabilityAuditOptions.Production','BuildSourceInventory','ReadScheduledTaskActions','ReadServiceImages','Не трогать','Драйвер / оставить','Необязательный')){
        if(-not$a.Contains($token)){throw "R55 analyzer contract missing: $token"}
    }

    $dist=Join-Path $root 'dist\app'
    foreach($n in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){
        $p=Join-Path $dist $n
        if(!(Test-Path $p)){throw "R55 missing $n"}
        $version=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString()
        if($version-ne'0.1.55.0'){throw "R55 $n version=$version"}
    }
    Write-Host 'R55_PROCESS_STABILITY_ALL_BUILD_GATES_PASS'
}
finally {
    Set-Content $controller $original -Encoding UTF8
    Set-Content $deepBase $deepOriginal -Encoding UTF8
}
