@echo off
setlocal EnableExtensions
rem Scoped environment repair: old installed updater sets TMP equal to the downloaded BAT file.
rem This BAT must make TEMP/TMP actual directories BEFORE PowerShell/.NET/MSBuild.
if not exist "D:\" (
  echo ERROR: Test Center requires drive D:.
  pause
  exit /b 2
)
set "MWO_LAB_TEMP=D:\MerzoOptimizer-LocalLab\Temp\ToolchainTemp"
if not exist "%MWO_LAB_TEMP%" mkdir "%MWO_LAB_TEMP%"
if not exist "%MWO_LAB_TEMP%\." (
  echo ERROR: Cannot create a safe MSBuild temporary folder on D:.
  pause
  exit /b 3
)
set "TEMP=%MWO_LAB_TEMP%"
set "TMP=%MWO_LAB_TEMP%"
echo TEMP/TMP verified as directory: %MWO_LAB_TEMP%
set "BASE=https://raw.githubusercontent.com/Merzo4/my-app-updates/mwo-local-test-center/tools/MerzoOptimizer.LocalLab"
set "TMPDIR=D:\MerzoOptimizer-LocalLab\Temp\BootstrapSource"
if exist "%TMPDIR%" rmdir /s /q "%TMPDIR%"
mkdir "%TMPDIR%" || exit /b 1

where curl.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: curl.exe was not found.
  pause
  exit /b 1
)
where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: Windows PowerShell was not found.
  pause
  exit /b 1
)

for %%F in (Build-NativeHost.ps1 Bootstrap-PowerShell7.ps1 Start-TestCenter.ps1 MerzoOptimizer.LocalLab.ps1 Run-Profile.ps1 Run-Profile.Core.ps1 AUTO-REPORT.ps1 local-lab-profile.json ENABLE-DESTRUCTIVE-LAB.ps1 PACK-EVIDENCE.ps1 PUBLISH-EVIDENCE.ps1 Install-LocalLab.ps1 README.md) do (
  echo Downloading %%F...
  curl.exe -fsSL --retry 3 --connect-timeout 15 "%BASE%/%%F" -o "%TMPDIR%\%%F"
  if errorlevel 1 (
    echo ERROR: failed to download %%F
    pause
    exit /b 1
  )
)

echo.
if not exist "%TMPDIR%\NativeHost" mkdir "%TMPDIR%\NativeHost"
for %%F in (MerzoOptimizer.TestCenter.csproj Program.cs) do (
  echo Downloading NativeHost/%%F...
  curl.exe -fsSL --retry 3 --connect-timeout 15 "%BASE%/NativeHost/%%F" -o "%TMPDIR%\NativeHost\%%F"
  if errorlevel 1 (echo ERROR: NativeHost/%%F missing & pause & exit /b 1)
)
echo.
echo Preparing stable PowerShell 7...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TMPDIR%\Bootstrap-PowerShell7.ps1"
if errorlevel 1 (
  echo ERROR: stable PowerShell 7 bootstrap failed.
  pause
  exit /b 1
)

set "PWSH=C:\Program Files\PowerShell\7\pwsh.exe"
if not exist "%PWSH%" (
  echo ERROR: stable pwsh.exe was not found in Program Files after bootstrap.
  pause
  exit /b 1
)
set "PATH=C:\Program Files\PowerShell\7;%PATH%"

echo.
echo Installing Merzo Optimizer Local Test Center 0.2.2 NATIVE EXE / R57 profile ...
"%PWSH%" -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%TMPDIR%\Install-LocalLab.ps1"
if errorlevel 1 (
  echo ERROR: Local Test Center installation failed.
  echo Check D:\MerzoOptimizer-LocalLab\Logs\native-build.log or native-smoke.log.
  pause
  exit /b 1
)

echo.
echo DONE. Parser and GUI smoke gates passed.
echo Native EXE GUI and automatic evidence queue are enabled.
echo PowerShell remains the hidden backend only while tests execute.
echo GitHub Actions workflows were not started.
exit /b 0
