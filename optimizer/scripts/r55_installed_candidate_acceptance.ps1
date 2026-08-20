param(
  [Parameter(Mandatory=$true)][string]$ArtifactDir,
  [Parameter(Mandatory=$true)][long]$BuildRun,
  [Parameter(Mandatory=$true)][string]$BuildHead
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Stop-MerzoApp {
  Get-Process MerzoWindowsOptimizer -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}
function Invoke-MerzoInstaller([string]$Setup) {
  Stop-MerzoApp
  $p=Start-Process $Setup -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-' -PassThru
  $deadline=(Get-Date).AddMinutes(4)
  while(!$p.HasExited -and (Get-Date)-lt$deadline){Stop-MerzoApp;Start-Sleep -Milliseconds 600;$p.Refresh()}
  if(!$p.HasExited){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue;throw 'R55 installer timeout'}
  if($p.ExitCode-ne0){throw "R55 installer exit=$($p.ExitCode)"}
  $childDeadline=(Get-Date).AddSeconds(60)
  while((Get-Date)-lt$childDeadline){
    Stop-MerzoApp
    $children=Get-Process -ErrorAction SilentlyContinue | Where-Object {$_.ProcessName -like 'MerzoWindowsOptimizerSetup*'}
    if(!$children){break}
    Start-Sleep -Milliseconds 500
  }
  if(Get-Process -ErrorAction SilentlyContinue | Where-Object {$_.ProcessName -like 'MerzoWindowsOptimizerSetup*'}){throw 'R55 installer child process did not finish'}
  Stop-MerzoApp
}

$artifact=(Resolve-Path $ArtifactDir).Path
$installer=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
$side=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256' | Select-Object -First 1
$zip=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip' | Select-Object -First 1
$zipSide=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256' | Select-Object -First 1
if(!$installer -or !$side -or !$zip -or !$zipSide){throw 'R55 installed acceptance artifact incomplete'}
$installerSha=(Get-FileHash $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$declared=((Get-Content $side.FullName -Raw)-split '\s+')[0].ToLowerInvariant()
if($installerSha-ne$declared){throw "R55 installer sidecar mismatch $installerSha != $declared"}
$portableSha=(Get-FileHash $zip.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$portableDeclared=((Get-Content $zipSide.FullName -Raw)-split '\s+')[0].ToLowerInvariant()
if($portableSha-ne$portableDeclared){throw 'R55 portable sidecar mismatch'}
Write-Host "R55_INSTALL_ARTIFACT_SHA_PASS installer=$installerSha portable=$portableSha"

Invoke-MerzoInstaller $installer.FullName
$canonical=Join-Path $env:ProgramFiles 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'
if(!(Test-Path $canonical)){throw "R55 canonical installed EXE missing: $canonical"}
$fv=[Diagnostics.FileVersionInfo]::GetVersionInfo($canonical).FileVersion
if($fv-ne'0.1.55.0'){throw "R55 installed FileVersion=$fv"}

# Installer and portable must deploy the exact same application payload.
$portableDir=Join-Path $env:RUNNER_TEMP ('r55-installed-compare-'+[guid]::NewGuid().ToString('N'))
Expand-Archive $zip.FullName $portableDir -Force
foreach($name in @('MerzoWindowsOptimizer.exe','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.exe')){
  $a=Join-Path $portableDir $name
  $b=Join-Path (Split-Path $canonical -Parent) $name
  if(!(Test-Path $a) -or !(Test-Path $b)){throw "R55 payload compare missing $name"}
  $ha=(Get-FileHash $a -Algorithm SHA256).Hash
  $hb=(Get-FileHash $b -Algorithm SHA256).Hash
  if($ha-ne$hb){throw "R55 installed payload differs from portable: $name"}
}
Write-Host 'R55_INSTALLER_PORTABLE_PAYLOAD_MATCH_PASS'

$app=Start-Process $canonical -PassThru
Start-Sleep -Seconds 8
$app.Refresh()
if($app.HasExited){throw "R55 installed application exited during launch: $($app.ExitCode)"}
Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue
Write-Host "R55_INSTALLED_LAUNCH_PASS path=$canonical version=$fv"

# Some Windows uninstall registry children legitimately have no DisplayName or
# DisplayVersion. Under StrictMode, direct property access on those objects is
# an exception, so inspect PSObject.Properties explicitly instead of weakening
# StrictMode or hiding the registry validation.
$entries=@(
  Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue
  Get-ItemProperty 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue
  Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue
)
$entry=$entries | Where-Object {
  $p=$_.PSObject.Properties['DisplayName']
  $p -and [string]$p.Value -like '*Merzo*Optimizer*'
} | Sort-Object {
  $p=$_.PSObject.Properties['DisplayVersion']
  if($p){[string]$p.Value}else{''}
} -Descending | Select-Object -First 1
if(!$entry){throw 'R55 uninstall registration missing'}
$displayName=[string]$entry.PSObject.Properties['DisplayName'].Value
$displayVersionProp=$entry.PSObject.Properties['DisplayVersion']
$displayVersion=if($displayVersionProp){[string]$displayVersionProp.Value}else{''}
if([string]::IsNullOrWhiteSpace($displayName)){throw 'R55 uninstall DisplayName empty'}
if(-not[string]::IsNullOrWhiteSpace($displayVersion) -and $displayVersion-notlike '0.1.55*'){throw "R55 uninstall DisplayVersion=$displayVersion"}
Write-Host "R55_UNINSTALL_REGISTRATION_PASS name=$displayName version=$displayVersion"

[ordered]@{
  conclusion='success'
  createdAt=(Get-Date).ToUniversalTime().ToString('o')
  databaseId=[long]$env:GITHUB_RUN_ID
  headSha=$env:GITHUB_SHA
  buildRun=$BuildRun
  buildHead=$BuildHead
  installerSha=$installerSha
  portableSha=$portableSha
  installedVersion=$fv
  canonicalPath=$canonical
  payloadMatch='success'
  launch='success'
  uninstallRegistration='success'
  uninstallDisplayName=$displayName
  uninstallDisplayVersion=$displayVersion
} | ConvertTo-Json | Set-Content '.\optimizer\R55_INSTALLED_CANDIDATE_STATUS.json' -Encoding UTF8
Write-Host 'R55_INSTALLED_CANDIDATE_ACCEPTANCE_PASS'
