param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$src=Get-Content $base -Raw

# Instantiate the production broker with isolated snapshot/log/backup folders.
$old='await using var broker=new ElevatedOperationBroker(portable);'
$new=@'
var brokerCtor=typeof(ElevatedOperationBroker).GetConstructors().Single(c=>c.GetParameters().Length==3 && c.GetParameters().All(p=>p.ParameterType==typeof(string)));
var brokerParams=brokerCtor.GetParameters();
Console.WriteLine("R542_BROKER_CTOR "+string.Join(",",brokerParams.Select(p=>$"{p.Name}:{p.ParameterType.Name}")));
var brokerTemp=Path.Combine(Path.GetTempPath(),"mwo-r542-broker-"+Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(brokerTemp);
object?[] brokerArgs=brokerParams.Select(p=>(object?)brokerTemp).ToArray();
await using var broker=(ElevatedOperationBroker)brokerCtor.Invoke(brokerArgs);
'@.Trim()
if(($src.Split($old).Count-1)-ne1){throw 'R54.2 mutation broker constructor anchor mismatch'}
$src=$src.Replace($old,$new)

# The helper validates that the caller/test host is the same product version.
$probeProps='<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup>'
$probePropsNew='<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><AssemblyVersion>0.1.54.2</AssemblyVersion><FileVersion>0.1.54.2</FileVersion><InformationalVersion>0.1.54.2</InformationalVersion><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup>'
if(($src.Split($probeProps).Count-1)-ne1){throw 'R54.2 mutation probe version anchor mismatch'}
$src=$src.Replace($probeProps,$probePropsNew)

# Build the probe first, then place the exact packaged elevated-helper files
# beside Probe.dll before executing it. This exercises the real helper/broker.
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

# UIA often returns the TextBlock child before its Button. First walk up the
# automation parents; if WPF still exposes no action pattern, physically click
# the visible child rectangle on the disposable desktop.
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
    for($depth=0;$depth-lt8 -and $cur;$depth++){
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
    try{
        if(-not ('MerzoUiMouse' -as [type])){
            Add-Type -TypeDefinition @"
using System.Runtime.InteropServices;
public static class MerzoUiMouse {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X,int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags,uint dx,uint dy,uint data,System.UIntPtr extra);
  public static void Click(int x,int y){SetCursorPos(x,y);mouse_event(0x0002,0,0,0,System.UIntPtr.Zero);mouse_event(0x0004,0,0,0,System.UIntPtr.Zero);}
}
"@
        }
        $r=$El.Current.BoundingRectangle
        if($r.Width-gt1 -and $r.Height-gt1){
            [MerzoUiMouse]::Click([int]($r.X+$r.Width/2),[int]($r.Y+$r.Height/2))
            Start-Sleep -Milliseconds 250
            return $true
        }
    }catch{}
    return $false
}
'@.Trim()
if(($src.Split($oldInvoke).Count-1)-ne1){throw 'R54.2 mutation UI invoke anchor mismatch'}
$src=$src.Replace($oldInvoke,$newInvoke)

$tmp=Join-Path $env:RUNNER_TEMP 'r54_2_game_mutation_acceptance_v2_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v2 failed: $LASTEXITCODE"}
