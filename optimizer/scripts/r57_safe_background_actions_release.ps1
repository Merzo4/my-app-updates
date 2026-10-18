$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

# R57 is intentionally built on the exact cumulative R56 controller. This
# recreates the proven R55.1 -> R56 source tree first, then adds only the
# diagnostic-to-reviewed-tweak bridge introduced by R57.
$baseline='.\optimizer\scripts\r56_baseline_process_intelligence_release.ps1'
if(!(Test-Path $baseline)){throw 'R57 R56 baseline controller missing'}
& $baseline
if($LASTEXITCODE-ne0){throw "R57 R56 baseline failed: $LASTEXITCODE"}

$root=(Resolve-Path '.\r49').Path
$xaml=Join-Path $root 'src\MerzoOptimizer.App\MainWindow.xaml'
$vm=Join-Path $root 'src\MerzoOptimizer.App\ViewModels\MainWindowViewModel.cs'
$models=Join-Path $root 'src\MerzoOptimizer.Core\Audit\ProcessStabilityModels.cs'
$analyzer=Join-Path $root 'src\MerzoOptimizer.Windows\Processes\WindowsProcessStabilityAnalyzer.cs'
foreach($p in @($xaml,$vm,$models,$analyzer)){
  if(!(Test-Path $p)){throw "R57 generated R56 baseline file missing: $p"}
}
$x=Get-Content $xaml -Raw
$v=Get-Content $vm -Raw
if(-not$x.Contains('Production R56 · 0.1.56')){throw 'R57 generated root is not the proven R56 source identity'}
if(-not$x.Contains('Value="{Binding ProcessStabilityProgress, Mode=OneWay}"')){throw 'R57 baseline lost R55.1 OneWay startup fix'}
if(-not$v.Contains('ProcessStabilityFinalRows')){throw 'R57 baseline lost R56 permanent-background collection'}
$env:SOURCE_ROOT=$root
Write-Host "R57_R56_BASELINE_ROOT_PASS root=$root"

python (Join-Path $PWD 'optimizer\patches\r57_safe_background_actions.py')
if($LASTEXITCODE-ne0){throw 'R57 patch failed'}

& .\optimizer\scripts\r57_safe_background_actions_acceptance.ps1 -SourceRoot $root
if($LASTEXITCODE-ne0){throw 'R57 safe background actions acceptance failed'}

$x=Get-Content $xaml -Raw
$v=Get-Content $vm -Raw
$m=Get-Content $models -Raw
$a=Get-Content $analyzer -Raw
if(-not$x.Contains('Production R57 · 0.1.57')){throw 'R57 visible identity missing'}
if(-not$x.Contains('Production 0.1.57 · R57 SAFE BACKGROUND ACTIONS')){throw 'R57 window identity missing'}
if(-not$x.Contains('Value="{Binding ProcessStabilityProgress, Mode=OneWay}"')){throw 'R57 lost R55.1 OneWay startup fix'}
if($x.Contains('Value="{Binding ProcessStabilityProgress}"')){throw 'R57 unsafe progress binding returned'}
if(-not$v.Contains('PrepareDetectedSafeBackgroundActionsCommand')){throw 'R57 safe action command missing'}
if(-not$m.Contains('IReadOnlyList<string> SafeTweakIds')){throw 'R57 safe action model mapping missing'}
if(-not$a.Contains('ResolveSafeManagement')){throw 'R57 safe management resolver missing'}
try{[xml]$x|Out-Null}catch{throw "R57 malformed XAML: $($_.Exception.Message)"}
Write-Host 'R57_PREBUILD_CONTRACT_PASS'

Push-Location $root
try {
  & .\build\Build-Production.ps1 -Version '0.1.57' -SkipObfuscation
  if($LASTEXITCODE-ne0){throw 'R57 Production build failed'}
  dotnet run --project .\src\MerzoOptimizer.SelfTest\MerzoOptimizer.SelfTest.csproj -c Release
  if($LASTEXITCODE-ne0){throw 'R57 SelfTest failed'}
} finally { Pop-Location }

$dist=Join-Path $root 'dist\app'
foreach($n in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){
  $p=Join-Path $dist $n
  if(!(Test-Path $p)){throw "R57 missing $n"}
  $version=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString()
  if($version-ne'0.1.57.0'){throw "R57 $n version=$version"}
}
Write-Host 'R57_ASSEMBLY_IDENTITY_PASS'

# Strong real-window startup gate. Process-alive is insufficient because the
# application deliberately catches startup exceptions and can keep an error
# window alive.
$exe=Join-Path $dist 'MerzoWindowsOptimizer.exe'
if(!(Test-Path $exe)){throw 'R57 finished EXE missing'}
$crashDir=Join-Path $env:LOCALAPPDATA 'MerzoWindowsOptimizer\logs'
$launchAt=(Get-Date).ToUniversalTime()
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$proc=Start-Process $exe -WorkingDirectory $dist -PassThru
$mainFound=$false
$errorWindow=''
try {
  $deadline=(Get-Date).AddSeconds(25)
  while((Get-Date)-lt$deadline){
    $proc.Refresh()
    if($proc.HasExited){throw "R57 finished EXE exited $($proc.ExitCode)"}
    $windows=[System.Windows.Automation.AutomationElement]::RootElement.FindAll(
      [System.Windows.Automation.TreeScope]::Children,
      [System.Windows.Automation.Condition]::TrueCondition)
    foreach($w in $windows){
      try{
        if($w.Current.ProcessId-ne$proc.Id){continue}
        $name=[string]$w.Current.Name
        if($name-match'(?i)startup error'){$errorWindow=$name}
        if($name-like'*Merzo Windows Optimizer — Production 0.1.57*R57*'){$mainFound=$true}
      }catch{}
    }
    if($errorWindow){throw "R57 startup error window detected: $errorWindow"}
    if($mainFound){break}
    Start-Sleep -Milliseconds 400
  }
  if(!$mainFound){throw 'R57 real Production main window was not detected'}
  if(Test-Path $crashDir){
    $newCrash=Get-ChildItem $crashDir -File -Filter 'startup-crash-*.log' -ErrorAction SilentlyContinue |
      Where-Object{$_.LastWriteTimeUtc-ge$launchAt.AddSeconds(-1)} |
      Select-Object -First 1
    if($newCrash){throw "R57 created startup crash log: $($newCrash.FullName)"}
  }
  Write-Host 'R57_REAL_MAIN_WINDOW_LAUNCH_PASS'
} finally {
  if(!$proc.HasExited){Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue}
}

$zip=Join-Path $root 'dist\MerzoWindowsOptimizer-portable-win-x64.zip'
if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path (Join-Path $dist '*') -DestinationPath $zip -CompressionLevel Optimal

# The Test Center may discover per-user Inno Setup 6 via registry/winget.
# Accept its process-scoped compiler path (also support original machine paths),
# but NEVER execute a non-ISCC.exe or a compiler without version 6 metadata.
# Genuine Inno Setup 6 may expose 0.0.0.0 as the ISCC.exe file version.
# Its documented "/?" banner is a safe, read-only secondary identity check.
# Only a discovered ISCC.exe is invoked, with a fixed argument and timeout.
function Test-Inno6CompilerIdentity {
  param([Parameter(Mandatory)][string]$CompilerPath)
  try {
    $file=Get-Item -LiteralPath $CompilerPath -ErrorAction Stop
    if($file.PSIsContainer -or $file.Name -ine 'ISCC.exe'){return $false}
    $versions=@([string]$file.VersionInfo.FileVersion,[string]$file.VersionInfo.ProductVersion)
    if(@($versions|Where-Object{$_ -match '(?<!\d)7\.[0-9]+'}).Count-gt0){return $false}
    if(@($versions|Where-Object{$_ -match '(?<!\d)6\.[0-9]+'}).Count-gt0){return $true}
    $psi=[Diagnostics.ProcessStartInfo]::new()
    $psi.FileName=[string]$file.FullName
    $psi.ArgumentList.Add('/?')
    $psi.WorkingDirectory=[string]$file.DirectoryName
    $psi.UseShellExecute=$false
    $psi.CreateNoWindow=$true
    $psi.RedirectStandardOutput=$true
    $psi.RedirectStandardError=$true
    $proc=[Diagnostics.Process]::new()
    try {
      $proc.StartInfo=$psi
      if(-not $proc.Start()){return $false}
      $outputTask=$proc.StandardOutput.ReadToEndAsync()
      $errorTask=$proc.StandardError.ReadToEndAsync()
      if(-not $proc.WaitForExit(6000)){
        try{$proc.Kill($true)}catch{}
        return $false
      }
      $banner=$outputTask.GetAwaiter().GetResult()+[Environment]::NewLine+$errorTask.GetAwaiter().GetResult()
      return ($banner -match '(?im)^\s*Inno Setup 6(?:\.\d+)*\s+Command[- ]Line Compiler\b')
    }finally{
      $proc.Dispose()
    }
  }catch{
    return $false
  }
}

$iscc=@(
  $env:MWO_INNO6_ISCC,
  'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
  'C:\Program Files\Inno Setup 6\ISCC.exe'
) | Where-Object {
  if(-not $_){return $false}
  Test-Inno6CompilerIdentity -CompilerPath ([string]$_)
} | Select-Object -First 1
if(!$iscc){throw 'R57 ISCC missing'}
Push-Location $root
try {
  & $iscc '/DMyAppVersion=0.1.57' '.\installer\MerzoWindowsOptimizer.iss'
  if($LASTEXITCODE-ne0){throw 'R57 installer build failed'}
} finally { Pop-Location }

$installer=Join-Path $root 'dist\MerzoWindowsOptimizerSetup-win-x64.exe'
if(!(Test-Path $installer)){throw 'R57 installer missing'}
$ih=(Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant()
$zh=(Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$ih  MerzoWindowsOptimizerSetup-win-x64.exe"|Set-Content "$installer.sha256" -Encoding ascii
"$zh  MerzoWindowsOptimizer-portable-win-x64.zip"|Set-Content "$zip.sha256" -Encoding ascii

# Local Test Center consumes these in the current shell. GITHUB_ENV writes are
# retained only when that compatibility file exists; no GitHub Actions run is
# required for R57 development.
$env:R57_ROOT=$root
$env:SOURCE_ROOT=$root
$env:R57_INSTALLER_SHA=$ih
$env:R57_PORTABLE_SHA=$zh
if($env:GITHUB_ENV){
  "R57_ROOT=$root" >> $env:GITHUB_ENV
  "SOURCE_ROOT=$root" >> $env:GITHUB_ENV
  "R57_INSTALLER_SHA=$ih" >> $env:GITHUB_ENV
  "R57_PORTABLE_SHA=$zh" >> $env:GITHUB_ENV
}
Write-Host 'R57_OUTPUT_HANDOFF_PASS'
Write-Host 'R57_ALL_BUILD_GATES_PASS'
Write-Host "R57_INSTALLER_SHA256=$ih"
Write-Host "R57_PORTABLE_SHA256=$zh"
