param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'

$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$src=Get-Content $base -Raw

# Capture a representative reversible service state immediately before the real GAME run.
$launchAnchor='$proc=Start-Process $exe -PassThru'
$launchReplacement=@'
$trkPath='HKLM:\SYSTEM\CurrentControlSet\Services\TrkWks'
$trkPre=$null
try{$trkPre=(Get-ItemProperty -Path $trkPath -Name Start -ErrorAction Stop).Start;Write-Host "R542_RECOVERY_TRKWKS_PRE start=$trkPre"}catch{Write-Host "R542_RECOVERY_TRKWKS_PRE unavailable=$($_.Exception.Message)"}
$proc=Start-Process $exe -PassThru
'@.Trim()
if(($src.Split($launchAnchor).Count-1)-ne1){throw 'R54.2 v11 launch anchor mismatch'}
$src=$src.Replace($launchAnchor,$launchReplacement)

# Replace the weak UI Undo probe with the actual packaged WindowsRestoreService.
$startMarker='# Verify that the installed package left a usable Undo contract.'
$statusMarker='@{' + "`r`n" + "  conclusion='success'"
$start=$src.IndexOf($startMarker,[StringComparison]::Ordinal)
if($start-lt0){throw 'R54.2 v11 Undo section start marker missing'}
$status=$src.IndexOf($statusMarker,$start,[StringComparison]::Ordinal)
if($status-lt0){$statusMarker='@{' + "`n" + "  conclusion='success'";$status=$src.IndexOf($statusMarker,$start,[StringComparison]::Ordinal)}
if($status-lt0){throw 'R54.2 v11 final status marker missing'}

$restore=@'
# Close the UI/helper before invoking the exact production local restore engine.
try{$proc.CloseMainWindow()|Out-Null;Start-Sleep -Seconds 1;if(!$proc.HasExited){$proc.Kill();$proc.WaitForExit(5000)|Out-Null}}catch{}
Get-Process MerzoOptimizer.ElevatedHelper -ErrorAction SilentlyContinue | ForEach-Object {try{$_.WaitForExit(5000)}catch{}}

$trkPost=$null
try{$trkPost=(Get-ItemProperty -Path $trkPath -Name Start -ErrorAction Stop).Start;Write-Host "R542_RECOVERY_TRKWKS_POST_GAME start=$trkPost"}catch{Write-Host "R542_RECOVERY_TRKWKS_POST_GAME unavailable=$($_.Exception.Message)"}

$snapshotDir=Join-Path $env:LOCALAPPDATA 'MerzoWindowsOptimizer\snapshots'
$logDir=Join-Path $env:LOCALAPPDATA 'MerzoWindowsOptimizer\logs'
if(!(Test-Path $snapshotDir)){throw "R54.2 production snapshot directory missing after GAME: $snapshotDir"}
New-Item -ItemType Directory -Force $logDir|Out-Null

$restoreProbe=Join-Path $work 'restore-probe'
New-Item -ItemType Directory -Force $restoreProbe|Out-Null
$w=[Security.SecurityElement]::Escape($winDll);$c=[Security.SecurityElement]::Escape($coreDll)
@"
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup>
  <ItemGroup>
    <Reference Include="MerzoOptimizer.Core"><HintPath>$c</HintPath><Private>true</Private></Reference>
    <Reference Include="MerzoOptimizer.Windows"><HintPath>$w</HintPath><Private>true</Private></Reference>
  </ItemGroup>
</Project>
"@|Set-Content (Join-Path $restoreProbe 'RestoreProbe.csproj') -Encoding UTF8
@'
using MerzoOptimizer.Core.Logging;
using MerzoOptimizer.Windows.Restore;
using MerzoOptimizer.Windows.Snapshots;

var snapshotDir=Path.GetFullPath(args[0]);
var logDir=Path.GetFullPath(args[1]);
var snapshots=new WindowsSnapshotService(snapshotDir);
var before=(await snapshots.ListAsync(CancellationToken.None)).Where(x=>!x.IsRestored).ToList();
Console.WriteLine($"R542_RESTORE_ACTIVE_BEFORE count={before.Count}");
if(before.Count==0) throw new Exception("GAME produced no active snapshots for production RestoreAll validation");
var logger=(IAuditLogger?)Activator.CreateInstance(typeof(JsonLinesAuditLogger),logDir) ?? throw new Exception("JsonLinesAuditLogger creation failed");
var restore=new WindowsRestoreService(snapshots,logger);
var result=await restore.RestoreAllActiveAsync(CancellationToken.None);
Console.WriteLine($"R542_RESTORE_RESULT success={result.Success} message={result.Message}");
if(!result.Success) throw new Exception("production RestoreAllActiveAsync failed: "+result.Message);
var after=(await snapshots.ListAsync(CancellationToken.None)).Where(x=>!x.IsRestored).ToList();
Console.WriteLine($"R542_RESTORE_ACTIVE_AFTER count={after.Count}");
if(after.Count!=0) throw new Exception($"production RestoreAll left {after.Count} active snapshots");
Console.WriteLine("R54_2_PRODUCTION_RESTORE_ALL_ACTIVE_PASS");
'@|Set-Content (Join-Path $restoreProbe 'Program.cs') -Encoding UTF8

dotnet run --project (Join-Path $restoreProbe 'RestoreProbe.csproj') -c Release -- $snapshotDir $logDir
if($LASTEXITCODE-ne0){throw "R54.2 production RestoreAll probe failed: $LASTEXITCODE"}

$trkAfter=$null
try{$trkAfter=(Get-ItemProperty -Path $trkPath -Name Start -ErrorAction Stop).Start;Write-Host "R542_RECOVERY_TRKWKS_AFTER_RESTORE start=$trkAfter"}catch{Write-Host "R542_RECOVERY_TRKWKS_AFTER_RESTORE unavailable=$($_.Exception.Message)"}
if($null-ne$trkPre -and $null-ne$trkAfter -and [int]$trkAfter-ne[int]$trkPre){throw "R54.2 Recovery did not restore TrkWks Start: pre=$trkPre postGame=$trkPost after=$trkAfter"}
Write-Host "R54_2_RECOVERY_STATE_VERIFICATION_PASS trkPre=$trkPre trkPostGame=$trkPost trkAfter=$trkAfter"

'@
$src=$src.Substring(0,$start)+$restore+$src.Substring($status)

# Strengthen final status fields for the real recovery gate.
$src=$src.Replace("  undoContractProbe='attempted'","  undoContractProbe='production-restore-all-success'`r`n  recoveryRestoreAll='success'`r`n  recoveryStateVerification='success'")
Set-Content $base $src -Encoding UTF8

Write-Host 'R54_2_V11_PRODUCTION_RESTORE_ALL_READY'
& '.\optimizer\scripts\r54_2_game_mutation_acceptance_v6.ps1' -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v11 failed: $LASTEXITCODE"}
