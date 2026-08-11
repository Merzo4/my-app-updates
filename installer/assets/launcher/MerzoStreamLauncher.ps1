param([switch]$NoUpdate, [string]$ActivateVersion = "")
$ErrorActionPreference = "Stop"
$InstallRoot = [IO.Path]::GetFullPath((Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)))
$Engine = Join-Path $InstallRoot "launcher\launcher6.py"
$RuntimePython = Join-Path $env:LOCALAPPDATA "MerzoStreamSuite\runtime\py312\Scripts\python.exe"

function Show-Error([string]$Text) {
    try {
        Add-Type -AssemblyName PresentationFramework -ErrorAction SilentlyContinue
        [System.Windows.MessageBox]::Show($Text, "MerzoStream Suite") | Out-Null
    } catch { Write-Host $Text -ForegroundColor Red }
}

try {
    if (-not (Test-Path -LiteralPath $Engine)) { throw "Не найден Launcher Engine 6: $Engine" }
    if (Test-Path -LiteralPath $RuntimePython) {
        $argsList = @($Engine, "--install-root", $InstallRoot)
        if (-not [string]::IsNullOrWhiteSpace($ActivateVersion)) { $argsList += @("--activate-version", $ActivateVersion) }
        & $RuntimePython @argsList
        exit $LASTEXITCODE
    }
    try {
        $argsList = @("-3.12", $Engine, "--install-root", $InstallRoot)
        if (-not [string]::IsNullOrWhiteSpace($ActivateVersion)) { $argsList += @("--activate-version", $ActivateVersion) }
        & py.exe @argsList
        exit $LASTEXITCODE
    } catch {}
    try {
        $argsList = @($Engine, "--install-root", $InstallRoot)
        if (-not [string]::IsNullOrWhiteSpace($ActivateVersion)) { $argsList += @("--activate-version", $ActivateVersion) }
        & python.exe @argsList
        exit $LASTEXITCODE
    } catch {}
    throw "Не найден Python 3.12 runtime MerzoStream Suite. Запусти MerzoStreamSetup.exe для восстановления."
} catch {
    Show-Error $_.Exception.Message
    exit 1
}
