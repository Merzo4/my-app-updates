param(
    [switch]$ForceUpdate,
    [switch]$ReinstallCurrent,
    [switch]$NoUpdate,
    [int]$WaitPid = 0
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$InstallRoot = [IO.Path]::GetFullPath((Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)))
$LauncherRoot = Join-Path $InstallRoot "launcher"
$VersionsRoot = Join-Path $InstallRoot "versions"
$SharedRoot = Join-Path $InstallRoot "shared"
$ConfigPath = Join-Path $LauncherRoot "config.json"

$AppDataRoot = Join-Path $env:LOCALAPPDATA "MerzoStreamSuite"
$StateRoot = Join-Path $AppDataRoot "update5"
$StateFile = Join-Path $StateRoot "state.json"
$ReleaseCache = Join-Path $StateRoot "latest_release.json"
$HealthRoot = Join-Path $StateRoot "health"
$LogDir = Join-Path $AppDataRoot "logs"
$LogFile = Join-Path $LogDir "launcher5.log"
$HistoryFile = Join-Path $AppDataRoot "updates\history_v5.json"

New-Item -ItemType Directory -Force -Path `
    $VersionsRoot, $StateRoot, $HealthRoot, $LogDir, (Split-Path -Parent $HistoryFile) | Out-Null

function Write-Log {
    param([string]$Message)
    $line = "{0} [Launcher5] {1}" -f (Get-Date).ToUniversalTime().ToString("o"), $Message
    Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value $line
}

function Read-Json {
    param([string]$Path)
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Save-JsonAtomic {
    param([string]$Path, $Value)
    $temp = $Path + ".tmp"
    $Value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $temp -Encoding UTF8
    Move-Item -LiteralPath $temp -Destination $Path -Force
}

function New-DefaultState {
    return [pscustomobject][ordered]@{
        schema = 5
        engine_version = "5.0"
        current_version = ""
        previous_version = ""
        last_good_version = ""
        pending_version = ""
        pending_since_utc = ""
        pending_release_id = ""
        pending_package_sha256 = ""
        rollback_path = ""
        failed_version = ""
        last_check_utc = ""
        last_release_id = ""
    }
}

function Parse-Version {
    param([string]$Value)

    $text = $Value.Trim().ToLowerInvariant()
    if ($text.StartsWith("v")) { $text = $text.Substring(1) }
    if ($text -notmatch '^(\d+)\.(\d+)\.(\d+)([a-z]*)$') {
        return @(0, 0, 0, 0)
    }

    $rank = 0
    foreach ($char in $Matches[4].ToCharArray()) {
        $rank = ($rank * 26) + ([int][char]$char - [int][char]'a' + 1)
    }

    return @([int]$Matches[1], [int]$Matches[2], [int]$Matches[3], [int]$rank)
}

function Compare-Version {
    param([string]$A, [string]$B)

    $left = Parse-Version $A
    $right = Parse-Version $B
    for ($i = 0; $i -lt 4; $i++) {
        if ($left[$i] -lt $right[$i]) { return -1 }
        if ($left[$i] -gt $right[$i]) { return 1 }
    }
    return 0
}

function Normalize-Version {
    param([string]$Tag)
    $version = $Tag.Trim()
    if ($version.StartsWith("v", [StringComparison]::OrdinalIgnoreCase)) {
        $version = $version.Substring(1)
    }
    return $version
}

function Get-HighestInstalledVersion {
    $best = ""
    foreach ($dir in @(Get-ChildItem -LiteralPath $VersionsRoot -Directory -ErrorAction SilentlyContinue)) {
        if ($dir.Name.StartsWith(".")) { continue }
        if (-not (Test-Path -LiteralPath (Join-Path $dir.FullName "release_manifest.json"))) { continue }
        if ([string]::IsNullOrWhiteSpace($best) -or (Compare-Version $dir.Name $best) -gt 0) {
            $best = $dir.Name
        }
    }
    return $best
}

function Ensure-State {
    $state = $null
    if (Test-Path -LiteralPath $StateFile) {
        try { $state = Read-Json $StateFile } catch {}
    }
    if ($null -eq $state) { $state = New-DefaultState }

    $current = [string]$state.current_version
    if ([string]::IsNullOrWhiteSpace($current) -or -not (Test-Path -LiteralPath (Join-Path $VersionsRoot $current))) {
        $best = Get-HighestInstalledVersion
        if (-not [string]::IsNullOrWhiteSpace($best)) {
            $state.current_version = $best
            if ([string]::IsNullOrWhiteSpace([string]$state.last_good_version)) {
                $state.last_good_version = $best
            }
            Save-JsonAtomic $StateFile $state
        }
    }

    return $state
}

function Get-Config {
    $config = [pscustomobject]@{
        repository = "Merzo4/my-app-updates"
        api_version = "2026-03-10"
        check_interval_minutes = 30
        network_timeout_seconds = 3
        startup_health_timeout_seconds = 45
        keep_versions = 2
        auto_install = $true
        check_on_start = $true
        channel = "beta"
    }

    if (Test-Path -LiteralPath $ConfigPath) {
        try {
            $fileConfig = Read-Json $ConfigPath
            foreach ($property in $fileConfig.PSObject.Properties) {
                $config | Add-Member -NotePropertyName $property.Name -NotePropertyValue $property.Value -Force
            }
        } catch {}
    }

    $userSettings = Join-Path $AppDataRoot "settings\updates.json"
    if (Test-Path -LiteralPath $userSettings) {
        try {
            $user = Read-Json $userSettings
            if ($null -ne $user.check_on_start) {
                $config.check_on_start = [bool]$user.check_on_start
            }
            if ($null -ne $user.check_interval_minutes -and [int]$user.check_interval_minutes -ge 5) {
                $config.check_interval_minutes = [int]$user.check_interval_minutes
            }
        } catch {}
    }

    return $config
}

function Wait-ForPid {
    param([int]$PidToWait)
    if ($PidToWait -le 0) { return }

    for ($i = 0; $i -lt 600; $i++) {
        try {
            Get-Process -Id $PidToWait -ErrorAction Stop | Out-Null
            Start-Sleep -Milliseconds 200
        } catch {
            return
        }
    }
}

function Append-History {
    param([string]$From, [string]$To, [string]$Status)

    $history = @()
    if (Test-Path -LiteralPath $HistoryFile) {
        try {
            $old = Read-Json $HistoryFile
            if ($old -is [System.Array]) { $history = @($old) }
        } catch {}
    }

    $history += [pscustomobject][ordered]@{
        from_version = $From
        to_version = $To
        status = $Status
        update_engine = "5.0"
        time_utc = (Get-Date).ToUniversalTime().ToString("o")
        updated_files = @("full release package")
        release_notes = @()
    }

    if ($history.Count -gt 30) {
        $history = @($history | Select-Object -Last 30)
    }
    Save-JsonAtomic $HistoryFile $history
}

function Start-Version {
    param(
        [string]$Version,
        $State,
        $Config,
        [switch]$HealthCheck
    )

    $versionRoot = Join-Path $VersionsRoot $Version
    $runScript = Join-Path $versionRoot "RUN_VERSION.ps1"
    if (-not (Test-Path -LiteralPath $runScript)) {
        throw "Не найден RUN_VERSION.ps1 версии $Version"
    }

    $safeVersion = $Version -replace '[^0-9A-Za-z._-]', '_'
    $healthFile = Join-Path $HealthRoot ($safeVersion + ".json")

    if ($HealthCheck) {
        Remove-Item -LiteralPath $healthFile -Force -ErrorAction SilentlyContinue
        $env:MERZOSTREAM_HEALTH_FILE = $healthFile
    } else {
        $env:MERZOSTREAM_HEALTH_FILE = ""
    }

    $env:MERZOSTREAM_INSTALL_ROOT = $InstallRoot
    $env:MERZOSTREAM_SHARED_ROOT = $SharedRoot
    $env:MERZOSTREAM_ACTIVE_VERSION = $Version

    & powershell.exe `
        -NoLogo `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File $runScript `
        -AppRoot $versionRoot

    if ($LASTEXITCODE -ne 0) {
        throw "Версия $Version не смогла запустить runtime"
    }

    if (-not $HealthCheck) { return $true }

    $iterations = [int]$Config.startup_health_timeout_seconds * 4
    for ($i = 0; $i -lt $iterations; $i++) {
        if (Test-Path -LiteralPath $healthFile) {
            try {
                $health = Read-Json $healthFile
                if ([bool]$health.ok -and [string]$health.version -eq $Version) {
                    return $true
                }
            } catch {}
        }
        Start-Sleep -Milliseconds 250
    }

    return $false
}

function Cleanup-OldVersions {
    param($State)

    $keep = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
    foreach ($version in @(
        [string]$State.current_version,
        [string]$State.previous_version,
        [string]$State.last_good_version
    )) {
        if (-not [string]::IsNullOrWhiteSpace($version)) { [void]$keep.Add($version) }
    }

    foreach ($dir in @(Get-ChildItem -LiteralPath $VersionsRoot -Directory -ErrorAction SilentlyContinue)) {
        if (-not $dir.Name.StartsWith(".") -and -not $keep.Contains($dir.Name)) {
            Remove-Item -LiteralPath $dir.FullName -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    Get-ChildItem -LiteralPath $VersionsRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name.StartsWith(".rollback-") -and $_.LastWriteTimeUtc -lt [datetime]::UtcNow.AddDays(-7) } |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

function Rollback-Pending {
    param($State, $Config, [string]$FailedVersion)

    Write-Log "Health-check failed for $FailedVersion. Starting automatic rollback."

    $rollbackPath = [string]$State.rollback_path
    $failedTarget = Join-Path $VersionsRoot $FailedVersion
    if (-not [string]::IsNullOrWhiteSpace($rollbackPath) -and (Test-Path -LiteralPath $rollbackPath)) {
        if (Test-Path -LiteralPath $failedTarget) {
            Remove-Item -LiteralPath $failedTarget -Recurse -Force -ErrorAction SilentlyContinue
        }
        Move-Item -LiteralPath $rollbackPath -Destination $failedTarget -Force
    }

    $previous = [string]$State.previous_version
    if ([string]::IsNullOrWhiteSpace($previous) -or -not (Test-Path -LiteralPath (Join-Path $VersionsRoot $previous))) {
        $previous = [string]$State.last_good_version
    }

    if (-not [string]::IsNullOrWhiteSpace($previous) -and (Test-Path -LiteralPath (Join-Path $VersionsRoot $previous))) {
        $State.current_version = $previous
    }

    $State.pending_version = ""
    $State.failed_version = $FailedVersion
    $State.rollback_path = ""
    Save-JsonAtomic $StateFile $State
    Append-History $FailedVersion ([string]$State.current_version) "rollback"

    try {
        Add-Type -AssemblyName PresentationFramework -ErrorAction SilentlyContinue
        [System.Windows.MessageBox]::Show(
            "Новая версия не подтвердила запуск. Автоматически возвращена предыдущая рабочая версия.",
            "MerzoStream Suite"
        ) | Out-Null
    } catch {}

    if (-not [string]::IsNullOrWhiteSpace([string]$State.current_version)) {
        [void](Start-Version ([string]$State.current_version) $State $Config)
    }
}

function Fetch-LatestRelease {
    param($Config)
    $url = "https://api.github.com/repos/$($Config.repository)/releases?per_page=20"
    $releases = Invoke-RestMethod `
        -Uri $url `
        -Method Get `
        -TimeoutSec ([int]$Config.network_timeout_seconds) `
        -Headers @{
            "User-Agent" = "MerzoStreamSuite-Launcher/5.0"
            "Accept" = "application/vnd.github+json"
            "X-GitHub-Api-Version" = [string]$Config.api_version
        }

    $selected = $null
    foreach ($candidate in @($releases)) {
        if ([bool]$candidate.draft) { continue }
        if ([string]$Config.channel -eq "stable" -and [bool]$candidate.prerelease) { continue }
        $candidateVersion = Normalize-Version ([string]$candidate.tag_name)
        if ($candidateVersion -notmatch '^\d+\.\d+\.\d+[a-z]*$') { continue }
        if ($null -eq $selected -or (Compare-Version $candidateVersion (Normalize-Version ([string]$selected.tag_name))) -gt 0) {
            $selected = $candidate
        }
    }
    if ($null -eq $selected) { throw "В GitHub нет подходящего опубликованного Release" }
    return $selected
}

try {
    Wait-ForPid $WaitPid
    $config = Get-Config
    $state = Ensure-State

    if ([string]::IsNullOrWhiteSpace([string]$state.current_version)) {
        throw "Не найдена установленная версия MerzoStream Suite"
    }

    # Explicit Update Center request. It waits for the running app to exit and then updates synchronously.
    if ($ForceUpdate) {
        $mutex = New-Object System.Threading.Mutex($false, "Local\MerzoStreamSuite_UpdateEngine5")
        $locked = $false
        try {
            $locked = $mutex.WaitOne(120000)
            if (-not $locked) { throw "Update Engine занят другим процессом" }

            $release = Fetch-LatestRelease $config
            $remoteVersion = Normalize-Version ([string]$release.tag_name)
            $comparison = Compare-Version $remoteVersion ([string]$state.current_version)

            if ($comparison -gt 0 -or ($ReinstallCurrent -and $comparison -eq 0)) {
                $release | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $ReleaseCache -Encoding UTF8

                $updaterArgs = @(
                    "-InstallRoot", $InstallRoot,
                    "-ReleaseJsonPath", $ReleaseCache
                )
                if ($ReinstallCurrent) { $updaterArgs += "-ReinstallCurrent" }

                & powershell.exe `
                    -NoLogo `
                    -NoProfile `
                    -ExecutionPolicy Bypass `
                    -File (Join-Path $LauncherRoot "Updater5.ps1") `
                    @updaterArgs

                if ($LASTEXITCODE -ne 0) {
                    throw "Updater5 завершился с кодом $LASTEXITCODE"
                }
            }
        } catch {
            Write-Log ("Force update failed: " + $_.Exception.Message)
        } finally {
            if ($locked) {
                try { $mutex.ReleaseMutex() } catch {}
            }
            if ($null -ne $mutex) { $mutex.Dispose() }
        }

        $state = Ensure-State
    }

    # A background-prepared version is activated only here, before launching its UI.
    $currentVersion = [string]$state.current_version
    $hasPending = (
        -not [string]::IsNullOrWhiteSpace([string]$state.pending_version) -and
        [string]$state.pending_version -eq $currentVersion
    )

    if ($hasPending) {
        $mutex = New-Object System.Threading.Mutex($false, "Local\MerzoStreamSuite_UpdateEngine5")
        $locked = $false
        try {
            $locked = $mutex.WaitOne(120000)
            if (-not $locked) { throw "Update Engine занят другим процессом" }

            $state = Ensure-State
            $currentVersion = [string]$state.current_version
            if ([string]$state.pending_version -eq $currentVersion) {
                $healthy = $false
                try {
                    $healthy = Start-Version $currentVersion $state $config -HealthCheck
                } catch {
                    Write-Log ("First start failed: " + $_.Exception.Message)
                }

                if ($healthy) {
                    $from = [string]$state.previous_version
                    $state.pending_version = ""
                    $state.last_good_version = $currentVersion
                    $state.rollback_path = ""
                    $state.failed_version = ""
                    Save-JsonAtomic $StateFile $state
                    Append-History $from $currentVersion "success"
                    Cleanup-OldVersions $state
                    Write-Log "Version $currentVersion confirmed healthy."
                    exit 0
                }

                Rollback-Pending $state $config $currentVersion
                exit 0
            }
        } finally {
            if ($locked) {
                try { $mutex.ReleaseMutex() } catch {}
            }
            if ($null -ne $mutex) { $mutex.Dispose() }
        }
    }

    # Fast path: launch immediately. No network call is allowed to delay the UI.
    [void](Start-Version $currentVersion $state $config)

    # Check/download updates in a detached low-priority process after the UI has been launched.
    if (-not $NoUpdate -and -not $ForceUpdate -and [bool]$config.check_on_start) {
        $backgroundScript = Join-Path $LauncherRoot "BackgroundCheck.ps1"
        if (Test-Path -LiteralPath $backgroundScript) {
            $backgroundProcess = Start-Process `
                -FilePath "powershell.exe" `
                -ArgumentList @(
                    "-NoLogo",
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-WindowStyle", "Hidden",
                    "-File", ('"' + $backgroundScript + '"'),
                    "-InstallRoot", ('"' + $InstallRoot + '"')
                ) `
                -WindowStyle Hidden `
                -PassThru
            try { $backgroundProcess.PriorityClass = "BelowNormal" } catch {}
        }
    }

    exit 0
} catch {
    Write-Log ("FATAL: " + $_.Exception.Message)
    try {
        Add-Type -AssemblyName PresentationFramework -ErrorAction SilentlyContinue
        [System.Windows.MessageBox]::Show(
            $_.Exception.Message,
            "MerzoStream Suite — Launcher 5.0"
        ) | Out-Null
    } catch {}
    exit 1
}
