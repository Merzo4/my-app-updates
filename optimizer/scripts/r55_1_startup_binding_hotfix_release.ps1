$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$baseline='.\optimizer\scripts\r54_2_onedrive_game_reliability_release.ps1'
if(!(Test-Path $baseline)){throw 'R55.1 exact R54.2 baseline controller missing'}
& $baseline
if($LASTEXITCODE-ne0){throw "R55.1 exact R54.2 baseline failed: $LASTEXITCODE"}
if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R55.1 SOURCE_ROOT missing after R54.2 baseline'}
$root=$env:SOURCE_ROOT

foreach($patch in @('r55_process_stability.py','r55_compile_fix.py','r55_version_finalize.py','r55_1_startup_binding_hotfix.py')){
  python (Join-Path $PWD "optimizer\patches\$patch")
  if($LASTEXITCODE-ne0){throw "R55.1 patch failed: $patch"}
}

$xaml=Join-Path $root 'src\MerzoOptimizer.App\MainWindow.xaml'
$vm=Join-Path $root 'src\MerzoOptimizer.App\ViewModels\MainWindowViewModel.cs'
$x=Get-Content $xaml -Raw
$v=Get-Content $vm -Raw
if(-not$x.Contains('Value="{Binding ProcessStabilityProgress, Mode=OneWay}"')){throw 'R55.1 OneWay progress binding missing'}
if($x.Contains('Value="{Binding ProcessStabilityProgress}"')){throw 'R55.1 unsafe progress binding still present'}
if(-not$v.Contains('public double ProcessStabilityProgress')){throw 'R55.1 VM progress property missing'}
if(-not$x.Contains('Production R55.1 · 0.1.55.1')){throw 'R55.1 visible identity missing'}
if(-not$x.Contains('Production 0.1.55.1 · R55.1 STARTUP BINDING HOTFIX')){throw 'R55.1 window title identity missing'}
try{[xml]$x|Out-Null}catch{throw "R55.1 malformed XAML: $($_.Exception.Message)"}
Write-Host 'R55_1_XAML_ONEWAY_CONTRACT_PASS'

Push-Location $root
try{
  & .\build\Build-Production.ps1 -Version '0.1.55.1' -SkipObfuscation
  if($LASTEXITCODE-ne0){throw 'R55.1 Production build failed'}
  dotnet run --project .\src\MerzoOptimizer.SelfTest\MerzoOptimizer.SelfTest.csproj -c Release
  if($LASTEXITCODE-ne0){throw 'R55.1 SelfTest failed'}
}finally{Pop-Location}

$dist=Join-Path $root 'dist\app'
foreach($n in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){
  $p=Join-Path $dist $n
  if(!(Test-Path $p)){throw "R55.1 missing $n"}
  $version=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString()
  if($version-ne'0.1.55.1'){throw "R55.1 $n version=$version"}
}
Write-Host 'R55_1_ASSEMBLY_IDENTITY_PASS'

# Strong startup acceptance. A startup-error dialog keeps the process alive, so
# process-alive alone is explicitly NOT sufficient.
$exe=Join-Path $dist 'MerzoWindowsOptimizer.exe'
if(!(Test-Path $exe)){throw 'R55.1 finished EXE missing'}
$crashDir=Join-Path $env:LOCALAPPDATA 'MerzoWindowsOptimizer\logs'
$launchAt=(Get-Date).ToUniversalTime()
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$proc=Start-Process $exe -WorkingDirectory $dist -PassThru
$mainFound=$false
$errorWindow=''
try{
  $deadline=(Get-Date).AddSeconds(25)
  while((Get-Date)-lt$deadline){
    $proc.Refresh()
    if($proc.HasExited){throw "R55.1 finished EXE exited $($proc.ExitCode)"}
    $windows=[System.Windows.Automation.AutomationElement]::RootElement.FindAll(
      [System.Windows.Automation.TreeScope]::Children,
      [System.Windows.Automation.Condition]::TrueCondition)
    foreach($w in $windows){
      try{
        if($w.Current.ProcessId-ne$proc.Id){continue}
        $name=[string]$w.Current.Name
        if($name -match '(?i)startup error'){ $errorWindow=$name }
        if($name -like '*Merzo Windows Optimizer — Production 0.1.55.1*R55.1*'){ $mainFound=$true }
      }catch{}
    }
    if($errorWindow){throw "R55.1 startup error window detected: $errorWindow"}
    if($mainFound){break}
    Start-Sleep -Milliseconds 400
  }
  if(!$mainFound){throw 'R55.1 real Production main window was not detected'}
  if(Test-Path $crashDir){
    $newCrash=Get-ChildItem $crashDir -File -Filter 'startup-crash-*.log' -ErrorAction SilentlyContinue | Where-Object {$_.LastWriteTimeUtc -ge $launchAt.AddSeconds(-1)} | Select-Object -First 1
    if($newCrash){throw "R55.1 created startup crash log: $($newCrash.FullName)"}
  }
  Write-Host 'R55_1_REAL_MAIN_WINDOW_LAUNCH_PASS'
}finally{
  if(!$proc.HasExited){Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue}
}

$zip=Join-Path $root 'dist\MerzoWindowsOptimizer-portable-win-x64.zip'
if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path (Join-Path $dist '*') -DestinationPath $zip -CompressionLevel Optimal
$iscc=@('C:\Program Files (x86)\Inno Setup 6\ISCC.exe','C:\Program Files\Inno Setup 6\ISCC.exe')|Where-Object{Test-Path $_}|Select-Object -First 1
if(!$iscc){throw 'R55.1 ISCC missing'}
Push-Location $root
try{
  & $iscc '/DMyAppVersion=0.1.55.1' '.\installer\MerzoWindowsOptimizer.iss'
  if($LASTEXITCODE-ne0){throw 'R55.1 installer build failed'}
}finally{Pop-Location}
$installer=Join-Path $root 'dist\MerzoWindowsOptimizerSetup-win-x64.exe'
if(!(Test-Path $installer)){throw 'R55.1 installer missing'}
$ih=(Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant()
$zh=(Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$ih  MerzoWindowsOptimizerSetup-win-x64.exe"|Set-Content "$installer.sha256" -Encoding ascii
"$zh  MerzoWindowsOptimizer-portable-win-x64.zip"|Set-Content "$zip.sha256" -Encoding ascii
"R55_1_ROOT=$root" >> $env:GITHUB_ENV
"SOURCE_ROOT=$root" >> $env:GITHUB_ENV
"R55_1_INSTALLER_SHA=$ih" >> $env:GITHUB_ENV
"R55_1_PORTABLE_SHA=$zh" >> $env:GITHUB_ENV
Write-Host 'R55_1_ALL_BUILD_GATES_PASS'
Write-Host "R55_1_INSTALLER_SHA256=$ih"
Write-Host "R55_1_PORTABLE_SHA256=$zh"
