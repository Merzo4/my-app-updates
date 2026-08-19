param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$src=Get-Content $base -Raw

$old='await using var broker=new ElevatedOperationBroker(portable);'
$new=@'
var brokerCtor=typeof(ElevatedOperationBroker).GetConstructors().Single(c=>c.GetParameters().Length==3 && c.GetParameters().All(p=>p.ParameterType==typeof(string)));
var brokerParams=brokerCtor.GetParameters();
Console.WriteLine("R542_BROKER_CTOR "+string.Join(",",brokerParams.Select(p=>$"{p.Name}:{p.ParameterType.Name}")));
var brokerTemp=Path.Combine(Path.GetTempPath(),"mwo-r542-broker-"+Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(brokerTemp);
var helperExe=Path.Combine(portable,"MerzoOptimizer.ElevatedHelper.exe");
if(!File.Exists(helperExe)) throw new Exception("Packaged elevated helper missing: "+helperExe);
object?[] brokerArgs=brokerParams.Select(p=>
{
    var n=p.Name??string.Empty;
    if(n.Contains("helper",StringComparison.OrdinalIgnoreCase)) return (object?)helperExe;
    if(n.Contains("log",StringComparison.OrdinalIgnoreCase)) return (object?)brokerTemp;
    if(n.Contains("snapshot",StringComparison.OrdinalIgnoreCase)) return (object?)brokerTemp;
    if(n.Contains("data",StringComparison.OrdinalIgnoreCase)) return (object?)portable;
    if(n.Contains("app",StringComparison.OrdinalIgnoreCase) || n.Contains("base",StringComparison.OrdinalIgnoreCase)) return (object?)portable;
    return (object?)portable;
}).ToArray();
await using var broker=(ElevatedOperationBroker)brokerCtor.Invoke(brokerArgs);
'@.Trim()
if(($src.Split($old).Count-1)-ne1){throw 'R54.2 mutation broker constructor anchor mismatch'}
$src=$src.Replace($old,$new)

# PowerShell variables are case-insensitive: $Pid collides with read-only $PID.
$oldFn='function Get-ProcessWindows([int]$Pid){'
$newFn='function Get-ProcessWindows([int]$ProcessId){'
if(($src.Split($oldFn).Count-1)-ne1){throw 'R54.2 mutation ProcessId function anchor mismatch'}
$src=$src.Replace($oldFn,$newFn)
$oldPid='ProcessIdProperty,$Pid)'
$newPid='ProcessIdProperty,$ProcessId)'
if(($src.Split($oldPid).Count-1)-ne1){throw 'R54.2 mutation ProcessId property anchor mismatch'}
$src=$src.Replace($oldPid,$newPid)

$tmp=Join-Path $env:RUNNER_TEMP 'r54_2_game_mutation_acceptance_v2_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v2 failed: $LASTEXITCODE"}
