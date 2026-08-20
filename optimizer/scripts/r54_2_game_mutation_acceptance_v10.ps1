param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$src=Get-Content $base -Raw
$startMarker='# Verify that the installed package left a usable Undo contract.'
$statusMarker='@{' + "`r`n" + "  conclusion='success'"
$start=$src.IndexOf($startMarker,[StringComparison]::Ordinal);if($start-lt0){throw 'R54.2 v10 Undo section start marker missing'}
$status=$src.IndexOf($statusMarker,$start,[StringComparison]::Ordinal);if($status-lt0){$statusMarker='@{' + "`n" + "  conclusion='success'";$status=$src.IndexOf($statusMarker,$start,[StringComparison]::Ordinal)}
if($status-lt0){throw 'R54.2 v10 final status marker missing'}
$recovery=@'
$recoveryTextEl=Find-NameContains $main 'Восстановление'
if(!$recoveryTextEl){try{$proc.Kill()}catch{};throw 'R54.2 recovery navigation text missing'}
$cur=$recoveryTextEl;$radio=$null
for($depth=0;$depth-lt8 -and $cur;$depth++){
    try{$ct=$cur.Current.ControlType}catch{$ct=$null}
    if($ct -eq [System.Windows.Automation.ControlType]::RadioButton){$radio=$cur;break}
    try{$cur=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($cur)}catch{$cur=$null}
}
if(!$radio){try{$proc.Kill()}catch{};throw 'R54.2 recovery parent RadioButton missing'}
try{
    $rr=$radio.Current.BoundingRectangle
    Write-Host "R542_RECOVERY_RADIO x=$($rr.X) y=$($rr.Y) w=$($rr.Width) h=$($rr.Height) enabled=$($radio.Current.IsEnabled) offscreen=$($radio.Current.IsOffscreen)"
    if($rr.Width-le1 -or $rr.Height-le1){throw 'invalid Recovery radio bounds'}
    [MerzoUiNative]::Click([int]($rr.X+$rr.Width/2),[int]($rr.Y+$rr.Height/2))
}catch{try{$proc.Kill()}catch{};throw "R54.2 recovery radio click failed: $($_.Exception.Message)"}

$pageReady=$false;$deadlineRecovery=(Get-Date).AddSeconds(12)
while((Get-Date)-lt$deadlineRecovery -and !$pageReady){
    Start-Sleep -Milliseconds 400
    foreach($candidate in (Get-ProcessWindows $proc.Id)){
        $candidateText=Window-Text $candidate
        if($candidateText -match 'Merzo Windows Optimizer' -and $candidateText -notmatch 'Сборки Windows' -and $candidateText -match '(?i)restore|snapshot|восстанов|откат|undo'){$main=$candidate;$pageReady=$true;break}
    }
}
$rt=Window-Text $main;$flat=($rt-replace "`r?`n",' | ');if($flat.Length-gt16000){$flat=$flat.Substring(0,16000)};Write-Host "R542_RECOVERY_PAGE_TEXT $flat"
if(!$pageReady){try{$proc.Kill()}catch{};throw 'R54.2 Recovery page did not become active after RadioButton click'}
$found=0
foreach($e in (Get-Desc $main)){
  try{$n=$e.Current.Name;$ct=$e.Current.ControlType.ProgrammaticName;$enabled=$e.Current.IsEnabled;$off=$e.Current.IsOffscreen;$r=$e.Current.BoundingRectangle}catch{continue}
  if($n -and $n -match '(?i)restore|undo|snapshot|восстанов|откат|автовосстанов|последн|вернуть'){$safe=($n-replace "`r?`n",' ');if($safe.Length-gt700){$safe=$safe.Substring(0,700)};Write-Host "R542_RECOVERY_CONTROL name=$safe type=$ct enabled=$enabled offscreen=$off x=$($r.X) y=$($r.Y) w=$($r.Width) h=$($r.Height)";$found++}
}
Write-Host "R54_2_RECOVERY_PAGE_DISCOVERY_PASS controls=$found"
try{$proc.Kill()}catch{}
throw 'R54.2 RECOVERY_PAGE_DISCOVERY_COMPLETE'

'@
$src=$src.Substring(0,$start)+$recovery+$src.Substring($status)
Set-Content $base $src -Encoding UTF8
Write-Host 'R54_2_V10_RECOVERY_RADIO_CLICK_READY'
& '.\optimizer\scripts\r54_2_game_mutation_acceptance_v6.ps1' -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v10 failed: $LASTEXITCODE"}
