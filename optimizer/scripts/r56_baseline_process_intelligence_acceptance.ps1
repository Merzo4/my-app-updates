param(
  [Parameter(Mandatory=$true)][string]$SourceRoot
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$an=Join-Path $SourceRoot 'src\MerzoOptimizer.Windows\Processes\WindowsProcessStabilityAnalyzer.cs'
$vm=Join-Path $SourceRoot 'src\MerzoOptimizer.App\ViewModels\MainWindowViewModel.cs'
$xaml=Join-Path $SourceRoot 'src\MerzoOptimizer.App\MainWindow.xaml'
foreach($p in @($an,$vm,$xaml)){if(!(Test-Path $p)){throw "R56 acceptance missing $p"}}
$a=Get-Content $an -Raw;$v=Get-Content $vm -Raw;$x=Get-Content $xaml -Raw

foreach($name in @('SearchIndexer','SearchProtocolHost','SearchFilterHost','sppsvc','TiWorker','MoUsoCoreWorker','UsoClient','TextInputHost','ApplicationFrameHost','Taskmgr')){
  if($a-notmatch('"'+[regex]::Escape($name)+'"')){throw "R56 protected family missing: $name"}
}
if($a-notmatch'"AMDRSSrcExt"'){throw 'R56 AMD RSS driver family missing'}
if($a-notmatch'AMDRSServ", "AMDRSSrcExt"'){throw 'R56 AMDRSSrcExt is not in driver process hint list'}
Write-Host 'R56_CLASSIFICATION_SOURCE_CONTRACT_PASS'

if($v-notmatch'ObservableCollection<ProcessStabilityFamilySnapshot> ProcessStabilityFinalRows'){throw 'R56 final rows collection missing'}
if($v-notmatch'finalSample\.Families'){throw 'R56 final sample population missing'}
if($v-notmatch'Сохранённый Smart Audit: процессов'){throw 'R56 saved Smart Audit label missing'}
if($v-notmatch'Это не живой счётчик 15-минутного аудита'){throw 'R56 live/saved distinction missing'}
if($x-notmatch'Header="Постоянный фон"'){throw 'R56 final background tab missing'}
if($x-notmatch'ItemsSource="\{Binding ProcessStabilityFinalRows\}"'){throw 'R56 final background grid binding missing'}
if($x-notmatch'Production R56 · 0\.1\.56'){throw 'R56 visible identity missing'}
if($x-notmatch'Production 0\.1\.56 · R56 BASELINE PROCESS INTELLIGENCE'){throw 'R56 window identity missing'}
try{[xml]$x|Out-Null}catch{throw "R56 malformed XAML: $($_.Exception.Message)"}
Write-Host 'R56_FINAL_BACKGROUND_UI_CONTRACT_PASS'
Write-Host 'R56_LIVE_VS_SAVED_UI_CONTRACT_PASS'

# R56 must remain diagnostic: no new mutation surface is allowed in its patch.
$patch=Join-Path $PWD 'optimizer\patches\r56_baseline_process_intelligence.py'
if(!(Test-Path $patch)){throw 'R56 patch missing for mutation gate'}
$ptext=Get-Content $patch -Raw
foreach($bad in @('Stop-Process','taskkill','sc.exe stop','Set-Service','Disable-ScheduledTask','Registry.SetValue','CreateSubKey(','DeleteValue(')){
  if($ptext.Contains($bad)){throw "R56 diagnostic-only gate found mutation token: $bad"}
}
Write-Host 'R56_NO_NEW_MUTATION_SURFACE_PASS'

# Re-run the proven short synthetic delayed-start acceptance against the R56
# generated source. This preserves the core R55 detection/source contract.
& .\optimizer\scripts\r55_process_stability_acceptance.ps1 -SourceRoot $SourceRoot
if($LASTEXITCODE-ne0){throw 'R56 inherited R55 analyzer acceptance failed'}
Write-Host 'R56_INHERITED_DELAYED_ANALYZER_PASS'
Write-Host 'R56_BASELINE_PROCESS_INTELLIGENCE_ACCEPTANCE_PASS'
