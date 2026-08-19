param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$repo=$env:GITHUB_REPOSITORY
if([string]::IsNullOrWhiteSpace($repo)){throw 'GITHUB_REPOSITORY missing'}
$approvedRun=32232868999
$approvedHead='c8ed6d8bdaca6ef7178f8876379821bc3c16ed23'
$approvedArtifact='MerzoWindowsOptimizer-0.1.54.1-SERVICE-CONTROL-HOTFIX'

# Pin publication to the immutable Actions run/artifact that was actually used
# by the real TrkWks runtime acceptance. Do not trust mutable "latest CI" files.
$run=gh api "repos/$repo/actions/runs/$approvedRun" | ConvertFrom-Json
if($run.status -ne 'completed' -or $run.conclusion -ne 'success' -or $run.head_sha -ne $approvedHead){
  throw "Approved R54.1 Actions run is not exact-green: status=$($run.status) conclusion=$($run.conclusion) head=$($run.head_sha)"
}
$artifacts=gh api "repos/$repo/actions/runs/$approvedRun/artifacts" | ConvertFrom-Json
$approved=$artifacts.artifacts | Where-Object {$_.name -eq $approvedArtifact -and -not $_.expired} | Select-Object -First 1
if(!$approved){throw 'Approved R54.1 artifact is missing or expired'}

$runtime=Get-Content '.\optimizer\R54_1_TRKWKS_RUNTIME_STATUS.json' -Raw | ConvertFrom-Json
if($runtime.conclusion -ne 'success' -or [long]$runtime.buildRun -ne $approvedRun -or $runtime.artifact -ne $approvedArtifact -or $runtime.applyViaProductScm -ne 'success' -or $runtime.restoreViaProductScm -ne 'success' -or $runtime.launch -ne 'success'){
  throw 'R54.1 TrkWks runtime acceptance is not pinned to the approved green artifact'
}

$artifact=(Resolve-Path $ArtifactDir).Path
$setup=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
$setupSide=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256' | Select-Object -First 1
$zip=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip' | Select-Object -First 1
$zipSide=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256' | Select-Object -First 1
$notes=Get-ChildItem $artifact -Recurse -File -Filter 'R53_RELEASE_NOTES.md' | Select-Object -First 1
foreach($f in @($setup,$setupSide,$zip,$zipSide,$notes)){if(!$f){throw 'Exact green R54.1 artifact payload incomplete'}}
function Assert-Sha($file,$side){
  $actual=(Get-FileHash $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
  $expected=((Get-Content $side.FullName -Raw)-split '\s+')[0].ToLowerInvariant()
  if($actual -ne $expected){throw "SHA mismatch for $($file.Name): $actual != $expected"}
  return $actual
}
$setupSha=Assert-Sha $setup $setupSide
$zipSha=Assert-Sha $zip $zipSide
Write-Host "R54_1_PUBLISH_SHA_PASS setup=$setupSha zip=$zipSha artifactId=$($approved.id)"

$existing=$null
try{$existing=gh api "repos/$repo/releases/tags/mwo-v0.1.54.1" 2>$null | ConvertFrom-Json}catch{}
if($existing){throw 'mwo-v0.1.54.1 already exists; refusing to overwrite immutable public release'}

gh release create mwo-v0.1.54.1 --repo $repo --target $approvedHead --title 'Merzo Windows Optimizer 0.1.54.1 — Service Control Hotfix' --notes-file $notes.FullName $setup.FullName $setupSide.FullName $zip.FullName $zipSide.FullName
if($LASTEXITCODE -ne 0){throw 'gh release create R54.1 failed'}

$release=gh api "repos/$repo/releases/tags/mwo-v0.1.54.1" | ConvertFrom-Json
if($release.draft -or $release.prerelease -or $release.tag_name -ne 'mwo-v0.1.54.1'){throw 'Public R54.1 release metadata invalid'}
$pubSetup=$release.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
$pubSide=$release.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256' | Select-Object -First 1
if(!$pubSetup -or !$pubSide){throw 'Public R54.1 installer assets missing'}
if($pubSetup.digest -ne ('sha256:'+$setupSha)){throw "Public R54.1 GitHub digest mismatch: $($pubSetup.digest)"}
@{
 conclusion='success';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]$env:GITHUB_RUN_ID;buildRun=$approvedRun;buildHead=$approvedHead;artifactId=[long]$approved.id;tag='mwo-v0.1.54.1';installerSha=$setupSha;portableSha=$zipSha
} | ConvertTo-Json -Compress | Set-Content '.\optimizer\R54_1_PUBLISH_STATUS.json' -Encoding UTF8
Write-Host 'R54_1_PUBLICATION_PASS'
