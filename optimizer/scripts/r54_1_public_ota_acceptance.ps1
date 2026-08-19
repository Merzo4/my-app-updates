$ErrorActionPreference='Stop'
$statusPath='.\optimizer\R54_1_PUBLIC_OTA_STATUS.json'
$status=[ordered]@{
  conclusion='failure';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]($env:GITHUB_RUN_ID ?? '0');headSha=$env:GITHUB_SHA
  publicRelease='pending';r54Baseline='pending';r54UpdaterDownload='pending';r54ToR541Upgrade='pending';r541TrkWksApply='pending';r541TrkWksRestore='pending';r541Launch='pending';installerSha='';canonicalPath='';error=''
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
function Get-ServiceStart([string]$Name){$p="HKLM:\SYSTEM\CurrentControlSet\Services\$Name";if(!(Test-Path $p)){return $null};return [int](Get-ItemPropertyValue -Path $p -Name Start -ErrorAction Stop)}
function Restore-ServiceFallback([string]$Name,[int]$Start){$mode=switch($Start){2{'auto'}3{'demand'}4{'disabled'}default{$null}};if($mode){& sc.exe config $Name start= $mode|Out-Host;if($LASTEXITCODE-ne0){throw "Fallback service restore failed: $Name $Start"}}}
try{
  if([string]::IsNullOrWhiteSpace($env:GH_TOKEN)){throw 'GH_TOKEN missing'}
  if([string]::IsNullOrWhiteSpace($env:GITHUB_REPOSITORY)){throw 'GITHUB_REPOSITORY missing'}
  $repo=$env:GITHUB_REPOSITORY
  $release=gh api "repos/$repo/releases/tags/mwo-v0.1.54.1"|ConvertFrom-Json
  if($release.tag_name-ne'mwo-v0.1.54.1' -or $release.draft -or $release.prerelease){throw 'Public R54.1 release invalid'}
  if($release.target_commitish-ne'c8ed6d8bdaca6ef7178f8876379821bc3c16ed23'){throw "Public R54.1 target mismatch: $($release.target_commitish)"}
  $asset=$release.assets|Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe'|Select-Object -First 1
  $side=$release.assets|Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256'|Select-Object -First 1
  if(!$asset -or !$side){throw 'Public R54.1 installer/sidecar missing'}
  if(!$asset.digest -or $asset.digest-notmatch'^sha256:[0-9a-fA-F]{64}$'){throw 'Public R54.1 installer digest missing'}
  $expectedSha=$asset.digest.Substring(7).ToLowerInvariant();$status.installerSha=$expectedSha;$status.publicRelease='success'
  Write-Host "R54_1_PUBLIC_RELEASE_PASS target=$($release.target_commitish) sha=$expectedSha"

  Remove-Item public-r54 -Recurse -Force -ErrorAction SilentlyContinue;New-Item -ItemType Directory -Force public-r54|Out-Null
  gh release download mwo-v0.1.54 --repo $repo --dir public-r54 --pattern 'MerzoWindowsOptimizerSetup-win-x64.exe'
  if($LASTEXITCODE-ne0){throw 'Could not download public R54 baseline'}
  $r54Setup=(Resolve-Path 'public-r54/MerzoWindowsOptimizerSetup-win-x64.exe').Path
  Invoke-MerzoInstaller -Setup $r54Setup -Arguments '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
  $exe=Get-CanonicalExe;if(!$exe){throw 'Public R54 canonical EXE missing'}
  $base=[Diagnostics.FileVersionInfo]::GetVersionInfo($exe.FullName).FileVersion
  if($base-ne'0.1.54.0'){throw "Public baseline is not R54: $base"}
  $status.r54Baseline='success';Write-Host "R54_BASELINE_FOR_541_PASS path=$($exe.FullName) version=$base"

  $cfgPath=Join-Path $exe.DirectoryName 'data\update_settings.json';$winDll=Join-Path $exe.DirectoryName 'MerzoOptimizer.Windows.dll'
  if(!(Test-Path $cfgPath)-or!(Test-Path $winDll)){throw 'Installed R54 updater files missing'}
  $cfg=Get-Content $cfgPath -Raw|ConvertFrom-Json
  if($cfg.repository_owner-ne'Merzo4' -or $cfg.repository_name-ne'my-app-updates' -or $cfg.release_tag_prefix-ne'mwo-v'){throw 'Installed R54 official update channel mismatch'}
  $updateDir=Join-Path $env:TEMP 'MerzoWindowsOptimizer-R54-to-R541-RealDownload';Remove-Item $updateDir -Recurse -Force -ErrorAction SilentlyContinue
  $probe='.\optimizer\scripts\r54_1_r54_download_probe.ps1'
  $probeLines=& pwsh -NoLogo -NoProfile -File $probe -Dll $winDll -SettingsPath $cfgPath -UpdateDirectory $updateDir -ExpectedVersion '0.1.54.1' 2>&1
  $probeExit=$LASTEXITCODE;$probeText=($probeLines|ForEach-Object {[string]$_})-join"`n";Write-Host $probeText
  if($probeExit-ne0 -or $probeText-notmatch'R54_REAL_DOWNLOAD_PASS'){throw "Public R54 DownloadAsync rejected R54.1 (exit=$probeExit)"}
  $downloaded=Get-ChildItem $updateDir -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe'|Select-Object -First 1
  if(!$downloaded){throw 'R54 updater download output missing'}
  $actual=(Get-FileHash $downloaded.FullName -Algorithm SHA256).Hash.ToLowerInvariant();if($actual-ne$expectedSha){throw "R54-downloaded R54.1 SHA mismatch: $actual"}
  $status.r54UpdaterDownload='success';Write-Host "R54_REAL_UPDATER_ACCEPTS_541_PASS sha=$actual"

  Invoke-MerzoInstaller -Setup $downloaded.FullName -Arguments '/SILENT /MERZOUPDATE=1 /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
  $r541=Get-CanonicalExe;if(!$r541){throw 'R54.1 canonical EXE missing after OTA'}
  $fv=[Diagnostics.FileVersionInfo]::GetVersionInfo($r541.FullName).FileVersion;if($fv-ne'0.1.54.1'){throw "Installed R54.1 FileVersion mismatch: $fv"}
  $entry=Get-MerzoUninstallEntry;if(!$entry -or !$entry.InstallLocation){throw 'R54.1 uninstall InstallLocation missing'}
  $registered=Join-Path $entry.InstallLocation 'MerzoWindowsOptimizer.exe';if([IO.Path]::GetFullPath($registered).TrimEnd('\')-ne[IO.Path]::GetFullPath($r541.FullName).TrimEnd('\')){throw "R54.1 registry path is not canonical: $registered"}
  $status.canonicalPath=$r541.FullName;$status.r54ToR541Upgrade='success';Write-Host "R54_TO_541_REAL_OTA_PASS path=$($r541.FullName) version=$fv"

  $service=Get-Service TrkWks -ErrorAction SilentlyContinue;if(!$service){throw 'TrkWks missing on public OTA runner'}
  $original=Get-ServiceStart 'TrkWks';if($original-notin@(2,3,4)){throw "TrkWks unsupported baseline Start=$original"};$target=if($original-eq4){3}else{4}
  $newDll=Join-Path $r541.DirectoryName 'MerzoOptimizer.Windows.dll';Push-Location $r541.DirectoryName
  try{
    $asm=[Reflection.Assembly]::LoadFrom($newDll);$type=$asm.GetType('MerzoOptimizer.Windows.Services.WindowsServiceStartTypeManager',$true,$false);$method=$type.GetMethod('SetStartType',[Reflection.BindingFlags]'NonPublic,Static');if(!$method){throw 'Installed R54.1 SCM helper method missing'}
    $changed=$false
    try{
      $null=$method.Invoke($null,@('TrkWks',$target));$changed=$true;$after=Get-ServiceStart 'TrkWks';if($after-ne$target){throw "Installed R54.1 TrkWks apply mismatch: $after"};$status.r541TrkWksApply='success';Write-Host "R541_PUBLIC_TRKWKS_APPLY_PASS start=$after"
      $null=$method.Invoke($null,@('TrkWks',$original));$restored=Get-ServiceStart 'TrkWks';if($restored-ne$original){throw "Installed R54.1 TrkWks restore mismatch: $restored"};$changed=$false;$status.r541TrkWksRestore='success';Write-Host "R541_PUBLIC_TRKWKS_RESTORE_PASS start=$restored"
    }finally{if($changed -or (Get-ServiceStart 'TrkWks')-ne$original){try{$null=$method.Invoke($null,@('TrkWks',$original))}catch{};if((Get-ServiceStart 'TrkWks')-ne$original){Restore-ServiceFallback 'TrkWks' $original}}}
  }finally{Pop-Location}
  if((Get-ServiceStart 'TrkWks')-ne$original){throw 'TrkWks not restored after public acceptance'}

  Stop-MerzoApp;$app=Start-Process $r541.FullName -PassThru;Start-Sleep -Seconds 5;$app.Refresh();if($app.HasExited){throw "R54.1 exited during launch acceptance: $($app.ExitCode)"};Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue;$status.r541Launch='success';Write-Host "R541_PUBLIC_LAUNCH_PASS pid=$($app.Id)"
  $status.conclusion='success';Save-Status;Write-Host 'R54_TO_R541_PUBLIC_OTA_ACCEPTANCE_PASS'
}catch{$status.error=$_.Exception.Message;try{Save-Status}catch{};Write-Host "::error::$($_.Exception.Message)";exit 1}
