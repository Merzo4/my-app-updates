param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop';Set-StrictMode -Version Latest
$promotion='.\optimizer\R55_1_PROMOTION_STATUS.json'
try{
  if([string]::IsNullOrWhiteSpace($env:GH_TOKEN)){throw 'GH_TOKEN missing'};$repo=$env:GITHUB_REPOSITORY;if([string]::IsNullOrWhiteSpace($repo)){throw 'GITHUB_REPOSITORY missing'}
  $ci=Get-Content '.\optimizer\R55_1_CI_STATUS.json' -Raw|ConvertFrom-Json
  if($ci.conclusion-ne'success'){throw 'R55.1 CI status not green'}
  $run=[long]$ci.databaseId;$head=[string]$ci.headSha;$artifactId=[long]$ci.artifactId;$artifactName=[string]$ci.artifactName;$artifactDigest=[string]$ci.artifactDigest;$ih=[string]$ci.installerSha;$ph=[string]$ci.portableSha
  if(!$run-or[string]::IsNullOrWhiteSpace($head)-or!$artifactId-or[string]::IsNullOrWhiteSpace($ih)-or[string]::IsNullOrWhiteSpace($ph)){throw 'R55.1 CI provenance incomplete'}
  $api=gh api "repos/$repo/actions/artifacts/$artifactId"|ConvertFrom-Json
  if([long]$api.id-ne$artifactId-or$api.name-ne$artifactName-or$api.expired){throw 'R55.1 artifact API identity invalid'}
  if($api.PSObject.Properties['digest']-and![string]::IsNullOrWhiteSpace([string]$api.digest)){
    $apiDigest=([string]$api.digest).ToLowerInvariant().Replace('sha256:','')
    $ciDigest=$artifactDigest.ToLowerInvariant().Replace('sha256:','')
    if($apiDigest-ne$ciDigest){throw "R55.1 artifact digest mismatch API=$($api.digest) CI=$artifactDigest"}
  }
  $installer=Get-ChildItem $ArtifactDir -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe'|Select-Object -First 1;$portable=Get-ChildItem $ArtifactDir -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip'|Select-Object -First 1;$iside=Get-ChildItem $ArtifactDir -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256'|Select-Object -First 1;$pside=Get-ChildItem $ArtifactDir -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256'|Select-Object -First 1
  if(!$installer-or!$portable-or!$iside-or!$pside){throw 'R55.1 exact artifact payload incomplete'}
  $aih=(Get-FileHash $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant();$aph=(Get-FileHash $portable.FullName -Algorithm SHA256).Hash.ToLowerInvariant();if($aih-ne$ih-or$aph-ne$ph){throw 'R55.1 exact artifact file SHA mismatch'}
  Write-Host "R55_1_EXACT_ARTIFACT_PROVENANCE_PASS run=$run artifact=$artifactId installer=$aih portable=$aph"

  & '.\optimizer\scripts\r55_1_game_recovery_acceptance.ps1' -ArtifactDir $ArtifactDir -BuildRun $run -BuildHead $head -ExpectedPortableSha $ph
  if($LASTEXITCODE-ne0){throw 'R55.1 exact GAME/Recovery failed'}
  & '.\optimizer\scripts\r55_1_installed_candidate_acceptance.ps1' -ArtifactDir $ArtifactDir -BuildRun $run -BuildHead $head -ExpectedInstallerSha $ih -ExpectedPortableSha $ph
  if($LASTEXITCODE-ne0){throw 'R55.1 installed candidate failed'}

  $tag='mwo-v0.1.55.1';$title='Merzo Windows Optimizer 0.1.55.1 — Startup Binding Hotfix'
  $notes=@'
## Merzo Windows Optimizer 0.1.55.1 — Startup Binding Hotfix

Исправление критического регресса запуска R55.

- исправлена WPF-привязка ProcessStabilityProgress: ProgressBar теперь использует явный OneWay;
- R55 больше не падает при создании главного окна из-за попытки TwoWay-записи в read-only/private-set свойство;
- release gate усилен: требуется реальное окно Production, отсутствие окна startup error и отсутствие нового startup-crash лога;
- 15-минутный аудит процессов сохранён;
- GAME, OneDrive reliability, Snapshot/Undo и production RestoreAll повторно проверены на disposable Windows Server 2025.

Публикуется exact green artifact без пересборки.
'@
  $existing=$null;try{$existing=gh release view $tag --repo $repo --json id,tagName,url,targetCommitish 2>$null|ConvertFrom-Json}catch{}
  if(!$existing){gh release create $tag $installer.FullName $iside.FullName $portable.FullName $pside.FullName --repo $repo --target $head --title $title --notes $notes;if($LASTEXITCODE-ne0){throw 'R55.1 release create failed'}}else{if($existing.targetCommitish-ne$head){throw 'Existing R55.1 release target differs from exact build head'};gh release upload $tag $installer.FullName $iside.FullName $portable.FullName $pside.FullName --repo $repo --clobber;if($LASTEXITCODE-ne0){throw 'R55.1 release upload failed'}}
  $release=gh api "repos/$repo/releases/tags/$tag"|ConvertFrom-Json;if($release.target_commitish-ne$head-or$release.draft-or$release.prerelease){throw 'R55.1 published release invalid'}
  foreach($pair in @(@('MerzoWindowsOptimizerSetup-win-x64.exe',$ih),@('MerzoWindowsOptimizer-portable-win-x64.zip',$ph))){$a=$release.assets|Where-Object name -eq $pair[0]|Select-Object -First 1;if(!$a){throw "R55.1 release asset missing $($pair[0])"};if($a.digest-and$a.digest.Substring(7).ToLowerInvariant()-ne$pair[1]){throw "R55.1 release asset digest mismatch $($pair[0])"}}
  [ordered]@{conclusion='success';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]$env:GITHUB_RUN_ID;headSha=$env:GITHUB_SHA;buildRun=$run;buildHead=$head;artifactId=$artifactId;artifactName=$artifactName;artifactDigest=$artifactDigest;tag=$tag;releaseId=[string]$release.node_id;releaseUrl=$release.html_url;installerSha=$ih;portableSha=$ph}|ConvertTo-Json|Set-Content '.\optimizer\R55_1_PUBLISH_STATUS.json' -Encoding UTF8
  Write-Host "R55_1_PUBLICATION_PASS tag=$tag url=$($release.html_url)"

  & '.\optimizer\scripts\r55_1_public_ota_acceptance.ps1' -BuildRun $run -BuildHead $head -ExpectedInstallerSha $ih -ExpectedPortableSha $ph
  if($LASTEXITCODE-ne0){throw 'R55.1 public OTA acceptance failed'}
  [ordered]@{conclusion='success';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]$env:GITHUB_RUN_ID;headSha=$env:GITHUB_SHA;buildRun=$run;buildHead=$head;artifactId=$artifactId;artifactDigest=$artifactDigest;installerSha=$ih;portableSha=$ph;gameRecovery='success';installedCandidate='success';publication='success';publicOta='success'}|ConvertTo-Json|Set-Content $promotion -Encoding UTF8
  Write-Host 'R55_1_FULL_PROMOTION_PASS'
}catch{
  [ordered]@{conclusion='failure';createdAt=(Get-Date).ToUniversalTime().ToString('o');databaseId=[long]($env:GITHUB_RUN_ID??'0');headSha=$env:GITHUB_SHA;error=$_.Exception.Message}|ConvertTo-Json|Set-Content $promotion -Encoding UTF8
  Write-Host "::error::$($_.Exception.Message)";exit 1
}
