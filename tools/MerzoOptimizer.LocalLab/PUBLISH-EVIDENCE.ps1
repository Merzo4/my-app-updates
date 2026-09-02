param([switch]$FlushQueue)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$root=if($env:MWO_LAB_ROOT){$env:MWO_LAB_ROOT}else{'D:\MerzoOptimizer-LocalLab'}
$latest=Join-Path $root 'Results\Latest'
$log=Join-Path $root 'Logs\Current.log'
$queue=Join-Path $root 'State\EvidenceQueue'
$checkout=Join-Path $root 'EvidenceRepo'
$repoUrl='https://github.com/Merzo4/my-app-updates.git'
$branch='mwo-local-lab-evidence'
New-Item $queue -ItemType Directory -Force|Out-Null

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

$publishedQueue=[System.Collections.Generic.List[string]]::new()
$queuedEvents=@(Get-ChildItem $queue -Filter '*.json' -File -ErrorAction SilentlyContinue|Sort-Object Name)
foreach($eventFile in $queuedEvents){
  try{$ev=Get-Content $eventFile.FullName -Raw|ConvertFrom-Json}catch{continue}
  $eventId=[string]$ev.eventId
  if([string]::IsNullOrWhiteSpace($eventId)){continue}
  $machine=([string]$ev.machine -replace '[^A-Za-z0-9._-]','-')
  if([string]::IsNullOrWhiteSpace($machine)){$machine='unknown-machine'}
  $dest=Join-Path $checkout ("LOCAL_LAB_EVIDENCE\EVENTS\$machine\$eventId")
  New-Item $dest -ItemType Directory -Force|Out-Null
  Copy-Item $eventFile.FullName (Join-Path $dest 'EVENT.json') -Force
  $logName=[string]$ev.logFile
  if(-not[string]::IsNullOrWhiteSpace($logName)){
    $queuedLog=Join-Path $queue $logName
    if(Test-Path $queuedLog){Copy-Item $queuedLog (Join-Path $dest 'Current.log') -Force}
  }
  $latestEvent=Join-Path $checkout 'LOCAL_LAB_EVIDENCE\LATEST_EVENT'
  if(Test-Path $latestEvent){Remove-Item $latestEvent -Recurse -Force}
  New-Item $latestEvent -ItemType Directory -Force|Out-Null
  Copy-Item $eventFile.FullName (Join-Path $latestEvent 'EVENT.json') -Force
  if(-not[string]::IsNullOrWhiteSpace($logName)){
    $queuedLog=Join-Path $queue $logName
    if(Test-Path $queuedLog){Copy-Item $queuedLog (Join-Path $latestEvent 'Current.log') -Force}
  }
  $publishedQueue.Add($eventFile.FullName)
}

$resultPath=Join-Path $latest 'LAB-RESULT.json'
$reportPath=Join-Path $latest 'REPORT.txt'
if(Test-Path $resultPath){
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
  [ordered]@{
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
  }|ConvertTo-Json|Set-Content (Join-Path $dest 'EVIDENCE-META.json') -Encoding UTF8
}

& git -C $checkout config user.name 'Merzo Optimizer Local Test Center'
& git -C $checkout config user.email 'local-test-center@merzo.local'
& git -C $checkout add LOCAL_LAB_EVIDENCE
& git -C $checkout diff --cached --quiet
if($LASTEXITCODE-eq0){
  foreach($eventPath in $publishedQueue){
    $ev=Get-Content $eventPath -Raw|ConvertFrom-Json
    $logName=[string]$ev.logFile
    Remove-Item $eventPath -Force -ErrorAction SilentlyContinue
    if(-not[string]::IsNullOrWhiteSpace($logName)){Remove-Item (Join-Path $queue $logName) -Force -ErrorAction SilentlyContinue}
  }
  Write-Host 'EVIDENCE_ALREADY_CURRENT_OR_QUEUE_EMPTY'
  exit 0
}

$summary=if($queuedEvents.Count-gt0){"Local Lab evidence queue $($queuedEvents.Count) event(s)"}else{'Local Lab latest profile evidence'}
& git -C $checkout commit -m $summary
if($LASTEXITCODE-ne0){throw 'Evidence commit failed'}
& git -C $checkout push origin "HEAD:$branch"
if($LASTEXITCODE-ne0){throw 'Evidence push failed. Queue preserved. Проверь GitHub авторизацию Git Credential Manager/GitHub Desktop.'}

foreach($eventPath in $publishedQueue){
  try{
    $ev=Get-Content $eventPath -Raw|ConvertFrom-Json
    $logName=[string]$ev.logFile
    Remove-Item $eventPath -Force -ErrorAction SilentlyContinue
    if(-not[string]::IsNullOrWhiteSpace($logName)){Remove-Item (Join-Path $queue $logName) -Force -ErrorAction SilentlyContinue}
  }catch{}
}
Write-Host "EVIDENCE_PUBLISHED branch=$branch queued=$($publishedQueue.Count) actionsMinutes=0"
