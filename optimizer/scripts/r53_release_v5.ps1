$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r53_release_v1.ps1'
$original=Get-Content $base -Raw
$old=@'
$new="'r52_window_scroll_reliability.py','r52_game_wow_debloat_v3.py','r53_process_start_debloat.py')"
'@.Trim()
$new=@'
$new="'r52_window_scroll_reliability.py','r52_game_wow_debloat_v3.py','r53_process_start_debloat.py','r53_catalog_probe.py','r53_game_compat_guard.py','r53_ascii_targets.py','r53_product_install_branding.py','r53_version_finalize.py')"
'@.Trim()
if(($original.Split($old).Count-1)-ne1){throw 'R53 V5 patch-chain anchor mismatch'}
$patched=$original.Replace($old,$new)
# Avoid Unicode dash corruption in nested generated PowerShell/UTF-8 script layers.
$patched=$patched.Replace('80–100','80-100').Replace('60–80','60-80').Replace('90–120','90-120')
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
    if(!(Test-Path (Join-Path $root 'R53_GAME_COMPAT_GUARD.marker'))){throw 'R53 GAME compatibility marker missing'}
    if(!(Test-Path (Join-Path $root 'R53_ASCII_TARGETS.marker'))){throw 'R53 ASCII target marker missing'}
    $i=Get-Content $iss -Raw
    $m=Get-Content $manifest -Raw
    $p=Get-Content $appProj -Raw
    $v=Get-Content $vm -Raw
    foreach($token in @('DefaultDirName={autopf}\Merzo Windows Optimizer','PrivilegesRequired=admin','UsePreviousAppDir=no','WizardStyle=modern','R53 MERZO PRODUCT INSTALLER THEME','MERZO UPDATE · БЕЗОПАСНО ОБНОВЛЯЕМ ФАЙЛЫ')){if(-not$i.Contains($token)){throw "R53 installer contract missing: $token"}}
    if(-not$m.Contains('requestedExecutionLevel level="asInvoker" uiAccess="false"')){throw 'R53 main shell is not asInvoker'}
    if($m.Contains('requireAdministrator')){throw 'R53 main shell accidentally requires administrator'}
    if(-not$p.Contains('<ApplicationManifest>app.manifest</ApplicationManifest>')){throw 'R53 app project manifest link missing'}
    foreach($token in @('/SILENT','/MERZOUPDATE=1','unins000.exe','Merzo Windows Optimizer", "MerzoWindowsOptimizer.exe')){if(-not$v.Contains($token)){throw "R53 OTA migration contract missing: $token"}}
    if($v.Contains('/VERYSILENT')){throw 'R53 OTA must show branded progress; VERYSILENT is forbidden'}
    foreach($token in @('80-100','60-80')){if(-not$v.Contains($token)){throw "R53 process target missing: $token"}}
    foreach($badTarget in @('80–100','60–80')){if($v.Contains($badTarget)){throw "R53 Unicode target regression: $badTarget"}}
    $appSources=(Get-ChildItem (Join-Path $root 'src\MerzoOptimizer.App') -Recurse -Filter *.cs|Where-Object{$_.FullName-notmatch'\\(bin|obj)\\'}|ForEach-Object{Get-Content $_.FullName -Raw}) -join "`n"
    foreach($bad in @('RegisterHotKey(','SetWindowsHookEx','WH_KEYBOARD_LL','VK_SNAPSHOT','Key.PrintScreen')){if($appSources.Contains($bad)){throw "R53 screenshot hotkey regression: $bad"}}

    # GAME should remain compatible with Xbox/Game Bar; optional removal belongs to EXTREME only.
    $debloat=Get-Content (Join-Path $root 'src\MerzoOptimizer.Windows\Gaming\WindowsGamingDebloatService.cs') -Raw
    $gameBlock=[regex]::Match($debloat,'private static readonly string\[\] GameTargets\s*=\s*\[(.*?)\n\s*\];',[System.Text.RegularExpressions.RegexOptions]::Singleline).Groups[1].Value
    $extremeBlock=[regex]::Match($debloat,'private static readonly string\[\] ExtremeTargets\s*=\s*\[(.*?)\n\s*\];',[System.Text.RegularExpressions.RegexOptions]::Singleline).Groups[1].Value
    foreach($xbox in @('Microsoft.XboxGamingOverlay','Microsoft.XboxGameOverlay','Microsoft.XboxSpeechToTextOverlay','Microsoft.XboxIdentityProvider')){
        if($gameBlock.Contains($xbox)){throw "R53 GAME compatibility regression: $xbox"}
        if(-not$extremeBlock.Contains($xbox)){throw "R53 EXTREME conditional target missing: $xbox"}
    }

    # Release notes shipped with the verified artifact must describe the real product changes.
    $notes=Join-Path $root 'dist\R53_RELEASE_NOTES.md'
    if(!(Test-Path $notes)){throw 'R53 release notes missing'}
    $noteText=Get-Content $notes -Raw
    $noteText=$noteText.Replace(
      '- Xbox/Game Bar части удаляются только если Xbox app/Game Pass не обнаружены. При установленном Xbox/Game Pass его стек сохраняется.',
      '- GAME сохраняет Xbox/Game Bar/Identity-компоненты ради совместимости с играми. Их условное удаление доступно только в EXTREME и только при отсутствии Xbox/Game Pass.')
    Set-Content $notes $noteText -Encoding UTF8
    @'

## PRODUCT INSTALL / UPDATE EXPERIENCE

- Установка теперь идёт как у обычной Windows-программы: `C:\Program Files\Merzo Windows Optimizer`. Старые Inno-установки из нестандартного каталога мигрируют при OTA-обновлении, а после установки запускается новый EXE из Program Files.
- Главное окно Merzo Windows Optimizer закреплено как `asInvoker`; UAC используется только отдельным ElevatedHelper. Это сохраняет нормальную работу Print Screen / Snipping Tool даже когда окно программы активно.
- Инсталлятор получил фирменный тёмный Merzo-дизайн. Тот же стиль используется в видимом окне обновления/замены файлов с отдельным режимом `MERZO UPDATE`.
- GAME сохраняет Xbox/Game Bar/Identity-компоненты ради совместимости с играми; их условное удаление допускается только в EXTREME при отсутствии Xbox/Game Pass.
'@ | Add-Content $notes -Encoding UTF8

    foreach($token in @('Program Files','Print Screen','Snipping Tool','MERZO UPDATE','Xbox/Game Bar')){if(-not((Get-Content $notes -Raw).Contains($token))){throw "R53 release notes contract missing: $token"}}
    Write-Host 'R53_PROGRAMFILES_SCREENSHOT_BRANDING_PASS'
} finally {
    Set-Content $base $original -Encoding UTF8
}
Write-Host 'R53_V5_COMPLETE_PASS'
