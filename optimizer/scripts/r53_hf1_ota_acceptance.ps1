$ErrorActionPreference='Stop'
$optimizerRoot=Split-Path $PSScriptRoot -Parent
$statusPath=Join-Path $optimizerRoot 'R53_HF1_OTA_STATUS.json'
$feedProbe=Join-Path $PSScriptRoot 'r53_r52_feed_probe.ps1'
$status=[ordered]@{
  conclusion='failure'
  createdAt=(Get-Date).ToUniversalTime().ToString('o')
  databaseId=[long]($env:GITHUB_RUN_ID ?? '0')
  headSha=$env:GITHUB_SHA
  publicRelease='pending'
  r53Baseline='pending'
  r53FeedContract='pending'
  r53ToHf1Upgrade='pending'
  hf1Launch='pending'
  installerSha=''
  baselinePath=''
  hotfixPath=''
  error=''
}
function Save-Status {
  $status.createdAt=(Get-Date).ToUniversalTime().ToString('o')
  $status | ConvertTo-Json -Compress | Set-Content $statusPath -Encoding UTF8
}
function Stop-MerzoApp {
  Get-Process MerzoWindowsOptimizer -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}
function Invoke-MerzoInstaller {
  param([Parameter(Mandatory=$true)][string]$Setup,[Parameter(Mandatory=$true)][string]$Arguments,[int]$TimeoutSeconds=180)
  if(!(Test-Path $Setup)){throw "Installer missing: $Setup"}
  Stop-MerzoApp
  $p=Start-Process $Setup -ArgumentList $Arguments -PassThru
  $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
  while(!$p.HasExited -and (Get-Date)-lt$deadline){
    Stop-MerzoApp
    Start-Sleep -Milliseconds 700
    $p.Refresh()
  }
  if(!$p.HasExited){
    Stop-MerzoApp
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    throw "Installer timeout: $Setup"
  }
  if($p.ExitCode-ne0){throw "Installer exit $($p.ExitCode): $Setup"}
  $childDeadline=(Get-Date).AddSeconds(90)
  while((Get-Date)-lt$childDeadline){
    Stop-MerzoApp
    $children=Get-Process -ErrorAction SilentlyContinue | Where-Object {$_.ProcessName -like 'MerzoWindowsOptimizerSetup*'}
    if(!$children){break}
    Start-Sleep -Milliseconds 700
  }
  $left=Get-Process -ErrorAction SilentlyContinue | Where-Object {$_.ProcessName -like 'MerzoWindowsOptimizerSetup*'}
  if($left){throw 'Installer child process did not finish in acceptance window'}
  Stop-MerzoApp
}
function Get-CanonicalExe {
  $p=Join-Path $env:ProgramFiles 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'
  if(Test-Path $p){return (Get-Item $p)}
  return $null
}
function Get-MerzoUninstallEntry {
  $entries=@()
  foreach($rp in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*')){
    $entries += Get-ItemProperty $rp -ErrorAction SilentlyContinue | Where-Object {$_.DisplayName -like '*Merzo*Optimizer*'}
  }
  return $entries | Sort-Object DisplayVersion -Descending | Select-Object -First 1
}
try {
  if([string]::IsNullOrWhiteSpace($env:GH_TOKEN)){throw 'GH_TOKEN missing'}
  if([string]::IsNullOrWhiteSpace($env:GITHUB_REPOSITORY)){throw 'GITHUB_REPOSITORY missing'}
  if(!(Test-Path $feedProbe)){throw "Feed probe missing: $feedProbe"}
  $repo=$env:GITHUB_REPOSITORY
  $latest=gh api "repos/$repo/releases/latest" | ConvertFrom-Json
  if($latest.tag_name-ne'mwo-v0.1.53.1' -or $latest.draft -or $latest.prerelease){throw "Latest stable release is not R53.1: $($latest.tag_name)"}
  $status.publicRelease='success'

  Remove-Item public-r53,public-r531 -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force public-r53,public-r531 | Out-Null
  gh release download mwo-v0.1.53 --repo $repo --dir public-r53 --pattern 'MerzoWindowsOptimizerSetup-win-x64.exe'
  gh release download mwo-v0.1.53.1 --repo $repo --dir public-r531 --pattern 'MerzoWindowsOptimizerSetup-win-x64.exe' --pattern 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256'
  $r53Setup=(Resolve-Path 'public-r53/MerzoWindowsOptimizerSetup-win-x64.exe').Path
  $hfSetup=(Resolve-Path 'public-r531/MerzoWindowsOptimizerSetup-win-x64.exe').Path
  $hfSide=(Resolve-Path 'public-r531/MerzoWindowsOptimizerSetup-win-x64.exe.sha256').Path
  $sha=(Get-FileHash $hfSetup -Algorithm SHA256).Hash.ToLowerInvariant()
  if(-not(Get-Content $hfSide -Raw).ToLowerInvariant().Contains($sha)){throw 'Public R53.1 installer SHA sidecar mismatch'}
  $asset=$latest.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
  if(!$asset){throw 'Public R53.1 installer asset missing'}
  if($asset.digest -and $asset.digest-ne"sha256:$sha"){throw "Public R53.1 API digest mismatch: $($asset.digest)"}
  $status.installerSha=$sha
  Write-Host "R53_HF1_PUBLIC_RELEASE_PASS sha=$sha"

  Invoke-MerzoInstaller -Setup $r53Setup -Arguments '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
  $baseline=Get-CanonicalExe
  if(!$baseline){throw 'Public R53 canonical executable missing after baseline install'}
  $baselineVersion=[Diagnostics.FileVersionInfo]::GetVersionInfo($baseline.FullName).FileVersion
  if($baselineVersion-ne'0.1.53.0'){throw "Baseline FileVersion is not 0.1.53.0: $baselineVersion"}
  $status.baselinePath=$baseline.FullName
  $status.r53Baseline='success'
  Write-Host "R53_BASELINE_PASS path=$($baseline.FullName) version=$baselineVersion"

  $cfgPath=Join-Path $baseline.DirectoryName 'data\update_settings.json'
  if(!(Test-Path $cfgPath)){throw 'R53 update_settings.json missing'}
  $cfg=Get-Content $cfgPath -Raw | ConvertFrom-Json
  if($cfg.repository_owner-ne'Merzo4' -or $cfg.repository_name-ne'my-app-updates' -or $cfg.release_tag_prefix-ne'mwo-v'){throw 'R53 update channel contract mismatch'}
  $winDll=Join-Path $baseline.DirectoryName 'MerzoOptimizer.Windows.dll'
  if(!(Test-Path $winDll)){throw 'R53 updater assembly missing'}
  $probeLines=& pwsh -NoLogo -NoProfile -File $feedProbe -Dll $winDll -SettingsPath $cfgPath -UpdateDirectory (Join-Path $env:TEMP 'MerzoWindowsOptimizer-R53-HF1-Probe') -ExpectedVersion '0.1.53.1' 2>&1
  $probeExit=$LASTEXITCODE
  $probeText=($probeLines | ForEach-Object {[string]$_}) -join "`n"
  Write-Host $probeText
  if($probeExit-ne0 -or $probeText-notmatch'R52_LIVE_FEED_PASS'){throw "R53 live feed probe did not see 0.1.53.1 (exit=$probeExit)"}
  $status.r53FeedContract='success'
  Write-Host 'R53_LIVE_FEED_SEES_0_1_53_1_PASS'

  # Feed-probe process has exited, so no CI process holds installed Merzo DLLs.
  Invoke-MerzoInstaller -Setup $hfSetup -Arguments '/SILENT /MERZOUPDATE=1 /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
  $hotfix=Get-CanonicalExe
  if(!$hotfix){throw 'R53.1 canonical executable missing after OTA'}
  $hfVersion=[Diagnostics.FileVersionInfo]::GetVersionInfo($hotfix.FullName).FileVersion
  if($hfVersion-ne'0.1.53.1'){throw "Installed R53.1 FileVersion mismatch: $hfVersion"}
  $entry=Get-MerzoUninstallEntry
  if(!$entry -or !$entry.InstallLocation){throw 'R53.1 uninstall InstallLocation missing'}
  $registered=Join-Path $entry.InstallLocation 'MerzoWindowsOptimizer.exe'
  if([IO.Path]::GetFullPath($registered).TrimEnd('\') -ne [IO.Path]::GetFullPath($hotfix.FullName).TrimEnd('\')){throw "R53.1 registry path is not canonical: $registered"}
  $status.hotfixPath=$hotfix.FullName
  $status.r53ToHf1Upgrade='success'
  Write-Host "R53_TO_R53_HF1_OTA_PASS path=$($hotfix.FullName) version=$hfVersion"

  Stop-MerzoApp
  $app=Start-Process $hotfix.FullName -PassThru
  Start-Sleep -Seconds 5
  $app.Refresh()
  if($app.HasExited){throw "R53.1 exited during launch acceptance: $($app.ExitCode)"}
  Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue
  $status.hf1Launch='success'
  Write-Host "R53_HF1_LAUNCH_PASS pid=$($app.Id)"

  $status.conclusion='success'
  Save-Status
  Write-Host 'R53_HF1_PUBLIC_OTA_ACCEPTANCE_PASS'
}
catch {
  $status.error=$_.Exception.Message
  Save-Status
  Write-Host "::error::$($_.Exception.Message)"
  exit 1
}
