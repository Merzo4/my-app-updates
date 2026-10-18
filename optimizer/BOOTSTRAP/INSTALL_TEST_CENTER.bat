@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Merzo Optimizer - Install Local Test Center 0.2.6
rem Official pinned source: Merzo4/my-app-updates, commit 95c735c54ced62605e9c02cd98569b0b4d023665
rem Test Center is independent of the stable Optimizer and requires drive D:.
echo ===================================================
echo  MERZO OPTIMIZER - LOCAL TEST CENTER 0.2.6
echo ===================================================
echo Source: GitHub / pinned commit 95c735c54ced62605e9c02cd98569b0b4d023665
echo Install location: D:\MerzoOptimizer-LocalLab
echo Existing installed production Optimizer is not replaced.
echo.
if not exist "D:\" (
  echo ERROR: D: drive is required for the current Test Center 0.2.6.
  echo No disk or partition will be created automatically.
  pause
  exit /b 2
)
where curl.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: curl.exe is required.
  pause
  exit /b 3
)
where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo ERROR: Windows PowerShell is required.
  pause
  exit /b 4
)
echo.
echo Important: finish any ongoing Test Center checks before restarting the GUI.
choice /M "Close ONLY old Test Center GUI processes and continue to update 0.2.6"
if errorlevel 2 (
  echo Cancelled by user. No Test Center processes stopped.
  pause
  exit /b 0
)
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$prefix='D:\MerzoOptimizer-LocalLab\App\'; $matches=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pwsh.exe' -and $_.CommandLine -and ($_.CommandLine.IndexOf($prefix+'Start-TestCenter.ps1',[StringComparison]::OrdinalIgnoreCase) -ge 0 -or $_.CommandLine.IndexOf($prefix+'MerzoOptimizer.LocalLab.ps1',[StringComparison]::OrdinalIgnoreCase) -ge 0) }); foreach($p in $matches){Write-Host ('Stopping Test Center GUI PID '+$p.ProcessId); Stop-Process -Id $p.ProcessId -ErrorAction Stop}; if(-not $matches){Write-Host 'No old Test Center GUI process found.'}"
if errorlevel 1 (
  echo ERROR: Could not close old Test Center GUI. No update performed.
  pause
  exit /b 5
)
rem Contain legacy UPDATE-TEST-CENTER.bat poisoning system TMP with its own .bat path.
rem Both Windows PowerShell and MSBuild require TEMP/TMP to be directories.
set "MWO_SAFE_BUILD_TEMP=D:\MerzoOptimizer-LocalLab\Temp\ToolchainTemp"
if not exist "%MWO_SAFE_BUILD_TEMP%" mkdir "%MWO_SAFE_BUILD_TEMP%"
if not exist "%MWO_SAFE_BUILD_TEMP%\." (
  echo ERROR: Cannot prepare D: local build temporary directory.
  pause
  exit /b 10
)
set "TEMP=%MWO_SAFE_BUILD_TEMP%"
set "TMP=%MWO_SAFE_BUILD_TEMP%"
set "BASE=https://raw.githubusercontent.com/Merzo4/my-app-updates/95c735c54ced62605e9c02cd98569b0b4d023665/tools/MerzoOptimizer.LocalLab"
set "STAGE=%TEMP%\MerzoOptimizer-TestCenter-0.2.6-Pinned"
if not exist "%STAGE%" mkdir "%STAGE%"
if not exist "%STAGE%" (
  echo ERROR: Cannot create temporary bootstrap directory.
  pause
  exit /b 5
)
for %%F in (Build-NativeHost.ps1 Bootstrap-PowerShell7.ps1 Start-TestCenter.ps1 MerzoOptimizer.LocalLab.ps1 Run-Profile.ps1 Run-Profile.Core.ps1 AUTO-REPORT.ps1 local-lab-profile.json ENABLE-DESTRUCTIVE-LAB.ps1 PACK-EVIDENCE.ps1 PUBLISH-EVIDENCE.ps1 Install-LocalLab.ps1 README.md) do (
  echo Downloading pinned file %%F...
  curl.exe -fL --retry 3 --connect-timeout 15 --max-time 120 "%BASE%/%%F" -o "%STAGE%\%%F"
  if errorlevel 1 (
    echo ERROR: Download failed: %%F. Nothing was installed by this batch.
    pause
    exit /b 6
  )
)
echo.
if not exist "%STAGE%\NativeHost" mkdir "%STAGE%\NativeHost"
for %%F in (MerzoOptimizer.TestCenter.csproj Program.cs) do (
  echo Downloading native GUI source %%F...
  curl.exe -fL --retry 3 --connect-timeout 15 --max-time 120 "%BASE%/NativeHost/%%F" -o "%STAGE%\NativeHost\%%F"
  if errorlevel 1 (
    echo ERROR: Download NativeHost/%%F failed. Existing Test Center shortcut stays unchanged.
    pause
    exit /b 6
  )
)
echo.
echo Bootstrap may install official PowerShell 7 and ask for UAC.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%STAGE%\Bootstrap-PowerShell7.ps1"
if errorlevel 1 (
  echo ERROR: PowerShell 7 bootstrap failed.
  pause
  exit /b 7
)
set "PWSH=C:\Program Files\PowerShell\7\pwsh.exe"
if not exist "%PWSH%" (
  echo ERROR: PowerShell 7 not present at expected path.
  pause
  exit /b 8
)
echo.
echo Building/updating Local Test Center native EXE in D: ...
"%PWSH%" -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%STAGE%\Install-LocalLab.ps1"
if errorlevel 1 (
  echo ERROR: Test Center installation failed.
  echo See D:\MerzoOptimizer-LocalLab\Logs\native-build.log and native-smoke.log if present.
  pause
  exit /b 9
)
echo.
echo OK: Native Test Center 0.2.6 EXE installed. The GUI was launched.
echo Use Diagnostics, Update Source, QUICK, then FULL SAFE.
echo GAME to RESTORE is blocked on a normal workstation.
exit /b 0
