param(
  [Parameter(Mandatory=$true)][long]$BuildRun,
  [Parameter(Mandatory=$true)][string]$BuildHead,
  [Parameter(Mandatory=$true)][string]$ExpectedInstallerSha,
  [Parameter(Mandatory=$true)][string]$ExpectedPortableSha
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$source='.\optimizer\scripts\r55_1_public_ota_acceptance.ps1'
if(!(Test-Path $source)){throw 'R55.1 OTA v1 acceptance source missing'}
$text=Get-Content $source -Raw

# The v1 harness repeatedly killed MerzoWindowsOptimizer while Inno Setup was
# still inside Restart Manager / restart-applications processing. The exact
# public R55.1 installer itself is proven good by the independent argument
# matrix, including the full real updater argument set. Stop the app only before
# installer launch and after Setup + its child have completely exited.
$oldParent="while(!`$p.HasExited-and(Get-Date)-lt`$d){Stop-App;Start-Sleep -Milliseconds 700;`$p.Refresh()}"
$newParent="while(!`$p.HasExited-and(Get-Date)-lt`$d){Start-Sleep -Milliseconds 700;`$p.Refresh()}"
$oldChild="while((Get-Date)-lt`$d){Stop-App;`$c=Get-Process -ErrorAction SilentlyContinue|Where-Object{`$_.ProcessName-like'MerzoWindowsOptimizerSetup*'};if(!`$c){break};Start-Sleep -Milliseconds 600}"
$newChild="while((Get-Date)-lt`$d){`$c=Get-Process -ErrorAction SilentlyContinue|Where-Object{`$_.ProcessName-like'MerzoWindowsOptimizerSetup*'};if(!`$c){break};Start-Sleep -Milliseconds 600}"
if(($text.Split($oldParent).Count-1)-ne1){throw 'R55.1 OTA v2 parent-loop anchor mismatch'}
if(($text.Split($oldChild).Count-1)-ne1){throw 'R55.1 OTA v2 child-loop anchor mismatch'}
$text=$text.Replace($oldParent,$newParent).Replace($oldChild,$newChild)

$tmp=Join-Path $env:RUNNER_TEMP 'r55_1_public_ota_acceptance_v2_runtime.ps1'
Set-Content $tmp $text -Encoding UTF8
$tokens=$null;$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile($tmp,[ref]$tokens,[ref]$errors)|Out-Null
if($errors.Count-gt0){throw 'R55.1 OTA v2 runtime parser failure: '+(($errors|ForEach-Object{$_.Message})-join'; ')}
Write-Host 'R55_1_OTA_HARNESS_LIFECYCLE_FIX_PASS'
& pwsh -NoLogo -NoProfile -File $tmp -BuildRun $BuildRun -BuildHead $BuildHead -ExpectedInstallerSha $ExpectedInstallerSha -ExpectedPortableSha $ExpectedPortableSha
exit $LASTEXITCODE
