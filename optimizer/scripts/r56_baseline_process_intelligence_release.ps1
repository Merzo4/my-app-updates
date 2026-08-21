$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

# Recreate the exact R55.1 product source through the already-proven production
# controller, then apply only the diagnostic R56 delta. The intermediate R55.1
# package is discarded/overwritten; R56 itself is built once after the patch.
$baseline='.\optimizer\scripts\r55_1_startup_binding_hotfix_release.ps1'
if(!(Test-Path $baseline)){throw 'R56 exact R55.1 baseline controller missing'}
& $baseline
if($LASTEXITCODE-ne0){throw "R56 exact R55.1 baseline failed: $LASTEXITCODE"}
if([string]::IsNullOrWhiteSpace($env:R55_1_ROOT)){throw 'R56 R55_1_ROOT missing after exact baseline'}
$root=$env:R55_1_ROOT
$env:SOURCE_ROOT=$root

python (Join-Path $PWD 'optimizer\patches\r56_baseline_process_intelligence.py')
if($LASTEXITCODE-ne0){throw 'R56 patch failed'}

& .\optimizer\scripts\r56_baseline_process_intelligence_acceptance.ps1 -SourceRoot $root
if($LASTEXITCODE-ne0){throw 'R56 baseline intelligence acceptance failed'}

$xaml=Join-Path $root 'src\MerzoOptimizer.App\MainWindow.xaml'
$vm=Join-Path $root 'src\MerzoOptimizer.App\ViewModels\MainWindowViewModel.cs'
$x=Get-Content $xaml -Raw;$v=Get-Content $vm -Raw
if(-not$x.Contains('Value="{Binding ProcessStabilityProgress, Mode=OneWay}"')){throw 'R56 lost R55.1 OneWay startup fix'}
if($x.Contains('Value="{Binding ProcessStabilityProgress}"')){throw 'R56 unsafe progress binding returned'}
if(-not$x.Contains('Production R56 · 0.1.56')){throw 'R56 visible identity missing'}
if(-not$v.Contains('ProcessStabilityFinalRows')){throw 'R56 final background collection missing'}
try{[xml]$x|Out-Null}catch{throw "R56 malformed XAML: $($_.Exception.Message)"}
Write-Host 'R56_PREBUILD_CONTRACT_PASS'

Push-Location $root
try {
  & .\build\Build-Production.ps1 -Version '0.1.56' -SkipObfuscation
  if($LASTEXITCODE-ne0){throw 'R56 Production build failed'}
  dotnet run --project .\src\MerzoOptimizer.SelfTest\MerzoOptimizer.SelfTest.csproj -c Release
  if($LASTEXITCODE-ne0){throw 'R56 SelfTest failed'}
} finally { Pop-Location }

$dist=Join-Path $root 'dist\app'
foreach($n in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){
  $p=Join-Path $dist $n
  if(!(Test-Path $p)){throw "R56 missing $n"}
  $version=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString()
  if($version-ne'0.1.56.0'){throw "R56 $n version=$version"}
}
Write-Host 'R56_ASSEMBLY_IDENTITY_PASS'

# Strong startup gate inherited from R55.1: process-alive alone is NOT enough.
$exe=Join-Path $dist 'MerzoWindowsOptimizer.exe'
if(!(Test-Path $exe)){throw 'R56 finished EXE missing'}
$crashDir=Join-Path $env:LOCALAPPDATA 'MerzoWindowsOptimizer\logs'
$launchAt=(Get-Date).ToUniversalTime()
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$proc=Start-Process $exe -WorkingDirectory $dist -PassThru
$mainFound=$false;$errorWindow=''
try {
  $deadline=(Get-Date).AddSeconds(25)
  while((Get-Date)-lt$deadline){
    $proc.Refresh();if($proc.HasExited){throw "R56 finished EXE exited $($proc.ExitCode)"}
    $windows=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
    foreach($w in $windows){try{if($w.Current.ProcessId-ne$proc.Id){continue};$name=[string]$w.Current.Name;if($name-match'(?i)startup error'){$errorWindow=$name};if($name-like'*Merzo Windows Optimizer — Production 0.1.56*R56*'){$mainFound=$true}}catch{}}
    if($errorWindow){throw "R56 startup error window detected: $errorWindow"}
    if($mainFound){break};Start-Sleep -Milliseconds 400
  }
  if(!$mainFound){throw 'R56 real Production main window was not detected'}
  if(Test-Path $crashDir){$newCrash=Get-ChildItem $crashDir -File -Filter 'startup-crash-*.log' -ErrorAction SilentlyContinue|Where-Object{$_.LastWriteTimeUtc-ge$launchAt.AddSeconds(-1)}|Select-Object -First 1;if($newCrash){throw "R56 created startup crash log: $($newCrash.FullName)"}}
  Write-Host 'R56_REAL_MAIN_WINDOW_LAUNCH_PASS'
} finally {if(!$proc.HasExited){Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue}}

$zip=Join-Path $root 'dist\MerzoWindowsOptimizer-portable-win-x64.zip'
if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path (Join-Path $dist '*') -DestinationPath $zip -CompressionLevel Optimal
$iscc=@('C:\Program Files (x86)\Inno Setup 6\ISCC.exe','C:\Program Files\Inno Setup 6\ISCC.exe')|Where-Object{Test-Path $_}|Select-Object -First 1
if(!$iscc){throw 'R56 ISCC missing'}
Push-Location $root
try {& $iscc '/DMyAppVersion=0.1.56' '.\installer\MerzoWindowsOptimizer.iss';if($LASTEXITCODE-ne0){throw 'R56 installer build failed'}} finally {Pop-Location}
$installer=Join-Path $root 'dist\MerzoWindowsOptimizerSetup-win-x64.exe'
if(!(Test-Path $installer)){throw 'R56 installer missing'}
$ih=(Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant();$zh=(Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$ih  MerzoWindowsOptimizerSetup-win-x64.exe"|Set-Content "$installer.sha256" -Encoding ascii
"$zh  MerzoWindowsOptimizer-portable-win-x64.zip"|Set-Content "$zip.sha256" -Encoding ascii
"R56_ROOT=$root" >> $env:GITHUB_ENV
"SOURCE_ROOT=$root" >> $env:GITHUB_ENV
"R56_INSTALLER_SHA=$ih" >> $env:GITHUB_ENV
"R56_PORTABLE_SHA=$zh" >> $env:GITHUB_ENV
Write-Host 'R56_ALL_BUILD_GATES_PASS'
Write-Host "R56_INSTALLER_SHA256=$ih"
Write-Host "R56_PORTABLE_SHA256=$zh"
