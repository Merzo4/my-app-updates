$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$root='D:\MerzoOptimizer-LocalLab'
if(!(Test-Path 'D:\')){throw 'Для Merzo Optimizer Local Test Center нужен диск D:. Лаборатория не устанавливается в Program Files или профиль пользователя.'}

$sourceToolDir=Split-Path $MyInvocation.MyCommand.Path -Parent
$required=@('MerzoOptimizer.LocalLab.ps1','Run-Profile.ps1','Run-Profile.Core.ps1','local-lab-profile.json','ENABLE-DESTRUCTIVE-LAB.ps1','PACK-EVIDENCE.ps1','PUBLISH-EVIDENCE.ps1')
foreach($name in $required){if(!(Test-Path (Join-Path $sourceToolDir $name))){throw "Не хватает файла Test Center: $name"}}

# Local parser/self-contract gate. This replaces a GitHub parser workflow and costs 0 Actions minutes.
foreach($name in $required|Where-Object{$_-like'*.ps1'}){
  $tokens=$null;$errors=$null
  [System.Management.Automation.Language.Parser]::ParseFile((Join-Path $sourceToolDir $name),[ref]$tokens,[ref]$errors)|Out-Null
  if($errors.Count-gt0){
    $detail=($errors|ForEach-Object{"$($_.Extent.StartLineNumber): $($_.Message)"})-join'; '
    throw "TEST CENTER PARSER FAIL $name :: $detail"
  }
}
try{$profile=Get-Content (Join-Path $sourceToolDir 'local-lab-profile.json') -Raw|ConvertFrom-Json}catch{throw "TEST CENTER PROFILE JSON FAIL :: $($_.Exception.Message)"}
if([int]$profile.schemaVersion-ne1){throw "Unsupported Local Lab profile schema: $($profile.schemaVersion)"}
if([string]::IsNullOrWhiteSpace([string]$profile.targetBranch)-or[string]::IsNullOrWhiteSpace([string]$profile.buildController)){throw 'Local Lab profile is incomplete.'}
Write-Host 'LOCAL_TEST_CENTER_LOCAL_PARSER_GATE_PASS' -ForegroundColor Green

$dirs=@(
  'App','Source','EvidenceRepo','Toolchain\dotnet-home','Toolchain\nuget-packages','Toolchain\nuget-http-cache',
  'Sandbox\Current','TestBuild\Quick','TestBuild\Current','Results\Latest','Logs','State',
  'Temp\Run\Current','Temp\BundleExtract'
)
foreach($rel in $dirs){New-Item (Join-Path $root $rel) -ItemType Directory -Force|Out-Null}

$app=Join-Path $root 'App'
foreach($name in $required){Copy-Item (Join-Path $sourceToolDir $name) (Join-Path $app $name) -Force}
if(Test-Path (Join-Path $sourceToolDir 'README.md')){Copy-Item (Join-Path $sourceToolDir 'README.md') (Join-Path $app 'README.md') -Force}

$launcher=@'
@echo off
setlocal
set "MWO_LAB_ROOT=D:\MerzoOptimizer-LocalLab"
pwsh.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "D:\MerzoOptimizer-LocalLab\App\MerzoOptimizer.LocalLab.ps1"
if errorlevel 1 pause
'@
Set-Content (Join-Path $root 'START-TEST-CENTER.bat') $launcher -Encoding ASCII

$evidenceLauncher=@'
@echo off
setlocal
set "MWO_LAB_ROOT=D:\MerzoOptimizer-LocalLab"
pwsh.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "D:\MerzoOptimizer-LocalLab\App\PACK-EVIDENCE.ps1"
if errorlevel 1 pause
'@
Set-Content (Join-Path $root 'PACK-EVIDENCE.bat') $evidenceLauncher -Encoding ASCII

$publishLauncher=@'
@echo off
setlocal
set "MWO_LAB_ROOT=D:\MerzoOptimizer-LocalLab"
pwsh.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "D:\MerzoOptimizer-LocalLab\App\PUBLISH-EVIDENCE.ps1"
if errorlevel 1 pause
'@
Set-Content (Join-Path $root 'PUBLISH-EVIDENCE.bat') $publishLauncher -Encoding ASCII

$updateLauncher=@'
@echo off
setlocal EnableExtensions
set "URL=https://raw.githubusercontent.com/Merzo4/my-app-updates/mwo-local-test-center/INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat"
set "TMP=%TEMP%\INSTALL-MERZO-OPTIMIZER-TEST-CENTER.bat"
curl.exe -fL --retry 3 "%URL%" -o "%TMP%" || (pause & exit /b 1)
call "%TMP%"
'@
Set-Content (Join-Path $root 'UPDATE-TEST-CENTER.bat') $updateLauncher -Encoding ASCII

try{
  $desktop=[Environment]::GetFolderPath('Desktop')
  $shell=New-Object -ComObject WScript.Shell
  $shortcut=$shell.CreateShortcut((Join-Path $desktop 'Merzo Optimizer Test Center.lnk'))
  $shortcut.TargetPath=(Join-Path $root 'START-TEST-CENTER.bat')
  $shortcut.WorkingDirectory=$root
  $shortcut.Description='Merzo Optimizer Local Test Center — local verification without GitHub Actions minutes'
  $shortcut.Save()
}catch{}

Write-Host ''
Write-Host 'MERZO OPTIMIZER LOCAL TEST CENTER INSTALLED' -ForegroundColor Green
Write-Host "Root: $root"
Write-Host "Test Center: $($profile.testCenterVersion) | Product profile: $($profile.productVersion)"
Write-Host 'Production Program Files не изменялся.'
Write-Host 'Первый шаг: Диагностика -> Обновить Source -> QUICK.'
Write-Host 'Evidence автоматически пытается уйти в mwo-local-lab-evidence. Actions minutes = 0.'
Start-Process (Join-Path $root 'START-TEST-CENTER.bat')
