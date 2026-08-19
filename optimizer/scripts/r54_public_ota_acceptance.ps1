$ErrorActionPreference='Stop'
$optimizerRoot=Split-Path $PSScriptRoot -Parent
$statusPath=Join-Path $optimizerRoot 'R54_OTA_ACCEPTANCE_STATUS.json'
$downloadProbe=Join-Path $PSScriptRoot 'r54_r53_download_probe.ps1'
$status=[ordered]@{
  conclusion='failure'
  createdAt=(Get-Date).ToUniversalTime().ToString('o')
  databaseId=[long]($env:GITHUB_RUN_ID ?? '0')
  headSha=$env:GITHUB_SHA
  publicRelease='pending'
  r53Baseline='pending'
  r53RealUpdaterDownload='pending'
  r53ToR54Upgrade='pending'
  r54UpdaterRegression='pending'
  r54GameSafety='pending'
  r54Launch='pending'
  installerSha=''
  canonicalPath=''
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
  if(Get-Process -ErrorAction SilentlyContinue | Where-Object {$_.ProcessName -like 'MerzoWindowsOptimizerSetup*'}){
    throw 'Installer child process did not finish in acceptance window'
  }
  Stop-MerzoApp
}
function Get-CanonicalExe {
  $p=Join-Path $env:ProgramFiles 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'
  if(Test-Path $p){return Get-Item $p}
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
  if(!(Test-Path $downloadProbe)){throw "R54 old-client download probe missing: $downloadProbe"}
  $repo=$env:GITHUB_REPOSITORY

  $latest=gh api "repos/$repo/releases/latest" | ConvertFrom-Json
  if($latest.tag_name-ne'mwo-v0.1.54' -or $latest.draft -or $latest.prerelease){throw "Latest stable release is not R54 bridge: $($latest.tag_name)"}
  $asset=$latest.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
  $sideAsset=$latest.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256' | Select-Object -First 1
  if(!$asset -or !$sideAsset){throw 'R54 public installer/sidecar assets missing'}
  if(-not$asset.digest -or $asset.digest-notmatch'^sha256:[0-9a-fA-F]{64}$'){throw 'R54 public installer digest missing'}
  $expectedSha=$asset.digest.Substring(7).ToLowerInvariant()
  $status.installerSha=$expectedSha
  $status.publicRelease='success'
  Write-Host "R54_PUBLIC_RELEASE_PASS sha=$expectedSha"

  Remove-Item public-r53 -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force public-r53 | Out-Null
  gh release download mwo-v0.1.53 --repo $repo --dir public-r53 --pattern 'MerzoWindowsOptimizerSetup-win-x64.exe'
  $r53Setup=(Resolve-Path 'public-r53/MerzoWindowsOptimizerSetup-win-x64.exe').Path
  Invoke-MerzoInstaller -Setup $r53Setup -Arguments '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'

  $exe=Get-CanonicalExe
  if(!$exe){throw 'Public R53 canonical executable missing'}
  $baselineVersion=[Diagnostics.FileVersionInfo]::GetVersionInfo($exe.FullName).FileVersion
  if($baselineVersion-ne'0.1.53.0'){throw "Public baseline is not R53 0.1.53.0: $baselineVersion"}
  $status.r53Baseline='success'
  Write-Host "R53_BASELINE_FOR_R54_PASS path=$($exe.FullName) version=$baselineVersion"

  $cfgPath=Join-Path $exe.DirectoryName 'data\update_settings.json'
  $winDll=Join-Path $exe.DirectoryName 'MerzoOptimizer.Windows.dll'
  if(!(Test-Path $cfgPath) -or !(Test-Path $winDll)){throw 'Installed R53 updater files missing'}
  $cfg=Get-Content $cfgPath -Raw | ConvertFrom-Json
  if($cfg.repository_owner-ne'Merzo4' -or $cfg.repository_name-ne'my-app-updates' -or $cfg.release_tag_prefix-ne'mwo-v'){
    throw 'Installed R53 official update channel mismatch'
  }

  # Sanity: in the actual application host, 0.1.54 is newer than 0.1.53.0.
  if([version]'0.1.54' -le [version]$baselineVersion){throw 'R54 bridge is not newer than installed R53'}

  # Crucial acceptance: call the updater DLL FROM PUBLIC R53 and let its own
  # DownloadAsync validate official tag/URL/digest/checksum. This is the path
  # that four-part mwo-v0.1.53.1 could not pass.
  $updateDir=Join-Path $env:TEMP 'MerzoWindowsOptimizer-R53-to-R54-RealDownload'
  $probeLines=& pwsh -NoLogo -NoProfile -File $downloadProbe -Dll $winDll -SettingsPath $cfgPath -UpdateDirectory $updateDir -ExpectedVersion '0.1.54' 2>&1
  $probeExit=$LASTEXITCODE
  $probeText=($probeLines | ForEach-Object {[string]$_}) -join "`n"
  Write-Host $probeText
  if($probeExit-ne0 -or $probeText-notmatch'R53_REAL_DOWNLOAD_PASS'){throw "Public R53 DownloadAsync rejected R54 bridge (exit=$probeExit)"}
  $downloaded=Get-ChildItem $updateDir -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
  if(!$downloaded){throw 'Public R53 updater download output missing'}
  $downloadSha=(Get-FileHash $downloaded.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  if($downloadSha-ne$expectedSha){throw "R53-downloaded R54 SHA mismatch: $downloadSha"}
  $status.r53RealUpdaterDownload='success'
  Write-Host "R53_REAL_UPDATER_ACCEPTS_R54_PASS sha=$downloadSha"

  # Probe process is gone; it no longer holds installed assemblies. Apply the
  # exact installer downloaded by old R53, not a separate gh-downloaded copy.
  Invoke-MerzoInstaller -Setup $downloaded.FullName -Arguments '/SILENT /MERZOUPDATE=1 /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
  $r54=Get-CanonicalExe
  if(!$r54){throw 'R54 canonical executable missing after OTA'}
  $r54Version=[Diagnostics.FileVersionInfo]::GetVersionInfo($r54.FullName).FileVersion
  if($r54Version-ne'0.1.54.0'){throw "Installed R54 FileVersion mismatch: $r54Version"}
  $entry=Get-MerzoUninstallEntry
  if(!$entry -or !$entry.InstallLocation){throw 'R54 uninstall InstallLocation missing'}
  $registered=Join-Path $entry.InstallLocation 'MerzoWindowsOptimizer.exe'
  if([IO.Path]::GetFullPath($registered).TrimEnd('\') -ne [IO.Path]::GetFullPath($r54.FullName).TrimEnd('\')){
    throw "R54 registry path is not canonical: $registered"
  }
  $status.canonicalPath=$r54.FullName
  $status.r53ToR54Upgrade='success'
  Write-Host "R53_TO_R54_REAL_OTA_PASS path=$($r54.FullName) version=$r54Version"

  # New updater regression: future four-part tags must stay four-part and its
  # current version must come from MerzoOptimizer.Windows, not the host process.
  $newDll=Join-Path $r54.DirectoryName 'MerzoOptimizer.Windows.dll'
  $parserProbe=Join-Path $env:TEMP ('r54-installed-parser-'+[guid]::NewGuid().ToString('N')+'.ps1')
  @'
param([string]$Dll)
$ErrorActionPreference='Stop'
$dir=Split-Path $Dll -Parent
Push-Location $dir
try {
  $asm=[Reflection.Assembly]::LoadFrom($Dll)
  $type=$asm.GetTypes() | Where-Object {$_.FullName -match 'GitHubUpdateService$'} | Select-Object -First 1
  $flags=[Reflection.BindingFlags]'NonPublic,Static'
  $parse=$type.GetMethod('ParseTaggedVersion',$flags)
  $format=$type.GetMethod('FormatVersion',$flags)
  $current=$type.GetMethod('GetCurrentVersion',$flags)
  if(!$parse -or !$format -or !$current){throw 'Installed R54 updater regression methods missing'}
  $v=$parse.Invoke($null,@('mwo-v0.1.54.1','mwo-v'))
  $formatted=[string]$format.Invoke($null,@($v))
  $cur=[string]$current.Invoke($null,@())
  Write-Host "PARSED=$v FORMATTED=$formatted CURRENT=$cur"
  if($v.ToString()-ne'0.1.54.1' -or $formatted-ne'0.1.54.1'){throw 'Installed R54 loses four-part hotfix version'}
  if($cur-ne'0.1.54.0'){throw "Installed R54 current-version source mismatch: $cur"}
  Write-Host 'R54_INSTALLED_FOUR_PART_UPDATER_PASS'
}
finally {Pop-Location}
'@ | Set-Content $parserProbe -Encoding UTF8
  $parserLines=& pwsh -NoLogo -NoProfile -File $parserProbe -Dll $newDll 2>&1
  $parserExit=$LASTEXITCODE
  Write-Host (($parserLines | ForEach-Object {[string]$_}) -join "`n")
  Remove-Item $parserProbe -Force -ErrorAction SilentlyContinue
  if($parserExit-ne0){throw 'Installed R54 four-part updater regression failed'}
  $status.r54UpdaterRegression='success'

  # Installed SafetyEngine + installed catalog proof for the exact GAME blocker.
  $coreDll=Join-Path $r54.DirectoryName 'MerzoOptimizer.Core.dll'
  $catalogPath=Join-Path $r54.DirectoryName 'data\tweaks.json'
  $safetyProbe=Join-Path $env:TEMP ('r54-installed-safety-'+[guid]::NewGuid().ToString('N')+'.ps1')
  @'
param([string]$CoreDll,[string]$Catalog)
$ErrorActionPreference='Stop'
$dir=Split-Path $CoreDll -Parent
Push-Location $dir
try {
  $asm=[Reflection.Assembly]::LoadFrom($CoreDll)
  $safetyType=$asm.GetTypes() | Where-Object {$_.FullName -match 'SafetyEngine$'} | Select-Object -First 1
  if(!$safetyType){throw 'SafetyEngine missing'}
  $eval=$safetyType.GetMethods() | Where-Object {$_.Name-eq'Evaluate' -and $_.GetParameters().Count-eq3} | Select-Object -First 1
  if(!$eval){throw 'SafetyEngine.Evaluate missing'}
  $tweakType=$eval.GetParameters()[0].ParameterType
  $listType=[System.Collections.Generic.List``1].MakeGenericType($tweakType)
  $json=Get-Content $Catalog -Raw
  $items=[System.Text.Json.JsonSerializer]::Deserialize($json,$listType)
  $idProp=$tweakType.GetProperty('Id')
  $target=$null
  foreach($item in $items){if([string]$idProp.GetValue($item)-eq'r53.process.service_host_density'){$target=$item;break}}
  if(!$target){throw 'Installed Service Host Density tweak missing'}
  $engine=[Activator]::CreateInstance($safetyType)
  $result=$eval.Invoke($engine,@($target,$true,[Environment]::OSVersion.Version.Build))
  $allowed=[bool]$result.GetType().GetProperty('Allowed').GetValue($result)
  $message=[string]$result.GetType().GetProperty('Message').GetValue($result)
  Write-Host "R54_GAME_SAFETY_RESULT allowed=$allowed message=$message"
  if(!$allowed){throw 'Installed R54 still blocks exact GAME Service Host Density action'}
  Write-Host 'R54_INSTALLED_GAME_SERVICE_HOST_SAFETY_PASS'
}
finally {Pop-Location}
'@ | Set-Content $safetyProbe -Encoding UTF8
  $safetyLines=& pwsh -NoLogo -NoProfile -File $safetyProbe -CoreDll $coreDll -Catalog $catalogPath 2>&1
  $safetyExit=$LASTEXITCODE
  Write-Host (($safetyLines | ForEach-Object {[string]$_}) -join "`n")
  Remove-Item $safetyProbe -Force -ErrorAction SilentlyContinue
  if($safetyExit-ne0){throw 'Installed R54 GAME SafetyEngine regression failed'}
  $status.r54GameSafety='success'

  Stop-MerzoApp
  $app=Start-Process $r54.FullName -PassThru
  Start-Sleep -Seconds 5
  $app.Refresh()
  if($app.HasExited){throw "R54 exited during launch acceptance: $($app.ExitCode)"}
  Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue
  $status.r54Launch='success'
  Write-Host "R54_INSTALLED_LAUNCH_PASS pid=$($app.Id)"

  $status.conclusion='success'
  Save-Status
  Write-Host 'R54_PUBLIC_R53_TO_R54_ACCEPTANCE_PASS'
}
catch {
  $status.error=$_.Exception.Message
  Save-Status
  Write-Host "::error::$($_.Exception.Message)"
  exit 1
}
