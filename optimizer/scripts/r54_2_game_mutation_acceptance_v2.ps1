param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$src=Get-Content $base -Raw

# Instantiate the production broker with isolated snapshot/log/backup folders.
# The broker resolves MerzoOptimizer.ElevatedHelper.exe beside the test host,
# matching the real packaged application layout.
$old='await using var broker=new ElevatedOperationBroker(portable);'
$new=@'
var brokerCtor=typeof(ElevatedOperationBroker).GetConstructors().Single(c=>c.GetParameters().Length==3 && c.GetParameters().All(p=>p.ParameterType==typeof(string)));
var brokerParams=brokerCtor.GetParameters();
Console.WriteLine("R542_BROKER_CTOR "+string.Join(",",brokerParams.Select(p=>$"{p.Name}:{p.ParameterType.Name}")));
var brokerTemp=Path.Combine(Path.GetTempPath(),"mwo-r542-broker-"+Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(brokerTemp);
object?[] brokerArgs=brokerParams.Select(p=>
{
    var n=p.Name??string.Empty;
    if(n.Contains("snapshot",StringComparison.OrdinalIgnoreCase)) return (object?)brokerTemp;
    if(n.Contains("log",StringComparison.OrdinalIgnoreCase)) return (object?)brokerTemp;
    if(n.Contains("backup",StringComparison.OrdinalIgnoreCase)) return (object?)brokerTemp;
    return (object?)brokerTemp;
}).ToArray();
await using var broker=(ElevatedOperationBroker)brokerCtor.Invoke(brokerArgs);
'@.Trim()
if(($src.Split($old).Count-1)-ne1){throw 'R54.2 mutation broker constructor anchor mismatch'}
$src=$src.Replace($old,$new)

# Build the probe first, then place the exact packaged elevated-helper files
# beside Probe.dll before executing it. This exercises the real helper/broker
# path rather than the service-level exception fallback.
$oldRun="dotnet run --project (Join-Path `$probe 'Probe.csproj') -c Release -- `$portable `$dummyExe"
$newRun=@'
dotnet build (Join-Path $probe 'Probe.csproj') -c Release --nologo
if($LASTEXITCODE-ne0){throw 'R54.2 OneDrive probe build failed'}
$probeDll=Get-ChildItem (Join-Path $probe 'bin\Release') -Recurse -File -Filter 'Probe.dll' | Select-Object -First 1
if(!$probeDll){throw 'R54.2 OneDrive probe dll missing'}
$probeOut=$probeDll.Directory.FullName
$helperFiles=Get-ChildItem $portable -File -Filter 'MerzoOptimizer.ElevatedHelper.*'
if(!$helperFiles -or !($helperFiles | Where-Object Name -eq 'MerzoOptimizer.ElevatedHelper.exe')){throw 'R54.2 packaged elevated helper payload missing'}
$helperFiles | Copy-Item -Destination $probeOut -Force
Write-Host "R542_PROBE_HELPER_LAYOUT out=$probeOut files=$($helperFiles.Count)"
dotnet $probeDll.FullName $portable $dummyExe
'@.Trim()
if(($src.Split($oldRun).Count-1)-ne1){throw 'R54.2 mutation probe run anchor mismatch'}
$src=$src.Replace($oldRun,$newRun)

# PowerShell variables are case-insensitive: $Pid collides with read-only $PID.
$oldFn='function Get-ProcessWindows([int]$Pid){'
$newFn='function Get-ProcessWindows([int]$ProcessId){'
if(($src.Split($oldFn).Count-1)-ne1){throw 'R54.2 mutation ProcessId function anchor mismatch'}
$src=$src.Replace($oldFn,$newFn)
$oldPid='ProcessIdProperty,$Pid)'
$newPid='ProcessIdProperty,$ProcessId)'
if(($src.Split($oldPid).Count-1)-ne1){throw 'R54.2 mutation ProcessId property anchor mismatch'}
$src=$src.Replace($oldPid,$newPid)

# UIA often returns the TextBlock child (e.g. "Сборки") before its Button or
# TabItem. Walk up a few control-view parents and invoke/select the first action
# control so the disposable test follows the same real UI the user clicks.
$oldInvoke=@'
function Invoke-Element([System.Windows.Automation.AutomationElement]$El){
    if(!$El){return $false}
    try{
        $p=$El.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        ([System.Windows.Automation.InvokePattern]$p).Invoke();return $true
    }catch{}
    try{
        $p=$El.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
        ([System.Windows.Automation.SelectionItemPattern]$p).Select();return $true
    }catch{}
    return $false
}
'@.Trim()
$newInvoke=@'
function Invoke-Element([System.Windows.Automation.AutomationElement]$El){
    if(!$El){return $false}
    $cur=$El
    for($depth=0;$depth-lt6 -and $cur;$depth++){
        try{
            $p=$cur.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
            ([System.Windows.Automation.InvokePattern]$p).Invoke();return $true
        }catch{}
        try{
            $p=$cur.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
            ([System.Windows.Automation.SelectionItemPattern]$p).Select();return $true
        }catch{}
        try{$cur=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($cur)}catch{$cur=$null}
    }
    return $false
}
'@.Trim()
if(($src.Split($oldInvoke).Count-1)-ne1){throw 'R54.2 mutation UI invoke anchor mismatch'}
$src=$src.Replace($oldInvoke,$newInvoke)

$tmp=Join-Path $env:RUNNER_TEMP 'r54_2_game_mutation_acceptance_v2_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v2 failed: $LASTEXITCODE"}
