param(
    [Parameter(Mandatory = $true)]
    [string]$InstallRoot
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$InstallRoot = [IO.Path]::GetFullPath($InstallRoot)
$LauncherRoot = Join-Path $InstallRoot "launcher"
$ConfigPath = Join-Path $LauncherRoot "config.json"

$AppDataRoot = Join-Path $env:LOCALAPPDATA "MerzoStreamSuite"
$StateRoot = Join-Path $AppDataRoot "update5"
$StateFile = Join-Path $StateRoot "state.json"
$ReleaseCache = Join-Path $StateRoot "latest_release.json"
$LogDir = Join-Path $AppDataRoot "logs"
$LogFile = Join-Path $LogDir "launcher5.log"

New-Item -ItemType Directory -Force -Path $StateRoot, $LogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $line = "{0} [Background5] {1}" -f (Get-Date).ToUniversalTime().ToString("o"), $Message
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

function Get-Config {
    $config = [pscustomobject]@{
        repository = "Merzo4/my-app-updates"
        api_version = "2026-03-10"
        check_interval_minutes = 30
        network_timeout_seconds = 3
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

function Test-CheckDue {
    param($State, $Config)

    $text = [string]$State.last_check_utc
    if ([string]::IsNullOrWhiteSpace($text)) { return $true }

    try {
        $last = [datetime]::Parse($text).ToUniversalTime()
        return (([datetime]::UtcNow - $last).TotalMinutes -ge [double]$Config.check_interval_minutes)
    } catch {
        return $true
    }
}

$mutex = New-Object System.Threading.Mutex($false, "Local\MerzoStreamSuite_UpdateEngine5")
$locked = $false

try {
    $config = Get-Config
    if (-not [bool]$config.check_on_start) { exit 0 }
    if (-not (Test-Path -LiteralPath $StateFile)) { exit 0 }

    $state = Read-Json $StateFile
    if (-not (Test-CheckDue $state $config)) { exit 0 }

    $locked = $mutex.WaitOne(0)
    if (-not $locked) { exit 0 }

    # Another process could have completed an update while we were waiting.
    $state = Read-Json $StateFile
    if (-not (Test-CheckDue $state $config)) { exit 0 }

    $url = "https://api.github.com/repos/$($config.repository)/releases?per_page=20"
    try {
        $releases = Invoke-RestMethod `
            -Uri $url `
            -Method Get `
            -TimeoutSec ([int]$config.network_timeout_seconds) `
            -Headers @{
                "User-Agent" = "MerzoStreamSuite-Background/5.0"
                "Accept" = "application/vnd.github+json"
                "X-GitHub-Api-Version" = [string]$config.api_version
            }
        $release = $null
        foreach ($candidate in @($releases)) {
            if ([bool]$candidate.draft) { continue }
            if ([string]$config.channel -eq "stable" -and [bool]$candidate.prerelease) { continue }
            $candidateVersion = Normalize-Version ([string]$candidate.tag_name)
            if ($candidateVersion -notmatch '^\d+\.\d+\.\d+[a-z]*$') { continue }
            if ($null -eq $release -or (Compare-Version $candidateVersion (Normalize-Version ([string]$release.tag_name))) -gt 0) {
                $release = $candidate
            }
        }
        if ($null -eq $release) { throw "No matching published release" }
    } catch {
        $state.last_check_utc = (Get-Date).ToUniversalTime().ToString("o")
        Save-JsonAtomic $StateFile $state
        Write-Log ("GitHub unavailable: " + $_.Exception.Message)
        exit 0
    }

    $state.last_check_utc = (Get-Date).ToUniversalTime().ToString("o")
    $state.last_release_id = [string]$release.id
    Save-JsonAtomic $StateFile $state

    $remoteVersion = Normalize-Version ([string]$release.tag_name)
    if ((Compare-Version $remoteVersion ([string]$state.current_version)) -le 0) {
        exit 0
    }

    if (-not [bool]$config.auto_install) {
        Write-Log "Update $remoteVersion is available; auto_install is disabled."
        exit 0
    }

    $release | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $ReleaseCache -Encoding UTF8
    Write-Log "Preparing update in background: $($state.current_version) -> $remoteVersion"

    & powershell.exe `
        -NoLogo `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File (Join-Path $LauncherRoot "Updater5.ps1") `
        -InstallRoot $InstallRoot `
        -ReleaseJsonPath $ReleaseCache

    if ($LASTEXITCODE -eq 0) {
        Write-Log "Update $remoteVersion downloaded and staged. It will be health-checked on next launch."
    }
} catch {
    Write-Log ("Background fatal: " + $_.Exception.Message)
} finally {
    if ($locked) {
        try { $mutex.ReleaseMutex() } catch {}
    }
    $mutex.Dispose()
}
