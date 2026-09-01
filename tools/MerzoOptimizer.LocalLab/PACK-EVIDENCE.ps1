$ErrorActionPreference='Stop'
$root=if($env:MWO_LAB_ROOT){$env:MWO_LAB_ROOT}else{'D:\MerzoOptimizer-LocalLab'}
$latest=Join-Path $root 'Results\Latest'
$log=Join-Path $root 'Logs\Current.log'
$out=Join-Path $root 'Results\MerzoOptimizer-Verify-Evidence.zip'
if(!(Test-Path (Join-Path $latest 'LAB-RESULT.json'))){throw 'LAB-RESULT.json отсутствует. Сначала запусти профиль проверки.'}
$tmp=Join-Path $root 'Temp\Evidence';if(Test-Path $tmp){Remove-Item $tmp -Recurse -Force};New-Item $tmp -ItemType Directory -Force|Out-Null
Copy-Item (Join-Path $latest 'LAB-RESULT.json') $tmp -Force
if(Test-Path (Join-Path $latest 'REPORT.txt')){Copy-Item (Join-Path $latest 'REPORT.txt') $tmp -Force}
if(Test-Path $log){Copy-Item $log (Join-Path $tmp 'Current.log') -Force}
$hashes=@()
Get-ChildItem $tmp -File|ForEach-Object{$hashes+=[ordered]@{file=$_.Name;sha256=(Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant();size=$_.Length}}
$hashes|ConvertTo-Json -Depth 4|Set-Content (Join-Path $tmp 'EVIDENCE-HASHES.json') -Encoding UTF8
if(Test-Path $out){Remove-Item $out -Force}
Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $out -CompressionLevel Optimal
$size=(Get-Item $out).Length
if($size-gt25MB){Remove-Item $out -Force;throw "Evidence ZIP превышает 25 MB: $size"}
Write-Host "EVIDENCE_READY $out sha256=$((Get-FileHash $out -Algorithm SHA256).Hash.ToLowerInvariant())"
Start-Process explorer.exe "/select,`"$out`""
