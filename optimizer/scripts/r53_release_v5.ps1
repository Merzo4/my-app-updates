$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r53_release_v1.ps1'
$original=Get-Content $base -Raw
$old=@'
$new="'r52_window_scroll_reliability.py','r52_game_wow_debloat_v3.py','r53_process_start_debloat.py')"
'@.Trim()
$new=@'
$new="'r52_window_scroll_reliability.py','r52_game_wow_debloat_v3.py','r53_process_start_debloat.py','r53_version_finalize.py')"
'@.Trim()
if(($original.Split($old).Count-1)-ne1){throw 'R53 V5 patch-chain anchor mismatch'}
$patched=$original.Replace($old,$new)
try {
    Set-Content $base $patched -Encoding UTF8
    & '.\optimizer\scripts\r53_release_v4.ps1'
    if($LASTEXITCODE-ne0){throw "R53 V5 failed: $LASTEXITCODE"}
} finally {
    Set-Content $base $original -Encoding UTF8
}
Write-Host 'R53_V5_COMPLETE_PASS'
