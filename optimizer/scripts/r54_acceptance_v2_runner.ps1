$ErrorActionPreference='Stop'
$source=Join-Path $PSScriptRoot 'r54_public_ota_acceptance.ps1'
$runtime=Join-Path $PSScriptRoot 'r54_public_ota_acceptance_runtime.ps1'
if(!(Test-Path $source)){throw "R54 acceptance source missing: $source"}
$text=Get-Content $source -Raw
# PowerShell single-quoted strings do not consume backslashes, so regex tokens
# use one backslash each. This matches the exact two-line safety probe anchor.
$pattern='(?m)^  \$json=Get-Content \$Catalog -Raw\r?\n  \$items=\[System\.Text\.Json\.JsonSerializer\]::Deserialize\(\$json,\$listType\)$'
# The JSON below is written with doubled slashes by the GitHub API transport;
# normalize the regex string to the intended single-backslash form explicitly.
$pattern=$pattern.Replace('\\','\')
$replacement="  `$json=Get-Content `$Catalog -Raw`n  `$options=[System.Text.Json.JsonSerializerOptions]::new()`n  `$options.PropertyNamingPolicy=[System.Text.Json.JsonNamingPolicy]::SnakeCaseLower`n  `$options.PropertyNameCaseInsensitive=`$true`n  `$options.Converters.Add([System.Text.Json.Serialization.JsonStringEnumConverter]::new())`n  `$items=[System.Text.Json.JsonSerializer]::Deserialize(`$json,`$listType,`$options)"
$matches=[regex]::Matches($text,$pattern)
if($matches.Count-ne1){throw "R54 acceptance JSON-options patch anchor count=$($matches.Count)"}
$patched=[regex]::Replace($text,$pattern,$replacement,1)
Set-Content $runtime $patched -Encoding UTF8
try {
  & $runtime
  if($LASTEXITCODE-ne0){throw "R54 runtime acceptance failed: $LASTEXITCODE"}
}
finally {
  Remove-Item $runtime -Force -ErrorAction SilentlyContinue
}
