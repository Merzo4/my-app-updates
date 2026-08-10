param(
    [Parameter(Mandatory = $true)]
    [string]$InstallRoot,

    [Parameter(Mandatory = $true)]
    [string]$ReleaseJsonPath,

    [switch]$ReinstallCurrent
)

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Add-Type -AssemblyName System.IO.Compression.FileSystem

$InstallRoot = [IO.Path]::GetFullPath($InstallRoot)
$VersionsRoot = Join-Path $InstallRoot "versions"

$AppDataRoot = Join-Path $env:LOCALAPPDATA "MerzoStreamSuite"
$StateRoot = Join-Path $AppDataRoot "update5"
$DownloadsRoot = Join-Path $StateRoot "downloads"
$StagingRoot = Join-Path $StateRoot "staging"
$StateFile = Join-Path $StateRoot "state.json"
$LogDir = Join-Path $AppDataRoot "logs"
$LogFile = Join-Path $LogDir "updater5.log"

New-Item -ItemType Directory -Force -Path `
    $VersionsRoot, $StateRoot, $DownloadsRoot, $StagingRoot, $LogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $line = "{0} [Updater5] {1}" -f (Get-Date).ToUniversalTime().ToString("o"), $Message
    Add-Content -LiteralPath $LogFile -Encoding UTF8 -Value $line
    Write-Host $Message
}

function Read-Json {
    param([string]$Path)
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Save-JsonAtomic {
    param([string]$Path, $Value)
    $temp = $Path + ".tmp"
    $Value | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $temp -Encoding UTF8
    Move-Item -LiteralPath $temp -Destination $Path -Force
}

function Get-Sha256 {
    param([string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Normalize-Version {
    param([string]$Tag)
    $version = $Tag.Trim()
    if ($version.StartsWith("v", [StringComparison]::OrdinalIgnoreCase)) {
        $version = $version.Substring(1)
    }
    if ($version -notmatch '^\d+\.\d+\.\d+[a-z]*$') {
        throw "Некорректный tag версии: $Tag"
    }
    return $version
}

function Get-ReleaseAsset {
    param($Release, [string]$Name)
    foreach ($asset in @($Release.assets)) {
        if ([string]$asset.name -eq $Name) { return $asset }
    }
    return $null
}

function Download-WithRetry {
    param(
        [string]$Url,
        [string]$Destination,
        [int64]$ExpectedSize = 0,
        [int]$TimeoutSeconds = 90
    )

    $lastError = $null
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            $part = $Destination + ".part"
            Remove-Item -LiteralPath $part -Force -ErrorAction SilentlyContinue

            Write-Log "Скачивание Release ZIP: попытка $attempt/3"
            Invoke-WebRequest `
                -Uri $Url `
                -OutFile $part `
                -UseBasicParsing `
                -TimeoutSec $TimeoutSeconds `
                -Headers @{
                    "User-Agent" = "MerzoStreamSuite-Updater/5.0.1"
                    "Accept" = "application/octet-stream"
                }

            $length = (Get-Item -LiteralPath $part).Length
            if ($length -lt 1024) { throw "GitHub вернул слишком маленький файл" }
            if ($ExpectedSize -gt 0 -and $length -ne $ExpectedSize) {
                throw "Размер ZIP не совпал с данными GitHub: $length вместо $ExpectedSize"
            }

            Move-Item -LiteralPath $part -Destination $Destination -Force
            return
        } catch {
            $lastError = $_.Exception
            Start-Sleep -Seconds ([Math]::Min(8, [Math]::Pow(2, $attempt - 1)))
        }
    }

    throw "Не удалось скачать пакет после 3 попыток: $($lastError.Message)"
}

function Safe-ExtractZip {
    param([string]$ZipPath, [string]$Destination)

    if (Test-Path -LiteralPath $Destination) {
        Remove-Item -LiteralPath $Destination -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null

    $destinationFull = [IO.Path]::GetFullPath($Destination).TrimEnd([IO.Path]::DirectorySeparatorChar)
    $destinationPrefix = $destinationFull + [IO.Path]::DirectorySeparatorChar
    $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)

    $maxTotalBytes = 512MB
    $maxSingleBytes = 128MB
    [int64]$totalBytes = 0

    $archive = [IO.Compression.ZipFile]::OpenRead($ZipPath)
    try {
        foreach ($entry in $archive.Entries) {
            $entryName = [string]$entry.FullName
            if ([string]::IsNullOrWhiteSpace($entryName)) { continue }

            # Refuse symbolic links and suspicious archive entries.
            $unixMode = (($entry.ExternalAttributes -shr 16) -band 0xF000)
            if ($unixMode -eq 0xA000) { throw "ZIP содержит symbolic link: $entryName" }

            $normalized = $entryName.Replace('/', [IO.Path]::DirectorySeparatorChar)
            if ([IO.Path]::IsPathRooted($normalized)) { throw "ZIP содержит абсолютный путь: $entryName" }

            $parts = $normalized.Split([IO.Path]::DirectorySeparatorChar)
            if ($parts -contains "..") { throw "ZIP пытается выйти из staging: $entryName" }

            $target = [IO.Path]::GetFullPath((Join-Path $Destination $normalized))
            if (-not $target.StartsWith($destinationPrefix, [StringComparison]::OrdinalIgnoreCase) -and
                $target -ne $destinationFull) {
                throw "ZIP entry выходит за пределы staging: $entryName"
            }

            if (-not $seen.Add($target)) { throw "ZIP содержит дубликат пути: $entryName" }

            if ($entry.FullName.EndsWith("/")) {
                New-Item -ItemType Directory -Force -Path $target | Out-Null
                continue
            }

            if ($entry.Length -gt $maxSingleBytes) { throw "Слишком большой файл внутри ZIP: $entryName" }
            $totalBytes += [int64]$entry.Length
            if ($totalBytes -gt $maxTotalBytes) { throw "ZIP превышает допустимый распакованный размер" }

            $parent = Split-Path -Parent $target
            if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }

            $input = $entry.Open()
            try {
                $output = [IO.File]::Open(
                    $target,
                    [IO.FileMode]::Create,
                    [IO.FileAccess]::Write,
                    [IO.FileShare]::None
                )
                try { $input.CopyTo($output) } finally { $output.Dispose() }
            } finally {
                $input.Dispose()
            }
        }
    } finally {
        $archive.Dispose()
    }
}

function Validate-VersionPackage {
    param([string]$Root, [string]$ExpectedVersion)

    $manifestPath = Join-Path $Root "release_manifest.json"
    if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
        throw "В Release ZIP отсутствует release_manifest.json"
    }

    $manifest = Read-Json $manifestPath
    if ([string]$manifest.version -ne $ExpectedVersion) {
        throw "Версия внутри ZIP не совпадает с GitHub Release"
    }

    $minimumEngine = [string]$manifest.engine_min
    if (-not [string]::IsNullOrWhiteSpace($minimumEngine) -and -not $minimumEngine.StartsWith("5.")) {
        throw "Пакету нужен несовместимый Update Engine: $minimumEngine"
    }

    $items = @($manifest.files)
    if ($null -ne $manifest.file_count -and [int]$manifest.file_count -ne $items.Count) {
        throw "file_count в release_manifest.json не совпадает"
    }

    $expectedPaths = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
    $rootFull = [IO.Path]::GetFullPath($Root).TrimEnd([IO.Path]::DirectorySeparatorChar)
    $rootPrefix = $rootFull + [IO.Path]::DirectorySeparatorChar

    $index = 0
    foreach ($item in $items) {
        $index++
        $relative = ([string]$item.path).Replace('\', '/')
        if ([string]::IsNullOrWhiteSpace($relative) -or [IO.Path]::IsPathRooted($relative)) {
            throw "Небезопасный путь manifest: $relative"
        }
        if ($relative.Split('/') -contains "..") { throw "Небезопасный путь manifest: $relative" }
        if (-not $expectedPaths.Add($relative)) { throw "Дубликат в manifest: $relative" }

        $filePath = [IO.Path]::GetFullPath((Join-Path $Root ($relative.Replace('/', [IO.Path]::DirectorySeparatorChar))))
        if (-not $filePath.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Manifest path выходит из staging: $relative"
        }
        if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) { throw "Не найден файл пакета: $relative" }

        $expectedSize = [int64]$item.size
        $actualSize = (Get-Item -LiteralPath $filePath).Length
        if ($expectedSize -ne $actualSize) { throw "Размер не совпал: $relative" }

        $expectedHash = ([string]$item.sha256).ToLowerInvariant()
        if ($expectedHash -notmatch '^[0-9a-f]{64}$') { throw "Некорректный SHA-256 в manifest: $relative" }
        if ((Get-Sha256 $filePath) -ne $expectedHash) { throw "SHA-256 не совпал: $relative" }
    }

    foreach ($file in @(Get-ChildItem -LiteralPath $Root -File -Recurse)) {
        $relative = $file.FullName.Substring($rootFull.Length).TrimStart([char[]]"\/").Replace('\', '/')
        if ($relative -eq "release_manifest.json") { continue }
        if (-not $expectedPaths.Contains($relative)) { throw "В пакете найден незаявленный файл: $relative" }
    }

    return $manifest
}

$release = Read-Json $ReleaseJsonPath
$version = Normalize-Version ([string]$release.tag_name)
$packageName = "MerzoStreamSuite-$version.zip"
$packageAsset = Get-ReleaseAsset $release $packageName
if ($null -eq $packageAsset) {
    throw "В GitHub Release $version отсутствует $packageName"
}

$expectedPackageHash = ""
if ([string]$packageAsset.digest -match '^sha256:([0-9a-fA-F]{64})$') {
    $expectedPackageHash = $Matches[1].ToLowerInvariant()
}

if ([string]::IsNullOrWhiteSpace($expectedPackageHash)) {
    $shaAssetName = "MerzoStreamSuite-$version.sha256"
    $shaAsset = Get-ReleaseAsset $release $shaAssetName
    if ($null -eq $shaAsset) {
        throw "GitHub не вернул digest, а в Release отсутствует $shaAssetName"
    }

    $shaTemp = Join-Path $DownloadsRoot ($shaAssetName + ".tmp")
    Invoke-WebRequest `
        -Uri ([string]$shaAsset.browser_download_url) `
        -OutFile $shaTemp `
        -UseBasicParsing `
        -TimeoutSec 15 `
        -Headers @{ "User-Agent" = "MerzoStreamSuite-Updater/5.0.1" }

    $shaText = (Get-Content -LiteralPath $shaTemp -Raw).Trim()
    Remove-Item -LiteralPath $shaTemp -Force -ErrorAction SilentlyContinue
    if ($shaText -notmatch '([0-9a-fA-F]{64})') { throw "Некорректный SHA-256 asset" }
    $expectedPackageHash = $Matches[1].ToLowerInvariant()
}

$zipPath = Join-Path $DownloadsRoot $packageName
$zipValid = $false
if (Test-Path -LiteralPath $zipPath -PathType Leaf) {
    try {
        $zipValid = ((Get-Sha256 $zipPath) -eq $expectedPackageHash)
    } catch { $zipValid = $false }
}

if (-not $zipValid) {
    Download-WithRetry `
        -Url ([string]$packageAsset.browser_download_url) `
        -Destination $zipPath `
        -ExpectedSize ([int64]$packageAsset.size) `
        -TimeoutSeconds 90
}

$actualPackageHash = Get-Sha256 $zipPath
if ($actualPackageHash -ne $expectedPackageHash) {
    Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue
    throw "SHA-256 Release ZIP не совпал"
}
Write-Log "Release ZIP подтверждён SHA-256: $($actualPackageHash.Substring(0, 12))..."

$stagingPath = Join-Path $StagingRoot ("{0}-{1}" -f $version, [guid]::NewGuid().ToString("N"))
try {
    Safe-ExtractZip $zipPath $stagingPath
    $manifest = Validate-VersionPackage $stagingPath $version
    Write-Log "Внутренний manifest подтверждён: файлов $(@($manifest.files).Count)"

    $state = $null
    if (Test-Path -LiteralPath $StateFile) {
        try { $state = Read-Json $StateFile } catch {}
    }
    if ($null -eq $state) { $state = [pscustomobject]@{} }

    $currentVersion = [string]$state.current_version
    $targetPath = Join-Path $VersionsRoot $version
    $rollbackPath = ""

    if (Test-Path -LiteralPath $targetPath) {
        if ($ReinstallCurrent) {
            $rollbackPath = Join-Path $VersionsRoot (".rollback-{0}-{1}" -f $version, [guid]::NewGuid().ToString("N"))
            Move-Item -LiteralPath $targetPath -Destination $rollbackPath
            Move-Item -LiteralPath $stagingPath -Destination $targetPath
            $stagingPath = ""
        } else {
            # Avoid rewriting an already valid version folder.
            [void](Validate-VersionPackage $targetPath $version)
            Remove-Item -LiteralPath $stagingPath -Recurse -Force
            $stagingPath = ""
        }
    } else {
        Move-Item -LiteralPath $stagingPath -Destination $targetPath
        $stagingPath = ""
    }

    $previousVersion = $currentVersion
    if ([string]::IsNullOrWhiteSpace($previousVersion)) {
        $previousVersion = [string]$state.last_good_version
    }

    $newState = [pscustomobject][ordered]@{
        schema = 5
        engine_version = "5.0.1"
        current_version = $version
        previous_version = $previousVersion
        last_good_version = [string]$state.last_good_version
        pending_version = $version
        pending_since_utc = (Get-Date).ToUniversalTime().ToString("o")
        pending_release_id = [string]$release.id
        pending_package_sha256 = $expectedPackageHash
        rollback_path = $rollbackPath
        failed_version = ""
        last_check_utc = [string]$state.last_check_utc
        last_release_id = [string]$release.id
    }

    Save-JsonAtomic $StateFile $newState
    Write-Log "Версия $version установлена отдельно и ожидает health-check первого запуска."
} finally {
    if (-not [string]::IsNullOrWhiteSpace($stagingPath) -and (Test-Path -LiteralPath $stagingPath)) {
        Remove-Item -LiteralPath $stagingPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}

exit 0
