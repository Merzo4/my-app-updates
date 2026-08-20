param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'

$source='.\optimizer\scripts\r54_2_game_mutation_acceptance_v11.ps1'
$src=Get-Content $source -Raw
$old='<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup>'
$new='<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><LangVersion>latest</LangVersion><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup>'
if(($src.Split($old).Count-1)-ne1){throw 'R54.2 v12 restore probe project anchor mismatch'}
$src=$src.Replace($old,$new)
$tmp=Join-Path $env:RUNNER_TEMP 'r54_2_game_mutation_acceptance_v11_fixed.ps1'
Set-Content $tmp $src -Encoding UTF8
Write-Host 'R54_2_V12_RESTORE_PROJECT_ANCHOR_ISOLATED'
& $tmp -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v12 failed: $LASTEXITCODE"}
