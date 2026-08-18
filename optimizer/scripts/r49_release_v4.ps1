$ErrorActionPreference='Stop'
$src=Get-Content '.\optimizer\scripts\r49_release.ps1' -Raw
$old="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py')"
$new="'r49_catalog.py','r49_recovery_onedrive_infra.py','r49_build_integration.py','r49_finalize.py')"
if(($src.Split($old).Count-1)-ne1){throw 'R49 V4 patch-chain anchor mismatch'}
$src=$src.Replace($old,$new)
$oldGate="for marker in ['R49_CATALOG.marker','R49_RECOVERY_ONEDRIVE_INFRA.marker','R49_BUILD_INTEGRATION.marker']:"
$newGate="for marker in ['R49_CATALOG.marker','R49_RECOVERY_ONEDRIVE_INFRA.marker','R49_BUILD_INTEGRATION.marker','R49_FINALIZE.marker']:"
if(($src.Split($oldGate).Count-1)-ne1){throw 'R49 V4 marker-gate anchor mismatch'}
$src=$src.Replace($oldGate,$newGate)
$oldHarness='[STAThread]static void Main(){var a=new App();a.InitializeComponent();foreach(var s in new[]{(1000d,600d),(920d,560d)})'
$newHarness='[STAThread]static void Main(){var a=new App();a.InitializeComponent();a.ShutdownMode=ShutdownMode.OnExplicitShutdown;foreach(var s in new[]{(1000d,600d),(920d,560d)})'
if(($src.Split($oldHarness).Count-1)-ne1){throw 'R49 V4 WPF harness anchor mismatch'}
$src=$src.Replace($oldHarness,$newHarness)
$tmp=Join-Path $env:RUNNER_TEMP 'r49_release_v4_expanded.ps1'
Set-Content $tmp $src -Encoding UTF8
& $tmp
if($LASTEXITCODE-ne0){throw "R49 V4 expanded release script failed: $LASTEXITCODE"}
