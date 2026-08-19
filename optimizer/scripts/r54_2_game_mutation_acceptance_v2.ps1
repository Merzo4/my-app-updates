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
object?[] brokerArgs=brokerParams.Select(p=>(object?)brokerTemp).ToArray();
await using var broker=(ElevatedOperationBroker)brokerCtor.Invoke(brokerArgs);
'@.Trim()
if(($src.Split($old).Count-1)-ne1){throw 'R54.2 mutation broker constructor anchor mismatch'}
$src=$src.Replace($old,$new)

# Security helper reads the actual process executable version. Publish the test
# host as a self-contained Probe.exe 0.1.54.2 instead of running dotnet Probe.dll.
$probeProps='<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup>'
$probePropsNew='<PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><RuntimeIdentifier>win-x64</RuntimeIdentifier><SelfContained>true</SelfContained><PublishSingleFile>true</PublishSingleFile><PublishTrimmed>false</PublishTrimmed><AssemblyVersion>0.1.54.2</AssemblyVersion><FileVersion>0.1.54.2</FileVersion><InformationalVersion>0.1.54.2</InformationalVersion><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup>'
if(($src.Split($probeProps).Count-1)-ne1){throw 'R54.2 mutation probe version anchor mismatch'}
$src=$src.Replace($probeProps,$probePropsNew)

$oldRun="dotnet run --project (Join-Path `$probe 'Probe.csproj') -c Release -- `$portable `$dummyExe"
$newRun=@'
$probePublish=Join-Path $probe 'publish'
dotnet publish (Join-Path $probe 'Probe.csproj') -c Release -r win-x64 -o $probePublish --nologo
if($LASTEXITCODE-ne0){throw 'R54.2 OneDrive probe publish failed'}
$probeExe=Join-Path $probePublish 'Probe.exe'
if(!(Test-Path $probeExe)){throw 'R54.2 OneDrive Probe.exe missing'}
$probeVersion=(Get-Item $probeExe).VersionInfo.FileVersion
if($probeVersion-ne'0.1.54.2'){throw "R54.2 OneDrive Probe.exe version=$probeVersion"}
$helperFiles=Get-ChildItem $portable -File -Filter 'MerzoOptimizer.ElevatedHelper.*'
if(!$helperFiles -or !($helperFiles | Where-Object Name -eq 'MerzoOptimizer.ElevatedHelper.exe')){throw 'R54.2 packaged elevated helper payload missing'}
$helperFiles | Copy-Item -Destination $probePublish -Force
Write-Host "R542_PROBE_HELPER_LAYOUT out=$probePublish files=$($helperFiles.Count) probeVersion=$probeVersion"
& $probeExe $portable $dummyExe
'@.Trim()
if(($src.Split($oldRun).Count-1)-ne1){throw 'R54.2 mutation probe run anchor mismatch'}
$src=$src.Replace($oldRun,$newRun)

$oldFn='function Get-ProcessWindows([int]$Pid){'
$newFn='function Get-ProcessWindows([int]$ProcessId){'
if(($src.Split($oldFn).Count-1)-ne1){throw 'R54.2 mutation ProcessId function anchor mismatch'}
$src=$src.Replace($oldFn,$newFn)
$oldPid='ProcessIdProperty,$Pid)'
$newPid='ProcessIdProperty,$ProcessId)'
if(($src.Split($oldPid).Count-1)-ne1){throw 'R54.2 mutation ProcessId property anchor mismatch'}
$src=$src.Replace($oldPid,$newPid)

# Define native click support outside hidden catches so failures are visible.
$uiaAnchor="Add-Type -AssemblyName UIAutomationTypes"
$uiaNative=@'
Add-Type -AssemblyName UIAutomationTypes
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public static class MerzoUiNative {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X,int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint flags,uint dx,uint dy,uint data,UIntPtr extra);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  public static void Click(int x,int y){SetCursorPos(x,y);mouse_event(0x0002,0,0,0,UIntPtr.Zero);mouse_event(0x0004,0,0,0,UIntPtr.Zero);}
}
"@
'@.Trim()
if(($src.Split($uiaAnchor).Count-1)-ne1){throw 'R54.2 mutation UI native anchor mismatch'}
$src=$src.Replace($uiaAnchor,$uiaNative)

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
    if(!$El){Write-Host 'R542_UI_ACTION null-element';return $false}
    $cur=$El
    for($depth=0;$depth-lt8 -and $cur;$depth++){
        try{
            $p=$cur.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
            ([System.Windows.Automation.InvokePattern]$p).Invoke()
            Write-Host "R542_UI_ACTION invoke depth=$depth name=$($cur.Current.Name)"
            return $true
        }catch{}
        try{
            $p=$cur.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
            ([System.Windows.Automation.SelectionItemPattern]$p).Select()
            Write-Host "R542_UI_ACTION select depth=$depth name=$($cur.Current.Name)"
            return $true
        }catch{}
        try{$cur=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($cur)}catch{$cur=$null}
    }
    try{
        $r=$El.Current.BoundingRectangle
        Write-Host "R542_UI_CLICK_FALLBACK name=$($El.Current.Name) x=$($r.X) y=$($r.Y) w=$($r.Width) h=$($r.Height)"
        if($r.Width-gt1 -and $r.Height-gt1){
            [MerzoUiNative]::Click([int]($r.X+$r.Width/2),[int]($r.Y+$r.Height/2))
            Start-Sleep -Milliseconds 350
            return $true
        }
    }catch{Write-Host "R542_UI_CLICK_ERROR $($_.Exception.Message)"}
    return $false
}
'@.Trim()
if(($src.Split($oldInvoke).Count-1)-ne1){throw 'R54.2 mutation UI invoke anchor mismatch'}
$src=$src.Replace($oldInvoke,$newInvoke)

$focusAnchor="Write-Host 'R54_2_GAME_UI_MAIN_PASS'"
$focusNew=@'
Write-Host 'R54_2_GAME_UI_MAIN_PASS'
try{[MerzoUiNative]::SetForegroundWindow($proc.MainWindowHandle)|Out-Null;Start-Sleep -Milliseconds 500}catch{}
'@.Trim()
if(($src.Split($focusAnchor).Count-1)-ne1){throw 'R54.2 mutation foreground anchor mismatch'}
$src=$src.Replace($focusAnchor,$focusNew)

$tmp=Join-Path $env:RUNNER_TEMP 'r54_2_game_mutation_acceptance_v2_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v2 failed: $LASTEXITCODE"}
