$ErrorActionPreference='Stop'
$release='.\optimizer\scripts\r54_r53_hotfix_bridge_release.ps1'
& $release
if($LASTEXITCODE-ne0){throw "R54 production reconstruction failed: $LASTEXITCODE"}
if([string]::IsNullOrWhiteSpace($env:SOURCE_ROOT)){throw 'SOURCE_ROOT missing after R54 reconstruction'}
$root=$env:SOURCE_ROOT
$out=[Text.StringBuilder]::new()
[void]$out.AppendLine("R54 SERVICE FAILURE DIAG")
[void]$out.AppendLine("ROOT=$root")
[void]$out.AppendLine('')

$tweakPath=Join-Path $root 'data\tweaks.json'
$tweaks=Get-Content $tweakPath -Raw | ConvertFrom-Json
$hits=@($tweaks | Where-Object {
  $_.name -match 'Distributed Link|Tracking Client' -or
  $_.id -match 'track|link|trk' -or
  (($_.service_actions | ConvertTo-Json -Depth 8 -Compress) -match 'TrkWks|Distributed') -or
  (($_.registry_actions | ConvertTo-Json -Depth 8 -Compress) -match 'TrkWks|Distributed')
})
[void]$out.AppendLine("TWEAK_HITS=$($hits.Count)")
foreach($h in $hits){
  [void]$out.AppendLine('--- TWEAK ---')
  [void]$out.AppendLine(($h | ConvertTo-Json -Depth 12))
}

[void]$out.AppendLine('')
[void]$out.AppendLine('--- SOURCE MATCHES ---')
$patterns=@('ServiceController','Registry.LocalMachine','CurrentControlSet\\Services','SetValue','service_actions','ServiceAction','StartupType','ChangeService','sc.exe','StartService','StopService')
$files=Get-ChildItem (Join-Path $root 'src') -Recurse -File -Filter *.cs | Where-Object {$_.FullName -notmatch '\\(bin|obj)\\'}
foreach($f in $files){
  $text=Get-Content $f.FullName -Raw
  $matched=$false
  foreach($p in $patterns){if($text -match $p){$matched=$true;break}}
  if(!$matched){continue}
  $rel=$f.FullName.Substring($root.Length).TrimStart('\')
  [void]$out.AppendLine("FILE=$rel")
  $lines=Get-Content $f.FullName
  for($i=0;$i-lt$lines.Count;$i++){
    if($lines[$i] -match 'ServiceController|Registry.LocalMachine|CurrentControlSet\\Services|SetValue|service_actions|ServiceAction|StartupType|ChangeService|sc.exe|StartService|StopService'){
      $a=[Math]::Max(0,$i-5);$b=[Math]::Min($lines.Count-1,$i+10)
      for($j=$a;$j-le$b;$j++){[void]$out.AppendLine(('{0,5}: {1}' -f ($j+1),$lines[$j]))}
      [void]$out.AppendLine('-----')
    }
  }
}

$diag='.\optimizer\R54_SERVICE_FAILURE_DIAG.txt'
Set-Content $diag $out.ToString() -Encoding UTF8
Write-Host "R54_SERVICE_FAILURE_DIAG_READY $diag"
