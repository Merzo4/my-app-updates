param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'

# Rewrite only the disposable acceptance script. Product artifact remains immutable.
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$src=Get-Content $base -Raw
$startMarker='# Verify that the installed package left a usable Undo contract.'
$statusMarker='@{' + "`r`n" + "  conclusion='success'"
$start=$src.IndexOf($startMarker,[StringComparison]::Ordinal)
if($start-lt0){throw 'R54.2 v8 Undo section start marker missing'}
$status=$src.IndexOf($statusMarker,$start,[StringComparison]::Ordinal)
if($status-lt0){
  $statusMarker='@{' + "`n" + "  conclusion='success'"
  $status=$src.IndexOf($statusMarker,$start,[StringComparison]::Ordinal)
}
if($status-lt0){throw 'R54.2 v8 final status marker missing'}

$recovery=@'
# R54.2 disposable real-Recovery discovery after the completed GAME mutation.
$recoveryNav=Find-NameContains $main 'Восстановление'
if(!$recoveryNav){
    try{$proc.Kill()}catch{}
    throw 'R54.2 recovery navigation control missing'
}
if(!(Invoke-Element $recoveryNav)){
    try{$proc.Kill()}catch{}
    throw 'R54.2 recovery navigation not invokable'
}
Start-Sleep -Seconds 2

# Refresh the page host because navigation can replace the WPF content tree.
foreach($candidate in (Get-ProcessWindows $proc.Id)){
    $candidateText=Window-Text $candidate
    if($candidateText -match 'Восстановление' -and $candidateText -match 'Merzo Windows Optimizer'){$main=$candidate}
}
$recoveryText=Window-Text $main
$flatRecovery=($recoveryText -replace "`r?`n",' | ')
if($flatRecovery.Length-gt12000){$flatRecovery=$flatRecovery.Substring(0,12000)}
Write-Host "R542_RECOVERY_PAGE_TEXT $flatRecovery"

$found=0
foreach($e in (Get-Desc $main)){
    try{
        $n=$e.Current.Name
        $ct=$e.Current.ControlType.ProgrammaticName
        $enabled=$e.Current.IsEnabled
        $off=$e.Current.IsOffscreen
        $r=$e.Current.BoundingRectangle
    }catch{continue}
    if($n -and $n -match '(?i)restore|undo|snapshot|восстанов|откат|автовосстанов|последн|вернуть'){
        $safe=($n -replace "`r?`n",' ')
        if($safe.Length-gt700){$safe=$safe.Substring(0,700)}
        Write-Host "R542_RECOVERY_CONTROL name=$safe type=$ct enabled=$enabled offscreen=$off x=$($r.X) y=$($r.Y) w=$($r.Width) h=$($r.Height)"
        $found++
    }
}
Write-Host "R54_2_RECOVERY_DISCOVERY_PASS controls=$found"
try{$proc.Kill()}catch{}
throw 'R54.2 RECOVERY_DISCOVERY_COMPLETE'

'@
$src=$src.Substring(0,$start)+$recovery+$src.Substring($status)
Set-Content $base $src -Encoding UTF8

Write-Host 'R54_2_V8_RECOVERY_DISCOVERY_READY'
& '.\optimizer\scripts\r54_2_game_mutation_acceptance_v6.ps1' -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v8 failed: $LASTEXITCODE"}
