$ErrorActionPreference='Stop'
$statusPath='.\optimizer\R54_2_PUBLIC_OTA_STATUS.json'
$status=[ordered]@{
  conclusion='failure';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]($env:GITHUB_RUN_ID ?? '0');headSha=$env:GITHUB_SHA
  publicRelease='pending';r541Baseline='pending';r541UpdaterDownload='pending';r541ToR542Upgrade='pending';r542FileVersion='pending';r542Launch='pending';installedGameRecovery='pending';installerSha='';canonicalPath='';error=''
}
function Save-Status{$status.createdAt=(Get-Date).ToUniversalTime().ToString('o');$status|ConvertTo-Json -Compress|Set-Content $statusPath -Encoding UTF8}
function Stop-MerzoApp{Get-Process MerzoWindowsOptimizer -ErrorAction SilentlyContinue|Stop-Process -Force -ErrorAction SilentlyContinue}
function Invoke-MerzoInstaller{
  param([Parameter(Mandatory=$true)][string]$Setup,[Parameter(Mandatory=$true)][string]$Arguments,[int]$TimeoutSeconds=180)
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
  $entries=@();foreach($rp in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*')){$entries+=Get-ItemProperty $rp -ErrorAction SilentlyContinue|Where-Object {$_.DisplayName -like '*Merzo*Optimizer*'}}
  return $entries|Sort-Object DisplayVersion -Descending|Select-Object -First 1
}
try{
  if([string]::IsNullOrWhiteSpace($env:GH_TOKEN)){throw 'GH_TOKEN missing'}
  if([string]::IsNullOrWhiteSpace($env:GITHUB_REPOSITORY)){throw 'GITHUB_REPOSITORY missing'}
  $repo=$env:GITHUB_REPOSITORY
  $approvedHead='086c02fc648893e18961eeee74e8bd73c4f83a2f'
  $approvedRun=32270447478
  $approvedArtifactId=9372048444
  $mutationRun=32336202703

  $publish=Get-Content '.\optimizer\R54_2_PUBLISH_STATUS.json' -Raw|ConvertFrom-Json
  if($publish.conclusion-ne'success' -or [long]$publish.buildRun-ne$approvedRun -or [long]$publish.artifactId-ne$approvedArtifactId -or [long]$publish.mutationRun-ne$mutationRun -or $publish.tag-ne'mwo-v0.1.54.2'){throw 'R54.2 publication status is not exact-green'}

  $release=gh api "repos/$repo/releases/tags/mwo-v0.1.54.2"|ConvertFrom-Json
  if($release.tag_name-ne'mwo-v0.1.54.2' -or $release.draft -or $release.prerelease){throw 'Public R54.2 release invalid'}
  if($release.target_commitish-ne$approvedHead){throw "Public R54.2 target mismatch: $($release.target_commitish)"}
  $asset=$release.assets|Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe'|Select-Object -First 1
  $side=$release.assets|Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256'|Select-Object -First 1
  if(!$asset -or !$side){throw 'Public R54.2 installer/sidecar missing'}
  if(!$asset.digest -or $asset.digest-notmatch'^sha256:[0-9a-fA-F]{64}$'){throw 'Public R54.2 installer digest missing'}
  $expectedSha=$asset.digest.Substring(7).ToLowerInvariant();$status.installerSha=$expectedSha;$status.publicRelease='success'
  if($publish.installerSha-ne$expectedSha){throw "Public R54.2 installer digest differs from exact publication status: $expectedSha != $($publish.installerSha)"}
  Write-Host "R54_2_PUBLIC_RELEASE_PASS target=$($release.target_commitish) sha=$expectedSha"

  Remove-Item public-r541 -Recurse -Force -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force public-r541|Out-Null
  gh release download mwo-v0.1.54.1 --repo $repo --dir public-r541 --pattern 'MerzoWindowsOptimizerSetup-win-x64.exe'
  if($LASTEXITCODE-ne0){throw 'Could not download public R54.1 baseline'}
  $r541Setup=(Resolve-Path 'public-r541/MerzoWindowsOptimizerSetup-win-x64.exe').Path
  Invoke-MerzoInstaller -Setup $r541Setup -Arguments '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
  $exe=Get-CanonicalExe;if(!$exe){throw 'Public R54.1 canonical EXE missing'}
  $base=[Diagnostics.FileVersionInfo]::GetVersionInfo($exe.FullName).FileVersion
  if($base-ne'0.1.54.1'){throw "Public baseline is not R54.1: $base"}
  $status.r541Baseline='success';Write-Host "R541_BASELINE_FOR_542_PASS path=$($exe.FullName) version=$base"

  $cfgPath=Join-Path $exe.DirectoryName 'data\update_settings.json';$winDll=Join-Path $exe.DirectoryName 'MerzoOptimizer.Windows.dll'
  if(!(Test-Path $cfgPath)-or!(Test-Path $winDll)){throw 'Installed R54.1 updater files missing'}
  $cfg=Get-Content $cfgPath -Raw|ConvertFrom-Json
  if($cfg.repository_owner-ne'Merzo4' -or $cfg.repository_name-ne'my-app-updates' -or $cfg.release_tag_prefix-ne'mwo-v'){throw 'Installed R54.1 official update channel mismatch'}
  $updateDir=Join-Path $env:TEMP 'MerzoWindowsOptimizer-R541-to-R542-RealDownload';Remove-Item $updateDir -Recurse -Force -ErrorAction SilentlyContinue
  $probe='.\optimizer\scripts\r54_1_r54_download_probe.ps1'
  $probeLines=& pwsh -NoLogo -NoProfile -File $probe -Dll $winDll -SettingsPath $cfgPath -UpdateDirectory $updateDir -ExpectedVersion '0.1.54.2' 2>&1
  $probeExit=$LASTEXITCODE;$probeText=($probeLines|ForEach-Object {[string]$_})-join"`n";Write-Host $probeText
  if($probeExit-ne0 -or $probeText-notmatch'R54_REAL_DOWNLOAD_PASS'){throw "Public R54.1 DownloadAsync rejected R54.2 (exit=$probeExit)"}
  if($probeText-notmatch'current=0\.1\.54\.1\s+latest=0\.1\.54\.2'){throw 'R54.1 updater did not preserve/expose the four-component 0.1.54.1 -> 0.1.54.2 transition'}
  $downloaded=Get-ChildItem $updateDir -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe'|Select-Object -First 1
  if(!$downloaded){throw 'R54.1 updater download output missing'}
  $actual=(Get-FileHash $downloaded.FullName -Algorithm SHA256).Hash.ToLowerInvariant();if($actual-ne$expectedSha){throw "R54.1-downloaded R54.2 SHA mismatch: $actual"}
  $status.r541UpdaterDownload='success';Write-Host "R541_REAL_UPDATER_ACCEPTS_542_PASS sha=$actual"

  Invoke-MerzoInstaller -Setup $downloaded.FullName -Arguments '/SILENT /MERZOUPDATE=1 /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
  $r542=Get-CanonicalExe;if(!$r542){throw 'R54.2 canonical EXE missing after OTA'}
  $fv=[Diagnostics.FileVersionInfo]::GetVersionInfo($r542.FullName).FileVersion;if($fv-ne'0.1.54.2'){throw "Installed R54.2 FileVersion mismatch: $fv"}
  $entry=Get-MerzoUninstallEntry;if(!$entry -or !$entry.InstallLocation){throw 'R54.2 uninstall InstallLocation missing'}
  $registered=Join-Path $entry.InstallLocation 'MerzoWindowsOptimizer.exe';if([IO.Path]::GetFullPath($registered).TrimEnd('\')-ne[IO.Path]::GetFullPath($r542.FullName).TrimEnd('\')){throw "R54.2 registry path is not canonical: $registered"}
  $status.canonicalPath=$r542.FullName;$status.r541ToR542Upgrade='success';$status.r542FileVersion='success';Write-Host "R541_TO_542_REAL_OTA_PASS path=$($r542.FullName) version=$fv"

  Stop-MerzoApp;$app=Start-Process $r542.FullName -PassThru;Start-Sleep -Seconds 5;$app.Refresh();if($app.HasExited){throw "R54.2 exited during launch acceptance: $($app.ExitCode)"};Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue;$status.r542Launch='success';Write-Host "R542_PUBLIC_LAUNCH_PASS pid=$($app.Id)"

  # Strong optional gate: exercise the installed public R54.2 binaries through the
  # same full GAME -> production RestoreAll -> restored-state acceptance used pre-publish.
  $installedArtifact=Join-Path $env:RUNNER_TEMP ('mwo-r542-installed-smoke-'+[guid]::NewGuid().ToString('N'))
  New-Item -ItemType Directory -Force $installedArtifact|Out-Null
  $installedZip=Join-Path $installedArtifact 'MerzoWindowsOptimizer-portable-win-x64.zip'
  Compress-Archive -Path (Join-Path $r542.DirectoryName '*') -DestinationPath $installedZip -CompressionLevel Fastest -Force
  $installedZipSha=(Get-FileHash $installedZip -Algorithm SHA256).Hash.ToLowerInvariant()
  Set-Content (Join-Path $installedArtifact 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256') ($installedZipSha+'  MerzoWindowsOptimizer-portable-win-x64.zip') -Encoding ASCII
  & '.\optimizer\scripts\r54_2_game_mutation_acceptance_v12.ps1' -ArtifactDir $installedArtifact
  if($LASTEXITCODE-ne0){throw "Installed public R54.2 GAME + Recovery smoke failed: $LASTEXITCODE"}
  $status.installedGameRecovery='success';Write-Host 'R542_INSTALLED_PUBLIC_GAME_RECOVERY_PASS'

  $status.conclusion='success';Save-Status;Write-Host 'R541_TO_R542_PUBLIC_OTA_ACCEPTANCE_PASS'
}catch{$status.error=$_.Exception.Message;try{Save-Status}catch{};Write-Host "::error::$($_.Exception.Message)";exit 1}
