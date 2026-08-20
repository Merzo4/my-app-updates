param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'
$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$src=Get-Content $base -Raw

# Probe only prepares a controlled OneDrive state and verifies detection.
# It does NOT call the protected helper. The actual packaged Merzo EXE will do
# that later so the UAC security contract is exercised exactly as in production.
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

# Dummy OneDriveSetup leaves proof that the real application/helper actually
# invoked it, then returns the exact signed code seen on the user's PC.
$dummyOld='Environment.Exit(unchecked((int)0x8004069B));'
$dummyNew='var marker=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData),"MerzoR542OneDriveDummy.marker"); File.WriteAllText(marker,DateTime.UtcNow.ToString("O")); Environment.Exit(unchecked((int)0x8004069B));'
if(($src.Split($dummyOld).Count-1)-ne1){throw 'R54.2 dummy OneDrive exit anchor mismatch'}
$src=$src.Replace($dummyOld,$dummyNew)

# Keep the synthetic OneDrive.exe + OneDriveSetup.exe in place after the probe
# so the real Merzo process sees them. Remove only on probe failure.
$probeMutationOld=@'
    var result=await service.UninstallAsync();
    Console.WriteLine($"R542_ONEDRIVE_NONZERO_RESULT success={result.Success} changed={result.Changed} message={result.Message}");
    if(!result.Success) throw new Exception("non-zero optional OneDrive uninstall was package-fatal");
    if(!File.Exists(client)) throw new Exception("synthetic client unexpectedly removed by failing setup");

    File.Delete(client);
    var after=await service.InspectAsync();
    if(after.Installed) throw new Exception("setup leftover still counts as installed after failed uninstall");
    Console.WriteLine("R54_2_ONEDRIVE_NONFATAL_RUNTIME_PASS");
}
finally
{
    try{if(File.Exists(client))File.Delete(client);}catch{}
    try{if(File.Exists(setup))File.Delete(setup);}catch{}
    try{if(Directory.Exists(setupDir)&&!Directory.EnumerateFileSystemEntries(setupDir).Any())Directory.Delete(setupDir);}catch{}
    try{if(Directory.Exists(root)&&!Directory.EnumerateFileSystemEntries(root).Any())Directory.Delete(root);}catch{}
}
'@.Trim()
$probeMutationNew=@'
    Console.WriteLine("R54_2_ONEDRIVE_SYNTHETIC_READY");
}
catch
{
    try{if(File.Exists(client))File.Delete(client);}catch{}
    try{if(File.Exists(setup))File.Delete(setup);}catch{}
    try{if(Directory.Exists(setupDir)&&!Directory.EnumerateFileSystemEntries(setupDir).Any())Directory.Delete(setupDir);}catch{}
    try{if(Directory.Exists(root)&&!Directory.EnumerateFileSystemEntries(root).Any())Directory.Delete(root);}catch{}
    throw;
}
'@.Trim()
if(($src.Split($probeMutationOld).Count-1)-ne1){throw 'R54.2 synthetic OneDrive handoff anchor mismatch'}
$src=$src.Replace($probeMutationOld,$probeMutationNew)

# Probe is versioned like the product, though it no longer calls the protected helper.
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
Write-Host "R542_PROBE_LAYOUT out=$probePublish probeVersion=$probeVersion"
& $probeExe $portable $dummyExe
if($LASTEXITCODE-ne0){throw "R54.2 detection probe failed: $LASTEXITCODE"}
$dummyMarker=Join-Path $env:ProgramData 'MerzoR542OneDriveDummy.marker'
Remove-Item $dummyMarker -Force -ErrorAction SilentlyContinue
'@.Trim()
if(($src.Split($oldRun).Count-1)-ne1){throw 'R54.2 mutation probe run anchor mismatch'}
$src=$src.Replace($oldRun,$newRun)

# Full GAME now deliberately says YES to the synthetic unconfigured OneDrive.
$src=$src.Replace('with NO so the full package tests reversible GAME work; the failing uninstall\n# path was exercised separately above.','with YES for the synthetic OneDrive so the real trusted helper reproduces the non-zero uninstall;\n# the package must continue instead of rolling back.')
$oneDriveNo="if(`$txt -match '(?i)OneDrive'){`$button=Find-NameContains `$w 'Нет'}"
$oneDriveYes="if(`$txt -match '(?i)OneDrive'){`$button=Find-NameContains `$w 'Да'}"
if(($src.Split($oneDriveNo).Count-1)-ne1){throw 'R54.2 OneDrive dialog-choice anchor mismatch'}
$src=$src.Replace($oneDriveNo,$oneDriveYes)

# PowerShell variables are case-insensitive: $Pid collides with read-only $PID.
$oldFn='function Get-ProcessWindows([int]$Pid){'
$newFn='function Get-ProcessWindows([int]$ProcessId){'
if(($src.Split($oldFn).Count-1)-ne1){throw 'R54.2 mutation ProcessId function anchor mismatch'}
$src=$src.Replace($oldFn,$newFn)
$oldPid='ProcessIdProperty,$Pid)'
$newPid='ProcessIdProperty,$ProcessId)'
if(($src.Split($oldPid).Count-1)-ne1){throw 'R54.2 mutation ProcessId property anchor mismatch'}
$src=$src.Replace($oldPid,$newPid)

# Native click support for WPF controls whose TextBlock child has no InvokePattern.
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
    try{
        $p=$El.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
        ([System.Windows.Automation.InvokePattern]$p).Invoke()
        Write-Host "R542_UI_ACTION invoke name=$($El.Current.Name)"
        return $true
    }catch{}
    try{
        $r=$El.Current.BoundingRectangle
        Write-Host "R542_UI_CLICK name=$($El.Current.Name) x=$($r.X) y=$($r.Y) w=$($r.Width) h=$($r.Height)"
        if($r.Width-gt1 -and $r.Height-gt1){
            [MerzoUiNative]::Click([int]($r.X+$r.Width/2),[int]($r.Y+$r.Height/2))
            Start-Sleep -Milliseconds 450
            return $true
        }
    }catch{Write-Host "R542_UI_CLICK_ERROR $($_.Exception.Message)"}
    $cur=$El
    for($depth=0;$depth-lt8 -and $cur;$depth++){
        try{
            $p=$cur.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
            ([System.Windows.Automation.SelectionItemPattern]$p).Select()
            Write-Host "R542_UI_ACTION select depth=$depth name=$($cur.Current.Name)"
            return $true
        }catch{}
        try{
            $p=$cur.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
            ([System.Windows.Automation.InvokePattern]$p).Invoke()
            Write-Host "R542_UI_ACTION parent-invoke depth=$depth name=$($cur.Current.Name)"
            return $true
        }catch{}
        try{$cur=[System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($cur)}catch{$cur=$null}
    }
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

# Reacquire the live main AutomationElement after the RadioButton Click handler
# swaps pages; dump relevant names if the GAME button is still not exposed.
$navOld=@'
$buildNav=Find-NameContains $main 'Сборки'
if(!(Invoke-Element $buildNav)){try{$proc.Kill()}catch{};throw 'R54.2 GAME could not open Builds page'}
Start-Sleep -Seconds 1
$game=Find-NameContains $main 'Выбрать GAME'
if(!(Invoke-Element $game)){try{$proc.Kill()}catch{};throw 'R54.2 GAME select button not invokable'}
'@.Trim()
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
if(($src.Split($navOld).Count-1)-ne1){throw 'R54.2 GAME nav block anchor mismatch'}
$src=$src.Replace($navOld,$navNew)

# The actual trusted helper must have executed the dummy OneDriveSetup before a
# full GAME success is accepted. Then clean only the synthetic test files.
$passAnchor="Write-Host 'R54_2_GAME_FULL_MUTATION_PASS'"
$passNew=@'
$dummyMarker=Join-Path $env:ProgramData 'MerzoR542OneDriveDummy.marker'
if(!(Test-Path $dummyMarker)){
    try{$proc.Kill()}catch{}
    throw 'R54.2 GAME completed without invoking the synthetic OneDriveSetup through the trusted helper'
}
Write-Host "R54_2_REAL_ONEDRIVE_NONZERO_HELPER_PASS marker=$dummyMarker"
Remove-Item $dummyMarker -Force -ErrorAction SilentlyContinue
Remove-Item $fakeClient -Force -ErrorAction SilentlyContinue
Remove-Item $fakeSetup -Force -ErrorAction SilentlyContinue
try{if((Test-Path $fakeSetupDir) -and !(Get-ChildItem $fakeSetupDir -Force -ErrorAction SilentlyContinue)){Remove-Item $fakeSetupDir -Force}}catch{}
try{if((Test-Path $fakeRoot) -and !(Get-ChildItem $fakeRoot -Force -ErrorAction SilentlyContinue)){Remove-Item $fakeRoot -Force}}catch{}
Write-Host 'R54_2_GAME_FULL_MUTATION_PASS'
'@.Trim()
if(($src.Split($passAnchor).Count-1)-ne1){throw 'R54.2 GAME pass marker anchor mismatch'}
$src=$src.Replace($passAnchor,$passNew)

$tmp=Join-Path $env:RUNNER_TEMP 'r54_2_game_mutation_acceptance_v2_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v2 failed: $LASTEXITCODE"}
