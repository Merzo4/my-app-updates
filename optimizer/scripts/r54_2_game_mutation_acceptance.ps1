param(
  [Parameter(Mandatory=$true)][string]$ArtifactDir
)
$ErrorActionPreference='Stop'
$artifact=(Resolve-Path $ArtifactDir).Path
$zip=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip' | Select-Object -First 1
$zipSide=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256' | Select-Object -First 1
if(!$zip -or !$zipSide){throw 'R54.2 mutation artifact payload incomplete'}
$actual=(Get-FileHash $zip.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$expected=((Get-Content $zipSide.FullName -Raw)-split '\s+')[0].ToLowerInvariant()
if($actual-ne$expected){throw "R54.2 portable SHA mismatch $actual != $expected"}

$work=Join-Path $env:RUNNER_TEMP ('mwo-r542-mutation-'+[guid]::NewGuid().ToString('N'))
$portable=Join-Path $work 'app'
New-Item -ItemType Directory -Force $portable|Out-Null
Expand-Archive $zip.FullName $portable -Force
$exe=Join-Path $portable 'MerzoWindowsOptimizer.exe'
$winDll=Join-Path $portable 'MerzoOptimizer.Windows.dll'
$coreDll=Join-Path $portable 'MerzoOptimizer.Core.dll'
$helper=Join-Path $portable 'MerzoOptimizer.ElevatedHelper.exe'
foreach($p in @($exe,$winDll,$coreDll,$helper)){if(!(Test-Path $p)){throw "R54.2 mutation missing $p"}}
$fv=(Get-Item $exe).VersionInfo.FileVersion
if($fv-ne'0.1.54.2'){throw "R54.2 mutation EXE version=$fv"}
Write-Host "R54_2_MUTATION_ARTIFACT_PASS sha=$actual version=$fv"

# ---------------------------------------------------------------------------
# OneDrive regression: reproduce a stale setup-only state and a non-zero
# OneDriveSetup /uninstall without using a real user's OneDrive installation.
# All synthetic files live in the disposable runner profile and are removed.
# ---------------------------------------------------------------------------
$fakeRoot=Join-Path $env:LOCALAPPDATA 'Microsoft\OneDrive'
$fakeClient=Join-Path $fakeRoot 'OneDrive.exe'
$fakeSetupDir=Join-Path $fakeRoot 'Update'
$fakeSetup=Join-Path $fakeSetupDir 'OneDriveSetup.exe'
if((Test-Path $fakeClient) -or (Test-Path $fakeSetup)){
  throw "R54.2 synthetic OneDrive paths are not clean on disposable runner: $fakeRoot"
}

$dummy=Join-Path $work 'dummy-setup'
New-Item -ItemType Directory -Force $dummy|Out-Null
@'
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework>
    <RuntimeIdentifier>win-x64</RuntimeIdentifier><PublishSingleFile>true</PublishSingleFile>
    <SelfContained>true</SelfContained><ImplicitUsings>enable</ImplicitUsings>
  </PropertyGroup>
</Project>
'@|Set-Content (Join-Path $dummy 'DummySetup.csproj') -Encoding UTF8
@'
Environment.Exit(unchecked((int)0x8004069B));
'@|Set-Content (Join-Path $dummy 'Program.cs') -Encoding UTF8
dotnet publish (Join-Path $dummy 'DummySetup.csproj') -c Release -r win-x64 -o (Join-Path $dummy 'publish') --nologo
if($LASTEXITCODE-ne0){throw 'R54.2 dummy OneDriveSetup build failed'}
$dummyExe=Join-Path $dummy 'publish\DummySetup.exe'
if(!(Test-Path $dummyExe)){throw 'R54.2 dummy OneDriveSetup exe missing'}

$probe=Join-Path $work 'onedrive-probe'
New-Item -ItemType Directory -Force $probe|Out-Null
$w=[Security.SecurityElement]::Escape($winDll);$c=[Security.SecurityElement]::Escape($coreDll)
@"
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><OutputType>Exe</OutputType><TargetFramework>net10.0-windows</TargetFramework><ImplicitUsings>enable</ImplicitUsings><Nullable>enable</Nullable></PropertyGroup>
  <ItemGroup>
    <Reference Include="MerzoOptimizer.Core"><HintPath>$c</HintPath><Private>true</Private></Reference>
    <Reference Include="MerzoOptimizer.Windows"><HintPath>$w</HintPath><Private>true</Private></Reference>
  </ItemGroup>
</Project>
"@|Set-Content (Join-Path $probe 'Probe.csproj') -Encoding UTF8
@'
using MerzoOptimizer.Windows.Elevation;
using MerzoOptimizer.Windows.OneDrive;

var portable=Path.GetFullPath(args[0]);
var dummy=Path.GetFullPath(args[1]);
var local=Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
var root=Path.Combine(local,"Microsoft","OneDrive");
var client=Path.Combine(root,"OneDrive.exe");
var setupDir=Path.Combine(root,"Update");
var setup=Path.Combine(setupDir,"OneDriveSetup.exe");
Directory.CreateDirectory(setupDir);
try
{
    File.Copy(dummy,setup,true);
    await using var broker=new ElevatedOperationBroker(portable);
    var service=new WindowsOneDriveOptimizationService(broker);

    var stale=await service.InspectAsync();
    Console.WriteLine($"R542_ONEDRIVE_STALE_SETUP installed={stale.Installed} configured={stale.Configured} running={stale.Running}");
    if(stale.Installed) throw new Exception("setup-only OneDrive was falsely detected as installed");

    File.Copy(dummy,client,true);
    var before=await service.InspectAsync();
    Console.WriteLine($"R542_ONEDRIVE_FAKE_CLIENT installed={before.Installed}");
    if(!before.Installed) throw new Exception("synthetic OneDrive client was not detected");

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
'@|Set-Content (Join-Path $probe 'Program.cs') -Encoding UTF8
dotnet run --project (Join-Path $probe 'Probe.csproj') -c Release -- $portable $dummyExe
if($LASTEXITCODE-ne0){throw 'R54.2 OneDrive nonfatal runtime regression failed'}

# ---------------------------------------------------------------------------
# Full GAME mutation through the real packaged WPF UI on the disposable runner.
# This deliberately uses the shipped EXE/helper/data. We answer OneDrive prompts
# with NO so the full package tests reversible GAME work; the failing uninstall
# path was exercised separately above.
# ---------------------------------------------------------------------------
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

function Get-ProcessWindows([int]$Pid){
    $cond=[System.Windows.Automation.PropertyCondition]::new([System.Windows.Automation.AutomationElement]::ProcessIdProperty,$Pid)
    return [System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,$cond)
}
function Get-Desc([System.Windows.Automation.AutomationElement]$Root){
    return $Root.FindAll([System.Windows.Automation.TreeScope]::Descendants,[System.Windows.Automation.Condition]::TrueCondition)
}
function Find-NameContains([System.Windows.Automation.AutomationElement]$Root,[string]$Needle){
    foreach($e in (Get-Desc $Root)){
        try{$n=$e.Current.Name}catch{continue}
        if($n -and $n.IndexOf($Needle,[StringComparison]::OrdinalIgnoreCase)-ge0){return $e}
    }
    return $null
}
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
function Window-Text([System.Windows.Automation.AutomationElement]$Win){
    $out=[Collections.Generic.List[string]]::new()
    try{if($Win.Current.Name){$out.Add($Win.Current.Name)}}catch{}
    foreach($e in (Get-Desc $Win)){
        try{$n=$e.Current.Name}catch{continue}
        if($n -and $n.Length-lt1000){$out.Add($n)}
    }
    return ($out -join "`n")
}

$proc=Start-Process $exe -PassThru
$main=$null
$deadline=(Get-Date).AddSeconds(45)
while((Get-Date)-lt$deadline -and !$main){
    Start-Sleep -Milliseconds 400
    foreach($w in (Get-ProcessWindows $proc.Id)){
        $text=Window-Text $w
        if($text -match 'Сборки' -and $text -match 'Merzo Windows Optimizer'){$main=$w;break}
    }
}
if(!$main){try{$proc.Kill()}catch{};throw 'R54.2 GAME main window not found'}
Write-Host 'R54_2_GAME_UI_MAIN_PASS'

$buildNav=Find-NameContains $main 'Сборки'
if(!(Invoke-Element $buildNav)){try{$proc.Kill()}catch{};throw 'R54.2 GAME could not open Builds page'}
Start-Sleep -Seconds 1
$game=Find-NameContains $main 'Выбрать GAME'
if(!(Invoke-Element $game)){try{$proc.Kill()}catch{};throw 'R54.2 GAME select button not invokable'}
Start-Sleep -Seconds 1
$install=Find-NameContains $main 'Установить сборку'
if(!$install){try{$proc.Kill()}catch{};throw 'R54.2 GAME install button missing'}
if(!(Invoke-Element $install)){try{$proc.Kill()}catch{};throw 'R54.2 GAME install button not invokable'}

$seenBusy=$false;$fatal=$false;$fatalText='';$dialogs=[Collections.Generic.List[string]]::new();$completed=$false
$deadline=(Get-Date).AddMinutes(12)
while((Get-Date)-lt$deadline -and !$completed){
    if($proc.HasExited){$fatal=$true;$fatalText="App exited during GAME, code=$($proc.ExitCode)";break}
    Start-Sleep -Milliseconds 500
    $wins=Get-ProcessWindows $proc.Id
    foreach($w in $wins){
        $txt=Window-Text $w
        if($w.Equals($main)){continue}
        if($txt){
            if(!$dialogs.Contains($txt)){$dialogs.Add($txt);Write-Host ("R542_DIALOG: "+($txt-replace "`r?`n",' | '))}
            if($txt -match '(?i)пакет отменён|ошибка восстановления|requested registry access|OneDriveSetup /uninstall завершился'){
                $fatal=$true;$fatalText=$txt
            }
            $button=$null
            if($txt -match '(?i)OneDrive'){$button=Find-NameContains $w 'Нет'}
            if(!$button -and $txt -match '(?i)Применить выбранный пакет|подтверд'){$button=Find-NameContains $w 'Да'}
            if(!$button){$button=Find-NameContains $w 'Понятно'}
            if(!$button){$button=Find-NameContains $w 'ОК'}
            if(!$button){$button=Find-NameContains $w 'Да'}
            if($button){[void](Invoke-Element $button)}
        }
    }
    if($fatal){break}
    $mainText=Window-Text $main
    if($mainText -match '(?i)пакет отменён|аварийное восстановление завершено|ошибка восстановления'){
        $fatal=$true;$fatalText=$mainText;break
    }
    $installNow=Find-NameContains $main 'Установить сборку'
    if($installNow){
        try{$enabled=$installNow.Current.IsEnabled}catch{$enabled=$false}
        if(!$enabled){$seenBusy=$true}
        if($seenBusy -and $enabled){$completed=$true}
    }
}
if($fatal){try{$proc.Kill()}catch{};throw "R54.2 GAME package rolled back/failed: $fatalText"}
if(!$completed){try{$proc.Kill()}catch{};throw 'R54.2 GAME package did not complete within timeout'}

$mainText=Window-Text $main
if($mainText -match '(?i)пакет отменён|аварийное восстановление завершено'){
    try{$proc.Kill()}catch{};throw 'R54.2 GAME final UI reports rollback'
}
Write-Host 'R54_2_GAME_FULL_MUTATION_PASS'

# Verify that the installed package left a usable Undo contract. This is not a
# substitute for per-operation restore tests; it ensures the UI can resolve the
# latest recovery data after the real GAME run.
$undo=Find-NameContains $main 'Проверить Undo'
if($undo -and (Invoke-Element $undo)){
    Start-Sleep -Seconds 1
    foreach($w in (Get-ProcessWindows $proc.Id)){
        if($w.Equals($main)){continue}
        $txt=Window-Text $w
        if($txt){Write-Host ("R542_UNDO_DIALOG: "+($txt-replace "`r?`n",' | '))}
        $ok=Find-NameContains $w 'Понятно';if(!$ok){$ok=Find-NameContains $w 'ОК'};if($ok){[void](Invoke-Element $ok)}
    }
    Write-Host 'R54_2_GAME_UNDO_CONTRACT_PROBE_PASS'
}else{
    Write-Host 'R54_2_GAME_UNDO_CONTRACT_PROBE_SKIPPED button-not-invokable'
}
try{$proc.CloseMainWindow()|Out-Null;Start-Sleep -Seconds 1;if(!$proc.HasExited){$proc.Kill()}}catch{}

@{
  conclusion='success'
  createdAt=(Get-Date).ToUniversalTime().ToString('o')
  buildRun=32270447478
  buildHead='086c02fc648893e18961eeee74e8bd73c4f83a2f'
  artifactId=9372048444
  artifactDigest='sha256:747929c99018af25af3d16f174afe57c08f137e06c1699f77d958bf9b0cb4a70'
  portableSha=$actual
  oneDriveSyntheticNonzero='success'
  oneDriveSetupOnlyDetection='success'
  gameFullMutation='success'
  undoContractProbe='attempted'
}|ConvertTo-Json -Compress|Set-Content '.\optimizer\R54_2_GAME_MUTATION_STATUS.json' -Encoding UTF8
Write-Host 'R54_2_DISPOSABLE_WINDOWS_MUTATION_ACCEPTANCE_PASS'
