$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$stablePwsh = 'C:\Program Files\PowerShell\7\pwsh.exe'

if (Test-Path $stablePwsh) {
  Write-Host "Stable PowerShell 7 already installed: $stablePwsh"
  exit 0
}

Write-Host 'Stable PowerShell 7 is not installed in Program Files.'
Write-Host 'Downloading official x64 MSI from the PowerShell GitHub release...'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$headers = @{ 'User-Agent' = 'MerzoOptimizerLocalTestCenter' }
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/PowerShell/PowerShell/releases/latest' -Headers $headers
$asset = $release.assets | Where-Object { $_.name -match '^PowerShell-.*-win-x64\.msi$' } | Select-Object -First 1
if (-not $asset) { throw 'Official PowerShell 7 x64 MSI was not found in the latest release.' }

$msi = Join-Path $env:TEMP $asset.name
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $msi -Headers $headers -UseBasicParsing
if (-not (Test-Path $msi)) { throw 'PowerShell 7 MSI download failed.' }

Write-Host 'Windows will ask for Administrator permission to install stable PowerShell 7.'
$proc = Start-Process msiexec.exe -ArgumentList @('/i',"`"$msi`"",'/qn','/norestart','ADD_PATH=1','ENABLE_PSREMOTING=0','REGISTER_MANIFEST=1') -Verb RunAs -Wait -PassThru
if ($proc.ExitCode -ne 0 -and $proc.ExitCode -ne 3010) { throw "PowerShell 7 MSI failed with exit code $($proc.ExitCode)." }

Start-Sleep -Seconds 2
if (-not (Test-Path $stablePwsh)) { throw "PowerShell 7 installation finished, but stable pwsh.exe was not found at $stablePwsh" }
Write-Host "Stable PowerShell 7 installed: $stablePwsh"
exit 0
