param(
  [Parameter(Mandatory=$true)][long]$BuildRun,
  [Parameter(Mandatory=$true)][string]$BuildHead,
  [Parameter(Mandatory=$true)][string]$ExpectedInstallerSha,
  [Parameter(Mandatory=$true)][string]$ExpectedPortableSha
)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$statusPath='.\optimizer\R55_1_PUBLIC_OTA_STATUS.json'
$runId=0
if(-not[string]::IsNullOrWhiteSpace($env:GITHUB_RUN_ID)){$runId=[long]$env:GITHUB_RUN_ID}
$status=[ordered]@{conclusion='failure';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=$runId;headSha=$env:GITHUB_SHA;publicRelease='pending';r55Baseline='pending';r55BaselinePayloadMatch='pending';r55UpdaterDownload='pending';r55ToR551Upgrade='pending';r551FileVersion='pending';r551PayloadMatch='pending';r551Launch='pending';installedGameRecovery='pending';installerSha='';portableSha='';canonicalPath='';error=''}
function Save{$status.createdAt=(Get-Date).ToUniversalTime().ToString('o');$status|ConvertTo-Json|Set-Content $statusPath -Encoding UTF8}
function Stop-App{Get-Process MerzoWindowsOptimizer -ErrorAction SilentlyContinue|Stop-Process -Force -ErrorAction SilentlyContinue}
function Install([string]$setup,[string]$args){
  Stop-App
  $p=Start-Process $setup -ArgumentList $args -PassThru
  $d=(Get-Date).AddMinutes(4)
  while(!$p.HasExited-and(Get-Date)-lt$d){Stop-App;Start-Sleep -Milliseconds 700;$p.Refresh()}
  if(!$p.HasExited){Stop-App;Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue;throw 'OTA installer timeout'}
  if($p.ExitCode-ne0){throw "OTA installer exit=$($p.ExitCode)"}
  $d=(Get-Date).AddSeconds(75)
  while((Get-Date)-lt$d){Stop-App;$c=Get-Process -ErrorAction SilentlyContinue|Where-Object{$_.ProcessName-like'MerzoWindowsOptimizerSetup*'};if(!$c){break};Start-Sleep -Milliseconds 600}
  if(Get-Process -ErrorAction SilentlyContinue|Where-Object{$_.ProcessName-like'MerzoWindowsOptimizerSetup*'}){throw 'OTA installer child process did not finish'}
  Stop-App
}
function Canonical{Join-Path $env:ProgramFiles 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'}
function Compare-Payload([string]$portableDir,[string]$installedDir,[string]$label){
  foreach($n in @('MerzoWindowsOptimizer.exe','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.exe')){
    $a=Join-Path $portableDir $n;$b=Join-Path $installedDir $n
    if(!(Test-Path $a)-or!(Test-Path $b)){throw "$label payload compare missing $n"}
    if((Get-FileHash $a -Algorithm SHA256).Hash-ne(Get-FileHash $b -Algorithm SHA256).Hash){throw "$label installed payload differs $n"}
  }
}
function Assert-Main([string]$exe){Add-Type -AssemblyName UIAutomationClient;Add-Type -AssemblyName UIAutomationTypes;$crash=Join-Path $env:LOCALAPPDATA 'MerzoWindowsOptimizer\logs';$at=(Get-Date).ToUniversalTime();$p=Start-Process $exe -PassThru;$found=$false;try{$d=(Get-Date).AddSeconds(25);while((Get-Date)-lt$d){$p.Refresh();if($p.HasExited){throw "R55.1 OTA app exited=$($p.ExitCode)"};$wins=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition);foreach($w in $wins){try{if($w.Current.ProcessId-ne$p.Id){continue};$n=[string]$w.Current.Name;if($n-match'(?i)startup error'){throw "R55.1 OTA startup error window: $n"};if($n-like'*Merzo Windows Optimizer — Production 0.1.55.1*R55.1*'){$found=$true}}catch{if($_.Exception.Message-like'R55.1 OTA startup error*'){throw}}};if($found){break};Start-Sleep -Milliseconds 400};if(!$found){throw 'R55.1 OTA real main window not detected'};if(Test-Path $crash){$c=Get-ChildItem $crash -File -Filter 'startup-crash-*.log' -ErrorAction SilentlyContinue|Where-Object{$_.LastWriteTimeUtc-ge$at.AddSeconds(-1)}|Select-Object -First 1;if($c){throw "R55.1 OTA created crash log $($c.FullName)"}}}finally{if(!$p.HasExited){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue}}}
try{
  if([string]::IsNullOrWhiteSpace($env:GH_TOKEN)){throw 'GH_TOKEN missing'};$repo=$env:GITHUB_REPOSITORY;if([string]::IsNullOrWhiteSpace($repo)){throw 'GITHUB_REPOSITORY missing'}

  $release=gh api "repos/$repo/releases/tags/mwo-v0.1.55.1"|ConvertFrom-Json
  if($release.tag_name-ne'mwo-v0.1.55.1'-or$release.draft-or$release.prerelease){throw 'Public R55.1 release invalid'}
  if($release.target_commitish-ne$BuildHead){throw "R55.1 target mismatch $($release.target_commitish)"}
  $asset=$release.assets|Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe'|Select-Object -First 1;$zipAsset=$release.assets|Where-Object name -eq 'MerzoWindowsOptimizer-portable-win-x64.zip'|Select-Object -First 1
  if(!$asset-or!$zipAsset){throw 'Public R55.1 assets missing'}
  $ih=$asset.digest.Substring(7).ToLowerInvariant();$ph=$zipAsset.digest.Substring(7).ToLowerInvariant();if($ih-ne$ExpectedInstallerSha.ToLowerInvariant()-or$ph-ne$ExpectedPortableSha.ToLowerInvariant()){throw 'Public R55.1 digest mismatch'}
  $status.publicRelease='success';$status.installerSha=$ih;$status.portableSha=$ph;Write-Host "R55_1_PUBLIC_RELEASE_PASS installer=$ih portable=$ph"

  # R54.2 -> public R55 installer/updater path is already independently GREEN in
  # optimizer/R55_PUBLIC_OTA_STATUS.json. Seed this clean runner from the exact
  # public R55 portable payload so this gate tests the new edge only: R55 updater
  # -> exact R55.1 download -> exact R55.1 installer -> installed public R55.1.
  $prior=Get-Content '.\optimizer\R55_PUBLIC_OTA_STATUS.json' -Raw|ConvertFrom-Json
  if($prior.conclusion-ne'success' -or $prior.r542ToR55Upgrade-ne'success' -or $prior.r55PayloadMatch-ne'success' -or $prior.r55Launch-ne'success' -or $prior.installedGameRecovery-ne'success'){throw 'Prior R54.2 -> R55 public OTA proof is not green'}
  $r55Release=gh api "repos/$repo/releases/tags/mwo-v0.1.55"|ConvertFrom-Json
  if($r55Release.tag_name-ne'mwo-v0.1.55'-or$r55Release.draft-or$r55Release.prerelease){throw 'Public R55 baseline release invalid'}
  $r55PortableAsset=$r55Release.assets|Where-Object name -eq 'MerzoWindowsOptimizer-portable-win-x64.zip'|Select-Object -First 1
  if(!$r55PortableAsset-or!$r55PortableAsset.digest){throw 'Public R55 baseline portable/digest missing'}
  $r55PortableSha=$r55PortableAsset.digest.Substring(7).ToLowerInvariant()
  if($prior.portableSha.ToLowerInvariant()-ne$r55PortableSha){throw 'Prior R55 OTA proof portable SHA differs from current public R55'}
  Remove-Item public-r55 -Recurse -Force -ErrorAction SilentlyContinue;New-Item public-r55 -ItemType Directory|Out-Null
  gh release download mwo-v0.1.55 --repo $repo --dir public-r55 --pattern 'MerzoWindowsOptimizer-portable-win-x64.zip';if($LASTEXITCODE-ne0){throw 'Could not download public R55 baseline portable'}
  $r55Zip=(Resolve-Path 'public-r55/MerzoWindowsOptimizer-portable-win-x64.zip').Path
  if((Get-FileHash $r55Zip -Algorithm SHA256).Hash.ToLowerInvariant()-ne$r55PortableSha){throw 'Downloaded public R55 baseline portable SHA mismatch'}
  $r55PortableDir=Join-Path $env:RUNNER_TEMP ('r55-baseline-'+[guid]::NewGuid().ToString('N'));Expand-Archive $r55Zip $r55PortableDir -Force
  $installDir=Join-Path $env:ProgramFiles 'Merzo Windows Optimizer';Remove-Item $installDir -Recurse -Force -ErrorAction SilentlyContinue;New-Item $installDir -ItemType Directory -Force|Out-Null;Copy-Item (Join-Path $r55PortableDir '*') $installDir -Recurse -Force
  $exe=Canonical;if(!(Test-Path $exe)){throw 'Seeded R55 baseline EXE missing'};$base=[Diagnostics.FileVersionInfo]::GetVersionInfo($exe).FileVersion;if($base-ne'0.1.55.0'){throw "Seeded R55 baseline version=$base"}
  Compare-Payload $r55PortableDir $installDir 'R55 seeded baseline'
  $status.r55Baseline='success';$status.r55BaselinePayloadMatch='success';Write-Host "R55_BASELINE_FROM_EXACT_PUBLIC_PAYLOAD_PASS version=$base portable=$r55PortableSha priorOtaRun=$($prior.databaseId)"

  $dir=Split-Path $exe -Parent;$cfg=Join-Path $dir 'data\update_settings.json';$dll=Join-Path $dir 'MerzoOptimizer.Windows.dll';$updateDir=Join-Path $env:TEMP 'MerzoWindowsOptimizer-R55-to-R551';Remove-Item $updateDir -Recurse -Force -ErrorAction SilentlyContinue
  $lines=& pwsh -NoLogo -NoProfile -File '.\optimizer\scripts\r54_1_r54_download_probe.ps1' -Dll $dll -SettingsPath $cfg -UpdateDirectory $updateDir -ExpectedVersion '0.1.55.1' 2>&1;$ec=$LASTEXITCODE;$txt=($lines|ForEach-Object{[string]$_})-join"`n";Write-Host $txt
  if($ec-ne0-or$txt-notmatch'R54_REAL_DOWNLOAD_PASS'){throw "Public R55 updater rejected R55.1 exit=$ec"}
  if($txt-notmatch'current=0\.1\.55(?:\.0)?\s+latest=0\.1\.55\.1'){throw 'R55 updater did not expose expected 0.1.55 -> 0.1.55.1 transition'}
  $downloaded=Get-ChildItem $updateDir -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe'|Select-Object -First 1;if(!$downloaded){throw 'R55 updater output missing'}
  $actual=(Get-FileHash $downloaded.FullName -Algorithm SHA256).Hash.ToLowerInvariant();if($actual-ne$ih){throw "R55 downloaded SHA=$actual"};$status.r55UpdaterDownload='success';Write-Host "R55_REAL_UPDATER_ACCEPTS_R551_PASS sha=$actual"
  Install $downloaded.FullName '/SILENT /MERZOUPDATE=1 /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
  $r551=Canonical;$fv=[Diagnostics.FileVersionInfo]::GetVersionInfo($r551).FileVersion;if($fv-ne'0.1.55.1'){throw "R55.1 OTA FileVersion=$fv"};$status.r55ToR551Upgrade='success';$status.r551FileVersion='success';$status.canonicalPath=$r551;Write-Host "R55_TO_R551_REAL_OTA_PASS version=$fv"

  Remove-Item public-r551 -Recurse -Force -ErrorAction SilentlyContinue;New-Item public-r551 -ItemType Directory|Out-Null;gh release download mwo-v0.1.55.1 --repo $repo --dir public-r551 --pattern 'MerzoWindowsOptimizer-portable-win-x64.zip';if($LASTEXITCODE-ne0){throw 'Could not download public R55.1 portable'}
  $publicZip=(Resolve-Path 'public-r551/MerzoWindowsOptimizer-portable-win-x64.zip').Path;if((Get-FileHash $publicZip -Algorithm SHA256).Hash.ToLowerInvariant()-ne$ph){throw 'Public R55.1 portable downloaded SHA mismatch'}
  $pd=Join-Path $env:RUNNER_TEMP ('r551-public-'+[guid]::NewGuid().ToString('N'));Expand-Archive $publicZip $pd -Force
  Compare-Payload $pd (Split-Path $r551 -Parent) 'R55.1 OTA'
  $status.r551PayloadMatch='success';Write-Host 'R55_1_PUBLIC_OTA_PAYLOAD_MATCH_PASS';Assert-Main $r551;$status.r551Launch='success';Write-Host 'R55_1_PUBLIC_OTA_REAL_MAIN_WINDOW_PASS'

  $installedArtifact=Join-Path $env:RUNNER_TEMP ('r551-installed-game-'+[guid]::NewGuid().ToString('N'));New-Item $installedArtifact -ItemType Directory|Out-Null;$iz=Join-Path $installedArtifact 'MerzoWindowsOptimizer-portable-win-x64.zip';Compress-Archive -Path (Join-Path (Split-Path $r551 -Parent) '*') -DestinationPath $iz -CompressionLevel Fastest -Force;$izh=(Get-FileHash $iz -Algorithm SHA256).Hash.ToLowerInvariant();Set-Content (Join-Path $installedArtifact 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256') ($izh+'  MerzoWindowsOptimizer-portable-win-x64.zip') -Encoding ASCII
  & '.\optimizer\scripts\r55_1_game_recovery_acceptance.ps1' -ArtifactDir $installedArtifact -BuildRun $BuildRun -BuildHead $BuildHead -ExpectedPortableSha $izh;if($LASTEXITCODE-ne0){throw 'Installed public R55.1 GAME/Recovery failed'};$status.installedGameRecovery='success';Write-Host 'R55_1_INSTALLED_PUBLIC_GAME_RECOVERY_PASS'
  $status.conclusion='success';Save;Write-Host 'R55_TO_R551_PUBLIC_OTA_ACCEPTANCE_PASS'
}catch{$status.error=$_.Exception.Message;try{Save}catch{};Write-Host "::error::$($_.Exception.Message)";exit 1}
