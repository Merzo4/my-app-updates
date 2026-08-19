param(
    [Parameter(Mandatory=$true)][string]$Dll,
    [string]$ExpectedVersion = '0.1.53'
)
$ErrorActionPreference='Stop'
$dir=Split-Path $Dll -Parent
Push-Location $dir
try {
    $asm=[Reflection.Assembly]::LoadFrom($Dll)
    $type=$asm.GetTypes() | Where-Object {$_.FullName -match 'GitHubUpdateService$'} | Select-Object -First 1
    if(!$type){throw 'GitHubUpdateService type missing'}
    $ctor=$type.GetConstructors() | Where-Object {$_.GetParameters().Count -eq 3} | Select-Object -First 1
    if(!$ctor){throw 'Three-parameter GitHubUpdateService constructor missing'}
    $params=$ctor.GetParameters()
    Write-Output ('TYPE=' + $type.FullName)
    Write-Output ('CTOR_PARAMS=' + (($params | ForEach-Object {"$($_.Position):$($_.Name):$($_.ParameterType.FullName)"}) -join ' | '))
    Write-Output ('METHODS=' + (($type.GetMethods([Reflection.BindingFlags]'Public,Instance,Static,DeclaredOnly') | ForEach-Object {$_.ToString()}) -join ' | '))

    $method=$type.GetMethod('CheckAsync',[type[]]@([System.Threading.CancellationToken]))
    if(!$method){throw 'CheckAsync(CancellationToken) missing'}

    # Do not assume the semantics/order of the two historical string parameters.
    # Try only allow-listed values that appear in the installed production config.
    $pairs=@(
        @('Merzo4','my-app-updates'),
        @('my-app-updates','Merzo4'),
        @('Merzo4/my-app-updates','mwo-v'),
        @('mwo-v','Merzo4/my-app-updates'),
        @('Merzo4','mwo-v'),
        @('mwo-v','Merzo4'),
        @('my-app-updates','mwo-v'),
        @('mwo-v','my-app-updates'),
        @('Merzo4/my-app-updates','MerzoWindowsOptimizerSetup-win-x64.exe'),
        @('MerzoWindowsOptimizerSetup-win-x64.exe','Merzo4/my-app-updates')
    )

    $attempt=0
    foreach($pair in $pairs){
        $attempt++
        $handler=[System.Net.Http.HttpClientHandler]::new()
        $svc=$null
        try {
            $svc=$ctor.Invoke(@($pair[0],$pair[1],$handler))
            $settings=$type.GetProperty('Settings').GetValue($svc)
            $settingsJson=$settings | ConvertTo-Json -Depth 8 -Compress
            Write-Output ("CANDIDATE#$attempt ARGS=$($pair[0])|$($pair[1]) SETTINGS=$settingsJson")
            $task=$method.Invoke($svc,@([System.Threading.CancellationToken]::None))
            $task.GetAwaiter().GetResult() | Out-Null
            $result=$task.Result
            $json=$result | ConvertTo-Json -Depth 10 -Compress
            Write-Output ("CANDIDATE#$attempt CHECK=$json")
            $latest=[string]$result.LatestVersion
            if($result.Success -and $result.Configured -and $latest -match [regex]::Escape($ExpectedVersion)){
                Write-Output ("R52_LIVE_FEED_PASS ARGS=$($pair[0])|$($pair[1]) LATEST=$latest")
                exit 0
            }
        }
        catch {
            Write-Output ("CANDIDATE#$attempt ERROR=$($_.Exception.Message)")
        }
        finally {
            if($svc -is [IDisposable]){$svc.Dispose()}
            $handler.Dispose()
        }
    }
    throw "No safe constructor candidate produced configured live feed version $ExpectedVersion"
}
finally { Pop-Location }
