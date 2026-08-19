param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$src=Get-Content $base -Raw
$old='await using var broker=new ElevatedOperationBroker(portable);'
$new='var brokerLogs=Path.Combine(Path.GetTempPath(),"mwo-r542-broker-logs-"+Guid.NewGuid().ToString("N")); Directory.CreateDirectory(brokerLogs); await using var broker=new ElevatedOperationBroker(portable,portable,brokerLogs);'
if(($src.Split($old).Count-1)-ne1){throw 'R54.2 mutation broker constructor anchor mismatch'}
$src=$src.Replace($old,$new)
$tmp=Join-Path $env:RUNNER_TEMP 'r54_2_game_mutation_acceptance_v2_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v2 failed: $LASTEXITCODE"}
