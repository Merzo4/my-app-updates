$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$statusPath='.\optimizer\R55_PUBLIC_OTA_STATUS.json'
$status=[ordered]@{
  conclusion='failure';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]($env:GITHUB_RUN_ID ?? '0');headSha=$env:GITHUB_SHA
  publicRelease='pending';r542Baseline='pending';r542UpdaterDownload='pending';r542ToR55Upgrade='pending';r55FileVersion='pending';r55PayloadMatch='pending';r55Launch='pending';installedGameRecovery='pending';installerSha='';portableSha='';canonicalPath='';error=''
}
function Save-Status{$status.createdAt=(Get-Date).ToUniversalTime().ToString('o');$status|ConvertTo-Json|Set-Content $statusPath -Encoding UTF8}
function Stop-MerzoApp{Get-Process MerzoWindowsOptimizer -ErrorAction SilentlyContinue|Stop-Process -Force -ErrorAction SilentlyContinue}
function Invoke-MerzoInstaller{
  param([Parameter(Mandatory=$true)][string]$Setup,[Parameter(Mandatory=$true)][string]$Arguments,[int]$TimeoutSeconds=240)
  if(!(Test-Path $Setup)){throw "Installer missing: $Setup"}
  Stop-MerzoApp
  $p=Start-Process $Setup -ArgumentList $Arguments -PassThru
  $deadline=(Get-Date).AddSeconds($TimeoutSeconds)
  while(!$p.HasExited -and (Get-Date)-lt$deadline){Stop-MerzoApp;Start-Sleep -Milliseconds 700;$p.Refresh()}
  if(!$p.HasExited){Stop-MerzoApp;Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue;throw "Installer timeout: $Setup"}
  if($p.ExitCode-ne0){throw "Installer exit $($p.ExitCode): $Setup"}
  $childDeadline=(Get-Date).AddSeconds(90)
  while((Get-Date)-lt$childDeadline){Stop-MerzoApp;$children=Get-Process -ErrorAction SilentlyContinue|Where-Object {$_.ProcessName -like 'MerzoWindowsOptimizerSetup*'};if(!$children){break};Start-Sleep -Milliseconds 700}
  if(Get-Process -ErrorAction SilentlyContinue|Where-Object {$_.ProcessName -like 'MerzoWindowsOptimizerSetup*'}){throw 'Installer child process did not finish'}
  Stop-MerzoApp
}
function Get-CanonicalExe{$p=Join-Path $env:ProgramFiles 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe';if(Test-Path $p){return Get-Item $p};return $null}
function Get-MerzoUninstallEntry{
  $entries=@()
  foreach($rp in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*')){
    foreach($item in @(Get-ItemProperty $rp -ErrorAction SilentlyContinue)){
      $dn=$item.PSObject.Properties['DisplayName'];if($dn -and [string]$dn.Value -like '*Merzo*Optimizer*'){$entries+=$item}
    }
  }
  return $entries|Sort-Object @{Expression={if($_.PSObject.Properties['DisplayVersion']){$_.DisplayVersion}else{''}};Descending=$true}|Select-Object -First 1
}
try{
  if([string]::IsNullOrWhiteSpace($env:GH_TOKEN)){throw 'GH_TOKEN missing'}
  $repo=$env:GITHUB_REPOSITORY
  if([string]::IsNullOrWhiteSpace($repo)){throw 'GITHUB_REPOSITORY missing'}
  $approvedHead='d99d61fd5f34eb1ca5331359343c950b33fc3681'
  $approvedRun=32355454110
  $approvedArtifactId=9401609214
  $approvedInstallerSha='b845ecd3d46b0f552ae8c80acc48ad2deded6e1801cbe7e28c6a488f0e56fc2f'
  $approvedPortableSha='044900a8ab3ed17cb3441a0afff2627229de19b7b1fb32b405256b01f818dbe5'

  $publish=Get-Content '.\optimizer\R55_PUBLISH_STATUS.json' -Raw|ConvertFrom-Json
  if($publish.conclusion-ne'success' -or [long]$publish.buildRun-ne$approvedRun -or $publish.buildHead-ne$approvedHead -or [long]$publish.artifactId-ne$approvedArtifactId -or $publish.tag-ne'mwo-v0.1.55' -or $publish.installerSha-ne$approvedInstallerSha -or $publish.portableSha-ne$approvedPortableSha){throw 'R55 publication status is not exact-green'}

  $release=gh api "repos/$repo/releases/tags/mwo-v0.1.55"|ConvertFrom-Json
  if($release.tag_name-ne'mwo-v0.1.55' -or $release.draft -or $release.prerelease){throw 'Public R55 release invalid'}
  if($release.target_commitish-ne$approvedHead){throw "Public R55 target mismatch: $($release.target_commitish)"}
  $asset=$release.assets|Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe'|Select-Object -First 1
  $side=$release.assets|Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256'|Select-Object -First 1
  $portableAsset=$release.assets|Where-Object name -eq 'MerzoWindowsOptimizer-portable-win-x64.zip'|Select-Object -First 1
  $portableSide=$release.assets|Where-Object name -eq 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256'|Select-Object -First 1
  if(!$asset -or !$side -or !$portableAsset -or !$portableSide){throw 'Public R55 release assets incomplete'}
  if(!$asset.digest -or $asset.digest-notmatch'^sha256:[0-9a-fA-F]{64}$'){throw 'Public R55 installer digest missing'}
  if(!$portableAsset.digest -or $portableAsset.digest-notmatch'^sha256:[0-9a-fA-F]{64}$'){throw 'Public R55 portable digest missing'}
  $expectedSha=$asset.digest.Substring(7).ToLowerInvariant();$expectedPortable=$portableAsset.digest.Substring(7).ToLowerInvariant()
  if($expectedSha-ne$approvedInstallerSha){throw "Public R55 installer digest mismatch: $expectedSha"}
  if($expectedPortable-ne$approvedPortableSha){throw "Public R55 portable digest mismatch: $expectedPortable"}
  $status.installerSha=$expectedSha;$status.portableSha=$expectedPortable;$status.publicRelease='success'
  Write-Host "R55_PUBLIC_RELEASE_PASS target=$($release.target_commitish) installer=$expectedSha portable=$expectedPortable"

  Remove-Item public-r542 -Recurse -Force -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force public-r542|Out-Null
  gh release download mwo-v0.1.54.2 --repo $repo --dir public-r542 --pattern 'MerzoWindowsOptimizerSetup-win-x64.exe'
  if($LASTEXITCODE-ne0){throw 'Could not download public R54.2 baseline'}
  $r542Setup=(Resolve-Path 'public-r542/MerzoWindowsOptimizerSetup-win-x64.exe').Path
  Invoke-MerzoInstaller -Setup $r542Setup -Arguments '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
  $exe=Get-CanonicalExe;if(!$exe){throw 'Public R54.2 canonical EXE missing'}
  $base=[Diagnostics.FileVersionInfo]::GetVersionInfo($exe.FullName).FileVersion
  if($base-ne'0.1.54.2'){throw "Public baseline is not R54.2: $base"}
  $status.r542Baseline='success';Write-Host "R542_BASELINE_FOR_R55_PASS path=$($exe.FullName) version=$base"

  $cfgPath=Join-Path $exe.DirectoryName 'data\update_settings.json';$winDll=Join-Path $exe.DirectoryName 'MerzoOptimizer.Windows.dll'
  if(!(Test-Path $cfgPath)-or!(Test-Path $winDll)){throw 'Installed R54.2 updater files missing'}
  $cfg=Get-Content $cfgPath -Raw|ConvertFrom-Json
  if($cfg.repository_owner-ne'Merzo4' -or $cfg.repository_name-ne'my-app-updates' -or $cfg.release_tag_prefix-ne'mwo-v'){throw 'Installed R54.2 official update channel mismatch'}
  $updateDir=Join-Path $env:TEMP 'MerzoWindowsOptimizer-R542-to-R55-RealDownload';Remove-Item $updateDir -Recurse -Force -ErrorAction SilentlyContinue
  $probe='.\optimizer\scripts\r54_1_r54_download_probe.ps1'
  $probeLines=& pwsh -NoLogo -NoProfile -File $probe -Dll $winDll -SettingsPath $cfgPath -UpdateDirectory $updateDir -ExpectedVersion '0.1.55' 2>&1
  $probeExit=$LASTEXITCODE;$probeText=($probeLines|ForEach-Object {[string]$_})-join"`n";Write-Host $probeText
  if($probeExit-ne0 -or $probeText-notmatch'R54_REAL_DOWNLOAD_PASS'){throw "Public R54.2 DownloadAsync rejected R55 (exit=$probeExit)"}
  $downloaded=Get-ChildItem $updateDir -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe'|Select-Object -First 1
  if(!$downloaded){throw 'R54.2 updater download output missing'}
  $actual=(Get-FileHash $downloaded.FullName -Algorithm SHA256).Hash.ToLowerInvariant();if($actual-ne$expectedSha){throw "R54.2-downloaded R55 SHA mismatch: $actual"}
  $status.r542UpdaterDownload='success';Write-Host "R542_REAL_UPDATER_ACCEPTS_R55_PASS sha=$actual"

  Invoke-MerzoInstaller -Setup $downloaded.FullName -Arguments '/SILENT /MERZOUPDATE=1 /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
  $r55=Get-CanonicalExe;if(!$r55){throw 'R55 canonical EXE missing after OTA'}
  $fv=[Diagnostics.FileVersionInfo]::GetVersionInfo($r55.FullName).FileVersion;if($fv-ne'0.1.55.0'){throw "Installed R55 FileVersion mismatch: $fv"}
  $entry=Get-MerzoUninstallEntry;if(!$entry){throw 'R55 uninstall registration missing'}
  $status.canonicalPath=$r55.FullName;$status.r542ToR55Upgrade='success';$status.r55FileVersion='success';Write-Host "R542_TO_R55_REAL_OTA_PASS path=$($r55.FullName) version=$fv"

  Remove-Item public-r55 -Recurse -Force -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force public-r55|Out-Null
  gh release download mwo-v0.1.55 --repo $repo --dir public-r55 --pattern 'MerzoWindowsOptimizer-portable-win-x64.zip'
  if($LASTEXITCODE-ne0){throw 'Could not download public R55 portable'}
  $publicZip=(Resolve-Path 'public-r55/MerzoWindowsOptimizer-portable-win-x64.zip').Path
  if((Get-FileHash $publicZip -Algorithm SHA256).Hash.ToLowerInvariant()-ne$expectedPortable){throw 'Public R55 portable SHA mismatch after download'}
  $publicPortable=Join-Path $env:RUNNER_TEMP ('r55-public-portable-'+[guid]::NewGuid().ToString('N'));Expand-Archive $publicZip $publicPortable -Force
  foreach($name in @('MerzoWindowsOptimizer.exe','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.exe')){
    $a=Join-Path $publicPortable $name;$b=Join-Path $r55.DirectoryName $name
    if(!(Test-Path $a)-or!(Test-Path $b)){throw "R55 public payload compare missing $name"}
    if((Get-FileHash $a -Algorithm SHA256).Hash-ne(Get-FileHash $b -Algorithm SHA256).Hash){throw "R55 OTA installed payload differs from public portable: $name"}
  }
  $status.r55PayloadMatch='success';Write-Host 'R55_PUBLIC_OTA_PAYLOAD_MATCH_PASS'

  Stop-MerzoApp;$app=Start-Process $r55.FullName -PassThru;Start-Sleep -Seconds 6;$app.Refresh();if($app.HasExited){throw "R55 exited during launch acceptance: $($app.ExitCode)"};Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue;$status.r55Launch='success';Write-Host "R55_PUBLIC_LAUNCH_PASS pid=$($app.Id)"

  # Strong public-binary gate: exercise installed R55 through the inherited GAME -> production RestoreAll -> restored-state acceptance.
  $installedArtifact=Join-Path $env:RUNNER_TEMP ('mwo-r55-installed-smoke-'+[guid]::NewGuid().ToString('N'));New-Item -ItemType Directory -Force $installedArtifact|Out-Null
  $installedZip=Join-Path $installedArtifact 'MerzoWindowsOptimizer-portable-win-x64.zip';Compress-Archive -Path (Join-Path $r55.DirectoryName '*') -DestinationPath $installedZip -CompressionLevel Fastest -Force
  $installedZipSha=(Get-FileHash $installedZip -Algorithm SHA256).Hash.ToLowerInvariant();Set-Content (Join-Path $installedArtifact 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256') ($installedZipSha+'  MerzoWindowsOptimizer-portable-win-x64.zip') -Encoding ASCII
  & '.\optimizer\scripts\r54_2_game_mutation_acceptance_v12.ps1' -ArtifactDir $installedArtifact
  if($LASTEXITCODE-ne0){throw "Installed public R55 GAME + Recovery smoke failed: $LASTEXITCODE"}
  $status.installedGameRecovery='success';Write-Host 'R55_INSTALLED_PUBLIC_GAME_RECOVERY_PASS'

  $status.conclusion='success';Save-Status;Write-Host 'R542_TO_R55_PUBLIC_OTA_ACCEPTANCE_PASS'
}catch{$status.error=$_.Exception.Message;try{Save-Status}catch{};Write-Host "::error::$($_.Exception.Message)";exit 1}
