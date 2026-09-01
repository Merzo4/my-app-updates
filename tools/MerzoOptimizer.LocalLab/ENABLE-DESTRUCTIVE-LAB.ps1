param([switch]$DedicatedLabOnly)
$ErrorActionPreference='Stop'
$root=if($env:MWO_LAB_ROOT){$env:MWO_LAB_ROOT}else{'D:\MerzoOptimizer-LocalLab'}
if(!$DedicatedLabOnly){
  Write-Host 'BLOCKED.' -ForegroundColor Red
  Write-Host 'Этот режим реально применяет настройки GAME к Windows и затем проверяет RestoreAll.'
  Write-Host 'Его разрешено включать ТОЛЬКО на выделенной лабораторной Windows/тестовом ПК.'
  Write-Host ''
  Write-Host 'Для выделенного стенда запусти:'
  Write-Host '  pwsh -File .\ENABLE-DESTRUCTIVE-LAB.ps1 -DedicatedLabOnly'
  exit 2
}
$state=Join-Path $root 'State';New-Item $state -ItemType Directory -Force|Out-Null
[ordered]@{
  labOnly=$true
  machineName=$env:COMPUTERNAME
  armedAt=(Get-Date).ToUniversalTime().ToString('o')
  warning='This machine is explicitly designated for destructive Merzo Optimizer GAME/Restore testing.'
}|ConvertTo-Json|Set-Content (Join-Path $state 'ALLOW-SYSTEM-MUTATION.json') -Encoding UTF8
Write-Host "DESTRUCTIVE LAB ARMED for $env:COMPUTERNAME" -ForegroundColor Yellow
Write-Host 'Чтобы снова заблокировать режим, удали D:\MerzoOptimizer-LocalLab\State\ALLOW-SYSTEM-MUTATION.json'
