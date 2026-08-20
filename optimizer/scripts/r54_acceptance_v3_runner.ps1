$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'r54_public_ota_acceptance.ps1'
$runtime=Join-Path $PSScriptRoot 'r54_public_ota_acceptance_runtime.ps1'
if(!(Test-Path $source)){throw "R54 acceptance source missing: $source"}
$text=(Get-Content $source -Raw).Replace("`r`n","`n")

$oldRelease=@'
  $latest=gh api "repos/$repo/releases/latest" | ConvertFrom-Json
  if($latest.tag_name-ne'mwo-v0.1.54' -or $latest.draft -or $latest.prerelease){throw "Latest stable release is not R54 bridge: $($latest.tag_name)"}
  $asset=$latest.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
  $sideAsset=$latest.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256' | Select-Object -First 1
'@
$newRelease=@'
  # The repository contains multiple products. The repo-global /releases/latest
  # may belong to MerzoStream, so verify the exact MWO tag instead. The installed
  # R53 updater is tested separately below and must still discover R54 by mwo-v.
  $latest=gh api "repos/$repo/releases/tags/mwo-v0.1.54" | ConvertFrom-Json
  if($latest.tag_name-ne'mwo-v0.1.54' -or $latest.draft -or $latest.prerelease){throw "Public R54 bridge release invalid: $($latest.tag_name)"}
  $asset=$latest.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
  $sideAsset=$latest.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256' | Select-Object -First 1
'@
$oldRelease=$oldRelease.Replace("`r`n","`n")
$newRelease=$newRelease.Replace("`r`n","`n")
if(!$text.Contains($oldRelease)){throw 'R54 acceptance exact-release patch anchor missing'}
$text=$text.Replace($oldRelease,$newRelease)

$oldJson=@'
  $json=Get-Content $Catalog -Raw
  $items=[System.Text.Json.JsonSerializer]::Deserialize($json,$listType)
'@
$newJson=@'
  $json=Get-Content $Catalog -Raw
  $options=[System.Text.Json.JsonSerializerOptions]::new()
  $options.PropertyNamingPolicy=[System.Text.Json.JsonNamingPolicy]::SnakeCaseLower
  $options.PropertyNameCaseInsensitive=$true
  $options.Converters.Add([System.Text.Json.Serialization.JsonStringEnumConverter]::new())
  $items=[System.Text.Json.JsonSerializer]::Deserialize($json,$listType,$options)
'@
$oldJson=$oldJson.Replace("`r`n","`n")
$newJson=$newJson.Replace("`r`n","`n")
if(!$text.Contains($oldJson)){throw 'R54 acceptance JSON-options patch anchor missing'}
$text=$text.Replace($oldJson,$newJson)

$oldSafety=@'
  $safetyType=$asm.GetTypes() | Where-Object {$_.FullName -match 'SafetyEngine$'} | Select-Object -First 1
'@
$newSafety=@'
  $safetyType=$asm.GetTypes() | Where-Object {$_.FullName -match 'SafetyEngine$' -and -not $_.IsInterface -and -not $_.IsAbstract} | Select-Object -First 1
'@
$oldSafety=$oldSafety.Replace("`r`n","`n")
$newSafety=$newSafety.Replace("`r`n","`n")
if(!$text.Contains($oldSafety)){throw 'R54 acceptance concrete SafetyEngine patch anchor missing'}
$text=$text.Replace($oldSafety,$newSafety)

Set-Content $runtime $text -Encoding UTF8
try {
  & $runtime
  if($LASTEXITCODE-ne0){throw "R54 runtime acceptance failed: $LASTEXITCODE"}
}
finally {
  Remove-Item $runtime -Force -ErrorAction SilentlyContinue
}
