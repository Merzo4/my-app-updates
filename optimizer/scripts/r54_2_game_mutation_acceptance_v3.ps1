param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance_v2.ps1'
$src=Get-Content $base -Raw

$old=@'
$navNew=@'
$buildNav=Find-NameContains $main 'Сборки'
if(!(Invoke-Element $buildNav)){try{$proc.Kill()}catch{};throw 'R54.2 GAME could not open Builds page'}
Start-Sleep -Seconds 1
foreach($candidate in (Get-ProcessWindows $proc.Id)){
    $candidateText=Window-Text $candidate
    if($candidateText -match 'Сборки Windows'){$main=$candidate;break}
}
$game=Find-NameContains $main 'Выбрать GAME'
if(!$game){
    foreach($e in (Get-Desc $main)){
        try{$n=$e.Current.Name;$ct=$e.Current.ControlType.ProgrammaticName;$r=$e.Current.BoundingRectangle}catch{continue}
        if($n -and ($n -match 'GAME|Выбрать')){Write-Host "R542_UI_DISCOVERY name=$n type=$ct x=$($r.X) y=$($r.Y) w=$($r.Width) h=$($r.Height)"}
    }
}
if(!(Invoke-Element $game)){try{$proc.Kill()}catch{};throw 'R54.2 GAME select button not invokable'}
'@.Trim()
'@
$new=@'
$navNew=@'
# Prefer the real dashboard action button. It reaches the same Builds page but
# exposes a proper InvokePattern on hosted Windows, unlike the sidebar TextBlock.
$openBuilds=Find-NameContains $main 'Выбрать сборку'
if(!$openBuilds){$openBuilds=Find-NameContains $main 'Сборки'}
if(!(Invoke-Element $openBuilds)){try{$proc.Kill()}catch{};throw 'R54.2 GAME could not open Builds page'}
$deadlinePage=(Get-Date).AddSeconds(8)
$pageReady=$false
while((Get-Date)-lt$deadlinePage -and !$pageReady){
    Start-Sleep -Milliseconds 350
    foreach($candidate in (Get-ProcessWindows $proc.Id)){
        $candidateText=Window-Text $candidate
        if($candidateText -match 'Сборки Windows' -and $candidateText -match 'Выбрать GAME'){$main=$candidate;$pageReady=$true;break}
    }
}
if(!$pageReady){
    $txt=Window-Text $main
    try{$proc.Kill()}catch{}
    throw "R54.2 GAME Builds page did not become ready. UI=$txt"
}
Write-Host 'R54_2_GAME_BUILDS_PAGE_PASS'
$game=Find-NameContains $main 'Выбрать GAME'
if(!$game){
    foreach($e in (Get-Desc $main)){
        try{$n=$e.Current.Name;$ct=$e.Current.ControlType.ProgrammaticName;$r=$e.Current.BoundingRectangle}catch{continue}
        if($n -and ($n -match 'GAME|Выбрать')){Write-Host "R542_UI_DISCOVERY name=$n type=$ct x=$($r.X) y=$($r.Y) w=$($r.Width) h=$($r.Height)"}
    }
}
if(!(Invoke-Element $game)){try{$proc.Kill()}catch{};throw 'R54.2 GAME select button not invokable'}
'@.Trim()
'@
if(($src.Split($old).Count-1)-ne1){throw 'R54.2 v3 dashboard navigation anchor mismatch'}
$src=$src.Replace($old,$new)

$tmp=Join-Path $env:RUNNER_TEMP 'r54_2_game_mutation_acceptance_v3_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v3 failed: $LASTEXITCODE"}
