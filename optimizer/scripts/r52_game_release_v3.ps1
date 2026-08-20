$ErrorActionPreference='Stop'
$src=Get-Content '.\optimizer\scripts\r52_game_release_v2.ps1' -Raw
$old="'r52_game_wow_debloat.py')"
$new="'r52_game_wow_debloat_v2.py')"
if(($src.Split($old).Count-1)-ne1){throw 'R52 V3 GAME patch filename anchor mismatch'}
$src=$src.Replace($old,$new)
$tmp=Join-Path $env:RUNNER_TEMP 'r52_game_release_v3_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp
if($LASTEXITCODE-ne0){throw "R52 V3 failed: $LASTEXITCODE"}
Write-Host 'R52_V3_COMPLETE_PASS'
