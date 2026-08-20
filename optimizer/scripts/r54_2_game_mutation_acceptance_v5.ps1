param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance_v4.ps1'
$v4=Get-Content $base -Raw
$tailStart=$v4.IndexOf("$tmp=Join-Path $env:RUNNER_TEMP 'r54_2_game_mutation_acceptance_v4_expanded.ps1'",[StringComparison]::Ordinal)
if($tailStart-lt0){throw 'R54.2 v5 v4 execution tail missing'}
$replacement=@'
# R54.2 v5: instrument the real post-install wait so a disposable runner shows
# exactly what the shipped GAME package is waiting on. This does not change the
# product artifact; it only shortens the diagnostic wait and emits state.
$deadlineOld='$deadline=(Get-Date).AddMinutes(12)'
$deadlineNew='$deadline=(Get-Date).AddMinutes(2)'
if(($src.Split($deadlineOld).Count-1)-ne1){throw 'R54.2 v5 deadline anchor mismatch'}
$src=$src.Replace($deadlineOld,$deadlineNew)

$stateOld='$seenBusy=$false;$fatal=$false;$fatalText='''';$dialogs=[Collections.Generic.List[string]]::new();$completed=$false'
$stateNew=@'
$seenBusy=$false;$fatal=$false;$fatalText='';$dialogs=[Collections.Generic.List[string]]::new();$completed=$false
$diagNext=(Get-Date)
function Write-R542HangDiag([string]$Reason){
    Write-Host "R542_HANG_DIAG_BEGIN reason=$Reason at=$((Get-Date).ToUniversalTime().ToString('o')) appPid=$($proc.Id)"
    try{
        $t=Window-Text $main
        $flat=($t -replace "`r?`n",' | ')
        if($flat.Length-gt1800){$flat=$flat.Substring(0,1800)}
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
            try{$n=$w.Current.Name;$pid=$w.Current.ProcessId;$ct=$w.Current.ControlType.ProgrammaticName;$off=$w.Current.IsOffscreen}catch{continue}
            if($n){
                $n=($n -replace "`r?`n",' ');if($n.Length-gt300){$n=$n.Substring(0,300)}
                Write-Host "R542_HANG_WINDOW pid=$pid type=$ct offscreen=$off name=$n"
            }
        }
    }catch{Write-Host "R542_HANG_WINDOWS_ERROR $($_.Exception.Message)"}
    try{
        $cut=(Get-Date).AddMinutes(-5)
        $roots=@($portable,$env:TEMP,(Join-Path $env:LOCALAPPDATA 'Merzo Windows Optimizer'),(Join-Path $env:APPDATA 'Merzo Windows Optimizer')) | Where-Object {$_ -and (Test-Path $_)} | Select-Object -Unique
        $files=foreach($r in $roots){
            Get-ChildItem $r -Recurse -File -ErrorAction SilentlyContinue | Where-Object {$_.LastWriteTime -ge $cut -and ($_.Extension -in '.log','.json','.txt')} 
        }
        foreach($f in ($files | Sort-Object LastWriteTime -Descending | Select-Object -First 12)){
            Write-Host "R542_HANG_FILE time=$($f.LastWriteTime.ToString('o')) size=$($f.Length) path=$($f.FullName)"
            if($f.Length-gt0 -and $f.Length-lt1048576){
                try{
                    $tail=Get-Content $f.FullName -Tail 5 -ErrorAction Stop
                    foreach($line in $tail){$s=[string]$line;if($s.Length-gt500){$s=$s.Substring(0,500)};Write-Host "R542_HANG_FILE_TAIL $s"}
                }catch{}
            }
        }
    }catch{Write-Host "R542_HANG_FILES_ERROR $($_.Exception.Message)"}
    Write-Host "R542_HANG_DIAG_END reason=$Reason"
}
'@.Trim()
if(($src.Split($stateOld).Count-1)-ne1){throw 'R54.2 v5 state anchor mismatch'}
$src=$src.Replace($stateOld,$stateNew)

$pollOld=@'
    Start-Sleep -Milliseconds 500
    $wins=Get-ProcessWindows $proc.Id
'@.Trim()
$pollNew=@'
    Start-Sleep -Milliseconds 500
    if((Get-Date)-ge$diagNext){Write-R542HangDiag 'poll';$diagNext=(Get-Date).AddSeconds(5)}
    $wins=Get-ProcessWindows $proc.Id
'@.Trim()
if(($src.Split($pollOld).Count-1)-ne1){throw 'R54.2 v5 poll anchor mismatch'}
$src=$src.Replace($pollOld,$pollNew)

$timeoutOld="if(!$completed){try{$proc.Kill()}catch{};throw 'R54.2 GAME package did not complete within timeout'}"
$timeoutNew="if(!$completed){Write-R542HangDiag 'timeout';try{$proc.Kill()}catch{};throw 'R54.2 GAME package did not complete within diagnostic timeout'}"
if(($src.Split($timeoutOld).Count-1)-ne1){throw 'R54.2 v5 timeout anchor mismatch'}
$src=$src.Replace($timeoutOld,$timeoutNew)

$tmp=Join-Path $env:RUNNER_TEMP 'r54_2_game_mutation_acceptance_v5_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v5 failed: $LASTEXITCODE"}
'@
$v5=$v4.Substring(0,$tailStart)+$replacement
$tmpWrapper=Join-Path $env:RUNNER_TEMP 'r54_2_game_mutation_acceptance_v5_wrapper.ps1'
Set-Content $tmpWrapper $v5 -Encoding UTF8
& $tmpWrapper -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v5 wrapper failed: $LASTEXITCODE"}
