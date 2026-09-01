$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$root=if($env:MWO_LAB_ROOT){$env:MWO_LAB_ROOT}else{'D:\MerzoOptimizer-LocalLab'}
$latest=Join-Path $root 'Results\Latest'
$log=Join-Path $root 'Logs\Current.log'
$checkout=Join-Path $root 'EvidenceRepo'
$repoUrl='https://github.com/Merzo4/my-app-updates.git'
$branch='mwo-local-lab-evidence'

$resultPath=Join-Path $latest 'LAB-RESULT.json'
$reportPath=Join-Path $latest 'REPORT.txt'
if(!(Test-Path $resultPath)){throw 'LAB-RESULT.json отсутствует. Сначала запусти профиль проверки.'}
if(!(Get-Command git -ErrorAction SilentlyContinue)){throw 'Git не найден.'}

if(!(Test-Path (Join-Path $checkout '.git'))){
  if(Test-Path $checkout){Remove-Item $checkout -Recurse -Force}
  & git clone --branch $branch --single-branch $repoUrl $checkout
  if($LASTEXITCODE-ne0){throw "Не удалось клонировать evidence branch: $LASTEXITCODE"}
}
$origin=(& git -C $checkout remote get-url origin).Trim()
if($origin.TrimEnd('/').Replace('.git','')-ne$repoUrl.TrimEnd('/').Replace('.git','')){throw "Неверный evidence origin: $origin"}
& git -C $checkout fetch origin $branch --prune
if($LASTEXITCODE-ne0){throw 'Evidence fetch failed'}
& git -C $checkout checkout -B $branch "origin/$branch"
if($LASTEXITCODE-ne0){throw 'Evidence checkout failed'}
& git -C $checkout reset --hard "origin/$branch"
if($LASTEXITCODE-ne0){throw 'Evidence reset failed'}
& git -C $checkout clean -fdx
if($LASTEXITCODE-ne0){throw 'Evidence clean failed'}

$dest=Join-Path $checkout 'LOCAL_LAB_EVIDENCE\LATEST'
if(Test-Path $dest){Remove-Item $dest -Recurse -Force}
New-Item $dest -ItemType Directory -Force|Out-Null
Copy-Item $resultPath (Join-Path $dest 'LAB-RESULT.json') -Force
if(Test-Path $reportPath){Copy-Item $reportPath (Join-Path $dest 'REPORT.txt') -Force}
if(Test-Path $log){
  $lines=@(Get-Content $log -ErrorAction SilentlyContinue)
  if($lines.Count-gt5000){$lines=$lines[($lines.Count-5000)..($lines.Count-1)]}
  $lines|Set-Content (Join-Path $dest 'Current.log') -Encoding UTF8
}
$r=Get-Content $resultPath -Raw|ConvertFrom-Json
$meta=[ordered]@{
  publishedAt=(Get-Date).ToUniversalTime().ToString('o')
  testCenterVersion=[string]$r.testCenterVersion
  productVersion=[string]$r.productVersion
  profile=[string]$r.profile
  conclusion=[string]$r.conclusion
  sourceBranch=[string]$r.sourceBranch
  sourceCommit=[string]$r.sourceCommit
  machine=[string]$r.machine
  actionsMinutesUsed=0
  evidenceBranch=$branch
}
$meta|ConvertTo-Json|Set-Content (Join-Path $dest 'EVIDENCE-META.json') -Encoding UTF8

& git -C $checkout config user.name 'Merzo Optimizer Local Test Center'
& git -C $checkout config user.email 'local-test-center@merzo.local'
& git -C $checkout add LOCAL_LAB_EVIDENCE/LATEST
& git -C $checkout diff --cached --quiet
if($LASTEXITCODE-eq0){Write-Host 'EVIDENCE_ALREADY_CURRENT';exit 0}
$msg="Local Lab $($r.profile) $($r.conclusion) $([string]$r.sourceCommit)"
& git -C $checkout commit -m $msg
if($LASTEXITCODE-ne0){throw 'Evidence commit failed'}
& git -C $checkout push origin "HEAD:$branch"
if($LASTEXITCODE-ne0){throw 'Evidence push failed. Проверь GitHub авторизацию Git Credential Manager/GitHub Desktop.'}
Write-Host "EVIDENCE_PUBLISHED branch=$branch source=$($r.sourceCommit) result=$($r.conclusion) actionsMinutes=0"
