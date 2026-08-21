param(
  [Parameter(Mandatory=$true)][string]$ArtifactDir,
  [Parameter(Mandatory=$true)][long]$BuildRun,
  [Parameter(Mandatory=$true)][string]$BuildHead,
  [Parameter(Mandatory=$true)][string]$ExpectedInstallerSha,
  [Parameter(Mandatory=$true)][string]$ExpectedPortableSha
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Stop-MerzoApp { Get-Process MerzoWindowsOptimizer -ErrorAction SilentlyContinue|Stop-Process -Force -ErrorAction SilentlyContinue }
$artifact=(Resolve-Path $ArtifactDir).Path
$installer=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe'|Select-Object -First 1
$side=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256'|Select-Object -First 1
$zip=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip'|Select-Object -First 1
$zipSide=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256'|Select-Object -First 1
if(!$installer-or!$side-or!$zip-or!$zipSide){throw 'R56 installed candidate artifact incomplete'}
$installerSha=(Get-FileHash $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant();$portableSha=(Get-FileHash $zip.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$declared=((Get-Content $side.FullName -Raw)-split '\s+')[0].ToLowerInvariant();$portableDeclared=((Get-Content $zipSide.FullName -Raw)-split '\s+')[0].ToLowerInvariant()
if($installerSha-ne$declared-or$installerSha-ne$ExpectedInstallerSha.ToLowerInvariant()){throw "R56 installer SHA mismatch $installerSha"}
if($portableSha-ne$portableDeclared-or$portableSha-ne$ExpectedPortableSha.ToLowerInvariant()){throw "R56 portable SHA mismatch $portableSha"}
Write-Host "R56_INSTALL_ARTIFACT_SHA_PASS installer=$installerSha portable=$portableSha"

Stop-MerzoApp
$log=Join-Path $env:RUNNER_TEMP 'r56-installed-inno.log'
$args="/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /LOG=`"$log`""
$p=Start-Process $installer.FullName -ArgumentList $args -PassThru
$deadline=(Get-Date).AddMinutes(4)
while(!$p.HasExited-and(Get-Date)-lt$deadline){Start-Sleep -Milliseconds 600;$p.Refresh()}
if(!$p.HasExited){if(Test-Path $log){Get-Content $log -Tail 120|ForEach-Object{Write-Host $_}};Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue;throw 'R56 installer timeout'}
if($p.ExitCode-ne0){if(Test-Path $log){Get-Content $log -Tail 120|ForEach-Object{Write-Host $_}};throw "R56 installer exit=$($p.ExitCode)"}
$childDeadline=(Get-Date).AddSeconds(60)
while((Get-Date)-lt$childDeadline){$children=Get-Process -ErrorAction SilentlyContinue|Where-Object{$_.ProcessName-like'MerzoWindowsOptimizerSetup*'};if(!$children){break};Start-Sleep -Milliseconds 500}
if(Get-Process -ErrorAction SilentlyContinue|Where-Object{$_.ProcessName-like'MerzoWindowsOptimizerSetup*'}){throw 'R56 installer child did not finish'}
Stop-MerzoApp

$canonical=Join-Path $env:ProgramFiles 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'
if(!(Test-Path $canonical)){throw "R56 canonical installed EXE missing: $canonical"}
$fv=[Diagnostics.FileVersionInfo]::GetVersionInfo($canonical).FileVersion;if($fv-ne'0.1.56.0'){throw "R56 installed FileVersion=$fv"}
$portableDir=Join-Path $env:RUNNER_TEMP ('r56-installed-compare-'+[guid]::NewGuid().ToString('N'));Expand-Archive $zip.FullName $portableDir -Force
foreach($name in @('MerzoWindowsOptimizer.exe','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.exe')){
  $a=Join-Path $portableDir $name;$b=Join-Path (Split-Path $canonical -Parent) $name
  if(!(Test-Path $a)-or!(Test-Path $b)){throw "R56 payload compare missing $name"}
  if((Get-FileHash $a -Algorithm SHA256).Hash-ne(Get-FileHash $b -Algorithm SHA256).Hash){throw "R56 installed payload differs from portable: $name"}
}
Write-Host 'R56_INSTALLER_PORTABLE_PAYLOAD_MATCH_PASS'

Add-Type -AssemblyName UIAutomationClient;Add-Type -AssemblyName UIAutomationTypes
$crashDir=Join-Path $env:LOCALAPPDATA 'MerzoWindowsOptimizer\logs';$launchAt=(Get-Date).ToUniversalTime();$app=Start-Process $canonical -WorkingDirectory (Split-Path $canonical -Parent) -PassThru;$mainFound=$false;$startupError=''
try{
  $d=(Get-Date).AddSeconds(25)
  while((Get-Date)-lt$d){
    $app.Refresh();if($app.HasExited){throw "R56 installed app exited=$($app.ExitCode)"}
    $wins=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
    foreach($w in $wins){try{if($w.Current.ProcessId-ne$app.Id){continue};$n=[string]$w.Current.Name;if($n-match'(?i)startup error'){$startupError=$n};if($n-like'*Merzo Windows Optimizer — Production 0.1.56*R56*'){$mainFound=$true}}catch{}}
    if($startupError){throw "R56 installed startup error window: $startupError"};if($mainFound){break};Start-Sleep -Milliseconds 400
  }
  if(!$mainFound){throw 'R56 installed real main window not detected'}
  if(Test-Path $crashDir){$c=Get-ChildItem $crashDir -File -Filter 'startup-crash-*.log' -ErrorAction SilentlyContinue|Where-Object{$_.LastWriteTimeUtc-ge$launchAt.AddSeconds(-1)}|Select-Object -First 1;if($c){throw "R56 installed startup crash log: $($c.FullName)"}}
}finally{if(!$app.HasExited){Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue}}
Write-Host "R56_INSTALLED_REAL_MAIN_WINDOW_PASS path=$canonical version=$fv"

$entries=@(
 Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue
 Get-ItemProperty 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue
 Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue
)
$entry=$entries|Where-Object{$q=$_.PSObject.Properties['DisplayName'];$q-and[string]$q.Value-like'*Merzo*Optimizer*'}|Sort-Object{$q=$_.PSObject.Properties['DisplayVersion'];if($q){[string]$q.Value}else{''}} -Descending|Select-Object -First 1
if(!$entry){throw 'R56 uninstall registration missing'}
$displayName=[string]$entry.PSObject.Properties['DisplayName'].Value;$vp=$entry.PSObject.Properties['DisplayVersion'];$displayVersion=if($vp){[string]$vp.Value}else{''}
if(-not[string]::IsNullOrWhiteSpace($displayVersion)-and$displayVersion-notlike'0.1.56*'){throw "R56 uninstall DisplayVersion=$displayVersion"}
Write-Host "R56_UNINSTALL_REGISTRATION_PASS name=$displayName version=$displayVersion"

[ordered]@{conclusion='success';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]$env:GITHUB_RUN_ID;headSha=$env:GITHUB_SHA;buildRun=$BuildRun;buildHead=$BuildHead;installerSha=$installerSha;portableSha=$portableSha;installedVersion=$fv;canonicalPath=$canonical;payloadMatch='success';launch='real-main-window-success';uninstallRegistration='success';uninstallDisplayName=$displayName;uninstallDisplayVersion=$displayVersion}|ConvertTo-Json|Set-Content '.\optimizer\R56_INSTALLED_CANDIDATE_STATUS.json' -Encoding UTF8
Write-Host 'R56_INSTALLED_CANDIDATE_ACCEPTANCE_PASS'
