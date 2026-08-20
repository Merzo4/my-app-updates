param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'

# Instrument only the disposable acceptance base script in this CI checkout.
# Product binaries/artifacts are immutable and are not modified here.
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$src=Get-Content $base -Raw

$deadlineOld='$deadline=(Get-Date).AddMinutes(12)'
$deadlineNew='$deadline=(Get-Date).AddMinutes(2)'
if(!$src.Contains($deadlineOld)){throw 'R54.2 v6 deadline anchor mismatch'}
$src=$src.Replace($deadlineOld,$deadlineNew)

$stateOld='$seenBusy=$false;$fatal=$false;$fatalText='''';$dialogs=[Collections.Generic.List[string]]::new();$completed=$false'
if(!$src.Contains($stateOld)){throw 'R54.2 v6 state anchor mismatch'}
$diag=@'
$diagNext=(Get-Date)
$mainOneDriveAnswered=$false
$mainApplyAnswered=$false
$mainOneDriveLeftAcknowledged=$false
function Invoke-R542ExactButton([System.Windows.Automation.AutomationElement]$Root,[string]$Name,[string]$Reason){
    foreach($e in (Get-Desc $Root)){
        try{$n=$e.Current.Name;$ct=$e.Current.ControlType;$enabled=$e.Current.IsEnabled;$off=$e.Current.IsOffscreen}catch{continue}
        if($n -eq $Name -and $ct -eq [System.Windows.Automation.ControlType]::Button -and $enabled -and !$off){
            if(Invoke-Element $e){Write-Host "R542_INLINE_ACTION reason=$Reason button=$Name";return $true}
        }
    }
    Write-Host "R542_INLINE_ACTION_MISSING reason=$Reason button=$Name"
    return $false
}
function Invoke-R542ButtonNearText([System.Windows.Automation.AutomationElement]$Root,[string]$Anchor,[string]$ButtonName,[string]$Reason){
    $anchorEl=Find-NameContains $Root $Anchor
    if(!$anchorEl){Write-Host "R542_INLINE_ANCHOR_MISSING reason=$Reason anchor=$Anchor";return $false}
    $cur=$anchorEl
    for($depth=0;$depth-lt8 -and $cur;$depth++){
        foreach($e in (Get-Desc $cur)){
            try{$n=$e.Current.Name;$ct=$e.Current.ControlType;$enabled=$e.Current.IsEnabled;$off=$e.Current.IsOffscreen}catch{continue}
            if($n -eq $ButtonName -and $ct -eq [System.Windows.Automation.ControlType]::Button -and $enabled -and !$off){
                if(Invoke-Element $e){Write-Host "R542_INLINE_CONTEXT_ACTION reason=$Reason anchor=$Anchor button=$ButtonName depth=$depth";return $true}
            }
        }
        try{$cur=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($cur)}catch{$cur=$null}
    }
    Write-Host "R542_INLINE_CONTEXT_ACTION_MISSING reason=$Reason anchor=$Anchor button=$ButtonName"
    return $false
}
function Handle-R542MainInlinePrompt{
    try{$txt=Window-Text $main}catch{return}
    if(!$mainOneDriveAnswered -and $txt -match 'OneDrive установлен, но настроенный аккаунт не обнаружен' -and $txt -match 'Да — удалить только приложение OneDrive'){
        if(Invoke-R542ExactButton $main 'Да' 'onedrive-unconfigured'){$script:mainOneDriveAnswered=$true;Start-Sleep -Milliseconds 500}
        return
    }
    if(!$mainApplyAnswered -and $txt -match 'Применить выбранный пакет'){
        if(Invoke-R542ExactButton $main 'Да' 'apply-package-confirm'){$script:mainApplyAnswered=$true;Start-Sleep -Milliseconds 500}
        return
    }
    if(!$mainOneDriveLeftAcknowledged -and $txt -match 'OneDrive оставлен' -and $txt -match 'ВАЖНО'){
        if(Invoke-R542ButtonNearText $main 'OneDrive оставлен' 'Понятно' 'onedrive-left-warning'){$script:mainOneDriveLeftAcknowledged=$true;Start-Sleep -Milliseconds 500}
        return
    }
}
function Write-R542HangDiag([string]$Reason){
    Write-Host "R542_HANG_DIAG_BEGIN reason=$Reason at=$((Get-Date).ToUniversalTime().ToString('o')) appPid=$($proc.Id)"
    try{
        $t=Window-Text $main
        $flat=($t -replace "`r?`n",' | ')
        if($flat.Length-gt3200){$flat=$flat.Substring(0,3200)}
        Write-Host "R542_HANG_MAIN $flat"
    }catch{Write-Host "R542_HANG_MAIN_ERROR $($_.Exception.Message)"}
    try{
        $ib=Find-NameContains $main 'Установить сборку'
        if($ib){Write-Host "R542_HANG_INSTALL enabled=$($ib.Current.IsEnabled) offscreen=$($ib.Current.IsOffscreen) name=$($ib.Current.Name)"}
        else{Write-Host 'R542_HANG_INSTALL missing'}
    }catch{Write-Host "R542_HANG_INSTALL_ERROR $($_.Exception.Message)"}
    try{
        $marker=Join-Path $env:ProgramData 'MerzoR542OneDriveDummy.marker'
        Write-Host "R542_HANG_ONEDRIVE_MARKER exists=$(Test-Path $marker) path=$marker"
    }catch{}
    try{
        $all=Get-CimInstance Win32_Process
        $interesting=$all | Where-Object {
            $_.ProcessId -eq $proc.Id -or $_.ParentProcessId -eq $proc.Id -or
            $_.Name -match '^(Merzo|OneDrive|consent|sc\.exe|cmd\.exe|powershell\.exe|pwsh\.exe|conhost\.exe|RuntimeBroker\.exe|taskhostw\.exe|TiWorker\.exe)'
        } | Sort-Object ProcessId
        foreach($p in $interesting){
            $cmd=($p.CommandLine -replace "`r?`n",' ')
            if($cmd -and $cmd.Length-gt700){$cmd=$cmd.Substring(0,700)}
            Write-Host "R542_HANG_PROC pid=$($p.ProcessId) ppid=$($p.ParentProcessId) name=$($p.Name) cmd=$cmd"
        }
    }catch{Write-Host "R542_HANG_PROC_ERROR $($_.Exception.Message)"}
    try{
        foreach($w in [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)){
            try{$n=$w.Current.Name;$wpid=$w.Current.ProcessId;$ct=$w.Current.ControlType.ProgrammaticName;$off=$w.Current.IsOffscreen}catch{continue}
            if($n){
                $n=($n -replace "`r?`n",' ')
                if($n.Length-gt350){$n=$n.Substring(0,350)}
                Write-Host "R542_HANG_WINDOW pid=$wpid type=$ct offscreen=$off name=$n"
            }
        }
    }catch{Write-Host "R542_HANG_WINDOWS_ERROR $($_.Exception.Message)"}
    Write-Host "R542_HANG_DIAG_END reason=$Reason"
}
'@.Trim()
$src=$src.Replace($stateOld,$stateOld+"`r`n"+$diag)

$pollOld="    Start-Sleep -Milliseconds 500`r`n    `$wins=Get-ProcessWindows `$proc.Id"
if(!$src.Contains($pollOld)){$pollOld="    Start-Sleep -Milliseconds 500`n    `$wins=Get-ProcessWindows `$proc.Id"}
if(!$src.Contains($pollOld)){throw 'R54.2 v6 poll anchor mismatch'}
$pollNew="    Start-Sleep -Milliseconds 500`r`n    Handle-R542MainInlinePrompt`r`n    if((Get-Date)-ge`$diagNext){Write-R542HangDiag 'poll';`$diagNext=(Get-Date).AddSeconds(5)}`r`n    `$wins=Get-ProcessWindows `$proc.Id"
if($pollOld.Contains("`n") -and !$pollOld.Contains("`r`n")){$pollNew=$pollNew.Replace("`r`n","`n")}
$src=$src.Replace($pollOld,$pollNew)

$timeoutOld="if(!`$completed){try{`$proc.Kill()}catch{};throw 'R54.2 GAME package did not complete within timeout'}"
$timeoutNew="if(!`$completed){Write-R542HangDiag 'timeout';try{`$proc.Kill()}catch{};throw 'R54.2 GAME package did not complete within diagnostic timeout'}"
if(!$src.Contains($timeoutOld)){throw 'R54.2 v6 timeout anchor mismatch'}
$src=$src.Replace($timeoutOld,$timeoutNew)

Set-Content $base $src -Encoding UTF8
Write-Host 'R54_2_V6_DIAGNOSTIC_INSTRUMENTATION_READY'
& '.\optimizer\scripts\r54_2_game_mutation_acceptance_v4.ps1' -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v6 failed: $LASTEXITCODE"}
