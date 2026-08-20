$ErrorActionPreference='Stop'
$src=Get-Content '.\optimizer\scripts\r53_release_v1.ps1' -Raw
$old=@'
$src=$src.Replace('Production R52','Production R53')
'@.Trim()
$new=@'
$src=$src.Replace('Production R52','Production R53')
$src=$src.Replace("'Production 0.1.53'","'Production R53 · 0.1.53'")
'@.Trim()
if(($src.Split($old).Count-1)-ne1){throw 'R53 V2 production identity anchor mismatch'}
$src=$src.Replace($old,$new)
$tmp=Join-Path $env:RUNNER_TEMP 'r53_release_v2_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp
if($LASTEXITCODE-ne0){throw "R53 V2 failed: $LASTEXITCODE"}
Write-Host 'R53_V2_COMPLETE_PASS'
