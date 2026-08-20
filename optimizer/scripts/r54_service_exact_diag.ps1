$ErrorActionPreference='Stop'
& '.\optimizer\scripts\r54_r53_hotfix_bridge_release.ps1'
if($LASTEXITCODE-ne0){throw "R54 reconstruction failed: $LASTEXITCODE"}
$root=$env:SOURCE_ROOT
if([string]::IsNullOrWhiteSpace($root)){throw 'SOURCE_ROOT missing'}
$out=[Text.StringBuilder]::new()
[void]$out.AppendLine('R54 EXACT SERVICE PATH')

$targets=@(
 'src\MerzoOptimizer.Windows\Services\WindowsServiceAuditService.cs',
 'src\MerzoOptimizer.Windows\Tweaks\WindowsTweakExecutionService.cs',
 'src\MerzoOptimizer.App\ViewModels\MainWindowViewModel.cs',
 'src\MerzoOptimizer.Core\Services\ServiceModels.cs',
 'src\MerzoOptimizer.Windows\Elevation\ElevationAwareServices.cs',
 'src\MerzoOptimizer.Windows\Elevation\ElevatedOperationBroker.cs',
 'src\MerzoOptimizer.ElevatedHelper\Program.cs'
)
foreach($rel in $targets){
  $p=Join-Path $root $rel
  if(!(Test-Path $p)){continue}
  $lines=Get-Content $p
  [void]$out.AppendLine("=== $rel ===")
  for($i=0;$i-lt$lines.Count;$i++){
    if($lines[$i] -match 'Distributed|TrkWks|DisableAsync|RestoreServiceAsync|Apply.*Service|service\.|ServiceAudit|SetValue\(|OpenSubKey\(|CurrentControlSet\\Services|ChangeService|ServiceController|gaming_build|ApplyGaming|Install.*Build|Rollback|RestoreAsync|ServiceName|StartValue'){
      $a=[Math]::Max(0,$i-12);$b=[Math]::Min($lines.Count-1,$i+20)
      [void]$out.AppendLine("--- around $($i+1) ---")
      for($j=$a;$j-le$b;$j++){[void]$out.AppendLine(('{0,5}: {1}' -f ($j+1),$lines[$j]))}
    }
  }
}

# Also dump all service audit rules exactly.
$p=Join-Path $root 'src\MerzoOptimizer.Windows\Services\WindowsServiceAuditService.cs'
if(Test-Path $p){
  [void]$out.AppendLine('=== FULL WindowsServiceAuditService.cs ===')
  [void]$out.AppendLine((Get-Content $p -Raw))
}
Set-Content '.\optimizer\R54_SERVICE_EXACT_DIAG.txt' $out.ToString() -Encoding UTF8
Write-Host 'R54_SERVICE_EXACT_DIAG_READY'
