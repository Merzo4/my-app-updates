param([Parameter(Mandatory=$true)][string]$ArtifactDir)
$ErrorActionPreference='Stop'

$base='.\optimizer\scripts\r54_2_game_mutation_acceptance.ps1'
$src=Get-Content $base -Raw

$launchAnchor='$proc=Start-Process $exe -PassThru'
$launchReplacement=@'
$trkPath='HKLM:\SYSTEM\CurrentControlSet\Services\TrkWks'
$trkPre=$null
try{$trkPre=(Get-ItemProperty -Path $trkPath -Name Start -ErrorAction Stop).Start;Write-Host "R542_RECOVERY_TRKWKS_PRE start=$trkPre"}catch{Write-Host "R542_RECOVERY_TRKWKS_PRE unavailable=$($_.Exception.Message)"}
$proc=Start-Process $exe -PassThru
'@.Trim()
if(($src.Split($launchAnchor).Count-1)-ne1){throw 'R54.2 v11 launch anchor mismatch'}
$src=$src.Replace($launchAnchor,$launchReplacement)

$startMarker='# Verify that the installed package left a usable Undo contract.'
$statusMarker='@{' + "`r`n" + "  conclusion='success'"
$start=$src.IndexOf($startMarker,[StringComparison]::Ordinal)
if($start-lt0){throw 'R54.2 v11 Undo section start marker missing'}
$status=$src.IndexOf($statusMarker,$start,[StringComparison]::Ordinal)
if($status-lt0){$statusMarker='@{' + "`n" + "  conclusion='success'";$status=$src.IndexOf($statusMarker,$start,[StringComparison]::Ordinal)}
if($status-lt0){throw 'R54.2 v11 final status marker missing'}

$csB64='dXNpbmcgTWVyem9PcHRpbWl6ZXIuQ29yZS5Mb2dnaW5nOwp1c2luZyBNZXJ6b09wdGltaXplci5XaW5kb3dzLlJlc3RvcmU7CnVzaW5nIE1lcnpvT3B0aW1pemVyLldpbmRvd3MuU25hcHNob3RzOwoKdmFyIHNuYXBzaG90RGlyPVBhdGguR2V0RnVsbFBhdGgoYXJnc1swXSk7CnZhciBsb2dEaXI9UGF0aC5HZXRGdWxsUGF0aChhcmdzWzFdKTsKdmFyIHNuYXBzaG90cz1uZXcgV2luZG93c1NuYXBzaG90U2VydmljZShzbmFwc2hvdERpcik7CnZhciBiZWZvcmU9KGF3YWl0IHNuYXBzaG90cy5MaXN0QXN5bmMoQ2FuY2VsbGF0aW9uVG9rZW4uTm9uZSkpLldoZXJlKHg9PiF4LklzUmVzdG9yZWQpLlRvTGlzdCgpOwpDb25zb2xlLldyaXRlTGluZSgkIlI1NDJfUkVTVE9SRV9BQ1RJVkVfQkVGT1JFIGNvdW50PXtiZWZvcmUuQ291bnR9Iik7CmlmKGJlZm9yZS5Db3VudD09MCkgdGhyb3cgbmV3IEV4Y2VwdGlvbigiR0FNRSBwcm9kdWNlZCBubyBhY3RpdmUgc25hcHNob3RzIGZvciBwcm9kdWN0aW9uIFJlc3RvcmVBbGwgd mFsaWRhdGlvbiIpOwp2YXIgbG9nZ2VyPShJQXVkaXRMb2dnZXI/KUFjdGl2YXRvci5DcmVhdGVJbnN0YW5jZSh0eXBlb2YoSnNvbkxpbmVzQXVkaXRMb2dnZXIpLGxvZ0RpcikgPz8gdGhyb3cgbmV3IEV4Y2VwdGlvbigiSnNvbkxpbmVzQXVkaXRMb2dnZXIgY3JlYXRpb24gZmFpbGVkIik7CnZhciByZXN0b3JlPW5ldyBXaW5kb3dzUmVzdG9yZVNlcnZpY2Uoc25hcHNob3RzLGxvZ2dlcik7CnZhciByZXN1bHQ9YXdhaXQgcmVzdG9yZS5SZXN0b3JlQWxsQWN0aXZlQXN5bmMoQ2FuY2VsbGF0aW9uVG9rZW4uTm9uZSk7CkNvbnNvbGUuV3JpdGVMaW5lKCQiUjU0Ml9SRVNUT1JFX1JFU1VMVCBzdWNjZXNzPXtyZXN1bHQuU3VjY2Vzc30gbWVzc2FnZT17cmVzdWx0Lk1lc3NhZ2V9Iik7CmlmKCFyZXN1bHQuU3VjY2VzcykgdGhyb3cgbmV3IEV4Y2VwdGlvbigicHJvZHVjdGlvbiBSZXN0b3JlQWxsQWN0aXZlQXN5bmMgZmFpbGVkOiAiK3Jlc3VsdC5NZXNzYWdlKTsKdmFyIGFmdGVyPShhd2FpdCBzbmFwc2hvdHMuTGlzdEFzeW5jKENhbmNlbGxhdGlvblRva2VuLk5vbmUpKS5XaGVyZSh4PT4heC5Jc1Jlc3RvcmVkKS5Ub0xpc3QoKTsKQ29uc29sZS5Xcml0ZUxpbmUoJCJSNTQyX1JFU1RPUkVfQUNUSVZFX0FGVEVSIGNvdW50PXthZnRlci5Db3VudH0iKTsKaWYoYWZ0ZXIuQ291bnQhPTApIHRocm93IG5ldyBFeGNlcHRpb24oJCJwcm9kdWN0aW9uIFJlc3RvcmVBbGwgbGVmdCB7YWZ0ZXIuQ291bnR9IGFjdGl2ZSBzbmFwc2hvdHMiKTsKQ29uc29sZS5Xcml0ZUxpbmUoIlI1NF8yX1BST0RVQ1RJT05fUkVTVE9SRV9BTExfQUNUSVZFX1BBU1MiKTsK'.Replace(' ','')

$restore=@'
try{$proc.CloseMainWindow()|Out-Null;Start-Sleep -Seconds 1;if(!$proc.HasExited){$proc.Kill();$proc.WaitForExit(5000)|Out-Null}}catch{}
Get-Process MerzoOptimizer.ElevatedHelper -ErrorAction SilentlyContinue | ForEach-Object {try{$_.WaitForExit(5000)}catch{}}
$trkPost=$null
try{$trkPost=(Get-ItemProperty -Path $trkPath -Name Start -ErrorAction Stop).Start;Write-Host "R542_RECOVERY_TRKWKS_POST_GAME start=$trkPost"}catch{Write-Host "R542_RECOVERY_TRKWKS_POST_GAME unavailable=$($_.Exception.Message)"}
$snapshotDir=Join-Path $env:LOCALAPPDATA 'MerzoWindowsOptimizer\snapshots'
$logDir=Join-Path $env:LOCALAPPDATA 'MerzoWindowsOptimizer\logs'
if(!(Test-Path $snapshotDir)){throw "R54.2 production snapshot directory missing after GAME: $snapshotDir"}
New-Item -ItemType Directory -Force $logDir|Out-Null
$restoreProbe=Join-Path $work 'restore-probe';New-Item -ItemType Directory -Force $restoreProbe|Out-Null
$w=[Security.SecurityElement]::Escape($winDll);$c=[Security.SecurityElement]::Escape($coreDll)
$proj="<Project Sdk=`"Microsoft.NET.Sdk`"><PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup><ItemGroup><Reference Include=`"MerzoOptimizer.Core`"><HintPath>$c</HintPath><Private>true</Private></Reference><Reference Include=`"MerzoOptimizer.Windows`"><HintPath>$w</HintPath><Private>true</Private></Reference></ItemGroup></Project>"
Set-Content (Join-Path $restoreProbe 'RestoreProbe.csproj') $proj -Encoding UTF8
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__CS_B64__'))|Set-Content (Join-Path $restoreProbe 'Program.cs') -Encoding UTF8
dotnet run --project (Join-Path $restoreProbe 'RestoreProbe.csproj') -c Release -- $snapshotDir $logDir
if($LASTEXITCODE-ne0){throw "R54.2 production RestoreAll probe failed: $LASTEXITCODE"}
$trkAfter=$null
try{$trkAfter=(Get-ItemProperty -Path $trkPath -Name Start -ErrorAction Stop).Start;Write-Host "R542_RECOVERY_TRKWKS_AFTER_RESTORE start=$trkAfter"}catch{Write-Host "R542_RECOVERY_TRKWKS_AFTER_RESTORE unavailable=$($_.Exception.Message)"}
if($null-ne$trkPre -and $null-ne$trkAfter -and [int]$trkAfter-ne[int]$trkPre){throw "R54.2 Recovery did not restore TrkWks Start: pre=$trkPre postGame=$trkPost after=$trkAfter"}
Write-Host "R54_2_RECOVERY_STATE_VERIFICATION_PASS trkPre=$trkPre trkPostGame=$trkPost trkAfter=$trkAfter"

'@
$restore=$restore.Replace('__CS_B64__',$csB64)
$src=$src.Substring(0,$start)+$restore+$src.Substring($status)
$src=$src.Replace("  undoContractProbe='attempted'","  undoContractProbe='production-restore-all-success'`r`n  recoveryRestoreAll='success'`r`n  recoveryStateVerification='success'")
Set-Content $base $src -Encoding UTF8
Write-Host 'R54_2_V11_PRODUCTION_RESTORE_ALL_READY'
& '.\optimizer\scripts\r54_2_game_mutation_acceptance_v6.ps1' -ArtifactDir $ArtifactDir
if($LASTEXITCODE-ne0){throw "R54.2 GAME mutation v11 failed: $LASTEXITCODE"}
