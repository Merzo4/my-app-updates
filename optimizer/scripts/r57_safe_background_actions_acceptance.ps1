param([Parameter(Mandatory=$true)][string]$SourceRoot)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

function Require([bool]$Condition,[string]$Marker){ if(-not $Condition){ throw "R57_ACCEPTANCE_FAIL $Marker" }; Write-Host "R57_$Marker`_PASS" }
function ReadText([string]$Rel){ $p=Join-Path $SourceRoot $Rel; if(!(Test-Path $p)){throw "Missing $Rel"}; return [IO.File]::ReadAllText($p) }

$models=ReadText 'src/MerzoOptimizer.Core/Audit/ProcessStabilityModels.cs'
$analyzer=ReadText 'src/MerzoOptimizer.Windows/Processes/WindowsProcessStabilityAnalyzer.cs'
$vm=ReadText 'src/MerzoOptimizer.App/ViewModels/MainWindowViewModel.cs'
$xaml=ReadText 'src/MerzoOptimizer.App/MainWindow.xaml'
$tweaks=Get-Content (Join-Path $SourceRoot 'data/tweaks.json') -Raw | ConvertFrom-Json
$marker=Join-Path $SourceRoot 'R57_SAFE_BACKGROUND_ACTIONS.marker'

Require (Test-Path $marker) 'MARKER'
Require ($models.Contains('string Management,') -and $models.Contains('IReadOnlyList<string> SafeTweakIds')) 'MODEL_ACTIONABILITY'
Require ($analyzer.Contains('ResolveSafeManagement') -and $analyzer.Contains('r34.edge.disable_startup_boost') -and $analyzer.Contains('browser.chrome.disable_background_mode') -and $analyzer.Contains('r34.widgets.disable_widgets_policy')) 'REVIEWED_MAPPING'
Require ($analyzer.Contains('WebView2 — общий runtime автоматически не отключается') -and $analyzer.Contains('OneDrive/Автозагрузка сценарий; из аудита не удалять')) 'UNKNOWN_OWNER_GUARD'

$allowed=@('r34.edge.disable_startup_boost','r34.edge.disable_background_mode','browser.chrome.disable_background_mode','r34.widgets.disable_widgets_policy')
$ids=@($tweaks | ForEach-Object {[string]$_.id})
foreach($id in $allowed){ Require ($ids -contains $id) ("CATALOG_"+($id -replace '[^A-Za-z0-9]','_')) }

$methodStart=$vm.IndexOf('private Task PrepareDetectedSafeBackgroundActionsAsync()', [StringComparison]::Ordinal)
$methodEnd=$vm.IndexOf('private Task CancelProcessStabilityAuditAsync()', $methodStart, [StringComparison]::Ordinal)
Require ($methodStart -ge 0 -and $methodEnd -gt $methodStart) 'PREPARE_METHOD'
$method=$vm.Substring($methodStart,$methodEnd-$methodStart)
Require ($method.Contains('card.IsSelected = true') -and $method.Contains('card.Definition.ScanOnly') -and $method.Contains('!card.IsSupported') -and $method.Contains('card.IsApplied')) 'SELECTION_ONLY'
Require (-not $method.Contains('_tweakService.ApplyAsync') -and -not $method.Contains('_serviceAudit.DisableAsync') -and -not $method.Contains('_taskAudit.DisableAsync') -and -not $method.Contains('Stop-Process') -and -not $method.Contains('Process.Kill')) 'NO_DIRECT_MUTATION'
Require ($method.Contains('SelectedOptimizationTabIndex = 3')) 'ROUTE_TO_SELECTED'

Require ($xaml.Contains('Command="{Binding PrepareDetectedSafeBackgroundActionsCommand}"') -and $xaml.Contains('Content="Подготовить SAFE действия"')) 'UI_COMMAND'
Require ($xaml.Contains('Header="Управление" Binding="{Binding Management, Mode=OneWay}"')) 'UI_MANAGEMENT_COLUMN'
Require ($xaml.Contains('Production R57 · 0.1.57') -and $xaml.Contains('Production 0.1.57 · R57 SAFE BACKGROUND ACTIONS')) 'VISIBLE_IDENTITY'

$projects=Get-ChildItem (Join-Path $SourceRoot 'src') -Filter '*.csproj' -Recurse
Require ($projects.Count -ge 5) 'PROJECT_SET'
foreach($p in $projects){
  $t=Get-Content $p.FullName -Raw
  Require ($t.Contains('<Version>0.1.57</Version>') -and $t.Contains('<FileVersion>0.1.57.0</FileVersion>')) ("VERSION_"+$p.BaseName)
}
$iss=ReadText 'installer/MerzoWindowsOptimizer.iss'
Require ($iss.Contains('0.1.57') -and -not $iss.Contains('0.1.56')) 'INSTALLER_VERSION'

Write-Host 'R57_SAFE_BACKGROUND_ACTIONS_ACCEPTANCE_PASS'
