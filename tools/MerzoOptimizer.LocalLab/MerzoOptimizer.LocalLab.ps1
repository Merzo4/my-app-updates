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
$PwshPath=(Get-Process -Id $PID).Path
if(!(Test-Path $Runner)-or!(Test-Path $ProfilePath)){throw "Local Test Center installation is incomplete: $AppDir"}
$Cfg=Get-Content $ProfilePath -Raw|ConvertFrom-Json

$createdNew=$false
$mutex=New-Object Threading.Mutex($true,'MerzoOptimizerLocalTestCenter',[ref]$createdNew)
if(!$createdNew){[System.Windows.Forms.MessageBox]::Show('Merzo Optimizer Test Center уже запущен.','Merzo Optimizer Test Center')|Out-Null;exit 0}

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
$form.StartPosition='CenterScreen'
$form.ClientSize=New-Object Drawing.Size(1080,650)
$form.MinimumSize=New-Object Drawing.Size(1000,690)
$form.BackColor=$bg
$form.ForeColor=$text
$form.Font=New-Object Drawing.Font('Segoe UI',9)

$header=New-Object Windows.Forms.Panel
$header.Location=New-Object Drawing.Point(0,0)
$header.Size=New-Object Drawing.Size(1080,62)
$header.Anchor='Top,Left,Right'
$header.BackColor=[Drawing.Color]::FromArgb(7,25,33)
$form.Controls.Add($header)

$title=New-Object Windows.Forms.Label
$title.Text='MERZO OPTIMIZER  •  LOCAL TEST CENTER'
$title.Font=New-Object Drawing.Font('Segoe UI Semibold',15)
$title.ForeColor=$text
$title.AutoSize=$true
$title.Location=New-Object Drawing.Point(18,10)
$header.Controls.Add($title)

$sub=New-Object Windows.Forms.Label
$sub.Text="Локальная проверка без GitHub Actions минут  •  Test Center $($Cfg.testCenterVersion)"
$sub.ForeColor=$muted
$sub.AutoSize=$true
$sub.Location=New-Object Drawing.Point(20,37)
$header.Controls.Add($sub)

$statusBadge=New-Object Windows.Forms.Label
$statusBadge.Text='ГОТОВ'
$statusBadge.TextAlign='MiddleCenter'
$statusBadge.Size=New-Object Drawing.Size(120,30)
$statusBadge.Location=New-Object Drawing.Point(940,15)
$statusBadge.Anchor='Top,Right'
$statusBadge.BackColor=$panel2
$statusBadge.ForeColor=$accent
$header.Controls.Add($statusBadge)

$nav=New-Object Windows.Forms.Panel
$nav.Location=New-Object Drawing.Point(0,62)
$nav.Size=New-Object Drawing.Size(205,588)
$nav.Anchor='Top,Bottom,Left'
$nav.BackColor=[Drawing.Color]::FromArgb(9,27,35)
$form.Controls.Add($nav)

$navTitle=New-Object Windows.Forms.Label
$navTitle.Text='ПРОФИЛИ'
$navTitle.AutoSize=$true
$navTitle.ForeColor=$muted
$navTitle.Location=New-Object Drawing.Point(14,14)
$nav.Controls.Add($navTitle)

function New-NavButton([string]$caption,[int]$y,[Drawing.Color]$color){
  $b=New-Object Windows.Forms.Button
  $b.Text=$caption
  $b.Size=New-Object Drawing.Size(178,36)
  $b.Location=New-Object Drawing.Point(12,$y)
  $b.FlatStyle='Flat'
  $b.FlatAppearance.BorderColor=$border
  $b.FlatAppearance.BorderSize=1
  $b.BackColor=$panel
  $b.ForeColor=$color
  $b.Cursor='Hand'
  $nav.Controls.Add($b)
  return $b
}
$btnDiag=New-NavButton 'Диагностика' 42 $text
$btnSync=New-NavButton 'Обновить Source' 82 $text
$btnQuick=New-NavButton 'QUICK' 132 $accent
$btnFull=New-NavButton 'FULL SAFE' 172 $green
$btnDestructive=New-NavButton 'GAME → RESTORE' 222 $red
$btnOpen=New-NavButton 'Открыть тестовую' 272 $text
$btnResults=New-NavButton 'Открыть результаты' 312 $text
$btnPack=New-NavButton 'Собрать evidence' 352 $text
$btnPublish=New-NavButton 'Отправить отчёт' 392 $accent
$btnFolder=New-NavButton 'Открыть D:\ Lab' 432 $text
$btnStop=New-NavButton 'Остановить' 482 $amber
$btnStop.Enabled=$false

$safety=New-Object Windows.Forms.Label
$safety.Location=New-Object Drawing.Point(12,530)
$safety.Size=New-Object Drawing.Size(178,48)
$safety.Anchor='Bottom,Left'
$safety.BackColor=$panel
$safety.ForeColor=$green
$safety.Padding=New-Object Windows.Forms.Padding(7)
$nav.Controls.Add($safety)

$main=New-Object Windows.Forms.Panel
$main.Location=New-Object Drawing.Point(205,62)
$main.Size=New-Object Drawing.Size(875,588)
$main.Anchor='Top,Bottom,Left,Right'
$main.BackColor=$bg
$form.Controls.Add($main)

function New-Card([string]$caption,[int]$x,[int]$w){
  $p=New-Object Windows.Forms.Panel
  $p.Location=New-Object Drawing.Point($x,12)
  $p.Size=New-Object Drawing.Size($w,80)
  $p.BackColor=$panel
  $main.Controls.Add($p)
  $h=New-Object Windows.Forms.Label
  $h.Text=$caption
  $h.ForeColor=$muted
  $h.AutoSize=$true
  $h.Location=New-Object Drawing.Point(10,8)
  $p.Controls.Add($h)
  $v=New-Object Windows.Forms.Label
  $v.Text='—'
  $v.ForeColor=$text
  $v.Font=New-Object Drawing.Font('Segoe UI Semibold',9.5)
  $v.Location=New-Object Drawing.Point(10,29)
  $v.Size=New-Object Drawing.Size($w-20,44)
  $p.Controls.Add($v)
  return $v
}
$cardEnv=New-Card 'СРЕДА' 14 185
$cardSource=New-Card 'SOURCE' 209 255
$cardSafety=New-Card 'БЕЗОПАСНОСТЬ' 474 185
$cardLast=New-Card 'ПОСЛЕДНИЙ РЕЗУЛЬТАТ' 669 192

$journalTitle=New-Object Windows.Forms.Label
$journalTitle.Text='ЖУРНАЛ'
$journalTitle.ForeColor=$muted
$journalTitle.AutoSize=$true
$journalTitle.Location=New-Object Drawing.Point(14,105)
$main.Controls.Add($journalTitle)

$journal=New-Object Windows.Forms.RichTextBox
$journal.ReadOnly=$true
$journal.BackColor=[Drawing.Color]::FromArgb(6,18,24)
$journal.ForeColor=$text
$journal.BorderStyle='None'
$journal.Font=New-Object Drawing.Font('Consolas',9)
$journal.Location=New-Object Drawing.Point(14,126)
$journal.Size=New-Object Drawing.Size(847,260)
$journal.Anchor='Top,Bottom,Left,Right'
$main.Controls.Add($journal)

$checksTitle=New-Object Windows.Forms.Label
$checksTitle.Text='ПРОВЕРКИ'
$checksTitle.ForeColor=$muted
$checksTitle.AutoSize=$true
$checksTitle.Anchor='Bottom,Left'
$checksTitle.Location=New-Object Drawing.Point(14,401)
$main.Controls.Add($checksTitle)

$list=New-Object Windows.Forms.ListView
$list.View='Details'
$list.FullRowSelect=$true
$list.BackColor=[Drawing.Color]::FromArgb(7,22,29)
$list.ForeColor=$text
$list.BorderStyle='None'
$list.Location=New-Object Drawing.Point(14,422)
$list.Size=New-Object Drawing.Size(847,150)
$list.Anchor='Bottom,Left,Right'
[void]$list.Columns.Add('Статус',85)
[void]$list.Columns.Add('Проверка',230)
[void]$list.Columns.Add('Результат',500)
$main.Controls.Add($list)

$script:CurrentProcess=$null
$script:LogLineCount=0
$script:Busy=$false

function Get-SourceIdentity {
  if(!(Test-Path (Join-Path $SourceDir '.git'))){return 'Source ещё не подготовлен'}
  try{
    $b=(& git -C $SourceDir branch --show-current 2>$null).Trim()
    $s=(& git -C $SourceDir rev-parse --short=10 HEAD 2>$null).Trim()
    return "$b`n$s"
  }catch{return 'Source: ошибка чтения'}
}
function Is-Armed {
  if(!(Test-Path $ArmPath)){return $false}
  try{$a=Get-Content $ArmPath -Raw|ConvertFrom-Json;return ($a.labOnly-eq$true-and[string]$a.machineName-eq$env:COMPUTERNAME)}catch{return $false}
}
function Refresh-Cards {
  $cardEnv.Text="Windows $([Environment]::OSVersion.Version)`n$env:COMPUTERNAME"
  $cardSource.Text=Get-SourceIdentity
  $armed=Is-Armed
  $cardSafety.Text=if($armed){"LAB ONLY`nSYSTEM MUTATION: ARMED"}else{"PROTECTED`nSystem mutation blocked"}
  $cardSafety.ForeColor=if($armed){$red}else{$green}
  $safety.Text=if($armed){"LAB ONLY • ARMED"}else{"PROTECTED • GAME BLOCKED"}
  $safety.ForeColor=if($armed){$red}else{$green}
  if(Test-Path $ResultPath){
    try{
      $r=Get-Content $ResultPath -Raw|ConvertFrom-Json
      $sha=[string]$r.sourceCommit
      $short=if($sha){$sha.Substring(0,[math]::Min(10,$sha.Length))}else{'no-source'}
      $cardLast.Text="$($r.conclusion) • $($r.profile)`n$short"
      $cardLast.ForeColor=if($r.conclusion-eq'PASS'){$green}else{$red}
    }catch{$cardLast.Text='result read error';$cardLast.ForeColor=$red}
  }else{$cardLast.Text='Нет запусков';$cardLast.ForeColor=$muted}
}
function Set-Busy([bool]$busy,[string]$caption=''){
  $script:Busy=$busy
  foreach($b in @($btnDiag,$btnSync,$btnQuick,$btnFull,$btnOpen,$btnResults,$btnPack,$btnPublish,$btnFolder)){$b.Enabled=-not$busy}
  $btnDestructive.Enabled=(-not$busy-and(Is-Armed))
  $btnStop.Enabled=$busy
  if($busy){$statusBadge.Text='RUNNING';$statusBadge.ForeColor=$amber}else{$statusBadge.Text=if($caption){$caption}else{'ГОТОВ'};$statusBadge.ForeColor=if($caption-eq'PASS'){$green}elseif($caption-eq'FAIL'){$red}else{$accent}}
}
function Load-Result {
  $list.Items.Clear()
  if(!(Test-Path $ResultPath)){Set-Busy $false 'FAIL';return}
  try{
    $r=Get-Content $ResultPath -Raw|ConvertFrom-Json
    foreach($st in @($r.stages)){
      $it=New-Object Windows.Forms.ListViewItem([string]$st.state)
      [void]$it.SubItems.Add([string]$st.name)
      [void]$it.SubItems.Add([string]$st.summary)
      $it.ForeColor=if($st.state-eq'PASS'){$green}elseif($st.state-eq'FAIL'){$red}elseif($st.state-eq'WARN'){$amber}else{$text}
      [void]$list.Items.Add($it)
    }
    Refresh-Cards
    Set-Busy $false ([string]$r.conclusion)
  }catch{Set-Busy $false 'FAIL'}
}
function Start-Profile([string]$name,[bool]$elevated=$false){
  if($script:Busy){return}
  $script:LogLineCount=0
  $journal.Clear()
  $list.Items.Clear()
  Set-Busy $true
  $psi=New-Object Diagnostics.ProcessStartInfo
  $psi.FileName=$PwshPath
  $psi.Arguments="-NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File `"$Runner`" -Profile $name"
  $psi.WorkingDirectory=$AppDir
  if($elevated){$psi.UseShellExecute=$true;$psi.Verb='runas'}else{$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true}
  try{$script:CurrentProcess=[Diagnostics.Process]::Start($psi)}catch{Set-Busy $false 'FAIL';[Windows.Forms.MessageBox]::Show($_.Exception.Message,'Не удалось запустить профиль')|Out-Null}
}
function Run-Utility([string]$scriptPath,[string]$titleText){
  if($script:Busy){return}
  if(!(Test-Path $scriptPath)){[Windows.Forms.MessageBox]::Show("Файл не найден:`n$scriptPath",$titleText)|Out-Null;return}
  try{
    $p=Start-Process $PwshPath -ArgumentList @('-NoLogo','-NoProfile','-ExecutionPolicy','Bypass','-File',$scriptPath) -PassThru
    $p.WaitForExit()
    if($p.ExitCode-ne0){[Windows.Forms.MessageBox]::Show("$titleText завершился с кодом $($p.ExitCode).",$titleText)|Out-Null}
  }catch{[Windows.Forms.MessageBox]::Show($_.Exception.Message,$titleText)|Out-Null}
  Refresh-Cards
}

$timer=New-Object Windows.Forms.Timer
$timer.Interval=500
$timer.Add_Tick({
  try{
    if(Test-Path $LogPath){
      $lines=@(Get-Content $LogPath -ErrorAction SilentlyContinue)
      if($lines.Count-gt$script:LogLineCount){
        for($i=$script:LogLineCount;$i-lt$lines.Count;$i++){$journal.AppendText($lines[$i]+[Environment]::NewLine)}
        $script:LogLineCount=$lines.Count
        $journal.SelectionStart=$journal.TextLength
        $journal.ScrollToCaret()
      }
    }
    if($script:Busy-and$script:CurrentProcess){$script:CurrentProcess.Refresh();if($script:CurrentProcess.HasExited){$script:CurrentProcess=$null;Load-Result}}
  }catch{}
})
$timer.Start()

$btnDiag.Add_Click({Start-Profile 'Diagnostics'})
$btnSync.Add_Click({Start-Profile 'Sync'})
$btnQuick.Add_Click({Start-Profile 'Quick'})
$btnFull.Add_Click({Start-Profile 'FullSafe'})
$btnDestructive.Add_Click({if(Is-Armed){$answer=[Windows.Forms.MessageBox]::Show('Этот профиль реально применит GAME-настройки и затем RestoreAll. Только для лабораторной Windows. Продолжить?','DESTRUCTIVE LAB',[Windows.Forms.MessageBoxButtons]::YesNo,[Windows.Forms.MessageBoxIcon]::Warning);if($answer-eq[Windows.Forms.DialogResult]::Yes){Start-Profile 'Destructive' $true}}})
$btnOpen.Add_Click({if(Test-Path $CurrentExe){Start-Process $CurrentExe -WorkingDirectory (Split-Path $CurrentExe -Parent)}else{[Windows.Forms.MessageBox]::Show('Нет TestBuild\Current. Сначала запусти FULL SAFE.','Test Center')|Out-Null}})
$btnResults.Add_Click({$p=Join-Path $LabRoot 'Results\Latest';New-Item $p -ItemType Directory -Force|Out-Null;Start-Process explorer.exe $p})
$btnPack.Add_Click({Run-Utility $PackScript 'Evidence ZIP'})
$btnPublish.Add_Click({Run-Utility $PublishScript 'Отправка отчёта'})
$btnFolder.Add_Click({Start-Process explorer.exe $LabRoot})
$btnStop.Add_Click({if($script:CurrentProcess){try{& taskkill.exe /PID $script:CurrentProcess.Id /T /F|Out-Null}catch{};$script:CurrentProcess=$null;Set-Busy $false 'STOPPED'}})
$form.Add_Resize({$main.Width=[math]::Max(760,$form.ClientSize.Width-205);$main.Height=[math]::Max(520,$form.ClientSize.Height-62);$header.Width=$form.ClientSize.Width;$nav.Height=[math]::Max(520,$form.ClientSize.Height-62);$journal.Height=[math]::Max(190,$main.ClientSize.Height-328);$checksTitle.Top=$main.ClientSize.Height-187;$list.Top=$main.ClientSize.Height-166;$list.Height=150})
$form.Add_FormClosing({param($sender,$e);if($script:Busy){$answer=[Windows.Forms.MessageBox]::Show('Проверка ещё выполняется. Закрыть Test Center и остановить её?','Test Center',[Windows.Forms.MessageBoxButtons]::YesNo,[Windows.Forms.MessageBoxIcon]::Warning);if($answer-ne[Windows.Forms.DialogResult]::Yes){$e.Cancel=$true;return};if($script:CurrentProcess){try{& taskkill.exe /PID $script:CurrentProcess.Id /T /F|Out-Null}catch{}}};$timer.Stop();try{$mutex.ReleaseMutex()}catch{};$mutex.Dispose()})

Refresh-Cards
Set-Busy $false 'ГОТОВ'
[void]$form.ShowDialog()
