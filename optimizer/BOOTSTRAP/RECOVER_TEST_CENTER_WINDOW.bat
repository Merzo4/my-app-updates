@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Merzo Windows Optimizer - Recover Test Center Window
set "LAB=D:\MerzoOptimizer-LocalLab"
set "PWSH=C:\Program Files\PowerShell\7\pwsh.exe"
if not exist "%LAB%\App\Start-TestCenter.ps1" (
  echo Test Center is not installed in D:.
  pause
  exit /b 2
)
if not exist "%PWSH%" (
  echo PowerShell 7 is not installed.
  pause
  exit /b 3
)
echo.
echo This tool stops ONLY the matching Test Center GUI process.
echo Other PowerShell processes and optimizer reports are not touched.
echo Do not close an active Test Center test without saving its results.
choice /M "Stop the old Test Center GUI and launch in visible diagnostic mode"
if errorlevel 2 exit /b 0
powershell.exe -NoLogo -NoProfile -NonInteractive -Command "$prefix='D:\MerzoOptimizer-LocalLab\App\'; $matches=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pwsh.exe' -and $_.CommandLine -and ($_.CommandLine.IndexOf($prefix+'Start-TestCenter.ps1',[StringComparison]::OrdinalIgnoreCase) -ge 0 -or $_.CommandLine.IndexOf($prefix+'MerzoOptimizer.LocalLab.ps1',[StringComparison]::OrdinalIgnoreCase) -ge 0) }); foreach($p in $matches){Write-Host ('Stopping Test Center GUI PID '+$p.ProcessId); Stop-Process -Id $p.ProcessId -ErrorAction Stop}; if(-not $matches){Write-Host 'No old Test Center GUI process found.'}"
if errorlevel 1 (
  echo Unable to close Test Center GUI, check Task Manager.
  pause
  exit /b 4
)
echo Starting with VISIBLE console: leave console open during debugging.
"%PWSH%" -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%LAB%\App\Start-TestCenter.ps1"
set "RESULT=%ERRORLEVEL%"
echo Exit code: %RESULT%
echo Debug logs: D:\MerzoOptimizer-LocalLab\Logs\
pause
exit /b %RESULT%
