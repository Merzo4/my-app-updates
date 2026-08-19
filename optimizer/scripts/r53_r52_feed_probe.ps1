param(
    [Parameter(Mandatory=$true)][string]$Dll,
    [Parameter(Mandatory=$true)][string]$SettingsPath,
    [Parameter(Mandatory=$true)][string]$UpdateDirectory,
    [string]$ExpectedVersion = '0.1.53'
)
$ErrorActionPreference='Stop'
$dir=Split-Path $Dll -Parent
Push-Location $dir
try {
    if(!(Test-Path $SettingsPath)){throw "R52 settings path missing: $SettingsPath"}
    New-Item -ItemType Directory -Force $UpdateDirectory | Out-Null

    $asm=[Reflection.Assembly]::LoadFrom($Dll)
    $type=$asm.GetTypes() | Where-Object {$_.FullName -match 'GitHubUpdateService$'} | Select-Object -First 1
    if(!$type){throw 'GitHubUpdateService type missing'}
    $ctor=$type.GetConstructors() | Where-Object {$_.GetParameters().Count -eq 3} | Select-Object -First 1
    if(!$ctor){throw 'Three-parameter GitHubUpdateService constructor missing'}
    $params=$ctor.GetParameters()
    $paramNames=($params | ForEach-Object {$_.Name}) -join ','
    if($paramNames -ne 'settingsPath,updateDirectory,handler'){
        throw "Unexpected R52 updater constructor parameters: $paramNames"
    }
    Write-Output ('TYPE=' + $type.FullName)
    Write-Output ('CTOR_PARAMS=' + (($params | ForEach-Object {"$($_.Position):$($_.Name):$($_.ParameterType.FullName)"}) -join ' | '))

    $handler=[System.Net.Http.HttpClientHandler]::new()
    $svc=$ctor.Invoke(@($SettingsPath,$UpdateDirectory,$handler))
    try {
        $settings=$type.GetProperty('Settings').GetValue($svc)
        $settingsJson=$settings | ConvertTo-Json -Depth 8 -Compress
        Write-Output ('SETTINGS=' + $settingsJson)
        if($settings.RepositoryOwner -ne 'Merzo4' -or $settings.RepositoryName -ne 'my-app-updates'){
            throw "Loaded updater settings are not official Merzo4/my-app-updates: $settingsJson"
        }
        if($settings.ReleaseTagPrefix -ne 'mwo-v'){
            throw "Loaded updater tag prefix mismatch: $($settings.ReleaseTagPrefix)"
        }

        $method=$type.GetMethod('CheckAsync',[type[]]@([System.Threading.CancellationToken]))
        if(!$method){throw 'CheckAsync(CancellationToken) missing'}
        $task=$method.Invoke($svc,@([System.Threading.CancellationToken]::None))
        $task.GetAwaiter().GetResult() | Out-Null
        $result=$task.Result
        $json=$result | ConvertTo-Json -Depth 10 -Compress
        Write-Output ('CHECK=' + $json)
        $latest=[string]$result.LatestVersion
        if(!$result.Success -or !$result.Configured){
            throw "R52 live updater check failed/configured=false: $($result.Message)"
        }
        if($latest -notmatch [regex]::Escape($ExpectedVersion)){
            throw "R52 live updater latest version is not $ExpectedVersion: $latest"
        }
        Write-Output ("R52_LIVE_FEED_PASS LATEST=$latest UPDATE_AVAILABLE=$($result.UpdateAvailable)")
    }
    finally {
        if($svc -is [IDisposable]){$svc.Dispose()}
        $handler.Dispose()
    }
}
finally { Pop-Location }
