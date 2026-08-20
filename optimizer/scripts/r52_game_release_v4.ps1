$ErrorActionPreference='Stop'
$src=Get-Content '.\optimizer\scripts\r52_game_release_v3.ps1' -Raw
$old="r52_game_wow_debloat_v2.py"
$new="r52_game_wow_debloat_v3.py"
if(($src.Split($old).Count-1)-ne1){throw 'R52 V4 patch wrapper anchor mismatch'}
$src=$src.Replace($old,$new)
$tmp=Join-Path $env:RUNNER_TEMP 'r52_game_release_v4_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp
if($LASTEXITCODE-ne0){throw "R52 V4 failed: $LASTEXITCODE"}
Write-Host 'R52_V4_COMPLETE_PASS'
