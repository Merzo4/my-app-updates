$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Find-Pwsh {
  $cmd = Get-Command pwsh.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  foreach ($p in @(
    'C:\Program Files\PowerShell\7\pwsh.exe',
    'C:\Program Files\PowerShell\7-preview\pwsh.exe'
  )) {
    if (Test-Path $p) { return $p }
  }
  return $null
}

$existing = Find-Pwsh
if ($existing) {
  Write-Host "PowerShell 7 already available: $existing"
  exit 0
}

Write-Host 'PowerShell 7 is not installed. Downloading official x64 MSI from GitHub...'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$headers = @{ 'User-Agent' = 'MerzoOptimizerLocalTestCenter' }
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/PowerShell/PowerShell/releases/latest' -Headers $headers
$asset = $release.assets | Where-Object { $_.name -match '^PowerShell-.*-win-x64\.msi$' } | Select-Object -First 1
if (-not $asset) { throw 'Official PowerShell 7 x64 MSI was not found in the latest release.' }

$msi = Join-Path $env:TEMP $asset.name
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $msi -Headers $headers -UseBasicParsing
if (-not (Test-Path $msi)) { throw 'PowerShell 7 MSI download failed.' }

Write-Host 'Windows will ask for Administrator permission to install PowerShell 7.'
$proc = Start-Process msiexec.exe -ArgumentList @('/i',"`"$msi`"",'/qn','/norestart','ADD_PATH=1','ENABLE_PSREMOTING=0','REGISTER_MANIFEST=1') -Verb RunAs -Wait -PassThru
if ($proc.ExitCode -ne 0 -and $proc.ExitCode -ne 3010) { throw "PowerShell 7 MSI failed with exit code $($proc.ExitCode)." }

Start-Sleep -Seconds 2
$installed = Find-Pwsh
if (-not $installed) { throw 'PowerShell 7 installation finished, but pwsh.exe was not found.' }
Write-Host "PowerShell 7 installed: $installed"
exit 0
