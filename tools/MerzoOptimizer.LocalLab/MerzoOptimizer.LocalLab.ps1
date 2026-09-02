param([switch]$SmokeTest)

$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$LabRoot=if($env:MWO_LAB_ROOT){$env:MWO_LAB_ROOT}else{'D:\MerzoOptimizer-LocalLab'}
$AppDir=Join-Path $LabRoot 'App'
$Runner=Join-Path $AppDir 'Run-Profile.ps1'
$ProfilePath=Join-Path $AppDir 'local-lab-profile.json'
$LogPath=Join-Path $LabRoot 'Logs\Current.log'
$ResultPath=Join-Path $LabRoot 'Results\Latest\LAB-RESULT.json'
$SourceDir=Join-Path $LabRoot 'Source'
$CurrentExe=Join-Path $LabRoot 'TestBuild\Current\App\MerzoWindowsOptimizer.exe'
$ArmPath=Join-Path $LabRoot 'State\ALLOW-SYSTEM-MUTATION.json'
$PackScript=Join-Path $AppDir 'PACK-EVIDENCE.ps1'
$PublishScript=Join-Path $AppDir 'PUBLISH-EVIDENCE.ps1'
$AutoReport=Join-Path $AppDir 'AUTO-REPORT.ps1'
$PwshPath=(Get-Process -Id $PID).Path
if(!(Test-Path $Runner)-or!(Test-Path $ProfilePath)){throw "Local Test Center installation is incomplete: $AppDir"}
$Cfg=Get-Content $ProfilePath -Raw|ConvertFrom-Json

$createdNew=$false
$mutex=[Threading.Mutex]::new($true,'MerzoOptimizerLocalTestCenter',[ref]$createdNew)
if(!$createdNew){
  if($SmokeTest){throw 'Another Local Test Center instance is already running.'}
  [System.Windows.Forms.MessageBox]::Show('Merzo Optimizer Test Center уже запущен.','Merzo Optimizer Test Center')|Out-Null
  exit 0
}

$bg=[Drawing.Color]::FromArgb(8,20,28)
$panel=[Drawing.Color]::FromArgb(13,34,43)
$panel2=[Drawing.Color]::FromArgb(18,44,54)
$border=[Drawing.Color]::FromArgb(35,91,99)
$accent=[Drawing.Color]::FromArgb(70,188,177)
$text=[Drawing.Color]::FromArgb(230,240,242)
$muted=[Drawing.Color]::FromArgb(137,163,169)
$green=[Drawing.Color]::FromArgb(76,196,147)
$amber=[Drawing.Color]::FromArgb(227,174,73)
$red=[Drawing.Color]::FromArgb(225,88,88)

$form=New-Object Windows.Forms.Form
$form.Text='Merzo Optimizer Local Test Center'
$form.StartPosition=[Windows.Forms.FormStartPosition]::CenterScreen
$form.ClientSize=[Drawing.Size]::new(1040,640)
$form.FormBorderStyle=[Windows.Forms.FormBorderStyle]::FixedSingle
$form.MaximizeBox=$false
$form.BackColor=$bg
$form.ForeColor=$text
$form.Font=[Drawing.Font]::new('Segoe UI',9)

$header=New-Object Windows.Forms.Panel
$header.Location=[Drawing.Point]::new(0,0)
$header.Size=[Drawing.Size]::new(1040,60)
$header.BackColor=[Drawing.Color]::FromArgb(7,25,33)
$form.Controls.Add($header)

$title=New-Object Windows.Forms.Label
$title.Text='MERZO OPTIMIZER  •  LOCAL TEST CENTER'
$title.Font=[Drawing.Font]::new('Segoe UI Semibold',15)
$title.ForeColor=$text
$title.AutoSize=$true
$title.Location=[Drawing.Point]::new(18,9)
$header.Controls.Add($title)

$sub=New-Object Windows.Forms.Label
$sub.Text="Локальная проверка без GitHub Actions минут  •  Test Center $($Cfg.testCenterVersion)"
$sub.ForeColor=$muted
$sub.AutoSize=$true
$sub.Location=[Drawing.Point]::new(20,36)
$header.Controls.Add($sub)

$statusBadge=New-Object Windows.Forms.Label
$statusBadge.Text='ГОТОВ'
$statusBadge.TextAlign=[Drawing.ContentAlignment]::MiddleCenter
$statusBadge.Size=[Drawing.Size]::new(120,30)
$statusBadge.Location=[Drawing.Point]::new(900,15)
$statusBadge.BackColor=$panel2
$statusBadge.ForeColor=$accent
$header.Controls.Add($statusBadge)

$nav=New-Object Windows.Forms.Panel
$nav.Location=[Drawing.Point]::new(0,60)
$nav.Size=[Drawing.Size]::new(205,580)
$nav.BackColor=[Drawing.Color]::FromArgb(9,27,35)
$form.Controls.Add($nav)

$navTitle=New-Object Windows.Forms.Label
$navTitle.Text='ПРОФИЛИ'
$navTitle.AutoSize=$true
$navTitle.ForeColor=$muted
$navTitle.Location=[Drawing.Point]::new(14,14)
$nav.Controls.Add($navTitle)

function New-NavButton([string]$caption,[int]$y,[Drawing.Color]$color){
  $b=New-Object Windows.Forms.Button
  $b.Text=$caption
  $b.Size=[Drawing.Size]::new(178,35)
  $b.Location=[Drawing.Point]::new(12,$y)
  $b.FlatStyle=[Windows.Forms.FlatStyle]::Flat
  $b.FlatAppearance.BorderColor=$border
  $b.FlatAppearance.BorderSize=1
  $b.BackColor=$panel
  $b.ForeColor=$color
  $b.Cursor=[Windows.Forms.Cursors]::Hand
  $nav.Controls.Add($b)
  return $b
}

$btnDiag=New-NavButton 'Диагностика' 40 $text
$btnSync=New-NavButton 'Обновить Source' 79 $text
$btnQuick=New-NavButton 'QUICK' 128 $accent
$btnFull=New-NavButton 'FULL SAFE' 167 $green
$btnDestructive=New-NavButton 'GAME → RESTORE' 216 $red
$btnOpen=New-NavButton 'Открыть тестовую' 265 $text
$btnResults=New-NavButton 'Открыть результаты' 304 $text
$btnPack=New-NavButton 'Собрать evidence' 343 $text
$btnPublish=New-NavButton 'Отправить отчёт' 382 $accent
$btnFolder=New-NavButton 'Открыть D:\ Lab' 421 $text
$btnStop=New-NavButton 'Остановить' 470 $amber
$btnStop.Enabled=$false

$safety=New-Object Windows.Forms.Label
$safety.Location=[Drawing.Point]::new(12,522)
$safety.Size=[Drawing.Size]::new(178,44)
$safety.BackColor=$panel
$safety.ForeColor=$green
$safety.Padding=[Windows.Forms.Padding]::new(7)
$nav.Controls.Add($safety)

$main=New-Object Windows.Forms.Panel
$main.Location=[Drawing.Point]::new(205,60)
$main.Size=[Drawing.Size]::new(835,580)
$main.BackColor=$bg
$form.Controls.Add($main)

function New-Card([string]$caption,[int]$x,[int]$width){
  $p=New-Object Windows.Forms.Panel
  $p.Location=[Drawing.Point]::new($x,12)
  $p.Size=[Drawing.Size]::new($width,78)
  $p.BackColor=$panel
  $main.Controls.Add($p)

  $h=New-Object Windows.Forms.Label
  $h.Text=$caption
  $h.ForeColor=$muted
  $h.AutoSize=$true
  $h.Location=[Drawing.Point]::new(10,8)
  $p.Controls.Add($h)

  $v=New-Object Windows.Forms.Label
  $v.Text='—'
  $v.ForeColor=$text
  $v.Font=[Drawing.Font]::new('Segoe UI Semibold',9.5)
  $v.Location=[Drawing.Point]::new(10,29)
  $labelWidth=[int]$width - 20
  $v.Size=[Drawing.Size]::new($labelWidth,42)
  $p.Controls.Add($v)
  return $v
}

$cardEnv=New-Card 'СРЕДА' 14 175
$cardSource=New-Card 'SOURCE' 199 235
$cardSafety=New-Card 'БЕЗОПАСНОСТЬ' 444 175
$cardLast=New-Card 'ПОСЛЕДНИЙ РЕЗУЛЬТАТ' 629 192

$journalTitle=New-Object Windows.Forms.Label
$journalTitle.Text='ЖУРНАЛ'
$journalTitle.ForeColor=$muted
$journalTitle.AutoSize=$true
$journalTitle.Location=[Drawing.Point]::new(14,102)
$main.Controls.Add($journalTitle)

$journal=New-Object Windows.Forms.RichTextBox
$journal.ReadOnly=$true
$journal.BackColor=[Drawing.Color]::FromArgb(6,18,24)
$journal.ForeColor=$text
$journal.BorderStyle=[Windows.Forms.BorderStyle]::None
$journal.Font=[Drawing.Font]::new('Consolas',9)
$journal.Location=[Drawing.Point]::new(14,123)
$journal.Size=[Drawing.Size]::new(807,245)
$main.Controls.Add($journal)

$checksTitle=New-Object Windows.Forms.Label
$checksTitle.Text='ПРОВЕРКИ'
$checksTitle.ForeColor=$muted
$checksTitle.AutoSize=$true
$checksTitle.Location=[Drawing.Point]::new(14,382)
$main.Controls.Add($checksTitle)

$list=New-Object Windows.Forms.ListView
$list.View=[Windows.Forms.View]::Details
$list.FullRowSelect=$true
$list.BackColor=[Drawing.Color]::FromArgb(7,22,29)
$list.ForeColor=$text
$list.BorderStyle=[Windows.Forms.BorderStyle]::None
$list.Location=[Drawing.Point]::new(14,403)
$list.Size=[Drawing.Size]::new(807,160)
[void]$list.Columns.Add('Статус',85)
[void]$list.Columns.Add('Проверка',225)
[void]$list.Columns.Add('Результат',470)
$main.Controls.Add($list)

$script:CurrentProcess=$null
$script:LogLineCount=0
$script:Busy=$false

function Start-HiddenPwsh([string[]]$args,[bool]$wait=$false){
  $psi=[Diagnostics.ProcessStartInfo]::new()
  $psi.FileName=$PwshPath
  $psi.UseShellExecute=$false
  $psi.CreateNoWindow=$true
  foreach($arg in $args){[void]$psi.ArgumentList.Add($arg)}
  $p=[Diagnostics.Process]::Start($psi)
  if($wait){$p.WaitForExit();return $p.ExitCode}
  return $p
}

function Report-GuiFailure([string]$eventName,[string]$message,[string]$logFile=$LogPath){
  try{
    if(!(Test-Path $AutoReport)){return}
    [void](Start-HiddenPwsh @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$AutoReport,'-Event',$eventName,'-Outcome','FAIL','-Message',$message,'-LogPath',$logFile) $false)
  }catch{}
}

function Get-SourceIdentity {
  if(!(Test-Path (Join-Path $SourceDir '.git'))){return 'Source ещё не подготовлен'}
  try{
    $branch=(& git -C $SourceDir branch --show-current 2>$null).Trim()
    $sha=(& git -C $SourceDir rev-parse --short=10 HEAD 2>$null).Trim()
    return "$branch`n$sha"
  }catch{return 'Source: ошибка чтения'}
}

function Is-Armed {
  if(!(Test-Path $ArmPath)){return $false}
  try{
    $a=Get-Content $ArmPath -Raw|ConvertFrom-Json
    return ([bool]$a.labOnly -and ([string]$a.machineName -eq [string]$env:COMPUTERNAME))
  }catch{return $false}
}

function Refresh-Cards {
  $cardEnv.Text="Windows $([Environment]::OSVersion.Version)`n$env:COMPUTERNAME"
  $cardSource.Text=Get-SourceIdentity
  $armed=Is-Armed
  $cardSafety.Text=if($armed){"LAB ONLY`nSYSTEM MUTATION: ARMED"}else{"PROTECTED`nSystem mutation blocked"}
  $cardSafety.ForeColor=if($armed){$red}else{$green}
  $safety.Text=if($armed){'LAB ONLY • ARMED'}else{'PROTECTED • GAME BLOCKED'}
  $safety.ForeColor=if($armed){$red}else{$green}
  $btnDestructive.Enabled=($armed -and -not $script:Busy)

  if(Test-Path $ResultPath){
    try{
      $r=Get-Content $ResultPath -Raw|ConvertFrom-Json
      $sha=[string]$r.sourceCommit
      $short='no-source'
      if(-not [string]::IsNullOrWhiteSpace($sha)){
        $take=[Math]::Min(10,$sha.Length)
        $short=$sha.Substring(0,$take)
      }
      $cardLast.Text="$($r.conclusion) • $($r.profile)`n$short"
      $cardLast.ForeColor=if($r.conclusion-eq'PASS'){$green}else{$red}
    }catch{
      $cardLast.Text='result read error'
      $cardLast.ForeColor=$red
      Report-GuiFailure 'gui.result-read' $_.Exception.Message
    }
  }else{
    $cardLast.Text='Нет запусков'
    $cardLast.ForeColor=$muted
  }
}

function Set-Busy([bool]$busy,[string]$caption=''){
  $script:Busy=$busy
  foreach($b in @($btnDiag,$btnSync,$btnQuick,$btnFull,$btnOpen,$btnResults,$btnPack,$btnPublish,$btnFolder)){
    $b.Enabled=-not $busy
  }
  $btnDestructive.Enabled=(-not $busy -and (Is-Armed))
  $btnStop.Enabled=$busy
  if($busy){
    $statusBadge.Text='RUNNING'
    $statusBadge.ForeColor=$amber
  }else{
    $statusBadge.Text=if([string]::IsNullOrWhiteSpace($caption)){'ГОТОВ'}else{$caption}
    $statusBadge.ForeColor=if($caption-eq'PASS'){$green}elseif($caption-eq'FAIL'){$red}else{$accent}
  }
}

function Load-Result {
  $list.Items.Clear()
  if(!(Test-Path $ResultPath)){Set-Busy $false 'FAIL';return}
  try{
    $r=Get-Content $ResultPath -Raw|ConvertFrom-Json
    foreach($st in @($r.stages)){
      $item=[Windows.Forms.ListViewItem]::new([string]$st.state)
      [void]$item.SubItems.Add([string]$st.name)
      [void]$item.SubItems.Add([string]$st.summary)
      $item.ForeColor=if($st.state-eq'PASS'){$green}elseif($st.state-eq'FAIL'){$red}elseif($st.state-eq'WARN'){$amber}else{$text}
      [void]$list.Items.Add($item)
    }
    Refresh-Cards
    Set-Busy $false ([string]$r.conclusion)
  }catch{
    Set-Busy $false 'FAIL'
    Report-GuiFailure 'gui.load-result' $_.Exception.Message
  }
}

function Start-Profile([string]$name,[bool]$elevated=$false){
  if($script:Busy){return}
  $script:LogLineCount=0
  $journal.Clear()
  $list.Items.Clear()
  Set-Busy $true

  $psi=[Diagnostics.ProcessStartInfo]::new()
  $psi.FileName=$PwshPath
  $psi.WorkingDirectory=$AppDir
  if($elevated){
    $psi.UseShellExecute=$true
    $psi.Verb='runas'
    $psi.WindowStyle=[Diagnostics.ProcessWindowStyle]::Hidden
    $psi.Arguments="-NoLogo -NoProfile -STA -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Runner`" -Profile $name"
  }else{
    $psi.UseShellExecute=$false
    $psi.CreateNoWindow=$true
    foreach($arg in @('-NoLogo','-NoProfile','-STA','-ExecutionPolicy','Bypass','-File',$Runner,'-Profile',$name)){[void]$psi.ArgumentList.Add($arg)}
  }
  try{
    $script:CurrentProcess=[Diagnostics.Process]::Start($psi)
  }catch{
    $message=$_.Exception.Message
    Set-Busy $false 'FAIL'
    Report-GuiFailure ("gui.start-profile."+$name) $message
    [Windows.Forms.MessageBox]::Show($message,'Не удалось запустить профиль')|Out-Null
  }
}

function Run-Utility([string]$scriptPath,[string]$titleText,[string]$eventName){
  if($script:Busy){return}
  if(!(Test-Path $scriptPath)){
    $message="Файл не найден: $scriptPath"
    Report-GuiFailure $eventName $message
    [Windows.Forms.MessageBox]::Show($message,$titleText)|Out-Null
    return
  }
  try{
    $code=[int](Start-HiddenPwsh @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$scriptPath) $true)
    if($code-ne0){
      $message="$titleText завершился с кодом $code."
      Report-GuiFailure $eventName $message
      [Windows.Forms.MessageBox]::Show($message,$titleText)|Out-Null
    }
  }catch{
    $message=$_.Exception.Message
    Report-GuiFailure $eventName $message
    [Windows.Forms.MessageBox]::Show($message,$titleText)|Out-Null
  }
  Refresh-Cards
}

$timer=[Windows.Forms.Timer]::new()
$timer.Interval=500
$timer.Add_Tick({
  try{
    if(Test-Path $LogPath){
      $lines=@(Get-Content $LogPath -ErrorAction SilentlyContinue)
      if($lines.Count-gt$script:LogLineCount){
        for($i=$script:LogLineCount;$i-lt$lines.Count;$i++){
          $journal.AppendText(([string]$lines[$i])+[Environment]::NewLine)
        }
        $script:LogLineCount=$lines.Count
        $journal.SelectionStart=$journal.TextLength
        $journal.ScrollToCaret()
      }
    }
    if($script:Busy -and $null-ne$script:CurrentProcess){
      $script:CurrentProcess.Refresh()
      if($script:CurrentProcess.HasExited){
        $script:CurrentProcess=$null
        Load-Result
      }
    }
  }catch{}
})

$btnDiag.Add_Click({Start-Profile 'Diagnostics'})
$btnSync.Add_Click({Start-Profile 'Sync'})
$btnQuick.Add_Click({Start-Profile 'Quick'})
$btnFull.Add_Click({Start-Profile 'FullSafe'})
$btnDestructive.Add_Click({
  if(Is-Armed){
    $answer=[Windows.Forms.MessageBox]::Show(
      'Этот профиль реально применит GAME-настройки и затем RestoreAll. Только для лабораторной Windows. Продолжить?',
      'DESTRUCTIVE LAB',
      [Windows.Forms.MessageBoxButtons]::YesNo,
      [Windows.Forms.MessageBoxIcon]::Warning
    )
    if($answer-eq[Windows.Forms.DialogResult]::Yes){Start-Profile 'Destructive' $true}
  }
})
$btnOpen.Add_Click({
  if(Test-Path $CurrentExe){
    try{Start-Process $CurrentExe -WorkingDirectory (Split-Path $CurrentExe -Parent)}catch{Report-GuiFailure 'gui.open-test-build' $_.Exception.Message;[Windows.Forms.MessageBox]::Show($_.Exception.Message,'Test Center')|Out-Null}
  }else{
    [Windows.Forms.MessageBox]::Show('Нет TestBuild\Current. Сначала запусти FULL SAFE.','Test Center')|Out-Null
  }
})
$btnResults.Add_Click({
  try{
    $p=Join-Path $LabRoot 'Results\Latest'
    New-Item $p -ItemType Directory -Force|Out-Null
    Start-Process explorer.exe $p
  }catch{Report-GuiFailure 'gui.open-results' $_.Exception.Message;[Windows.Forms.MessageBox]::Show($_.Exception.Message,'Test Center')|Out-Null}
})
$btnPack.Add_Click({Run-Utility $PackScript 'Evidence ZIP' 'utility.pack-evidence'})
$btnPublish.Add_Click({Run-Utility $PublishScript 'Отправка отчёта' 'utility.publish-evidence'})
$btnFolder.Add_Click({try{Start-Process explorer.exe $LabRoot}catch{Report-GuiFailure 'gui.open-lab-folder' $_.Exception.Message;[Windows.Forms.MessageBox]::Show($_.Exception.Message,'Test Center')|Out-Null}})
$btnStop.Add_Click({
  if($null-ne$script:CurrentProcess){
    try{& taskkill.exe /PID $script:CurrentProcess.Id /T /F|Out-Null}catch{}
    $script:CurrentProcess=$null
    Set-Busy $false 'STOPPED'
  }
})

$form.Add_FormClosing({
  param($sender,$e)
  if($script:Busy){
    $answer=[Windows.Forms.MessageBox]::Show(
      'Проверка ещё выполняется. Закрыть Test Center и остановить её?',
      'Test Center',
      [Windows.Forms.MessageBoxButtons]::YesNo,
      [Windows.Forms.MessageBoxIcon]::Warning
    )
    if($answer-ne[Windows.Forms.DialogResult]::Yes){$e.Cancel=$true;return}
    if($null-ne$script:CurrentProcess){try{& taskkill.exe /PID $script:CurrentProcess.Id /T /F|Out-Null}catch{}}
  }
  $timer.Stop()
  try{$mutex.ReleaseMutex()}catch{}
  $mutex.Dispose()
})

Refresh-Cards

if($SmokeTest){
  Write-Host 'LOCAL_TEST_CENTER_GUI_SMOKE_TEST_PASS'
  $form.Dispose()
  try{$mutex.ReleaseMutex()}catch{}
  $mutex.Dispose()
  exit 0
}

$timer.Start()
[void]$form.ShowDialog()
