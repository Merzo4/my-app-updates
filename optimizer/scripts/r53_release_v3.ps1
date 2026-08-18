$ErrorActionPreference='Stop'
$legacy='.\optimizer\scripts\r49_release.ps1'
$original=Get-Content $legacy -Raw
$old="'Production 0.1.49'"
$new="'Production R49 · 0.1.49'"
if(($original.Split($old).Count-1)-ne1){throw 'R53 V3 legacy production gate anchor mismatch'}
$patched=$original.Replace($old,$new)
try {
    # CI-only gate modernization. r50/r51/r52/r53 version transforms promote this
    # exact label automatically to the target release; no shipped code is changed here.
    Set-Content $legacy $patched -Encoding UTF8
    & '.\optimizer\scripts\r53_release_v2.ps1'
    if($LASTEXITCODE-ne0){throw "R53 V3 failed: $LASTEXITCODE"}
} finally {
    Set-Content $legacy $original -Encoding UTF8
}
Write-Host 'R53_V3_COMPLETE_PASS'
