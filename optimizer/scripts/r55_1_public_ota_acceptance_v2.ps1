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

# r54_1_r54_download_probe.ps1 intentionally compiles a tiny host with dotnet
# against the installed R55 updater DLL. On hosted Windows this can leave
# VBCSCompiler/MSBuild build-server processes alive after the probe exits. Inno
# Restart Manager then sees a harness-created process holding files under the
# install tree and waits forever with the Setup .tmp child alive. Shut down only
# those build servers created by the acceptance harness before invoking Setup.
$oldPreInstall=@'
  $actual=(Get-FileHash $downloaded.FullName -Algorithm SHA256).Hash.ToLowerInvariant();if($actual-ne$ih){throw "R55 downloaded SHA=$actual"};$status.r55UpdaterDownload='success';Write-Host "R55_REAL_UPDATER_ACCEPTS_R551_PASS sha=$actual"
  Install $downloaded.FullName '/SILENT /MERZOUPDATE=1 /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
'@
$newPreInstall=@'
  $actual=(Get-FileHash $downloaded.FullName -Algorithm SHA256).Hash.ToLowerInvariant();if($actual-ne$ih){throw "R55 downloaded SHA=$actual"};$status.r55UpdaterDownload='success';Write-Host "R55_REAL_UPDATER_ACCEPTS_R551_PASS sha=$actual"
  dotnet build-server shutdown | ForEach-Object { Write-Host $_ }
  Get-Process VBCSCompiler -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 800
  if(Get-Process VBCSCompiler -ErrorAction SilentlyContinue){throw 'R55.1 OTA harness VBCSCompiler lock remains after shutdown'}
  Write-Host 'R55_1_OTA_BUILD_SERVERS_RELEASED_PASS'
  Install $downloaded.FullName '/SILENT /MERZOUPDATE=1 /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
'@
if(($text.Split($oldPreInstall).Count-1)-ne1){throw 'R55.1 OTA v2 pre-install build-server anchor mismatch'}
$text=$text.Replace($oldPreInstall,$newPreInstall)

$tmp=Join-Path $env:RUNNER_TEMP 'r55_1_public_ota_acceptance_v2_runtime.ps1'
Set-Content $tmp $text -Encoding UTF8
$tokens=$null;$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile($tmp,[ref]$tokens,[ref]$errors)|Out-Null
if($errors.Count-gt0){throw 'R55.1 OTA v2 runtime parser failure: '+(($errors|ForEach-Object{$_.Message})-join'; ')}
Write-Host 'R55_1_OTA_HARNESS_LIFECYCLE_FIX_PASS'
& pwsh -NoLogo -NoProfile -File $tmp -BuildRun $BuildRun -BuildHead $BuildHead -ExpectedInstallerSha $ExpectedInstallerSha -ExpectedPortableSha $ExpectedPortableSha
exit $LASTEXITCODE
