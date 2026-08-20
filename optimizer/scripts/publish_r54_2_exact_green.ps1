param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$repo=$env:GITHUB_REPOSITORY
if([string]::IsNullOrWhiteSpace($repo)){throw 'GITHUB_REPOSITORY missing'}
$approvedRun=32270447478
$approvedHead='086c02fc648893e18961eeee74e8bd73c4f83a2f'
$approvedArtifact='MerzoWindowsOptimizer-0.1.54.2-ONEDRIVE-GAME-RELIABILITY'
$approvedArtifactId=9372048444
$approvedArtifactDigest='sha256:747929c99018af25af3d16f174afe57c08f137e06c1699f77d958bf9b0cb4a70'
$approvedPortableSha='e31e5c06aa871411d3553fce564ec4d6dde89316b6db4e47d1af07267f35a7f3'
$approvedMutationRun=32336202703

$run=gh api "repos/$repo/actions/runs/$approvedRun" | ConvertFrom-Json
if($LASTEXITCODE -ne 0 -or $run.status -ne 'completed' -or $run.conclusion -ne 'success' -or $run.head_sha -ne $approvedHead){throw "Approved R54.2 Actions run is not exact-green: status=$($run.status) conclusion=$($run.conclusion) head=$($run.head_sha)"}
$artifacts=gh api "repos/$repo/actions/runs/$approvedRun/artifacts" | ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'Cannot read approved R54.2 artifact metadata'}
$approved=$artifacts.artifacts | Where-Object {$_.name -eq $approvedArtifact -and -not $_.expired} | Select-Object -First 1
if(!$approved){throw 'Approved R54.2 artifact is missing or expired'}
if([long]$approved.id -ne $approvedArtifactId){throw "Approved R54.2 artifact ID mismatch: $($approved.id) != $approvedArtifactId"}
if([string]$approved.digest -ne $approvedArtifactDigest){throw "Approved R54.2 artifact digest mismatch: $($approved.digest) != $approvedArtifactDigest"}

$mutation=Get-Content '.\optimizer\R54_2_GAME_MUTATION_STATUS.json' -Raw | ConvertFrom-Json
if($mutation.conclusion -ne 'success' -or [long]$mutation.databaseId -ne $approvedMutationRun -or [long]$mutation.buildRun -ne $approvedRun -or [long]$mutation.artifactId -ne $approvedArtifactId -or $mutation.artifactDigest -ne $approvedArtifactDigest -or $mutation.gameFullMutation -ne 'success' -or $mutation.recoveryRestoreAll -ne 'success' -or $mutation.recoveryStateVerification -ne 'success' -or $mutation.oneDriveSyntheticNonzero -ne 'success' -or $mutation.oneDriveSetupOnlyDetection -ne 'success'){throw 'R54.2 GAME + production Recovery acceptance is not pinned to the approved exact artifact'}

$artifact=(Resolve-Path $ArtifactDir).Path
$setup=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
$setupSide=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256' | Select-Object -First 1
$zip=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip' | Select-Object -First 1
$zipSide=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256' | Select-Object -First 1
$notes=Get-ChildItem $artifact -Recurse -File -Filter 'R53_RELEASE_NOTES.md' | Select-Object -First 1
foreach($f in @($setup,$setupSide,$zip,$zipSide,$notes)){if(!$f){throw 'Exact green R54.2 artifact payload incomplete'}}
function Assert-Sha($file,$side){$actual=(Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant();$expected=((Get-Content $side.FullName -Raw)-split '\s+')[0].ToLowerInvariant();if($actual -ne $expected){throw "SHA mismatch for $($file.Name): $actual != $expected"};return $actual}
$setupSha=Assert-Sha $setup $setupSide
$zipSha=Assert-Sha $zip $zipSide
if($zipSha -ne $approvedPortableSha){throw "R54.2 portable SHA mismatch against mutation-tested artifact: $zipSha != $approvedPortableSha"}
Write-Host "R54_2_PUBLISH_SHA_PASS setup=$setupSha zip=$zipSha artifactId=$($approved.id) digest=$($approved.digest)"

$release=$null
$raw=& gh api "repos/$repo/releases/tags/mwo-v0.1.54.2" 2>$null
$lookupExit=$LASTEXITCODE
if($lookupExit -eq 0 -and $raw){
  $release=($raw -join "`n") | ConvertFrom-Json
  if(!$release -or [string]::IsNullOrWhiteSpace([string]$release.tag_name)){throw 'R54.2 release lookup returned unusable JSON'}
}
$reused=$false
if($null -eq $release){
  Write-Host "R54_2_RELEASE_NOT_FOUND_CREATE lookupExit=$lookupExit"
  & gh release create mwo-v0.1.54.2 --repo $repo --target $approvedHead --title 'Merzo Windows Optimizer 0.1.54.2 — OneDrive + GAME Reliability' --notes-file $notes.FullName $setup.FullName $setupSide.FullName $zip.FullName $zipSide.FullName
  if($LASTEXITCODE -ne 0){throw 'gh release create R54.2 failed'}
  $raw=& gh api "repos/$repo/releases/tags/mwo-v0.1.54.2" 2>$null
  if($LASTEXITCODE -ne 0 -or !$raw){throw 'Public R54.2 release missing immediately after create'}
  $release=($raw -join "`n") | ConvertFrom-Json
}else{
  $reused=$true
  Write-Host "R54_2_EXISTING_RELEASE_VERIFY id=$($release.id) target=$($release.target_commitish)"
}

if(!$release -or $release.draft -or $release.prerelease -or $release.tag_name -ne 'mwo-v0.1.54.2'){throw 'Public R54.2 release metadata invalid'}
if($release.target_commitish -ne $approvedHead){throw "Public R54.2 release target mismatch: $($release.target_commitish) != $approvedHead"}
$pubSetup=$release.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
$pubSetupSide=$release.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256' | Select-Object -First 1
$pubZip=$release.assets | Where-Object name -eq 'MerzoWindowsOptimizer-portable-win-x64.zip' | Select-Object -First 1
$pubZipSide=$release.assets | Where-Object name -eq 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256' | Select-Object -First 1
if(!$pubSetup -or !$pubSetupSide -or !$pubZip -or !$pubZipSide){throw 'Public R54.2 asset set incomplete'}
if($pubSetup.digest -ne ('sha256:'+$setupSha)){throw "Public R54.2 installer GitHub digest mismatch: $($pubSetup.digest)"}
if($pubZip.digest -ne ('sha256:'+$zipSha)){throw "Public R54.2 portable GitHub digest mismatch: $($pubZip.digest)"}
@{conclusion='success';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]$env:GITHUB_RUN_ID;buildRun=$approvedRun;buildHead=$approvedHead;artifactId=[long]$approved.id;artifactDigest=$approved.digest;mutationRun=$approvedMutationRun;releaseId=[long]$release.id;reusedExistingRelease=$reused;tag='mwo-v0.1.54.2';installerSha=$setupSha;portableSha=$zipSha} | ConvertTo-Json -Compress | Set-Content '.\optimizer\R54_2_PUBLISH_STATUS.json' -Encoding UTF8
Write-Host 'R54_2_PUBLICATION_PASS'
