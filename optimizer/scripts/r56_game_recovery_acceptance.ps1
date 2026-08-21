param(
  [Parameter(Mandatory=$true)][string]$ArtifactDir,
  [Parameter(Mandatory=$true)][long]$BuildRun,
  [Parameter(Mandatory=$true)][string]$BuildHead,
  [Parameter(Mandatory=$true)][string]$ExpectedPortableSha
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

# R56 changes process diagnostics only. The destructive GAME/Recovery gate is
# intentionally inherited unchanged from the proven R54.2 production contract;
# only the expected application version is advanced.
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$original=Get-Content $base -Raw
$patched=$original
$old='$fv-ne''0.1.54.2'''
$new='$fv-ne''0.1.56.0'''
if(($patched.Split($old).Count-1)-ne1){throw 'R56 GAME version assertion anchor mismatch'}
$patched=$patched.Replace($old,$new)
try{
  Set-Content $base $patched -Encoding UTF8
  & '.\optimizer\scripts\r54_2_game_mutation_acceptance_v12.ps1' -ArtifactDir $ArtifactDir
  if($LASTEXITCODE-ne0){throw "R56 inherited GAME/RestoreAll v12 failed: $LASTEXITCODE"}
  $legacy='.\optimizer\R54_2_GAME_MUTATION_STATUS.json'
  if(!(Test-Path $legacy)){throw 'R56 inherited GAME status missing'}
  $j=Get-Content $legacy -Raw|ConvertFrom-Json
  foreach($name in @('oneDriveSyntheticNonzero','oneDriveSetupOnlyDetection','gameFullMutation','recoveryRestoreAll','recoveryStateVerification')){
    if($j.$name-ne'success'){throw "R56 GAME/Recovery field not green: $name=$($j.$name)"}
  }
  $portable=Get-ChildItem $ArtifactDir -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip'|Select-Object -First 1
  if(!$portable){throw 'R56 portable missing'}
  $portableSha=(Get-FileHash $portable.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  if($portableSha-ne$ExpectedPortableSha.ToLowerInvariant()){throw "R56 portable SHA mismatch $portableSha"}
  $work=Join-Path $env:RUNNER_TEMP ('r56-version-'+[guid]::NewGuid().ToString('N'));Expand-Archive $portable.FullName $work -Force
  $fv=(Get-Item (Join-Path $work 'MerzoWindowsOptimizer.exe')).VersionInfo.FileVersion
  if($fv-ne'0.1.56.0'){throw "R56 final GAME version=$fv"}
  [ordered]@{
    conclusion='success';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]$env:GITHUB_RUN_ID;headSha=$env:GITHUB_SHA
    buildRun=$BuildRun;buildHead=$BuildHead;candidateVersion=$fv;portableSha=$portableSha
    oneDriveSyntheticNonzero='success';oneDriveSetupOnlyDetection='success';gameFullMutation='success';undoContractProbe='production-restore-all-success';recoveryRestoreAll='success';recoveryStateVerification='success';mutationDelta='none'
  }|ConvertTo-Json|Set-Content '.\optimizer\R56_GAME_RECOVERY_STATUS.json' -Encoding UTF8
  Write-Host "R56_GAME_RECOVERY_ACCEPTANCE_PASS buildRun=$BuildRun version=$fv portableSha=$portableSha"
}finally{Set-Content $base $original -Encoding UTF8}
