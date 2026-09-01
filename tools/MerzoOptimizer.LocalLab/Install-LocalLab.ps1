$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$root='D:\MerzoOptimizer-LocalLab'
if(!(Test-Path 'D:\')){throw 'Для Merzo Optimizer Local Test Center нужен диск D:. Лаборатория не устанавливается в Program Files или профиль пользователя.'}

$sourceToolDir=Split-Path $MyInvocation.MyCommand.Path -Parent
$required=@('MerzoOptimizer.LocalLab.ps1','Run-Profile.ps1','local-lab-profile.json','ENABLE-DESTRUCTIVE-LAB.ps1','PACK-EVIDENCE.ps1')
foreach($name in $required){if(!(Test-Path (Join-Path $sourceToolDir $name))){throw "Не хватает файла Test Center: $name"}}

$dirs=@(
  'App','Source','Toolchain\dotnet-home','Toolchain\nuget-packages','Toolchain\nuget-http-cache',
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

# Desktop shortcut. This points only to the Test Center launcher on D:.
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
Write-Host 'Production Program Files не изменялся.'
Write-Host 'Первый шаг: Диагностика -> Обновить Source -> QUICK.'
Start-Process (Join-Path $root 'START-TEST-CENTER.bat')
