$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12

$root='D:\MerzoOptimizer-LocalLab'
if(!(Test-Path 'D:\')){throw 'Для Merzo Optimizer Local Test Center нужен диск D:. Лаборатория не устанавливается в Program Files или профиль пользователя.'}
# Defensive isolation: an older UPDATE-TEST-CENTER.bat set system TMP to a .bat FILE.
# PowerShell/.NET/MSBuild require TMP and TEMP to point to an existing DIRECTORY.
# Set process-scoped paths before parsing source or invoking any child process.
$labTemp=Join-Path $root 'Temp\ToolchainTemp'
New-Item -Path $labTemp -ItemType Directory -Force|Out-Null
if(!(Test-Path -LiteralPath $labTemp -PathType Container)){throw "Not a directory: $labTemp"}
$env:TEMP=$labTemp
$env:TMP=$labTemp
Write-Host "LAB_TEMP_READY: $labTemp" -ForegroundColor Green

function Resolve-PwshPath {
  $cmd=Get-Command pwsh.exe -ErrorAction SilentlyContinue
  if($cmd){return $cmd.Source}
  foreach($p in @('C:\Program Files\PowerShell\7\pwsh.exe','C:\Program Files\PowerShell\7-preview\pwsh.exe')){if(Test-Path $p){return $p}}
  return $null
}
function Ensure-PowerShell7 {
  $existing=Resolve-PwshPath
  if($existing){Write-Host "PowerShell 7 найден: $existing" -ForegroundColor Green;return $existing}
  throw 'PowerShell 7 отсутствует. Сначала должен успешно отработать Bootstrap-PowerShell7.ps1.'
}

$sourceToolDir=Split-Path $MyInvocation.MyCommand.Path -Parent
$nativeBuilder=Join-Path $sourceToolDir 'Build-NativeHost.ps1'
foreach($nativeFile in @($nativeBuilder,(Join-Path $sourceToolDir 'NativeHost\MerzoOptimizer.TestCenter.csproj'),(Join-Path $sourceToolDir 'NativeHost\Program.cs'))){
  if(!(Test-Path -LiteralPath $nativeFile)){throw "Missing native Test Center source: $nativeFile"}
}
$required=@('Start-TestCenter.ps1','MerzoOptimizer.LocalLab.ps1','Run-Profile.ps1','Run-Profile.Core.ps1','AUTO-REPORT.ps1','local-lab-profile.json','ENABLE-DESTRUCTIVE-LAB.ps1','PACK-EVIDENCE.ps1','PUBLISH-EVIDENCE.ps1')
foreach($name in $required){if(!(Test-Path (Join-Path $sourceToolDir $name))){throw "Не хватает файла Test Center: $name"}}
foreach($name in $required|Where-Object{$_-like'*.ps1'}){
  $tokens=$null;$errors=$null
  [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $sourceToolDir $name),[ref]$tokens,[ref]$errors)|Out-Null
  if($errors.Count-gt0){$detail=($errors|ForEach-Object{"$($_.Extent.StartLineNumber): $($_.Message)"})-join'; ';throw "TEST CENTER PARSER FAIL $name :: $detail"}
}
try{$profile=Get-Content (Join-Path $sourceToolDir 'local-lab-profile.json') -Raw|ConvertFrom-Json}catch{throw "TEST CENTER PROFILE JSON FAIL :: $($_.Exception.Message)"}
if([int]$profile.schemaVersion-ne1){throw "Unsupported Local Lab profile schema: $($profile.schemaVersion)"}
if([string]::IsNullOrWhiteSpace([string]$profile.targetBranch)-or[string]::IsNullOrWhiteSpace([string]$profile.buildController)){throw 'Local Lab profile is incomplete.'}
Write-Host 'LOCAL_TEST_CENTER_LOCAL_PARSER_GATE_PASS' -ForegroundColor Green

$pwshPath=Ensure-PowerShell7
$dirs=@('App','Source','EvidenceRepo','Toolchain\dotnet-home','Toolchain\nuget-packages','Toolchain\nuget-http-cache','Sandbox\Current','TestBuild\Quick','TestBuild\Current','Results\Latest','Logs','State\EvidenceQueue','Temp\Run\Current','Temp\BundleExtract')
foreach($rel in $dirs){New-Item (Join-Path $root $rel) -ItemType Directory -Force|Out-Null}

$app=Join-Path $root 'App'
foreach($name in $required){Copy-Item (Join-Path $sourceToolDir $name) (Join-Path $app $name) -Force}
if(Test-Path (Join-Path $sourceToolDir 'README.md')){Copy-Item (Join-Path $sourceToolDir 'README.md') (Join-Path $app 'README.md') -Force}

# Runtime GUI smoke gate on the real local Windows before shortcut creation.
$smokeLog=Join-Path $root 'Logs\\gui-smoke.log'
Remove-Item $smokeLog -Force -ErrorAction SilentlyContinue
$smokeArgs=@('-NoLogo','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',(Join-Path $app 'MerzoOptimizer.LocalLab.ps1'),'-SmokeTest')
$smokeOut=& $pwshPath @smokeArgs 2>&1
$smokeCode=$LASTEXITCODE
$smokeOut|Set-Content $smokeLog -Encoding UTF8
$smokeText=($smokeOut|Out-String)
if($smokeCode-ne0-or$smokeText-notmatch'LOCAL_TEST_CENTER_GUI_SMOKE_TEST_PASS'){
  throw "LOCAL TEST CENTER GUI SMOKE FAIL. Код=$smokeCode. Лог: $smokeLog"
}
Write-Host 'LOCAL_TEST_CENTER_GUI_SMOKE_TEST_PASS' -ForegroundColor Green
# Build and smoke the native GUI before replacing the desktop shortcut.
& $pwshPath -NoLogo -NoProfile -ExecutionPolicy Bypass -File $nativeBuilder -LabRoot $root
if($LASTEXITCODE-ne0){throw "Native EXE build/smoke FAIL; see Logs\native-build.log"}
$nativeExe=Join-Path $root 'App\Native\MerzoOptimizer.TestCenter.exe'
if(!(Test-Path $nativeExe)){throw "Native EXE not installed: $nativeExe"}
Write-Host 'NATIVE EXE READY' -ForegroundColor Green

# WinForms-first launcher: wscript starts pwsh normally. The host console is hidden ONLY after GUI Shown.
$vbsPath=Join-Path $app 'Launch-TestCenter.vbs'
$startScript=Join-Path $app 'Start-TestCenter.ps1'
$vbs=@"
Set sh = CreateObject("WScript.Shell")
cmd = Chr(34) & "$pwshPath" & Chr(34) & " -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File " & Chr(34) & "$startScript" & Chr(34) & " -ManagedShortcut"
' Window style 1 makes the WinForms UI visible; the GUI hides its console only after Shown.
sh.Run cmd, 1, False
"@
Set-Content $vbsPath $vbs -Encoding ASCII
# Rollback path for pre-native PowerShell WinForms GUI.
$legacy=@"
@echo off
start "" wscript.exe "$vbsPath"
exit /b 0
"@
Set-Content (Join-Path $root 'START-TEST-CENTER-LEGACY.bat') $legacy -Encoding ASCII

$launcher=@"
@echo off
start "" "$nativeExe"
exit /b 0
"@
Set-Content (Join-Path $root 'START-TEST-CENTER.bat') $launcher -Encoding ASCII

$evidenceLauncher=@"
@echo off
setlocal
set "MWO_LAB_ROOT=D:\MerzoOptimizer-LocalLab"
"$pwshPath" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "D:\MerzoOptimizer-LocalLab\App\PACK-EVIDENCE.ps1"
if errorlevel 1 pause
"@
Set-Content (Join-Path $root 'PACK-EVIDENCE.bat') $evidenceLauncher -Encoding ASCII

$publishLauncher=@"
@echo off
setlocal
set "MWO_LAB_ROOT=D:\MerzoOptimizer-LocalLab"
"$pwshPath" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "D:\MerzoOptimizer-LocalLab\App\PUBLISH-EVIDENCE.ps1" -FlushQueue
if errorlevel 1 pause
"@
Set-Content (Join-Path $root 'PUBLISH-EVIDENCE.bat') $publishLauncher -Encoding ASCII

$updateLauncher=@'
@echo off
setlocal EnableExtensions
set "URL=https://raw.githubusercontent.com/Merzo4/my-app-updates/mwo-local-test-center/INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat"
set "MWO_UPDATE_DOWNLOAD=%TEMP%\INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat"
curl.exe -fL --retry 3 "%URL%" -o "%MWO_UPDATE_DOWNLOAD%" || (pause & exit /b 1)
call "%MWO_UPDATE_DOWNLOAD%"
'@
Set-Content (Join-Path $root 'UPDATE-TEST-CENTER.bat') $updateLauncher -Encoding ASCII

$desktop=[Environment]::GetFolderPath('Desktop')
$shortcutPath=Join-Path $desktop 'Merzo Optimizer Test Center.lnk'
try{
  if(Test-Path $shortcutPath){Remove-Item $shortcutPath -Force}
  $shell=New-Object -ComObject WScript.Shell
  $shortcut=$shell.CreateShortcut($shortcutPath)
  $shortcut.TargetPath=$nativeExe
  $shortcut.Arguments=''
  $shortcut.WorkingDirectory=$app
  $shortcut.Description='Merzo Optimizer Local Test Center — локальная проверка без GitHub Actions минут'
  $productExe='C:\Program Files\Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'
  $shortcut.IconLocation="$nativeExe,0"
  $shortcut.Save()
}catch{throw "Не удалось создать ярлык: $($_.Exception.Message)"}

Write-Host ''
Write-Host 'MERZO OPTIMIZER LOCAL TEST CENTER INSTALLED' -ForegroundColor Green
Write-Host "Root: $root"
Write-Host "Test Center: $($profile.testCenterVersion) | Product profile: $($profile.productVersion)"
Write-Host "PowerShell: $pwshPath"
Write-Host 'Parser gate: PASS'
Write-Host 'GUI smoke gate: PASS'
Write-Host "Launcher: NATIVE EXE $nativeExe — no PowerShell UI host console."
Write-Host 'Backup: START-TEST-CENTER-LEGACY.bat (PowerShell WinForms UI)'
Write-Host 'Auto-report: queued + mwo-local-lab-evidence, Actions minutes = 0.'
$showMarker=Join-Path $root 'State\native-gui-shown.json'
Remove-Item -LiteralPath $showMarker -Force -ErrorAction SilentlyContinue
Start-Process -FilePath $nativeExe
$observed=$false
foreach($attempt in 1..20){
  Start-Sleep -Seconds 1
  if(Test-Path -LiteralPath $showMarker){$observed=$true;break}
}
if(-not $observed){
  throw 'Native WinForms EXE did not show within 20 seconds. Close previous Test Center instance and inspect Logs\native-gui-error.log. Legacy launcher preserved.'
}
Write-Host 'NATIVE_TEST_CENTER_GUI_SHOWN_MARKER_OBSERVED' -ForegroundColor Green
