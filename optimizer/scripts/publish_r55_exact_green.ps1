param()
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$repo='Merzo4/my-app-updates'
$buildRun=32355454110
$buildHead='d99d61fd5f34eb1ca5331359343c950b33fc3681'
$artifactId=9401609214
$artifactName='MerzoWindowsOptimizer-0.1.55-PROCESS-STABILITY-CANDIDATE'
$artifactDigest='sha256:3fe7ca12ac79499e0e377dbceb178063f16c0c6f40665ffb102f681034206983'
$installerSha='b845ecd3d46b0f552ae8c80acc48ad2deded6e1801cbe7e28c6a488f0e56fc2f'
$portableSha='044900a8ab3ed17cb3441a0afff2627229de19b7b1fb32b405256b01f818dbe5'
$tag='mwo-v0.1.55'
$title='Merzo Windows Optimizer 0.1.55 — Process Stability / Delayed Start'

$ci=Get-Content '.\optimizer\R55_CI_STATUS.json' -Raw | ConvertFrom-Json
$game=Get-Content '.\optimizer\R55_GAME_RECOVERY_STATUS.json' -Raw | ConvertFrom-Json
$installed=Get-Content '.\optimizer\R55_INSTALLED_CANDIDATE_STATUS.json' -Raw | ConvertFrom-Json
if($ci.conclusion-ne'success' -or [long]$ci.databaseId-ne$buildRun -or $ci.headSha-ne$buildHead -or $ci.installerSha-ne$installerSha -or $ci.portableSha-ne$portableSha){throw 'R55 CI provenance is not exact-green'}
if($game.conclusion-ne'success' -or [long]$game.buildRun-ne$buildRun -or $game.buildHead-ne$buildHead -or [long]$game.artifactId-ne$artifactId -or $game.artifactDigest-ne$artifactDigest -or $game.installerSha-ne$installerSha -or $game.portableSha-ne$portableSha -or $game.gameFullMutation-ne'success' -or $game.recoveryRestoreAll-ne'success' -or $game.recoveryStateVerification-ne'success'){throw 'R55 GAME/Recovery provenance is not exact-green'}
if($installed.conclusion-ne'success' -or [long]$installed.buildRun-ne$buildRun -or $installed.buildHead-ne$buildHead -or $installed.installerSha-ne$installerSha -or $installed.portableSha-ne$portableSha -or $installed.installedVersion-ne'0.1.55.0' -or $installed.payloadMatch-ne'success' -or $installed.launch-ne'success' -or $installed.uninstallRegistration-ne'success'){throw 'R55 installed candidate provenance is not exact-green'}

$artifactDir=Resolve-Path '.\artifact'
$installer=Get-ChildItem $artifactDir -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
$installerSide=Get-ChildItem $artifactDir -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256' | Select-Object -First 1
$portable=Get-ChildItem $artifactDir -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip' | Select-Object -First 1
$portableSide=Get-ChildItem $artifactDir -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256' | Select-Object -First 1
if(!$installer -or !$installerSide -or !$portable -or !$portableSide){throw 'R55 exact artifact payload incomplete'}
$actualInstaller=(Get-FileHash $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$actualPortable=(Get-FileHash $portable.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
if($actualInstaller-ne$installerSha){throw "R55 installer SHA mismatch: $actualInstaller"}
if($actualPortable-ne$portableSha){throw "R55 portable SHA mismatch: $actualPortable"}
$declaredInstaller=((Get-Content $installerSide.FullName -Raw)-split '\s+')[0].ToLowerInvariant()
$declaredPortable=((Get-Content $portableSide.FullName -Raw)-split '\s+')[0].ToLowerInvariant()
if($declaredInstaller-ne$installerSha -or $declaredPortable-ne$portableSha){throw 'R55 sidecar SHA mismatch'}
Write-Host "R55_EXACT_ARTIFACT_SHA_PASS installer=$actualInstaller portable=$actualPortable"

$notes=@'
## Merzo Windows Optimizer 0.1.55 — Process Stability / Delayed Start

Крупный cumulative-блок диагностики роста процессов после входа в Windows.

- временной аудит процессов: старт / 1 / 5 / 10 / 15 минут;
- показывает процессы, появившиеся после стартового снимка, и рост по семействам;
- сопоставляет источники: автозагрузка, Scheduled Tasks, службы и системные компоненты;
- защищает критические системные процессы от автоматической зачистки;
- неизвестные источники остаются read-only до подтверждения;
- сохранены и повторно проверены GAME, OneDrive reliability и production RestoreAll.

Проверено на disposable Windows Server 2025. Публикуется exact artifact build-run 32355454110 без пересборки.
'@

$existing=$null
try {$existing=gh release view $tag --repo $repo --json id,tagName,url 2>$null | ConvertFrom-Json} catch {}
$reused=$false
if(!$existing){
  gh release create $tag $installer.FullName $installerSide.FullName $portable.FullName $portableSide.FullName --repo $repo --target $buildHead --title $title --notes $notes
  if($LASTEXITCODE-ne0){throw 'R55 release create failed'}
}else{
  $reused=$true
  gh release upload $tag $installer.FullName $installerSide.FullName $portable.FullName $portableSide.FullName --repo $repo --clobber
  if($LASTEXITCODE-ne0){throw 'R55 release upload failed'}
}
$release=gh release view $tag --repo $repo --json id,tagName,url,targetCommitish,assets | ConvertFrom-Json
if(!$release){throw 'R55 published release not readable'}
$assetNames=@($release.assets | ForEach-Object {$_.name})
foreach($required in @('MerzoWindowsOptimizerSetup-win-x64.exe','MerzoWindowsOptimizerSetup-win-x64.exe.sha256','MerzoWindowsOptimizer-portable-win-x64.zip','MerzoWindowsOptimizer-portable-win-x64.zip.sha256')){if($assetNames-notcontains$required){throw "R55 release asset missing: $required"}}

$status=[ordered]@{
  conclusion='success'
  createdAt=(Get-Date).ToUniversalTime().ToString('o')
  databaseId=[long]$env:GITHUB_RUN_ID
  headSha=$env:GITHUB_SHA
  buildRun=$buildRun
  buildHead=$buildHead
  artifactId=$artifactId
  artifactName=$artifactName
  artifactDigest=$artifactDigest
  tag=$tag
  releaseId=[long]$release.id
  releaseUrl=$release.url
  installerSha=$installerSha
  portableSha=$portableSha
  reusedExistingRelease=$reused
}
$status|ConvertTo-Json|Set-Content '.\optimizer\R55_PUBLISH_STATUS.json' -Encoding UTF8
Write-Host "R55_PUBLICATION_PASS tag=$tag releaseId=$($release.id) reused=$reused"
