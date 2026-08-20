param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'

$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$src=Get-Content $base -Raw
$startMarker='# Verify that the installed package left a usable Undo contract.'
$statusMarker='@{' + "`r`n" + "  conclusion='success'"
$start=$src.IndexOf($startMarker,[StringComparison]::Ordinal)
if($start-lt0){throw 'R54.2 v9 Undo section start marker missing'}
$status=$src.IndexOf($statusMarker,$start,[StringComparison]::Ordinal)
if($status-lt0){$statusMarker='@{' + "`n" + "  conclusion='success'";$status=$src.IndexOf($statusMarker,$start,[StringComparison]::Ordinal)}
if($status-lt0){throw 'R54.2 v9 final status marker missing'}

$recovery=@'
# Real Recovery navigation must invoke/select the parent navigation control,
# not merely click the child TextBlock named "Восстановление".
function Invoke-R542ParentFirst([System.Windows.Automation.AutomationElement]$El){
    if(!$El){return $false}
    $cur=$El
    for($depth=0;$depth-lt8 -and $cur;$depth++){
        try{
            $ct=$cur.Current.ControlType.ProgrammaticName
            $name=$cur.Current.Name
            $p=$cur.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
            ([System.Windows.Automation.SelectionItemPattern]$p).Select()
            Write-Host "R542_RECOVERY_NAV select depth=$depth type=$ct name=$name"
            return $true
        }catch{}
        try{
            $ct=$cur.Current.ControlType.ProgrammaticName
            $name=$cur.Current.Name
            $p=$cur.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
            ([System.Windows.Automation.InvokePattern]$p).Invoke()
            Write-Host "R542_RECOVERY_NAV invoke depth=$depth type=$ct name=$name"
            return $true
        }catch{}
        try{$cur=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($cur)}catch{$cur=$null}
    }
    return $false
}

$recoveryNav=Find-NameContains $main 'Восстановление'
if(!$recoveryNav){try{$proc.Kill()}catch{};throw 'R54.2 recovery navigation control missing'}
if(!(Invoke-R542ParentFirst $recoveryNav)){try{$proc.Kill()}catch{};throw 'R54.2 recovery parent navigation not invokable'}

$pageReady=$false
$deadlineRecovery=(Get-Date).AddSeconds(12)
while((Get-Date)-lt$deadlineRecovery -and !$pageReady){
    Start-Sleep -Milliseconds 400
    foreach($candidate in (Get-ProcessWindows $proc.Id)){
        $candidateText=Window-Text $candidate
        if($candidateText -match 'Merzo Windows Optimizer' -and ($candidateText -match '(?i)Restore All|Restore snapshot|Safe recovery|активн.*snapshot|восстанов.*snapshot|точк.*восстанов')){
            $main=$candidate;$pageReady=$true;break
        }
    }
}
$recoveryText=Window-Text $main
$flatRecovery=($recoveryText -replace "`r?`n",' | ')
if($flatRecovery.Length-gt16000){$flatRecovery=$flatRecovery.Substring(0,16000)}
Write-Host "R542_RECOVERY_PAGE_TEXT $flatRecovery"
if(!$pageReady){try{$proc.Kill()}catch{};throw 'R54.2 Recovery page did not become active after parent navigation'}

$found=0
foreach($e in (Get-Desc $main)){
    try{$n=$e.Current.Name;$ct=$e.Current.ControlType.ProgrammaticName;$enabled=$e.Current.IsEnabled;$off=$e.Current.IsOffscreen;$r=$e.Current.BoundingRectangle}catch{continue}
    if($n -and $n -match '(?i)restore|undo|snapshot|восстанов|откат|автовосстанов|последн|вернуть'){
        $safe=($n -replace "`r?`n",' ');if($safe.Length-gt700){$safe=$safe.Substring(0,700)}
        Write-Host "R542_RECOVERY_CONTROL name=$safe type=$ct enabled=$enabled offscreen=$off x=$($r.X) y=$($r.Y) w=$($r.Width) h=$($r.Height)"
        $found++
    }
}
Write-Host "R54_2_RECOVERY_PAGE_DISCOVERY_PASS controls=$found"
try{$proc.Kill()}catch{}
throw 'R54.2 RECOVERY_PAGE_DISCOVERY_COMPLETE'

'@
$src=$src.Substring(0,$start)+$recovery+$src.Substring($status)
Set-Content $base $src -Encoding UTF8
Write-Host 'R54_2_V9_RECOVERY_PARENT_NAV_READY'
& '.\optimizer\scripts\r54_2_game_mutation_acceptance_v6.ps1' -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v9 failed: $LASTEXITCODE"}
