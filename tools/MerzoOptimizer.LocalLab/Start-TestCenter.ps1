$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$root=if($env:MWO_LAB_ROOT){$env:MWO_LAB_ROOT}else{'D:\MerzoOptimizer-LocalLab'}
$app=Join-Path $root 'App'
$logs=Join-Path $root 'Logs'
$gui=Join-Path $app 'MerzoOptimizer.LocalLab.ps1'
$autoReport=Join-Path $app 'AUTO-REPORT.ps1'
$pwshPath=(Get-Process -Id $PID).Path
New-Item $logs -ItemType Directory -Force|Out-Null
$startupLog=Join-Path $logs 'startup-error.log'
Remove-Item $startupLog -Force -ErrorAction SilentlyContinue

try{
  if(!(Test-Path $gui)){throw "GUI script missing: $gui"}
  & $gui
  exit $LASTEXITCODE
}catch{
  $message=$_.Exception.Message
  $detail=@(
    'MERZO OPTIMIZER LOCAL TEST CENTER STARTUP ERROR',
    "Time: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss'))",
    "PowerShell: $($PSVersionTable.PSVersion)",
    "PowerShellPath: $pwshPath",
    "Apartment: $([Threading.Thread]::CurrentThread.ApartmentState)",
    "Script: $gui",
    '',
    $_.Exception.ToString(),
    '',
    $_.ScriptStackTrace
  ) -join [Environment]::NewLine
  $detail|Set-Content $startupLog -Encoding UTF8
  if(Test-Path $autoReport){
    try{& $pwshPath -NoLogo -NoProfile -ExecutionPolicy Bypass -File $autoReport -Event 'gui.startup' -Outcome FAIL -Message $message -LogPath $startupLog|Out-Null}catch{}
  }
  try{
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
      "Merzo Optimizer Test Center не запустился.`n`n$message`n`nПолный лог:`n$startupLog`n`nОтчёт поставлен в очередь автоматической отправки.",
      'Merzo Optimizer Test Center — startup error',
      [System.Windows.Forms.MessageBoxButtons]::OK,
      [System.Windows.Forms.MessageBoxIcon]::Error
    )|Out-Null
  }catch{}
  exit 1
}
