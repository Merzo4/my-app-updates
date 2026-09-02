param(
  [Parameter(Mandatory=$true)][string]$Event,
  [ValidateSet('PASS','FAIL','WARN','INFO')][string]$Outcome='INFO',
  [string]$Message='',
  [string]$LogPath='',
  [string]$Profile='',
  [string]$SourceBranch='',
  [string]$SourceCommit=''
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest

$root=if($env:MWO_LAB_ROOT){$env:MWO_LAB_ROOT}else{'D:\MerzoOptimizer-LocalLab'}
$app=Join-Path $root 'App'
$queue=Join-Path $root 'State\EvidenceQueue'
$publisher=Join-Path $app 'PUBLISH-EVIDENCE.ps1'
New-Item $queue -ItemType Directory -Force|Out-Null

function Safe-Name([string]$value){
  $x=($value -replace '[^A-Za-z0-9._-]','-').Trim('-')
  if([string]::IsNullOrWhiteSpace($x)){return 'event'}
  if($x.Length-gt80){return $x.Substring(0,80)}
  return $x
}

if([string]::IsNullOrWhiteSpace($SourceBranch)-or[string]::IsNullOrWhiteSpace($SourceCommit)){
  $source=Join-Path $root 'Source'
  if(Test-Path (Join-Path $source '.git')){
    if([string]::IsNullOrWhiteSpace($SourceBranch)){try{$SourceBranch=(& git -C $source branch --show-current 2>$null).Trim()}catch{}}
    if([string]::IsNullOrWhiteSpace($SourceCommit)){try{$SourceCommit=(& git -C $source rev-parse HEAD 2>$null).Trim()}catch{}}
  }
}

$now=(Get-Date).ToUniversalTime()
$id='{0}-{1}-{2}' -f $now.ToString('yyyyMMddTHHmmssfffZ'),(Safe-Name $Event),([guid]::NewGuid().ToString('N').Substring(0,8))
$eventPath=Join-Path $queue ($id+'.json')
$logCopy=$null
if(-not[string]::IsNullOrWhiteSpace($LogPath)-and(Test-Path $LogPath)){
  $logCopy=Join-Path $queue ($id+'.log')
  try{
    $lines=@(Get-Content $LogPath -ErrorAction SilentlyContinue)
    if($lines.Count-gt5000){$lines=$lines[($lines.Count-5000)..($lines.Count-1)]}
    $lines|Set-Content $logCopy -Encoding UTF8
  }catch{$logCopy=$null}
}

[ordered]@{
  schemaVersion=1
  eventId=$id
  event=$Event
  outcome=$Outcome
  message=$Message
  profile=$Profile
  occurredAt=$now.ToString('o')
  machine=$env:COMPUTERNAME
  user=$env:USERNAME
  testCenterVersion=try{[string](Get-Content (Join-Path $app 'local-lab-profile.json') -Raw|ConvertFrom-Json).testCenterVersion}catch{''}
  productVersion=try{[string](Get-Content (Join-Path $app 'local-lab-profile.json') -Raw|ConvertFrom-Json).productVersion}catch{''}
  sourceBranch=$SourceBranch
  sourceCommit=$SourceCommit
  logFile=if($logCopy){[IO.Path]::GetFileName($logCopy)}else{$null}
  actionsMinutesUsed=0
}|ConvertTo-Json -Depth 6|Set-Content $eventPath -Encoding UTF8

Write-Host "AUTO_REPORT_QUEUED event=$Event outcome=$Outcome id=$id"

if(Test-Path $publisher){
  try{
    & pwsh -NoLogo -NoProfile -ExecutionPolicy Bypass -File $publisher -FlushQueue 2>&1|ForEach-Object{Write-Host $_}
    if($LASTEXITCODE-ne0){Write-Warning "AUTO_REPORT_UPLOAD_DEFERRED exit=$LASTEXITCODE queue=$eventPath"}
  }catch{Write-Warning "AUTO_REPORT_UPLOAD_DEFERRED $($_.Exception.Message) queue=$eventPath"}
}
exit 0
