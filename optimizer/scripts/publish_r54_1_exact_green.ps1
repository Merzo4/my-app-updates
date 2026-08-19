param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$repo=$env:GITHUB_REPOSITORY
if([string]::IsNullOrWhiteSpace($repo)){throw 'GITHUB_REPOSITORY missing'}
$ci=Get-Content '.\optimizer\R54_1_V2_CI_STATUS.json' -Raw | ConvertFrom-Json
$runtime=Get-Content '.\optimizer\R54_1_TRKWKS_RUNTIME_STATUS.json' -Raw | ConvertFrom-Json
if($ci.conclusion-ne'success' -or $ci.gates-ne'success' -or $ci.artifact-ne'success'){throw 'R54.1 CI status is not green'}
if([long]$ci.databaseId-ne32232868999 -or $ci.headSha-ne'c8ed6d8bdaca6ef7178f8876379821bc3c16ed23'){throw 'R54.1 CI status is not the exact approved green run'}
if($runtime.conclusion-ne'success' -or [long]$runtime.buildRun-ne32232868999 -or $runtime.applyViaProductScm-ne'success' -or $runtime.restoreViaProductScm-ne'success' -or $runtime.launch-ne'success'){throw 'R54.1 TrkWks runtime acceptance is not green'}

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
  if($actual-ne$expected){throw "SHA mismatch for $($file.Name): $actual != $expected"}
  return $actual
}
$setupSha=Assert-Sha $setup $setupSide
$zipSha=Assert-Sha $zip $zipSide
Write-Host "R54_1_PUBLISH_SHA_PASS setup=$setupSha zip=$zipSha"

$existing=$null
try{$existing=gh api "repos/$repo/releases/tags/mwo-v0.1.54.1" 2>$null | ConvertFrom-Json}catch{}
if($existing){throw 'mwo-v0.1.54.1 already exists; refusing to overwrite immutable public release'}

gh release create mwo-v0.1.54.1 --repo $repo --target c8ed6d8bdaca6ef7178f8876379821bc3c16ed23 --title 'Merzo Windows Optimizer 0.1.54.1 — Service Control Hotfix' --notes-file $notes.FullName $setup.FullName $setupSide.FullName $zip.FullName $zipSide.FullName
if($LASTEXITCODE-ne0){throw 'gh release create R54.1 failed'}

$release=gh api "repos/$repo/releases/tags/mwo-v0.1.54.1" | ConvertFrom-Json
if($release.draft -or $release.prerelease -or $release.tag_name-ne'mwo-v0.1.54.1'){throw 'Public R54.1 release metadata invalid'}
$pubSetup=$release.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
$pubSide=$release.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256' | Select-Object -First 1
if(!$pubSetup -or !$pubSide){throw 'Public R54.1 installer assets missing'}
if($pubSetup.digest-ne('sha256:'+$setupSha)){throw "Public R54.1 GitHub digest mismatch: $($pubSetup.digest)"}
@{
 conclusion='success';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]$env:GITHUB_RUN_ID;buildRun=32232868999;buildHead='c8ed6d8bdaca6ef7178f8876379821bc3c16ed23';tag='mwo-v0.1.54.1';installerSha=$setupSha;portableSha=$zipSha
} | ConvertTo-Json -Compress | Set-Content '.\optimizer\R54_1_PUBLISH_STATUS.json' -Encoding UTF8
Write-Host 'R54_1_PUBLICATION_PASS'
