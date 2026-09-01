@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "BASE=https://raw.githubusercontent.com/Merzo4/my-app-updates/mwo-local-test-center/tools/MerzoOptimizer.LocalLab"
set "TMPDIR=%TEMP%\MerzoOptimizer-LocalLab-Bootstrap"
if exist "%TMPDIR%" rmdir /s /q "%TMPDIR%"
mkdir "%TMPDIR%" || exit /b 1

where curl.exe >nul 2>nul
if errorlevel 1 (
  echo ОШИБКА: curl.exe не найден. Нужен стандартный Windows curl.
  pause
  exit /b 1
)
where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo ОШИБКА: встроенный Windows PowerShell не найден.
  pause
  exit /b 1
)

for %%F in (MerzoOptimizer.LocalLab.ps1 Run-Profile.ps1 Run-Profile.Core.ps1 local-lab-profile.json ENABLE-DESTRUCTIVE-LAB.ps1 PACK-EVIDENCE.ps1 PUBLISH-EVIDENCE.ps1 Install-LocalLab.ps1 README.md) do (
  echo Скачиваю %%F...
  curl.exe -fL --retry 3 --connect-timeout 15 "%BASE%/%%F" -o "%TMPDIR%\%%F"
  if errorlevel 1 (
    echo ОШИБКА: не удалось скачать %%F
    pause
    exit /b 1
  )
)

echo.
echo Устанавливаю Merzo Optimizer Local Test Center на D: ...
echo Если PowerShell 7 отсутствует, установщик поставит его автоматически.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%TMPDIR%\Install-LocalLab.ps1"
if errorlevel 1 (
  echo.
  echo Установка завершилась ошибкой.
  pause
  exit /b 1
)

echo.
echo ГОТОВО. GitHub Actions workflows не запускались.
exit /b 0
