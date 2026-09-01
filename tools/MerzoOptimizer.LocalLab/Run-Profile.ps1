param(
  [ValidateSet('Diagnostics','Sync','Quick','FullSafe','Destructive')]
  [string]$Profile = 'Diagnostics'
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$labRoot=if($env:MWO_LAB_ROOT){$env:MWO_LAB_ROOT}else{'D:\MerzoOptimizer-LocalLab'}
$appDir=Join-Path $labRoot 'App'
$core=Join-Path $appDir 'Run-Profile.Core.ps1'
$cfgPath=Join-Path $appDir 'local-lab-profile.json'
$logPath=Join-Path $labRoot 'Logs\Current.log'
$resultPath=Join-Path $labRoot 'Results\Latest\LAB-RESULT.json'
$publisher=Join-Path $appDir 'PUBLISH-EVIDENCE.ps1'
if(!(Test-Path $core)){throw "Local Test Center core runner missing: $core"}

& pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File $core -Profile $Profile
$coreExit=$LASTEXITCODE

try{
  if((Test-Path $cfgPath)-and(Test-Path $publisher)-and(Test-Path $resultPath)){
    $cfg=Get-Content $cfgPath -Raw|ConvertFrom-Json
    $result=Get-Content $resultPath -Raw|ConvertFrom-Json
    $auto=$false
    $prop=$cfg.PSObject.Properties['autoPublishEvidence']
    if($prop){$auto=[bool]$prop.Value}
    if($auto-and-not[string]::IsNullOrWhiteSpace([string]$result.sourceCommit)){
      & pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File $publisher 2>&1|ForEach-Object{
        Write-Host $_
        Add-Content $logPath "[evidence] $_" -Encoding UTF8
      }
      $pubExit=$LASTEXITCODE
      if($pubExit-ne0){
        $msg="[evidence] WARN: automatic report upload failed (exit=$pubExit). Local test result remains unchanged."
        Write-Warning $msg
        Add-Content $logPath $msg -Encoding UTF8
      }
    }
  }
}catch{
  $msg="[evidence] WARN: $($_.Exception.Message). Local test result remains unchanged."
  Write-Warning $msg
  try{Add-Content $logPath $msg -Encoding UTF8}catch{}
}

exit $coreExit
