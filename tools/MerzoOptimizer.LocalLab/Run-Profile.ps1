param(
  [ValidateSet('Diagnostics','Sync','Quick','FullSafe','Destructive')]
  [string]$Profile = 'Diagnostics'
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$labRoot=if($env:MWO_LAB_ROOT){$env:MWO_LAB_ROOT}else{'D:\MerzoOptimizer-LocalLab'}
$appDir=Join-Path $labRoot 'App'
$core=Join-Path $appDir 'Run-Profile.Core.ps1'
$logPath=Join-Path $labRoot 'Logs\Current.log'
$resultPath=Join-Path $labRoot 'Results\Latest\LAB-RESULT.json'
$autoReport=Join-Path $appDir 'AUTO-REPORT.ps1'
$pwshPath=(Get-Process -Id $PID).Path
if(!(Test-Path $core)){throw "Local Test Center core runner missing: $core"}

& $pwshPath -NoLogo -NoProfile -ExecutionPolicy Bypass -File $core -Profile $Profile
$coreExit=$LASTEXITCODE

try{
  $outcome=if($coreExit-eq0){'PASS'}else{'FAIL'}
  $message="Profile $Profile completed with exit=$coreExit"
  $branch=''
  $commit=''
  if(Test-Path $resultPath){
    try{
      $r=Get-Content $resultPath -Raw|ConvertFrom-Json
      if(-not[string]::IsNullOrWhiteSpace([string]$r.conclusion)){$outcome=[string]$r.conclusion}
      if(-not[string]::IsNullOrWhiteSpace([string]$r.firstCausalFailure)){$message=[string]$r.firstCausalFailure}
      $branch=[string]$r.sourceBranch
      $commit=[string]$r.sourceCommit
    }catch{}
  }
  if(Test-Path $autoReport){
    & $pwshPath -NoLogo -NoProfile -ExecutionPolicy Bypass -File $autoReport -Event ("profile."+$Profile) -Outcome $outcome -Message $message -LogPath $logPath -Profile $Profile -SourceBranch $branch -SourceCommit $commit 2>&1|ForEach-Object{
      Write-Host $_
      try{Add-Content $logPath "[auto-report] $_" -Encoding UTF8}catch{}
    }
  }
}catch{
  $msg="[auto-report] WARN: $($_.Exception.Message). Local test result remains unchanged."
  Write-Warning $msg
  try{Add-Content $logPath $msg -Encoding UTF8}catch{}
}

exit $coreExit
