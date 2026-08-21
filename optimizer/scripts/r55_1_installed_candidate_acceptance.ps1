param(
  [Parameter(Mandatory=$true)][string]$ArtifactDir,
  [Parameter(Mandatory=$true)][long]$BuildRun,
  [Parameter(Mandatory=$true)][string]$BuildHead,
  [Parameter(Mandatory=$true)][string]$ExpectedInstallerSha,
  [Parameter(Mandatory=$true)][string]$ExpectedPortableSha
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Stop-App{Get-Process MerzoWindowsOptimizer -ErrorAction SilentlyContinue|Stop-Process -Force -ErrorAction SilentlyContinue}
function Install([string]$setup){
  Stop-App;$p=Start-Process $setup -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-' -PassThru
  $d=(Get-Date).AddMinutes(4);while(!$p.HasExited-and(Get-Date)-lt$d){Stop-App;Start-Sleep -Milliseconds 600;$p.Refresh()}
  if(!$p.HasExited){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue;throw 'R55.1 installer timeout'}
  if($p.ExitCode-ne0){throw "R55.1 installer exit=$($p.ExitCode)"}
  $d=(Get-Date).AddSeconds(60);while((Get-Date)-lt$d){Stop-App;$c=Get-Process -ErrorAction SilentlyContinue|Where-Object{$_.ProcessName-like'MerzoWindowsOptimizerSetup*'};if(!$c){break};Start-Sleep -Milliseconds 500}
  if(Get-Process -ErrorAction SilentlyContinue|Where-Object{$_.ProcessName-like'MerzoWindowsOptimizerSetup*'}){throw 'R55.1 installer child did not finish'}
  Stop-App
}
function Assert-RealMainWindow([string]$exe){
  Add-Type -AssemblyName UIAutomationClient;Add-Type -AssemblyName UIAutomationTypes
  $crashDir=Join-Path $env:LOCALAPPDATA 'MerzoWindowsOptimizer\logs';$launchAt=(Get-Date).ToUniversalTime();$p=Start-Process $exe -PassThru;$found=$false
  try{
    $d=(Get-Date).AddSeconds(25)
    while((Get-Date)-lt$d){
      $p.Refresh();if($p.HasExited){throw "R55.1 installed app exited=$($p.ExitCode)"}
      $wins=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
      foreach($w in $wins){try{if($w.Current.ProcessId-ne$p.Id){continue};$n=[string]$w.Current.Name;if($n-match'(?i)startup error'){throw "R55.1 startup error window: $n"};if($n-like'*Merzo Windows Optimizer — Production 0.1.55.1*R55.1*'){$found=$true}}catch{if($_.Exception.Message-like'R55.1 startup error*'){throw}}}
      if($found){break};Start-Sleep -Milliseconds 400
    }
    if(!$found){throw 'R55.1 installed Production main window not detected'}
    if(Test-Path $crashDir){$c=Get-ChildItem $crashDir -File -Filter 'startup-crash-*.log' -ErrorAction SilentlyContinue|Where-Object{$_.LastWriteTimeUtc-ge$launchAt.AddSeconds(-1)}|Select-Object -First 1;if($c){throw "R55.1 installed launch created crash log: $($c.FullName)"}}
  }finally{if(!$p.HasExited){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue}}
}
$artifact=(Resolve-Path $ArtifactDir).Path
$installer=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe'|Select-Object -First 1
$side=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256'|Select-Object -First 1
$zip=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip'|Select-Object -First 1
$zipSide=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256'|Select-Object -First 1
if(!$installer-or!$side-or!$zip-or!$zipSide){throw 'R55.1 installed acceptance artifact incomplete'}
$ih=(Get-FileHash $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant();$ph=(Get-FileHash $zip.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
if($ih-ne$ExpectedInstallerSha.ToLowerInvariant()){throw "R55.1 installer SHA=$ih"};if($ph-ne$ExpectedPortableSha.ToLowerInvariant()){throw "R55.1 portable SHA=$ph"}
if(((Get-Content $side.FullName -Raw)-split'\s+')[0].ToLowerInvariant()-ne$ih){throw 'R55.1 installer sidecar mismatch'}
if(((Get-Content $zipSide.FullName -Raw)-split'\s+')[0].ToLowerInvariant()-ne$ph){throw 'R55.1 portable sidecar mismatch'}
Install $installer.FullName
$canonical=Join-Path $env:ProgramFiles 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe';if(!(Test-Path $canonical)){throw 'R55.1 canonical EXE missing'}
$fv=[Diagnostics.FileVersionInfo]::GetVersionInfo($canonical).FileVersion;if($fv-ne'0.1.55.1'){throw "R55.1 installed FileVersion=$fv"}
$portableDir=Join-Path $env:RUNNER_TEMP ('r551-installed-'+[guid]::NewGuid().ToString('N'));Expand-Archive $zip.FullName $portableDir -Force
foreach($n in @('MerzoWindowsOptimizer.exe','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.exe')){$a=Join-Path $portableDir $n;$b=Join-Path (Split-Path $canonical -Parent) $n;if(!(Test-Path $a)-or!(Test-Path $b)){throw "R55.1 payload missing $n"};if((Get-FileHash $a -Algorithm SHA256).Hash-ne(Get-FileHash $b -Algorithm SHA256).Hash){throw "R55.1 installed payload differs: $n"}}
Write-Host 'R55_1_INSTALLER_PORTABLE_PAYLOAD_MATCH_PASS'
Assert-RealMainWindow $canonical
Write-Host 'R55_1_INSTALLED_REAL_MAIN_WINDOW_PASS'
$entries=@(Get-ItemProperty 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue;Get-ItemProperty 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue;Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*' -ErrorAction SilentlyContinue)
$entry=$entries|Where-Object{$p=$_.PSObject.Properties['DisplayName'];$p-and[string]$p.Value-like'*Merzo*Optimizer*'}|Select-Object -First 1
if(!$entry){throw 'R55.1 uninstall registration missing'}
[ordered]@{conclusion='success';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]$env:GITHUB_RUN_ID;headSha=$env:GITHUB_SHA;buildRun=$BuildRun;buildHead=$BuildHead;installerSha=$ih;portableSha=$ph;installedVersion=$fv;canonicalPath=$canonical;payloadMatch='success';launch='real-main-window-success';uninstallRegistration='success'}|ConvertTo-Json|Set-Content '.\optimizer\R55_1_INSTALLED_CANDIDATE_STATUS.json' -Encoding UTF8
Write-Host 'R55_1_INSTALLED_CANDIDATE_ACCEPTANCE_PASS'
