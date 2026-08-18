$ErrorActionPreference='Stop'
$patch='.\optimizer\patches\r53_process_start_debloat.py'
$original=Get-Content $patch -Raw
$old="x=x.replace('R52 GAME WOW + UI RELIABILITY','R53 PROCESS + CLEAN START')"
$new="x=x.replace('Production R52 · 0.1.52','Production R53 · 0.1.53')`n$old"
if(($original.Split($old).Count-1)-ne1){throw 'R53 V4 UI identity patch anchor mismatch'}
$patched=$original.Replace($old,$new)
try {
    Set-Content $patch $patched -Encoding UTF8
    & '.\optimizer\scripts\r53_release_v3.ps1'
    if($LASTEXITCODE-ne0){throw "R53 V4 failed: $LASTEXITCODE"}
} finally {
    Set-Content $patch $original -Encoding UTF8
}
Write-Host 'R53_V4_COMPLETE_PASS'
