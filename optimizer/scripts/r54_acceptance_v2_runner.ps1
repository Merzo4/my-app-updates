$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'r54_public_ota_acceptance.ps1'
$runtime=Join-Path $PSScriptRoot 'r54_public_ota_acceptance_runtime.ps1'
if(!(Test-Path $source)){throw "R54 acceptance source missing: $source"}
$text=(Get-Content $source -Raw).Replace("`r`n","`n")
$old="  `$json=Get-Content `$Catalog -Raw`n  `$items=[System.Text.Json.JsonSerializer]::Deserialize(`$json,`$listType)"
$new="  `$json=Get-Content `$Catalog -Raw`n  `$options=[System.Text.Json.JsonSerializerOptions]::new()`n  `$options.PropertyNamingPolicy=[System.Text.Json.JsonNamingPolicy]::SnakeCaseLower`n  `$options.PropertyNameCaseInsensitive=`$true`n  `$options.Converters.Add([System.Text.Json.Serialization.JsonStringEnumConverter]::new())`n  `$items=[System.Text.Json.JsonSerializer]::Deserialize(`$json,`$listType,`$options)"
$count=$text.Split($old).Count-1
if($count-ne1){throw "R54 acceptance exact JSON-options anchor count=$count"}
$patched=$text.Replace($old,$new)
Set-Content $runtime $patched -Encoding UTF8
try {
  & $runtime
  if($LASTEXITCODE-ne0){throw "R54 runtime acceptance failed: $LASTEXITCODE"}
}
finally {
  Remove-Item $runtime -Force -ErrorAction SilentlyContinue
}
