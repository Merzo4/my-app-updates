$ErrorActionPreference='Stop'
& '.\optimizer\scripts\r54_r53_hotfix_bridge_release.ps1'
if($LASTEXITCODE-ne0){throw "R54 reconstruction failed: $LASTEXITCODE"}
$root=$env:SOURCE_ROOT
$p=Join-Path $root 'src\MerzoOptimizer.SelfTest\Program.cs'
if(!(Test-Path $p)){throw 'SelfTest Program.cs missing'}
$lines=Get-Content $p
$out=[Text.StringBuilder]::new()
for($i=0;$i-lt$lines.Count;$i++){
  if($lines[$i] -match 'Service Disable/Restore|WindowsServiceAuditService|WindowsRestoreService|SetValue\("Start"|RestoreService|DisableAsync'){
    $a=[Math]::Max(0,$i-18);$b=[Math]::Min($lines.Count-1,$i+24)
    [void]$out.AppendLine("--- around $($i+1) ---")
    for($j=$a;$j-le$b;$j++){[void]$out.AppendLine(('{0,5}: {1}' -f ($j+1),$lines[$j]))}
  }
}
Set-Content '.\optimizer\R54_SELFTEST_SERVICE_DIAG.txt' $out.ToString() -Encoding UTF8
Write-Host 'R54_SELFTEST_SERVICE_DIAG_READY'
