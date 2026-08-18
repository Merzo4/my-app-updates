$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r53_release_v1.ps1'
$original=Get-Content $base -Raw
$old=@'
$new="'r52_window_scroll_reliability.py','r52_game_wow_debloat_v3.py','r53_process_start_debloat.py')"
'@.Trim()
$new=@'
$new="'r52_window_scroll_reliability.py','r52_game_wow_debloat_v3.py','r53_process_start_debloat.py','r53_product_install_branding.py','r53_version_finalize.py')"
'@.Trim()
if(($original.Split($old).Count-1)-ne1){throw 'R53 V5 patch-chain anchor mismatch'}
$patched=$original.Replace($old,$new)
try {
    Set-Content $base $patched -Encoding UTF8
    & '.\optimizer\scripts\r53_release_v4.ps1'
    if($LASTEXITCODE-ne0){throw "R53 V5 failed: $LASTEXITCODE"}
    if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R53 V5 SOURCE_ROOT missing'}

    # Product-grade installation + screenshot compatibility gates.
    $root=$env:SOURCE_ROOT
    $iss=Join-Path $root 'installer\MerzoWindowsOptimizer.iss'
    $manifest=Join-Path $root 'src\MerzoOptimizer.App\app.manifest'
    $appProj=Join-Path $root 'src\MerzoOptimizer.App\MerzoOptimizer.App.csproj'
    $vm=Join-Path $root 'src\MerzoOptimizer.App\ViewModels\MainWindowViewModel.cs'
    if(!(Test-Path $iss)){throw 'R53 branded installer source missing'}
    if(!(Test-Path $manifest)){throw 'R53 asInvoker manifest missing'}
    if(!(Test-Path (Join-Path $root 'R53_PRODUCT_INSTALL_BRANDING.marker'))){throw 'R53 product branding marker missing'}
    $i=Get-Content $iss -Raw
    $m=Get-Content $manifest -Raw
    $p=Get-Content $appProj -Raw
    $v=Get-Content $vm -Raw
    foreach($token in @('DefaultDirName={autopf}\Merzo Windows Optimizer','PrivilegesRequired=admin','UsePreviousAppDir=no','WizardStyle=modern','R53 MERZO PRODUCT INSTALLER THEME','MERZO UPDATE · БЕЗОПАСНО ОБНОВЛЯЕМ ФАЙЛЫ')){if(-not$i.Contains($token)){throw "R53 installer contract missing: $token"}}
    if(-not$m.Contains('requestedExecutionLevel level="asInvoker" uiAccess="false"')){throw 'R53 main shell is not asInvoker'}
    if($m.Contains('requireAdministrator')){throw 'R53 main shell accidentally requires administrator'}
    if(-not$p.Contains('<ApplicationManifest>app.manifest</ApplicationManifest>')){throw 'R53 app project manifest link missing'}
    foreach($token in @('/MERZOUPDATE=1','unins000.exe','Merzo Windows Optimizer", "MerzoWindowsOptimizer.exe')){if(-not$v.Contains($token)){throw "R53 OTA migration contract missing: $token"}}
    foreach($bad in @('RegisterHotKey(','SetWindowsHookEx','WH_KEYBOARD_LL','VK_SNAPSHOT','Key.PrintScreen')){if((Get-ChildItem (Join-Path $root 'src\MerzoOptimizer.App') -Recurse -Filter *.cs|Where-Object{$_.FullName-notmatch'\\(bin|obj)\\'}|ForEach-Object{Get-Content $_.FullName -Raw}) -match [regex]::Escape($bad)){throw "R53 screenshot hotkey regression: $bad"}}
    Write-Host 'R53_PROGRAMFILES_SCREENSHOT_BRANDING_PASS'
} finally {
    Set-Content $base $original -Encoding UTF8
}
Write-Host 'R53_V5_COMPLETE_PASS'
