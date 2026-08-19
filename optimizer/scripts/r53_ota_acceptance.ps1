$ErrorActionPreference = 'Stop'

$statusPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'R53_OTA_ACCEPTANCE_STATUS.json'
$status = [ordered]@{
    conclusion = 'failure'
    createdAt = (Get-Date).ToUniversalTime().ToString('o')
    databaseId = [long]($env:GITHUB_RUN_ID ?? '0')
    headSha = $env:GITHUB_SHA
    publicRelease = 'pending'
    r52Baseline = 'pending'
    r52FeedContract = 'pending'
    r52ToR53Upgrade = 'pending'
    r53Launch = 'pending'
    installerSha = ''
    r52Path = ''
    r53Path = ''
    error = ''
}

function Save-Status {
    $status.createdAt = (Get-Date).ToUniversalTime().ToString('o')
    $status | ConvertTo-Json -Compress | Set-Content $statusPath -Encoding UTF8
}

function Stop-MerzoApp {
    Get-Process MerzoWindowsOptimizer -ErrorAction SilentlyContinue |
        Stop-Process -Force -ErrorAction SilentlyContinue
}

function Invoke-InnoInstaller {
    param(
        [Parameter(Mandatory=$true)][string]$Setup,
        [Parameter(Mandatory=$true)][string]$Arguments,
        [int]$TimeoutSeconds = 150
    )
    if (!(Test-Path $Setup)) { throw "Installer missing: $Setup" }
    Stop-MerzoApp
    $p = Start-Process $Setup -ArgumentList $Arguments -PassThru
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while (!$p.HasExited -and (Get-Date) -lt $deadline) {
        # Inherited Inno packages can launch the app from [Run] and wait for it.
        # CI closes only the app child, never Setup itself.
        Stop-MerzoApp
        Start-Sleep -Milliseconds 750
        $p.Refresh()
    }
    if (!$p.HasExited) {
        Stop-MerzoApp
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        throw "Installer timeout after $TimeoutSeconds seconds: $Setup"
    }
    if ($p.ExitCode -ne 0) { throw "Installer exit $($p.ExitCode): $Setup" }

    # Inno can hand work to a temporary child executable after the original
    # process exits. Do not inspect the installation until all Setup children stop.
    $childDeadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $childDeadline) {
        Stop-MerzoApp
        $children = Get-Process -ErrorAction SilentlyContinue |
            Where-Object { $_.ProcessName -like 'MerzoWindowsOptimizerSetup*' }
        if (!$children) { break }
        Start-Sleep -Milliseconds 750
    }
    $left = Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ProcessName -like 'MerzoWindowsOptimizerSetup*' }
    if ($left) { throw 'Installer child process did not finish in acceptance window' }
    Stop-MerzoApp
}

function Get-MerzoInstallEntry {
    $entries = @()
    foreach ($rp in @(
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
        'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )) {
        $entries += Get-ItemProperty $rp -ErrorAction SilentlyContinue |
            Where-Object { $_.DisplayName -like '*Merzo*Optimizer*' }
    }
    return $entries | Sort-Object DisplayVersion -Descending | Select-Object -First 1
}

function Find-MerzoExe {
    $entry = Get-MerzoInstallEntry
    $candidates = New-Object System.Collections.Generic.List[string]
    if ($entry) {
        if ($entry.InstallLocation) {
            $candidates.Add((Join-Path $entry.InstallLocation 'MerzoWindowsOptimizer.exe'))
        }
        if ($entry.UninstallString) {
            $raw = [string]$entry.UninstallString
            $uninstaller = ($raw -replace '^"([^\"]+)".*$','$1').Trim('"')
            if ($uninstaller -and (Test-Path $uninstaller)) {
                $candidates.Add((Join-Path (Split-Path $uninstaller -Parent) 'MerzoWindowsOptimizer.exe'))
            }
        }
    }
    foreach ($path in @(
        (Join-Path $env:ProgramFiles 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'),
        (Join-Path $env:LOCALAPPDATA 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\MerzoWindowsOptimizer\MerzoWindowsOptimizer.exe')
    )) { $candidates.Add($path) }

    foreach ($path in ($candidates | Select-Object -Unique)) {
        if ($path -and (Test-Path $path)) { return Get-Item $path }
    }

    foreach ($base in @($env:LOCALAPPDATA, $env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (!$base -or !(Test-Path $base)) { continue }
        foreach ($dir in (Get-ChildItem $base -Directory -Filter 'Merzo*' -ErrorAction SilentlyContinue)) {
            $hit = Get-ChildItem $dir.FullName -Recurse -Filter 'MerzoWindowsOptimizer.exe' -ErrorAction SilentlyContinue |
                Select-Object -First 1
            if ($hit) { return $hit }
        }
    }
    return $null
}

function Invoke-R52UpdateFeedProbe {
    param([Parameter(Mandatory=$true)][string]$WindowsDll)

    # The real R53 installer uses /CLOSEAPPLICATIONS. Therefore never LoadFrom
    # an installed Merzo DLL in this parent process: Restart Manager would
    # correctly close the CI shell because it holds a file being replaced.
    $probe = Join-Path $env:TEMP ("mwo-r52-feed-probe-{0}.ps1" -f [guid]::NewGuid().ToString('N'))
    @'
param([Parameter(Mandatory=$true)][string]$Dll)
$ErrorActionPreference='Stop'
$dir=Split-Path $Dll -Parent
Push-Location $dir
try {
    $asm=[Reflection.Assembly]::LoadFrom($Dll)
    $type=$asm.GetTypes() | Where-Object {$_.FullName -match 'GitHubUpdateService$'} | Select-Object -First 1
    if(!$type){throw 'GitHubUpdateService type missing'}
    Write-Output ('TYPE=' + $type.FullName)
    Write-Output ('CTORS=' + (($type.GetConstructors() | ForEach-Object {$_.ToString()}) -join ' | '))
    Write-Output ('METHODS=' + (($type.GetMethods([Reflection.BindingFlags]'Public,Instance,Static,DeclaredOnly') | ForEach-Object {$_.ToString()}) -join ' | '))
    $ctor=$type.GetConstructor([type[]]@([string],[string],[System.Net.Http.HttpMessageHandler]))
    if(!$ctor){throw 'Expected R52 updater constructor missing'}
    $handler=[System.Net.Http.HttpClientHandler]::new()
    $svc=$ctor.Invoke(@('Merzo4','my-app-updates',$handler))
    try {
        $method=$type.GetMethod('CheckAsync',[type[]]@([System.Threading.CancellationToken]))
        if(!$method){throw 'R52 CheckAsync(CancellationToken) missing'}
        $task=$method.Invoke($svc,@([System.Threading.CancellationToken]::None))
        $task.GetAwaiter().GetResult() | Out-Null
        $result=$task.Result
        Write-Output ('CHECK=' + ($result | ConvertTo-Json -Depth 10 -Compress))
    }
    finally {
        if($svc -is [IDisposable]){$svc.Dispose()}
        $handler.Dispose()
    }
}
finally { Pop-Location }
'@ | Set-Content $probe -Encoding UTF8

    try {
        $lines = & pwsh -NoLogo -NoProfile -File $probe -Dll $WindowsDll 2>&1
        $exit = $LASTEXITCODE
        $text = ($lines | ForEach-Object { [string]$_ }) -join "`n"
        Write-Host $text
        if ($exit -ne 0) { throw "R52 updater feed probe exit $exit" }
        if ($text -notmatch 'CHECK=') { throw 'R52 updater CheckAsync did not return a result' }
        if ($text -notmatch '0\.1\.53') { throw "R52 updater did not see R53 in live feed: $text" }
        return $text
    }
    finally {
        Remove-Item $probe -Force -ErrorAction SilentlyContinue
    }
}

try {
    if ([string]::IsNullOrWhiteSpace($env:GH_TOKEN)) { throw 'GH_TOKEN missing' }
    $repo = $env:GITHUB_REPOSITORY
    if ([string]::IsNullOrWhiteSpace($repo)) { throw 'GITHUB_REPOSITORY missing' }

    $latest = gh api "repos/$repo/releases/latest" | ConvertFrom-Json
    if ($latest.tag_name -ne 'mwo-v0.1.53' -or $latest.draft -or $latest.prerelease) {
        throw "Public latest release is not stable R53: $($latest.tag_name)"
    }
    $status.publicRelease = 'success'

    Remove-Item public-r52,public-r53 -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force public-r52,public-r53 | Out-Null
    gh release download mwo-v0.1.52 --repo $repo --dir public-r52 --pattern 'MerzoWindowsOptimizerSetup-win-x64.exe'
    gh release download mwo-v0.1.53 --repo $repo --dir public-r53 --pattern 'MerzoWindowsOptimizerSetup-win-x64.exe' --pattern 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256'

    $r52Setup = (Resolve-Path 'public-r52/MerzoWindowsOptimizerSetup-win-x64.exe').Path
    $r53Setup = (Resolve-Path 'public-r53/MerzoWindowsOptimizerSetup-win-x64.exe').Path
    $r53Sidecar = (Resolve-Path 'public-r53/MerzoWindowsOptimizerSetup-win-x64.exe.sha256').Path
    $sha = (Get-FileHash $r53Setup -Algorithm SHA256).Hash.ToLowerInvariant()
    if (-not (Get-Content $r53Sidecar -Raw).ToLowerInvariant().Contains($sha)) {
        throw 'Public R53 installer SHA sidecar mismatch'
    }
    $asset = $latest.assets | Where-Object name -eq 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
    if (!$asset) { throw 'Public R53 installer asset missing from latest release API' }
    if ($asset.digest -and $asset.digest -ne "sha256:$sha") { throw "Public R53 API digest mismatch: $($asset.digest)" }
    $status.installerSha = $sha
    Write-Host "R53_PUBLIC_RELEASE_PASS sha=$sha"

    Invoke-InnoInstaller -Setup $r52Setup -Arguments '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
    $r52Exe = Find-MerzoExe
    if (!$r52Exe) { throw 'Installed public R52 executable not found' }
    $r52Version = [Diagnostics.FileVersionInfo]::GetVersionInfo($r52Exe.FullName).FileVersion
    if (-not $r52Version.StartsWith('0.1.52')) { throw "Public baseline is not R52: $r52Version at $($r52Exe.FullName)" }
    $status.r52Path = $r52Exe.FullName
    $status.r52Baseline = 'success'
    Write-Host "R52_BASELINE_PASS path=$($r52Exe.FullName) version=$r52Version"

    $updateCfg = Join-Path $r52Exe.DirectoryName 'data\update_settings.json'
    if (Test-Path $updateCfg) { Write-Host ('R52_UPDATE_SETTINGS=' + (Get-Content $updateCfg -Raw)) }
    $winDll = Join-Path $r52Exe.DirectoryName 'MerzoOptimizer.Windows.dll'
    if (!(Test-Path $winDll)) { throw 'R52 updater assembly missing' }
    $feedText = Invoke-R52UpdateFeedProbe -WindowsDll $winDll
    if ($feedText -notmatch 'Merzo4' -or $feedText -notmatch 'my-app-updates') {
        # Constructor output does not contain values, so retain config/binary ownership proof below.
        $bytes = [IO.File]::ReadAllBytes($winDll)
        $ascii = [Text.Encoding]::ASCII.GetString($bytes)
        $unicode = [Text.Encoding]::Unicode.GetString($bytes)
        if (($ascii -notmatch 'Merzo4') -and ($unicode -notmatch 'Merzo4')) { throw 'R52 updater owner contract missing' }
        if (($ascii -notmatch 'my-app-updates') -and ($unicode -notmatch 'my-app-updates')) { throw 'R52 updater repository contract missing' }
    }
    $status.r52FeedContract = 'success'
    Write-Host 'R52_LIVE_CHECKASYNC_SEES_R53_PASS'

    # Child feed-probe is gone here, so no CI process holds Merzo assemblies.
    Invoke-InnoInstaller -Setup $r53Setup -Arguments '/SILENT /MERZOUPDATE=1 /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
    $canonical = Join-Path $env:ProgramFiles 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'
    if (!(Test-Path $canonical)) { throw "R53 canonical Program Files executable missing: $canonical" }
    $r53Version = [Diagnostics.FileVersionInfo]::GetVersionInfo($canonical).FileVersion
    if ($r53Version -ne '0.1.53.0') { throw "Installed R53 FileVersion mismatch: $r53Version" }
    $entry = Get-MerzoInstallEntry
    if (!$entry -or !$entry.InstallLocation) { throw 'R53 uninstall registry InstallLocation missing' }
    $registered = Join-Path $entry.InstallLocation 'MerzoWindowsOptimizer.exe'
    if ([IO.Path]::GetFullPath($registered).TrimEnd('\') -ne [IO.Path]::GetFullPath($canonical).TrimEnd('\')) {
        throw "R53 uninstall registry points outside canonical Program Files path: $registered"
    }
    $status.r53Path = $canonical
    $status.r52ToR53Upgrade = 'success'
    Write-Host "R52_TO_R53_OTA_MIGRATION_PASS path=$canonical version=$r53Version"
    if ($r52Exe.FullName -ne $canonical -and (Test-Path $r52Exe.FullName)) {
        Write-Host "R53_LEGACY_PATH_RESIDUAL_INFO=$($r52Exe.FullName)"
    }

    Stop-MerzoApp
    $app = Start-Process $canonical -PassThru
    Start-Sleep -Seconds 5
    $app.Refresh()
    if ($app.HasExited) { throw "Installed R53 executable exited during launch acceptance: $($app.ExitCode)" }
    Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue
    $status.r53Launch = 'success'
    Write-Host "R53_INSTALLED_LAUNCH_PASS pid=$($app.Id)"

    $status.conclusion = 'success'
    Save-Status
    Write-Host 'R53_PUBLIC_OTA_ACCEPTANCE_PASS'
}
catch {
    $status.error = $_.Exception.Message
    Save-Status
    Write-Host "::error::$($_.Exception.Message)"
    exit 1
}
