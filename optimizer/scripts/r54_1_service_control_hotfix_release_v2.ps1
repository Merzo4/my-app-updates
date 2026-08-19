$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_1_service_control_hotfix_release.ps1'
$original=Get-Content $base -Raw
$old="'r53_game_apply_hotfix.py','r53_version_finalize.py','r54_updater_bridge.py','r54_1_service_control_hotfix.py')"
$new="'r53_game_apply_hotfix.py','r53_version_finalize.py','r54_updater_bridge.py','r54_1_service_control_hotfix.py','r54_1_service_selftest_contract.py')"
if(($original.Split($old).Count-1)-ne1){throw 'R54.1 v2 SelfTest patch-chain anchor mismatch'}
$patched=$original.Replace($old,$new)
try {
    Set-Content $base $patched -Encoding UTF8
    & $base
    if($LASTEXITCODE-ne0){throw "R54.1 v2 production gates failed: $LASTEXITCODE"}
    Write-Host 'R54_1_V2_ALL_GATES_PASS'
}
finally {
    Set-Content $base $original -Encoding UTF8
}
