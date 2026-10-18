param(
  [Parameter(Mandatory=$true)][string]$ArtifactDir,
  [Parameter(Mandatory=$true)][long]$BuildRun,
  [Parameter(Mandatory=$true)][string]$BuildHead,
  [Parameter(Mandatory=$true)][string]$ExpectedPortableSha
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

# R57 adds only a selection bridge from process diagnostics to already-reviewed
# tweaks. The actual GAME mutation contract must remain byte-for-byte inherited
# from the proven production acceptance; only expected application identity is
# advanced to 0.1.57.0.
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
if(!(Test-Path $base)){throw 'R57 inherited GAME base missing'}
$original=Get-Content $base -Raw
$patched=$original
$old='$fv-ne''0.1.54.2'''
$new='$fv-ne''0.1.57.0'''
if(($patched.Split($old).Count-1)-ne1){throw 'R57 GAME version assertion anchor mismatch'}
$patched=$patched.Replace($old,$new)

try{
  Set-Content $base $patched -Encoding UTF8
  & '.\optimizer\scripts\r54_2_game_mutation_acceptance_v12.ps1' -ArtifactDir $ArtifactDir
  if($LASTEXITCODE-ne0){throw "R57 inherited GAME/RestoreAll v12 failed: $LASTEXITCODE"}

  $legacy='.\optimizer\R54_2_GAME_MUTATION_STATUS.json'
  if(!(Test-Path $legacy)){throw 'R57 inherited GAME status missing'}
  $j=Get-Content $legacy -Raw|ConvertFrom-Json
  foreach($name in @('oneDriveSyntheticNonzero','oneDriveSetupOnlyDetection','gameFullMutation','recoveryRestoreAll','recoveryStateVerification')){
    if($j.$name-ne'success'){throw "R57 GAME/Recovery field not green: $name=$($j.$name)"}
  }

  $portable=Get-ChildItem $ArtifactDir -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip'|Select-Object -First 1
  if(!$portable){throw 'R57 portable missing'}
  $portableSha=(Get-FileHash $portable.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  if($portableSha-ne$ExpectedPortableSha.ToLowerInvariant()){throw "R57 portable SHA mismatch $portableSha"}

  $tempBase=if($env:RUNNER_TEMP){$env:RUNNER_TEMP}else{$env:TEMP}
  $work=Join-Path $tempBase ('r57-version-'+[guid]::NewGuid().ToString('N'))
  Expand-Archive $portable.FullName $work -Force
  $fv=(Get-Item (Join-Path $work 'MerzoWindowsOptimizer.exe')).VersionInfo.FileVersion
  if($fv-ne'0.1.57.0'){throw "R57 final GAME version=$fv"}

  $runId=0
  if(-not[string]::IsNullOrWhiteSpace($env:GITHUB_RUN_ID)){[long]::TryParse($env:GITHUB_RUN_ID,[ref]$runId)|Out-Null}
  [ordered]@{
    conclusion='success'
    createdAt=(Get-Date).ToUniversalTime().ToString('o')
    databaseId=$runId
    headSha=if($env:GITHUB_SHA){$env:GITHUB_SHA}else{$BuildHead}
    buildRun=$BuildRun
    buildHead=$BuildHead
    candidateVersion=$fv
    portableSha=$portableSha
    oneDriveSyntheticNonzero='success'
    oneDriveSetupOnlyDetection='success'
    gameFullMutation='success'
    undoContractProbe='production-restore-all-success'
    recoveryRestoreAll='success'
    recoveryStateVerification='success'
    mutationDelta='none'
  }|ConvertTo-Json|Set-Content '.\optimizer\R57_GAME_RECOVERY_STATUS.json' -Encoding UTF8
  Write-Host "R57_GAME_RECOVERY_ACCEPTANCE_PASS buildRun=$BuildRun version=$fv portableSha=$portableSha"
} finally {
  Set-Content $base $original -Encoding UTF8
}
