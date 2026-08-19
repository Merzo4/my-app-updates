param(
  [Parameter(Mandatory=$true)][string]$Dll,
  [Parameter(Mandatory=$true)][string]$SettingsPath,
  [Parameter(Mandatory=$true)][string]$UpdateDirectory,
  [string]$ExpectedVersion='0.1.54'
)
$ErrorActionPreference='Stop'
$dir=Split-Path $Dll -Parent
Push-Location $dir
try {
  if(!(Test-Path $SettingsPath)){throw "Settings missing: $SettingsPath"}
  Remove-Item $UpdateDirectory -Recurse -Force -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force $UpdateDirectory | Out-Null

  $asm=[Reflection.Assembly]::LoadFrom($Dll)
  $type=$asm.GetTypes() | Where-Object {$_.FullName -match 'GitHubUpdateService$'} | Select-Object -First 1
  if(!$type){throw 'GitHubUpdateService missing'}
  $ctor=$type.GetConstructors() | Where-Object {$_.GetParameters().Count -eq 3} | Select-Object -First 1
  if(!$ctor){throw 'R53 updater constructor missing'}
  $names=($ctor.GetParameters() | ForEach-Object {$_.Name}) -join ','
  if($names-ne'settingsPath,updateDirectory,handler'){throw "Unexpected R53 updater constructor: $names"}

  $handler=[System.Net.Http.HttpClientHandler]::new()
  $svc=$ctor.Invoke(@($SettingsPath,$UpdateDirectory,$handler))
  try {
    $checkMethod=$type.GetMethod('CheckAsync',[type[]]@([System.Threading.CancellationToken]))
    if(!$checkMethod){throw 'R53 CheckAsync missing'}
    $checkTask=$checkMethod.Invoke($svc,@([System.Threading.CancellationToken]::None))
    $checkTask.GetAwaiter().GetResult() | Out-Null
    $check=$checkTask.Result
    $checkJson=$check | ConvertTo-Json -Depth 12 -Compress
    Write-Host ('R53_CHECK='+$checkJson)
    if(!$check.Success -or !$check.Configured){throw "R53 CheckAsync failed: $($check.Message)"}
    if(([string]$check.LatestVersion)-ne$ExpectedVersion){throw "R53 LatestVersion mismatch: $($check.LatestVersion)"}
    if(([string]$check.AssetUrl)-notmatch('/releases/download/mwo-v0\.1\.54/MerzoWindowsOptimizerSetup-win-x64\.exe$')){throw "R53 selected wrong R54 asset URL: $($check.AssetUrl)"}
    if(([string]$check.ChecksumUrl)-notmatch('/releases/download/mwo-v0\.1\.54/MerzoWindowsOptimizerSetup-win-x64\.exe\.sha256$')){throw "R53 selected wrong R54 checksum URL: $($check.ChecksumUrl)"}

    # The probe host is pwsh, so old R53 reports CurrentVersion=PowerShell's
    # assembly version and UpdateAvailable may be false. DownloadAsync itself is
    # the security-critical proof here: it reconstructs the expected tag from
    # LatestVersion and validates official URL, digest and checksum before save.
    $downloadMethod=$type.GetMethods() | Where-Object {
      $_.Name-eq'DownloadAsync' -and $_.GetParameters().Count-eq2 -and $_.GetParameters()[1].ParameterType-eq[System.Threading.CancellationToken]
    } | Select-Object -First 1
    if(!$downloadMethod){throw 'R53 DownloadAsync(check,cancellationToken) missing'}
    $downloadTask=$downloadMethod.Invoke($svc,@($check,[System.Threading.CancellationToken]::None))
    $downloadTask.GetAwaiter().GetResult() | Out-Null
    $download=$downloadTask.Result
    $downloadJson=$download | ConvertTo-Json -Depth 12 -Compress
    Write-Host ('R53_DOWNLOAD='+$downloadJson)
    $successProp=$download.GetType().GetProperty('Success')
    if($successProp -and -not [bool]$successProp.GetValue($download)){throw 'R53 DownloadAsync returned Success=false'}

    $installer=Get-ChildItem $UpdateDirectory -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
    if(!$installer){throw 'R53 DownloadAsync did not create official installer'}
    $hash=(Get-FileHash $installer.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Host "R53_REAL_DOWNLOAD_PASS path=$($installer.FullName) sha=$hash latest=$ExpectedVersion"
  }
  finally {
    if($svc -is [IDisposable]){$svc.Dispose()}
    $handler.Dispose()
  }
}
finally {Pop-Location}
