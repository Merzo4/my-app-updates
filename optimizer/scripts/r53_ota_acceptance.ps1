$ErrorActionPreference = 'Stop'

$optimizerRoot = Split-Path $PSScriptRoot -Parent
$statusPath = Join-Path $optimizerRoot 'R53_OTA_ACCEPTANCE_STATUS.json'
$feedProbe = Join-Path $PSScriptRoot 'r53_r52_feed_probe.ps1'
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

function Wait-MerzoSetupChildren {
    param([int]$TimeoutSeconds = 90)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        Stop-MerzoApp
        $children = Get-Process -ErrorAction SilentlyContinue |
            Where-Object { $_.ProcessName -like 'MerzoWindowsOptimizerSetup*' }
        if (!$children) { return }
        Start-Sleep -Milliseconds 700
    }
    throw 'Merzo installer child process did not finish in acceptance window'
}

function Invoke-MerzoInstaller {
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
        # Historical Inno packages may launch the app and wait for it.
        # CI closes only the app child; Setup continues normally.
        Stop-MerzoApp
        Start-Sleep -Milliseconds 700
        $p.Refresh()
    }
    if (!$p.HasExited) {
        Stop-MerzoApp
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        throw "Installer timeout after $TimeoutSeconds seconds: $Setup"
    }
    if ($p.ExitCode -ne 0) { throw "Installer exit $($p.ExitCode): $Setup" }
    Wait-MerzoSetupChildren
    Stop-MerzoApp
}

function Get-MerzoUninstallEntry {
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

try {
    if ([string]::IsNullOrWhiteSpace($env:GH_TOKEN)) { throw 'GH_TOKEN missing' }
    if ([string]::IsNullOrWhiteSpace($env:GITHUB_REPOSITORY)) { throw 'GITHUB_REPOSITORY missing' }
    if (!(Test-Path $feedProbe)) { throw "R52 feed probe missing: $feedProbe" }
    $repo = $env:GITHUB_REPOSITORY

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
    if ($asset.digest -and $asset.digest -ne "sha256:$sha") {
        throw "Public R53 API digest mismatch: $($asset.digest)"
    }
    $status.installerSha = $sha
    Write-Host "R53_PUBLIC_RELEASE_PASS sha=$sha"

    Invoke-MerzoInstaller -Setup $r52Setup -Arguments '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-'
    $canonical = Join-Path $env:ProgramFiles 'Merzo Windows Optimizer\MerzoWindowsOptimizer.exe'
    if (!(Test-Path $canonical)) { throw "Public R52 canonical executable missing: $canonical" }
    $r52Version = [Diagnostics.FileVersionInfo]::GetVersionInfo($canonical).FileVersion
    if ($r52Version -ne '0.1.52.0') { throw "Public baseline FileVersion is not 0.1.52.0: $r52Version" }
    $status.r52Path = $canonical
    $status.r52Baseline = 'success'
    Write-Host "R52_BASELINE_PASS path=$canonical version=$r52Version"

    $cfgPath = Join-Path (Split-Path $canonical -Parent) 'data\update_settings.json'
    if (!(Test-Path $cfgPath)) { throw 'R52 update_settings.json missing' }
    $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
    if ($cfg.repository_owner -ne 'Merzo4' -or $cfg.repository_name -ne 'my-app-updates') {
        throw 'R52 update channel is not Merzo4/my-app-updates'
    }
    if ($cfg.release_tag_prefix -ne 'mwo-v') { throw "R52 tag prefix mismatch: $($cfg.release_tag_prefix)" }
    if ($cfg.asset_name_contains -ne 'MerzoWindowsOptimizerSetup-win-x64.exe') {
        throw "R52 update asset selector mismatch: $($cfg.asset_name_contains)"
    }
    Write-Host ('R52_UPDATE_SETTINGS_PASS=' + ($cfg | ConvertTo-Json -Compress))

    $winDll = Join-Path (Split-Path $canonical -Parent) 'MerzoOptimizer.Windows.dll'
    if (!(Test-Path $winDll)) { throw 'R52 updater assembly missing' }
    # Execute in a separate process so Restart Manager can later replace the DLL.
    $probeLines = & pwsh -NoLogo -NoProfile -File $feedProbe -Dll $winDll -ExpectedVersion '0.1.53' 2>&1
    $probeExit = $LASTEXITCODE
    $probeText = ($probeLines | ForEach-Object { [string]$_ }) -join "`n"
    Write-Host $probeText
    if ($probeExit -ne 0) { throw "R52 live feed probe failed with exit $probeExit" }
    if ($probeText -notmatch 'R52_LIVE_FEED_PASS') { throw 'R52 live feed did not confirm R53' }
    $status.r52FeedContract = 'success'
    Write-Host 'R52_LIVE_CHECKASYNC_SEES_R53_PASS'

    Invoke-MerzoInstaller -Setup $r53Setup -Arguments '/SILENT /MERZOUPDATE=1 /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /SP-'
    if (!(Test-Path $canonical)) { throw "R53 canonical Program Files executable missing: $canonical" }
    $r53Version = [Diagnostics.FileVersionInfo]::GetVersionInfo($canonical).FileVersion
    if ($r53Version -ne '0.1.53.0') { throw "Installed R53 FileVersion mismatch: $r53Version" }
    $entry = Get-MerzoUninstallEntry
    if (!$entry -or !$entry.InstallLocation) { throw 'R53 uninstall registry InstallLocation missing' }
    $registered = Join-Path $entry.InstallLocation 'MerzoWindowsOptimizer.exe'
    if ([IO.Path]::GetFullPath($registered).TrimEnd('\') -ne [IO.Path]::GetFullPath($canonical).TrimEnd('\')) {
        throw "R53 uninstall registry points outside canonical Program Files path: $registered"
    }
    $status.r53Path = $canonical
    $status.r52ToR53Upgrade = 'success'
    Write-Host "R52_TO_R53_OTA_MIGRATION_PASS path=$canonical version=$r53Version"

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
