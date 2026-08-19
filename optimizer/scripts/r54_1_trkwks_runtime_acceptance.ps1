param(
    [Parameter(Mandatory=$true)][string]$ArtifactDir
)
$ErrorActionPreference='Stop'
$statusPath='.\optimizer\R54_1_TRKWKS_RUNTIME_STATUS.json'
$status=[ordered]@{
    conclusion='failure'
    createdAt=(Get-Date).ToUniversalTime().ToString('o')
    databaseId=[long]($env:GITHUB_RUN_ID ?? '0')
    buildRun=32232868999
    artifact='MerzoWindowsOptimizer-0.1.54.1-SERVICE-CONTROL-HOTFIX'
    fileVersion='pending'
    sha='pending'
    trkWksPresent=$false
    originalStart=-1
    targetStart=-1
    applyViaProductScm='pending'
    restoreViaProductScm='pending'
    launch='pending'
    error=''
}
function Save-Status {
    $status.createdAt=(Get-Date).ToUniversalTime().ToString('o')
    $status | ConvertTo-Json -Compress | Set-Content $statusPath -Encoding UTF8
}
function Get-ServiceStart([string]$Name) {
    $p="HKLM:\SYSTEM\CurrentControlSet\Services\$Name"
    if(!(Test-Path $p)){return $null}
    return [int](Get-ItemPropertyValue -Path $p -Name Start -ErrorAction Stop)
}
function Restore-WithScFallback([string]$Name,[int]$Start) {
    $mode=switch($Start){2{'auto'}3{'demand'}4{'disabled'}default{$null}}
    if($mode){
        & sc.exe config $Name start= $mode | Out-Host
        if($LASTEXITCODE-ne0){throw "Fallback SCM restore failed for $Name start=$Start"}
    }
}
try {
    $artifact=(Resolve-Path $ArtifactDir).Path
    $setup=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe' | Select-Object -First 1
    $setupSha=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizerSetup-win-x64.exe.sha256' | Select-Object -First 1
    $zip=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip' | Select-Object -First 1
    $zipSha=Get-ChildItem $artifact -Recurse -File -Filter 'MerzoWindowsOptimizer-portable-win-x64.zip.sha256' | Select-Object -First 1
    if(!$setup -or !$setupSha -or !$zip -or !$zipSha){throw 'R54.1 verified artifact payload incomplete'}

    $setupHash=(Get-FileHash $setup.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $setupExpected=((Get-Content $setupSha.FullName -Raw) -split '\s+')[0].Trim().ToLowerInvariant()
    $zipHash=(Get-FileHash $zip.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $zipExpected=((Get-Content $zipSha.FullName -Raw) -split '\s+')[0].Trim().ToLowerInvariant()
    if($setupHash-ne$setupExpected){throw "R54.1 installer SHA mismatch: $setupHash != $setupExpected"}
    if($zipHash-ne$zipExpected){throw "R54.1 portable SHA mismatch: $zipHash != $zipExpected"}
    $status.sha='success'
    Write-Host "R54_1_ARTIFACT_SHA_PASS setup=$setupHash zip=$zipHash"

    $extract=Join-Path $env:RUNNER_TEMP 'mwo-r54-1-runtime'
    Remove-Item $extract -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive $zip.FullName -DestinationPath $extract -Force
    $exe=Get-ChildItem $extract -Recurse -File -Filter 'MerzoWindowsOptimizer.exe' | Select-Object -First 1
    $dll=Get-ChildItem $extract -Recurse -File -Filter 'MerzoOptimizer.Windows.dll' | Select-Object -First 1
    if(!$exe -or !$dll){throw 'R54.1 portable EXE/Windows DLL missing'}
    $fv=[Diagnostics.FileVersionInfo]::GetVersionInfo($exe.FullName).FileVersion
    if($fv-ne'0.1.54.1'){throw "R54.1 portable FileVersion mismatch: $fv"}
    $status.fileVersion=$fv
    Write-Host "R54_1_FILE_VERSION_PASS $fv"

    $service=Get-Service -Name TrkWks -ErrorAction SilentlyContinue
    if(!$service){throw 'TrkWks is not present on Windows acceptance runner'}
    $status.trkWksPresent=$true
    $original=Get-ServiceStart 'TrkWks'
    if($null-eq$original){throw 'TrkWks Start value cannot be read'}
    if($original-notin@(2,3,4)){throw "TrkWks unsupported acceptance baseline Start=$original"}
    $target=if($original-eq4){3}else{4}
    $status.originalStart=$original
    $status.targetStart=$target
    Write-Host "R54_1_TRKWKS_BASELINE status=$($service.Status) start=$original target=$target"

    $dir=$dll.DirectoryName
    Push-Location $dir
    try {
        $asm=[Reflection.Assembly]::LoadFrom($dll.FullName)
        $type=$asm.GetType('MerzoOptimizer.Windows.Services.WindowsServiceStartTypeManager',$true,$false)
        $flags=[Reflection.BindingFlags]'NonPublic,Static'
        $method=$type.GetMethod('SetStartType',$flags)
        if(!$method){throw 'R54.1 product SCM SetStartType method missing'}

        $changed=$false
        try {
            $null=$method.Invoke($null,@('TrkWks',$target))
            $changed=$true
            $after=Get-ServiceStart 'TrkWks'
            if($after-ne$target){throw "R54.1 product SCM apply verification failed: $after != $target"}
            $status.applyViaProductScm='success'
            Write-Host "R54_1_TRKWKS_PRODUCT_SCM_APPLY_PASS start=$after"

            $null=$method.Invoke($null,@('TrkWks',$original))
            $restored=Get-ServiceStart 'TrkWks'
            if($restored-ne$original){throw "R54.1 product SCM restore verification failed: $restored != $original"}
            $changed=$false
            $status.restoreViaProductScm='success'
            Write-Host "R54_1_TRKWKS_PRODUCT_SCM_RESTORE_PASS start=$restored"
        }
        finally {
            if($changed -or (Get-ServiceStart 'TrkWks')-ne$original){
                try { $null=$method.Invoke($null,@('TrkWks',$original)) } catch {}
                if((Get-ServiceStart 'TrkWks')-ne$original){Restore-WithScFallback 'TrkWks' $original}
            }
        }
    }
    finally {Pop-Location}

    if((Get-ServiceStart 'TrkWks')-ne$original){throw 'TrkWks was not restored to its exact original Start value'}

    $app=Start-Process $exe.FullName -PassThru
    Start-Sleep -Seconds 5
    $app.Refresh()
    if($app.HasExited){throw "R54.1 portable app exited during launch acceptance: $($app.ExitCode)"}
    Stop-Process -Id $app.Id -Force -ErrorAction SilentlyContinue
    $status.launch='success'
    Write-Host "R54_1_PORTABLE_LAUNCH_PASS pid=$($app.Id)"

    $status.conclusion='success'
    Save-Status
    Write-Host 'R54_1_TRKWKS_RUNTIME_ACCEPTANCE_PASS'
}
catch {
    $status.error=$_.Exception.Message
    try { Save-Status } catch {}
    Write-Host "::error::$($_.Exception.Message)"
    exit 1
}
