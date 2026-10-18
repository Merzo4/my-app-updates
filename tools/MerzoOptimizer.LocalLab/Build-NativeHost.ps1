param([string]$LabRoot='D:\MerzoOptimizer-LocalLab')
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$project=Join-Path $PSScriptRoot 'NativeHost\MerzoOptimizer.TestCenter.csproj'
$publish=Join-Path $LabRoot 'Temp\NativeHostPublish'
$destination=Join-Path $LabRoot 'App\Native'
$log=Join-Path $LabRoot 'Logs\native-build.log'
if(!(Test-Path $project)){throw "Native C# project not found: $project"}
if(!(Get-Command dotnet -ErrorAction SilentlyContinue)){throw 'Native Test Center requires the .NET 10 SDK'}
if(-not (& dotnet --list-sdks | Where-Object {$_ -match '^10\.'})){throw 'Native Test Center requires the .NET 10 SDK'}
New-Item (Split-Path $log -Parent) -ItemType Directory -Force|Out-Null
New-Item $publish -ItemType Directory -Force|Out-Null
$arguments=@('publish',$project,'-c','Release','-r','win-x64','--self-contained','true','-p:PublishSingleFile=true','-p:PublishTrimmed=false','-p:PublishReadyToRun=false','-o',$publish)
& dotnet @arguments 2>&1|Tee-Object -FilePath $log
if($LASTEXITCODE-ne0){throw "Native EXE build failed. See $log"}
$exe=Join-Path $publish 'MerzoOptimizer.TestCenter.exe'
if(!(Test-Path $exe)){throw 'Native EXE missing after build'}
$smokeLog=Join-Path $LabRoot 'Logs\native-smoke.log'
$p=Start-Process -FilePath $exe -ArgumentList @('--smoke-test') -WorkingDirectory $publish -PassThru
try{
  if(-not$p.WaitForExit(30000)){
    try{$p.Kill($true)}catch{}
    throw "Native EXE smoke timeout. Old launcher remains valid. See $smokeLog"
  }
  "ExitCode=$($p.ExitCode)"|Set-Content $smokeLog -Encoding UTF8
  if($p.ExitCode-ne0){throw "Native EXE smoke FAIL $($p.ExitCode). See $smokeLog"}
}finally{$p.Dispose()}
New-Item $destination -ItemType Directory -Force|Out-Null
Copy-Item -LiteralPath $exe -Destination (Join-Path $destination 'MerzoOptimizer.TestCenter.exe') -Force
$installed=Join-Path $destination 'MerzoOptimizer.TestCenter.exe'
$sha=(Get-FileHash -LiteralPath $installed -Algorithm SHA256).Hash
Write-Host "NATIVE_EXE_SMOKE_PASS SHA256=$sha" -ForegroundColor Green
