$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

# R55 deliberately does NOT rewrite the historical R49-R54 wrappers. First run
# the already-proven exact R54.2 production controller unchanged, then apply the
# new feature layer to that finished source tree and build a fresh 0.1.55.
$baseline='.\optimizer\scripts\r54_2_onedrive_game_reliability_release.ps1'
if(!(Test-Path $baseline)){throw 'R55 exact R54.2 baseline controller missing'}

& $baseline
if($LASTEXITCODE-ne0){throw "R55 exact R54.2 baseline failed: $LASTEXITCODE"}
if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'R55 SOURCE_ROOT missing after R54.2 baseline'}
$root=$env:SOURCE_ROOT

# Prove the inherited source really is the already-accepted R54.2 baseline before
# adding anything new.
$baselineUi=Get-Content (Join-Path $root 'src\MerzoOptimizer.App\MainWindow.xaml') -Raw
$baselineDll=Join-Path $root 'dist\app\MerzoWindowsOptimizer.dll'
if(-not$baselineUi.Contains('Production R54.2 · 0.1.54.2')){throw 'R55 baseline visible identity is not R54.2'}
if(!(Test-Path $baselineDll)){throw 'R55 baseline app DLL missing'}
$baselineVersion=[Reflection.AssemblyName]::GetAssemblyName($baselineDll).Version.ToString()
if($baselineVersion-ne'0.1.54.2'){throw "R55 baseline DLL version=$baselineVersion"}
Write-Host 'R55_EXACT_R542_BASELINE_PASS'

foreach($patch in @('r55_process_stability.py','r55_compile_fix.py','r55_version_finalize.py')){
    python (Join-Path $PWD "optimizer\patches\$patch")
    if($LASTEXITCODE-ne0){throw "R55 patch failed: $patch"}
}

foreach($rel in @(
    'R55_PROCESS_STABILITY.marker',
    'R55_VERSION_FINAL.marker',
    'src\MerzoOptimizer.Core\Audit\ProcessStabilityModels.cs',
    'src\MerzoOptimizer.Windows\Processes\WindowsProcessStabilityAnalyzer.cs'
)){
    if(!(Test-Path (Join-Path $root $rel))){throw "R55 output missing: $rel"}
}

$xamlPath=Join-Path $root 'src\MerzoOptimizer.App\MainWindow.xaml'
$vmPath=Join-Path $root 'src\MerzoOptimizer.App\ViewModels\MainWindowViewModel.cs'
$analyzerPath=Join-Path $root 'src\MerzoOptimizer.Windows\Processes\WindowsProcessStabilityAnalyzer.cs'
$x=Get-Content $xamlPath -Raw
$v=Get-Content $vmPath -Raw
$a=Get-Content $analyzerPath -Raw
foreach($token in @('Production R55 · 0.1.55','R55 PROCESS STABILITY','Аудит 15 минут','ProcessStabilityRows','RunProcessStabilityAuditCommand')){
    if(-not(($x+"`n"+$v).Contains($token))){throw "R55 UI/VM contract missing: $token"}
}
foreach($token in @('ProcessStabilityAuditOptions.Production','BuildSourceInventory','ReadScheduledTaskActions','ReadServiceImages','Не трогать','Драйвер / оставить','Необязательный','Registry.CurrentUser','Registry.LocalMachine','writable: false','Process.GetProcesses()')){
    if(-not$a.Contains($token)){throw "R55 analyzer contract missing: $token"}
}
# The analyzer may terminate ONLY its own bounded child PowerShell probe when
# Get-ScheduledTask hangs. It must not contain code that mutates Windows service
# configuration, startup registry state, scheduled tasks, or arbitrary processes.
foreach($forbidden in @('Stop-Process','ChangeServiceConfig(','SetValue("Start"','DeleteValue(','CreateSubKey(','Set-ScheduledTask','Disable-ScheduledTask','Unregister-ScheduledTask','ServiceControllerStatus')){
    if($a.Contains($forbidden)){throw "R55 analyzer must remain read-only: $forbidden"}
}
if(($a.Split('p.Kill(entireProcessTree: true)').Count-1)-gt1){throw 'R55 analyzer has unexpected process termination paths'}
Write-Host 'R55_READONLY_SOURCE_CONTRACT_PASS'

# XAML must remain structurally valid before compiling.
try{[xml](Get-Content $xamlPath -Raw)|Out-Null}catch{throw "R55 malformed XAML: $($_.Exception.Message)"}

# Build a fresh production payload from the finished R54.2 + R55 source.
Push-Location $root
try {
    & .\build\Build-Production.ps1 -Version '0.1.55' -SkipObfuscation
    if($LASTEXITCODE-ne0){throw 'R55 Production build failed'}

    dotnet run --project .\src\MerzoOptimizer.SelfTest\MerzoOptimizer.SelfTest.csproj -c Release
    if($LASTEXITCODE-ne0){throw 'R55 SelfTest failed'}
}
finally { Pop-Location }

$dist=Join-Path $root 'dist\app'
foreach($n in @('MerzoWindowsOptimizer.dll','MerzoOptimizer.Core.dll','MerzoOptimizer.Windows.dll','MerzoOptimizer.ElevatedHelper.dll')){
    $p=Join-Path $dist $n
    if(!(Test-Path $p)){throw "R55 missing $n"}
    $version=[Reflection.AssemblyName]::GetAssemblyName($p).Version.ToString()
    if($version-ne'0.1.55.0'){throw "R55 $n version=$version"}
}
Write-Host 'R55_ASSEMBLY_IDENTITY_PASS'

# Finished WPF application must actually stay alive, catching XAML/composition or
# constructor failures that a compile-only check would miss.
$exe=Join-Path $dist 'MerzoWindowsOptimizer.exe'
if(!(Test-Path $exe)){throw 'R55 finished EXE missing'}
$proc=Start-Process $exe -WorkingDirectory $dist -PassThru
Start-Sleep 15
if($proc.HasExited){throw "R55 finished EXE exited $($proc.ExitCode)"}
Stop-Process -Id $proc.Id -Force
Write-Host 'R55_FINISHED_APP_LAUNCH_PASS'

# Repackage only the rebuilt R55 payload.
$zip=Join-Path $root 'dist\MerzoWindowsOptimizer-portable-win-x64.zip'
if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path (Join-Path $dist '*') -DestinationPath $zip -CompressionLevel Optimal
$iscc=@('C:\Program Files (x86)\Inno Setup 6\ISCC.exe','C:\Program Files\Inno Setup 6\ISCC.exe') | Where-Object { Test-Path $_ } | Select-Object -First 1
if(-not$iscc){throw 'R55 ISCC missing'}
Push-Location $root
try {
    & $iscc '/DMyAppVersion=0.1.55' '.\installer\MerzoWindowsOptimizer.iss'
    if($LASTEXITCODE-ne0){throw 'R55 installer build failed'}
}
finally { Pop-Location }

$installer=Join-Path $root 'dist\MerzoWindowsOptimizerSetup-win-x64.exe'
if(!(Test-Path $installer)){throw 'R55 installer missing'}
$ih=(Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant()
$zh=(Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$ih  MerzoWindowsOptimizerSetup-win-x64.exe" | Set-Content "$installer.sha256" -Encoding ascii
"$zh  MerzoWindowsOptimizer-portable-win-x64.zip" | Set-Content "$zip.sha256" -Encoding ascii
if((Get-Content "$installer.sha256" -Raw)-notmatch[regex]::Escape($ih)){throw 'R55 installer sidecar mismatch'}
if((Get-Content "$zip.sha256" -Raw)-notmatch[regex]::Escape($zh)){throw 'R55 portable sidecar mismatch'}

"R55_ROOT=$root" >> $env:GITHUB_ENV
"R55_INSTALLER_SHA=$ih" >> $env:GITHUB_ENV
"R55_PORTABLE_SHA=$zh" >> $env:GITHUB_ENV
Write-Host 'R55_PROCESS_STABILITY_ALL_BUILD_GATES_PASS'
Write-Host "R55_INSTALLER_SHA256=$ih"
Write-Host "R55_PORTABLE_SHA256=$zh"
