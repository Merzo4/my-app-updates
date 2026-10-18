param(
  [ValidateSet('Diagnostics','Sync','Quick','FullSafe','Destructive')]
  [string]$Profile = 'Diagnostics'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$LabRoot = if ($env:MWO_LAB_ROOT) { $env:MWO_LAB_ROOT } else { 'D:\MerzoOptimizer-LocalLab' }
$AppDir = Join-Path $LabRoot 'App'
$SourceDir = Join-Path $LabRoot 'Source'
$ResultsDir = Join-Path $LabRoot 'Results\Latest'
$LogsDir = Join-Path $LabRoot 'Logs'
$StateDir = Join-Path $LabRoot 'State'
$TestBuildDir = Join-Path $LabRoot 'TestBuild'
$TempDir = Join-Path $LabRoot 'Temp\Run\Current'
$SandboxDir = Join-Path $LabRoot 'Sandbox\Current'
$ProfilePath = Join-Path $AppDir 'local-lab-profile.json'

foreach ($p in @($ResultsDir,$LogsDir,$StateDir,$TestBuildDir,$TempDir,$SandboxDir)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
if (!(Test-Path $ProfilePath)) { throw "Local Lab profile missing: $ProfilePath" }
$Cfg = Get-Content $ProfilePath -Raw | ConvertFrom-Json
$RunStarted = (Get-Date).ToUniversalTime()
$LogPath = Join-Path $LogsDir 'Current.log'
$Stages = [System.Collections.Generic.List[object]]::new()
$FirstFailure = $null

function Write-Lab([string]$Message) {
  $line = "[{0}] {1}" -f (Get-Date).ToString('HH:mm:ss'), $Message
  Write-Host $line
  Add-Content -Path $LogPath -Value $line -Encoding UTF8
}

function Add-Stage([string]$Id,[string]$Name,[string]$State,[string]$Summary,[double]$Seconds = 0) {
  $script:Stages.Add([pscustomobject]@{ id=$Id; name=$Name; state=$State; durationSeconds=[math]::Round($Seconds,2); summary=$Summary })
  if ($State -eq 'FAIL' -and -not $script:FirstFailure) { $script:FirstFailure = "${Name}: $Summary" }
  Write-Lab "$State | $Name | $Summary"
}

function Save-Result([string]$Conclusion,[bool]$Authoritative=$false,[bool]$MutationUsed=$false) {
  $head = ''
  $branch = ''
  if (Test-Path (Join-Path $SourceDir '.git')) {
    try { $head = (& git -C $SourceDir rev-parse HEAD 2>$null).Trim() } catch {}
    try { $branch = (& git -C $SourceDir branch --show-current 2>$null).Trim() } catch {}
  }
  $result = [ordered]@{
    schemaVersion = 1
    testCenterVersion = [string]$Cfg.testCenterVersion
    productVersion = [string]$Cfg.productVersion
    profile = $Profile
    conclusion = $Conclusion
    authoritative = $Authoritative
    systemMutationUsed = $MutationUsed
    startedAt = $RunStarted.ToString('o')
    finishedAt = (Get-Date).ToUniversalTime().ToString('o')
    machine = $env:COMPUTERNAME
    sourceBranch = $branch
    sourceCommit = $head
    firstCausalFailure = $script:FirstFailure
    stages = @($script:Stages)
  }
  $jsonPath = Join-Path $ResultsDir 'LAB-RESULT.json'
  $result | ConvertTo-Json -Depth 8 | Set-Content $jsonPath -Encoding UTF8
  $report = @(
    'MERZO OPTIMIZER LOCAL TEST CENTER',
    "Profile: $Profile",
    "Result: $Conclusion",
    "Product: $($Cfg.productVersion)",
    "Branch: $branch",
    "SHA: $head",
    "Machine: $env:COMPUTERNAME",
    "First failure: $($script:FirstFailure)",
    '',
    'STAGES:'
  ) + ($Stages | ForEach-Object { "[$($_.state)] $($_.name) — $($_.summary)" })
  $report | Set-Content (Join-Path $ResultsDir 'REPORT.txt') -Encoding UTF8
  $historyPath = Join-Path $LabRoot 'Results\history.jsonl'
  ($result | ConvertTo-Json -Depth 8 -Compress) | Add-Content $historyPath -Encoding UTF8
  $history = @(Get-Content $historyPath -ErrorAction SilentlyContinue)
  if ($history.Count -gt 20) { $history[($history.Count-20)..($history.Count-1)] | Set-Content $historyPath -Encoding UTF8 }
  Write-Lab "FINAL $Conclusion | evidence=$jsonPath"
}

function Assert-DDriveBoundary {
  if (-not $LabRoot.StartsWith('D:\',[System.StringComparison]::OrdinalIgnoreCase)) { throw "Lab root must stay on D: : $LabRoot" }
  if (!(Test-Path 'D:\')) { throw 'D: drive is required by Local Test Center policy.' }
  $resolvedRoot = [IO.Path]::GetFullPath($LabRoot)
  foreach ($protected in @('C:\Program Files\Merzo Windows Optimizer')) {
    if ($resolvedRoot.StartsWith($protected,[System.StringComparison]::OrdinalIgnoreCase)) { throw "Lab root overlaps protected production path: $protected" }
  }
}

function Get-ProductionFingerprint {
  $root = 'C:\Program Files\Merzo Windows Optimizer'
  if (!(Test-Path $root)) { return 'ABSENT' }
  $lines = Get-ChildItem $root -File -Recurse -ErrorAction SilentlyContinue | Sort-Object FullName | ForEach-Object {
    $h = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
    "$($_.FullName.Substring($root.Length))|$($_.Length)|$h"
  }
  $tmp = Join-Path $TempDir 'production-fingerprint.txt'
  $lines | Set-Content $tmp -Encoding UTF8
  return (Get-FileHash $tmp -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-SourceOrigin {
  if (!(Test-Path (Join-Path $SourceDir '.git'))) { throw 'Dedicated Local Lab source checkout is missing.' }
  $origin = (& git -C $SourceDir remote get-url origin).Trim()
  $expected = [string]$Cfg.repositoryUrl
  $normalized = $origin.TrimEnd('/').Replace('.git','')
  $expectedNormalized = $expected.TrimEnd('/').Replace('.git','')
  if ($normalized -ne $expectedNormalized) { throw "Unexpected source origin: $origin" }
}

function Sync-Source {
  $sw = [Diagnostics.Stopwatch]::StartNew()
  Assert-DDriveBoundary
  if (!(Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is not installed or not in PATH.' }
  if (!(Test-Path (Join-Path $SourceDir '.git'))) {
    if (Test-Path $SourceDir) { Remove-Item $SourceDir -Recurse -Force }
    Write-Lab "Cloning $($Cfg.repositoryUrl) -> $SourceDir"
    & git clone --branch ([string]$Cfg.targetBranch) --single-branch ([string]$Cfg.repositoryUrl) $SourceDir 2>&1 | ForEach-Object { Write-Lab $_ }
    if ($LASTEXITCODE -ne 0) { throw "git clone failed: $LASTEXITCODE" }
  }
  Assert-SourceOrigin
  Write-Lab "Fetching exact branch $($Cfg.targetBranch)"
  & git -C $SourceDir fetch origin ([string]$Cfg.targetBranch) --prune 2>&1 | ForEach-Object { Write-Lab $_ }
  if ($LASTEXITCODE -ne 0) { throw "git fetch failed: $LASTEXITCODE" }
  & git -C $SourceDir checkout -B ([string]$Cfg.targetBranch) ("origin/" + [string]$Cfg.targetBranch) 2>&1 | ForEach-Object { Write-Lab $_ }
  if ($LASTEXITCODE -ne 0) { throw "git checkout failed: $LASTEXITCODE" }
  & git -C $SourceDir reset --hard ("origin/" + [string]$Cfg.targetBranch) 2>&1 | ForEach-Object { Write-Lab $_ }
  if ($LASTEXITCODE -ne 0) { throw "git reset failed: $LASTEXITCODE" }
  & git -C $SourceDir clean -fdx 2>&1 | ForEach-Object { Write-Lab $_ }
  if ($LASTEXITCODE -ne 0) { throw "git clean failed: $LASTEXITCODE" }
  $sha = (& git -C $SourceDir rev-parse HEAD).Trim()
  $sw.Stop(); Add-Stage 'source.sync' 'Source exact checkout' 'PASS' "$($Cfg.targetBranch) @ $sha" $sw.Elapsed.TotalSeconds
  return $sha
}


# Read-only discovery: winget may install Inno Setup 6 per-user, not under Program Files.
# Require a physical ISCC.exe with version metadata identifying major version 6.
# Do not copy local user paths into GitHub diagnostic stage summaries.

# Genuine Inno Setup 6 may expose 0.0.0.0 as the ISCC.exe file version.
# Its documented "/?" banner is a safe, read-only secondary identity check.
# Only a discovered ISCC.exe is invoked, with a fixed argument and timeout.
function Test-Inno6CompilerIdentity {
  param([Parameter(Mandatory)][string]$CompilerPath)
  try {
    $file=Get-Item -LiteralPath $CompilerPath -ErrorAction Stop
    if($file.PSIsContainer -or $file.Name -ine 'ISCC.exe'){return $false}
    $versions=@([string]$file.VersionInfo.FileVersion,[string]$file.VersionInfo.ProductVersion)
    if(@($versions|Where-Object{$_ -match '(?<!\d)7\.[0-9]+'}).Count-gt0){return $false}
    if(@($versions|Where-Object{$_ -match '(?<!\d)6\.[0-9]+'}).Count-gt0){return $true}
    $psi=[Diagnostics.ProcessStartInfo]::new()
    $psi.FileName=[string]$file.FullName
    $psi.ArgumentList.Add('/?')
    $psi.WorkingDirectory=[string]$file.DirectoryName
    $psi.UseShellExecute=$false
    $psi.CreateNoWindow=$true
    $psi.RedirectStandardOutput=$true
    $psi.RedirectStandardError=$true
    $proc=[Diagnostics.Process]::new()
    try {
      $proc.StartInfo=$psi
      if(-not $proc.Start()){return $false}
      $outputTask=$proc.StandardOutput.ReadToEndAsync()
      $errorTask=$proc.StandardError.ReadToEndAsync()
      if(-not $proc.WaitForExit(6000)){
        try{$proc.Kill($true)}catch{}
        return $false
      }
      $banner=$outputTask.GetAwaiter().GetResult()+[Environment]::NewLine+$errorTask.GetAwaiter().GetResult()
      return ($banner -match '(?im)^\s*Inno Setup 6(?:\.\d+)*\s+Command[- ]Line Compiler\b')
    }finally{
      $proc.Dispose()
    }
  }catch{
    return $false
  }
}

function Resolve-InnoSetup6Compiler {
  $candidates=[System.Collections.Generic.List[string]]::new()
  $x86=[Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
  foreach($dir in @(
    (Join-Path $env:ProgramFiles 'Inno Setup 6'),
    (Join-Path $x86 'Inno Setup 6'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6'),
    (Join-Path $env:LOCALAPPDATA 'Inno Setup 6')
  )) { if($dir){ $candidates.Add((Join-Path $dir 'ISCC.exe')) } }
  try {
    $cmd=Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if($cmd -and $cmd.Source){$candidates.Add([string]$cmd.Source)}
  }catch{}
  foreach($keyPath in @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\ISCC.exe',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\ISCC.exe'
  )){
    try{
      $appPath=(Get-Item -LiteralPath $keyPath -ErrorAction Stop).GetValue('')
      if($appPath){$candidates.Add([string]$appPath)}
    }catch{}
  }
  foreach($uninstallRoot in @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'
  )){
    foreach($key in @(Get-ChildItem -LiteralPath $uninstallRoot -ErrorAction SilentlyContinue)){
      try{
        $info=Get-ItemProperty -LiteralPath $key.PSPath -ErrorAction Stop
        if(([string]$info.DisplayName -notmatch '(?i)^Inno Setup(?:,? version)?\s*6(\b|\.)') -and
           ([string]$key.PSChildName -notmatch '(?i)^Inno Setup 6')){continue}
        foreach($location in @([string]$info.InstallLocation,[string]$info.'Inno Setup: App Path')){
          if(-not [string]::IsNullOrWhiteSpace($location)){
            $candidates.Add((Join-Path $location.Trim('"') 'ISCC.exe'))
          }
        }
      }catch{}
    }
  }
  # Search only the registered winget Inno package family, not the whole disk.
  $packages=Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
  if(Test-Path -LiteralPath $packages -PathType Container){
    foreach($package in @(Get-ChildItem -LiteralPath $packages -Directory -Filter 'JRSoftware.InnoSetup*' -ErrorAction SilentlyContinue)){
      foreach($item in @(Get-ChildItem -LiteralPath $package.FullName -File -Filter 'ISCC.exe' -Recurse -ErrorAction SilentlyContinue)){
        $candidates.Add([string]$item.FullName)
      }
    }
  }
  foreach($candidate in @($candidates | Select-Object -Unique)){
    try{
      $file=Get-Item -LiteralPath $candidate -ErrorAction Stop
      if($file.PSIsContainer -or $file.Name -ine 'ISCC.exe'){continue}
      if(Test-Inno6CompilerIdentity -CompilerPath ([string]$file.FullName)){
        return [string]$file.FullName
      }
    }catch{}
  }
  return $null
}

# Python 3 must be a working interpreter. The Windows App Execution Alias
# returns "Python" with exit code 9009 and is NOT a usable runtime.
# Running a tiny in-memory -c script is safer than trusting --version text.
function Test-Python3Runtime {
  try {
    $cmd=Get-Command python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if(-not $cmd){return $false}
    $result=@(& python -c 'import sys; print("MWO_PYTHON3_OK" if sys.version_info >= (3,10) else "MWO_PYTHON3_TOO_OLD")' 2>$null)
    if($LASTEXITCODE -ne 0){return $false}
    return (@($result|Where-Object{[string]$_ -eq 'MWO_PYTHON3_OK'}).Count -gt 0)
  }catch{
    return $false
  }
}

function Invoke-Diagnostics {
  $compiler=Resolve-InnoSetup6Compiler
  if($compiler){$env:MWO_INNO6_ISCC=$compiler}else{Remove-Item Env:\MWO_INNO6_ISCC -ErrorAction SilentlyContinue}
  $checks = @()
  $checks += @{ id='env.d'; name='D: доступен'; test={ Test-Path 'D:\' }; detail='D: required' }
  $checks += @{ id='env.git'; name='Git'; test={ [bool](Get-Command git -ErrorAction SilentlyContinue) }; detail='git in PATH' }
  $checks += @{ id='env.pwsh'; name='PowerShell 7'; test={ $PSVersionTable.PSVersion.Major -ge 7 }; detail=$PSVersionTable.PSVersion.ToString() }
  $checks += @{ id='env.dotnet'; name='.NET 10 SDK'; test={ try { [bool]((& dotnet --list-sdks 2>$null) -match '^10\.') } catch { $false } }; detail='dotnet --list-sdks' }
  $checks += @{ id='env.python'; name='Python 3.10+'; test={ Test-Python3Runtime }; detail='python -c script (reject Store alias exit 9009)' }
  $checks += @{ id='env.inno'; name='Inno Setup 6'; test={ [bool]$compiler }; detail=$(if($compiler){'ISCC.exe (version 6 detected)'}else{'ISCC.exe not found; inspect install location'}) }
  $checks += @{ id='safe.root'; name='Лаборатория только D:'; test={ $LabRoot.StartsWith('D:\',[System.StringComparison]::OrdinalIgnoreCase) }; detail=$LabRoot }
  $checks += @{ id='safe.prod'; name='Production Program Files только чтение'; test={ -not $LabRoot.StartsWith('C:\Program Files\Merzo Windows Optimizer',[System.StringComparison]::OrdinalIgnoreCase) }; detail='protected' }
  if (Test-Path (Join-Path $SourceDir '.git')) {
    $checks += @{ id='source.origin'; name='Source origin'; test={ try { Assert-SourceOrigin; $true } catch { $false } }; detail=[string]$Cfg.repository }
  }
  foreach ($c in $checks) {
    $sw=[Diagnostics.Stopwatch]::StartNew();$ok=$false
    try { $ok=[bool](& $c.test) } catch { $ok=$false }
    $sw.Stop();Add-Stage $c.id $c.name ($(if($ok){'PASS'}else{'FAIL'})) $c.detail $sw.Elapsed.TotalSeconds
  }
  $free = [math]::Round((Get-PSDrive D).Free/1GB,1)
  Add-Stage 'env.disk' 'Свободно на D:' ($(if($free-ge10){'PASS'}elseif($free-ge5){'WARN'}else{'FAIL'})) "$free GB" 0
}

function Prepare-BuildEnvironment {
  $dotnetHome=Join-Path $LabRoot 'Toolchain\dotnet-home'
  $nuget=Join-Path $LabRoot 'Toolchain\nuget-packages'
  $http=Join-Path $LabRoot 'Toolchain\nuget-http-cache'
  $bundle=Join-Path $LabRoot 'Temp\BundleExtract'
  $local=Join-Path $SandboxDir 'LocalAppData'
  foreach($p in @($dotnetHome,$nuget,$http,$bundle,$local)){New-Item $p -ItemType Directory -Force|Out-Null}
  $env:DOTNET_CLI_HOME=$dotnetHome
  $env:NUGET_PACKAGES=$nuget
  $env:NUGET_HTTP_CACHE_PATH=$http
  $env:DOTNET_BUNDLE_EXTRACT_BASE_DIR=$bundle
  $env:LOCALAPPDATA=$local
  $env:TEMP=$TempDir
  $env:TMP=$TempDir
  $env:RUNNER_TEMP=$TempDir
  $env:GITHUB_WORKSPACE=$SourceDir
  $env:GITHUB_ENV=Join-Path $TempDir 'github-env.txt'
  $env:GITHUB_OUTPUT=Join-Path $TempDir 'github-output.txt'
  $env:GITHUB_RUN_ID='0'
  $env:GITHUB_SHA=(& git -C $SourceDir rev-parse HEAD).Trim()
  $env:GITHUB_REPOSITORY=[string]$Cfg.repository
  Set-Content $env:GITHUB_ENV '' -Encoding UTF8
  Set-Content $env:GITHUB_OUTPUT '' -Encoding UTF8
}

function Stage-QuickBuild([string]$SourceSha) {
  $quick=Join-Path $TestBuildDir 'Quick'
  if(Test-Path $quick){Remove-Item $quick -Recurse -Force}
  New-Item $quick -ItemType Directory|Out-Null
  $distApp=Join-Path $SourceDir ([string]$Cfg.distApp)
  if(!(Test-Path $distApp)){throw "Built app missing: $distApp"}
  Copy-Item $distApp (Join-Path $quick 'App') -Recurse -Force
  $art=Join-Path $quick 'Artifacts'
  New-Item $art -ItemType Directory|Out-Null
  foreach($rel in @([string]$Cfg.portableZip,[string]$Cfg.portableSha,[string]$Cfg.installer,[string]$Cfg.installerSha)){
    $src=Join-Path $SourceDir $rel
    if(!(Test-Path $src)){throw "Built artifact missing: $rel"}
    Copy-Item $src (Join-Path $art (Split-Path $rel -Leaf)) -Force
  }
  $exe=Join-Path $quick 'App\MerzoWindowsOptimizer.exe'
  $exeSha=(Get-FileHash $exe -Algorithm SHA256).Hash.ToLowerInvariant()
  [ordered]@{sourceCommit=$SourceSha;sourceBranch=[string]$Cfg.targetBranch;productVersion=[string]$Cfg.productVersion;expectedFileVersion=[string]$Cfg.expectedFileVersion;exeSha=$exeSha;createdAt=(Get-Date).ToUniversalTime().ToString('o')}|ConvertTo-Json|Set-Content (Join-Path $quick 'BUILD.json') -Encoding UTF8
  return $quick
}

function Invoke-Quick {
  if(-not(Test-Python3Runtime)){throw 'Python 3.10+ interpreter unavailable. The Windows python alias (exit 9009) is not Python; install Python 3 and restart Test Center.'}
  $compiler=Resolve-InnoSetup6Compiler
  if(!$compiler){throw 'Inno Setup 6 ISCC.exe not found; run Diagnostics for prerequisite check.'}
  $env:MWO_INNO6_ISCC=$compiler
  $sourceSha=Sync-Source
  Prepare-BuildEnvironment
  $controller=Join-Path $SourceDir ([string]$Cfg.buildController)
  if(!(Test-Path $controller)){throw "Build controller missing: $controller"}
  $before=Get-ProductionFingerprint
  $sw=[Diagnostics.Stopwatch]::StartNew()
  Push-Location $SourceDir
  try {
    & pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File $controller 2>&1 | ForEach-Object { Write-Lab $_ }
    $code=$LASTEXITCODE
  } finally { Pop-Location }
  $sw.Stop()
  if($code-ne0){Add-Stage 'quick.build' 'Локальная cumulative сборка' 'FAIL' "controller exit=$code" $sw.Elapsed.TotalSeconds;throw "Build controller failed: $code"}
  Add-Stage 'quick.build' 'Локальная cumulative сборка' 'PASS' "controller=$($Cfg.buildController)" $sw.Elapsed.TotalSeconds
  $quick=Stage-QuickBuild $sourceSha
  $after=Get-ProductionFingerprint
  if($before-ne$after){Add-Stage 'safe.production' 'Production Program Files unchanged' 'FAIL' "$before -> $after" 0;throw 'Protected installed application changed during safe local verification.'}
  Add-Stage 'safe.production' 'Production Program Files unchanged' 'PASS' $after 0
  Add-Stage 'quick.stage' 'Quick test build' 'PASS' $quick 0
}

function Test-RealMainWindow([string]$ExePath) {
  Add-Type -AssemblyName UIAutomationClient
  Add-Type -AssemblyName UIAutomationTypes
  $p=Start-Process $ExePath -WorkingDirectory (Split-Path $ExePath -Parent) -PassThru
  $found=$false
  $startupError=''
  try {
    $deadline=(Get-Date).AddSeconds(25)
    while((Get-Date)-lt$deadline){
      $p.Refresh()
      if($p.HasExited){throw "Test app exited=$($p.ExitCode)"}
      $wins=[System.Windows.Automation.AutomationElement]::RootElement.FindAll([System.Windows.Automation.TreeScope]::Children,[System.Windows.Automation.Condition]::TrueCondition)
      foreach($w in $wins){
        try{
          if($w.Current.ProcessId-ne$p.Id){continue}
          $n=[string]$w.Current.Name
          if($n-match'(?i)startup error'){$startupError=$n}
          if($n-like'*Merzo Windows Optimizer*'){$found=$true}
        }catch{}
      }
      if($startupError){throw "Startup error window: $startupError"}
      if($found){break}
      Start-Sleep -Milliseconds 400
    }
    if(!$found){throw 'Real main window not detected.'}
    Start-Sleep -Seconds 5
    $p.Refresh()
    if($p.HasExited){throw "App was not stable after main window; exit=$($p.ExitCode)"}
  } finally {
    if(!$p.HasExited){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue}
  }
}

function Invoke-FullSafe {
  Invoke-Quick
  $quick=Join-Path $TestBuildDir 'Quick'
  $exe=Join-Path $quick 'App\MerzoWindowsOptimizer.exe'
  if(!(Test-Path $exe)){throw 'Quick build EXE missing'}
  $sw=[Diagnostics.Stopwatch]::StartNew()
  Test-RealMainWindow $exe
  $sw.Stop()
  Add-Stage 'full.runtime' 'Реальный запуск тестовой сборки' 'PASS' 'main window + bounded stability' $sw.Elapsed.TotalSeconds
  $current=Join-Path $TestBuildDir 'Current'
  $previous=Join-Path $TestBuildDir '.previous'
  if(Test-Path $previous){Remove-Item $previous -Recurse -Force}
  if(Test-Path $current){Move-Item $current $previous -Force}
  try {
    Copy-Item $quick $current -Recurse -Force
    if(Test-Path $previous){Remove-Item $previous -Recurse -Force}
  } catch {
    if(Test-Path $current){Remove-Item $current -Recurse -Force}
    if(Test-Path $previous){Move-Item $previous $current -Force}
    throw
  }
  Add-Stage 'full.promote' 'TestBuild Current' 'PASS' $current 0
}

function Assert-DestructiveLab {
  $flag=Join-Path $StateDir 'ALLOW-SYSTEM-MUTATION.json'
  if(!(Test-Path $flag)){throw 'Destructive profile BLOCKED. Dedicated lab machine is not armed.'}
  $j=Get-Content $flag -Raw|ConvertFrom-Json
  if($j.labOnly-ne$true-or[string]$j.machineName-ne$env:COMPUTERNAME){throw 'Destructive lab marker does not match this machine.'}
  $id=[Security.Principal.WindowsIdentity]::GetCurrent()
  $p=[Security.Principal.WindowsPrincipal]::new($id)
  if(-not$p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Destructive profile requires elevated Administrator process.'}
}

function Invoke-Destructive {
  Assert-DestructiveLab
  $current=Join-Path $TestBuildDir 'Current'
  $metaPath=Join-Path $current 'BUILD.json'
  if(!(Test-Path $metaPath)){throw 'No whole-profile Current build. Run Full Safe first.'}
  $meta=Get-Content $metaPath -Raw|ConvertFrom-Json
  $sourceNow=Sync-Source
  if([string]$meta.sourceCommit-ne[string]$sourceNow){throw "Current build is stale. Current=$($meta.sourceCommit) Source=$sourceNow. Run Full Safe again before destructive verification."}
  $art=Join-Path $current 'Artifacts'
  $zip=Join-Path $art 'MerzoWindowsOptimizer-portable-win-x64.zip'
  if(!(Test-Path $zip)){throw 'Current portable artifact missing'}
  $zipSha=(Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
  $scriptPath=Join-Path $SourceDir ([string]$Cfg.destructiveAcceptance)
  if(!(Test-Path $scriptPath)){throw "Destructive acceptance missing: $scriptPath"}
  Prepare-BuildEnvironment
  $sw=[Diagnostics.Stopwatch]::StartNew()
  Push-Location $SourceDir
  try {
    & pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File $scriptPath -ArtifactDir $art -BuildRun 0 -BuildHead ([string]$meta.sourceCommit) -ExpectedPortableSha $zipSha 2>&1|ForEach-Object{Write-Lab $_}
    $code=$LASTEXITCODE
  } finally { Pop-Location }
  $sw.Stop()
  if($code-ne0){Add-Stage 'destructive.game-recovery' 'GAME → production RestoreAll' 'FAIL' "exit=$code" $sw.Elapsed.TotalSeconds;throw "Destructive acceptance failed: $code"}
  Add-Stage 'destructive.game-recovery' 'GAME → production RestoreAll' 'PASS' 'mutation + production recovery verified' $sw.Elapsed.TotalSeconds
}

try {
  Set-Content $LogPath '' -Encoding UTF8
  Write-Lab "Merzo Optimizer Local Test Center $($Cfg.testCenterVersion) | profile=$Profile"
  Assert-DDriveBoundary
  switch($Profile){
    'Diagnostics' {
      Invoke-Diagnostics
      if(@($Stages|Where-Object state -eq 'FAIL').Count-gt0){Save-Result 'FAIL';exit 2}else{Save-Result 'PASS';exit 0}
    }
    'Sync' { Sync-Source|Out-Null;Save-Result 'PASS';exit 0 }
    'Quick' { Invoke-Quick;Save-Result 'PASS';exit 0 }
    'FullSafe' { Invoke-FullSafe;Save-Result 'PASS';exit 0 }
    'Destructive' { Invoke-Destructive;Save-Result 'PASS' $true $true;exit 0 }
  }
} catch {
  Add-Stage 'failure' 'First causal failure' 'FAIL' $_.Exception.Message 0
  Save-Result 'FAIL' ($Profile-eq'Destructive') ($Profile-eq'Destructive')
  Write-Error $_
  exit 1
}
