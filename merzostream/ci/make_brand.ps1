$ErrorActionPreference='Stop'
if(-not $env:MERZO_SRC){throw 'MERZO_SRC missing'}
Add-Type -AssemblyName System.Drawing
$content=Join-Path $env:MERZO_SRC 'content'
$web=Join-Path $env:MERZO_SRC 'ui\web'
New-Item -ItemType Directory -Force -Path $content,$web | Out-Null
$png=Join-Path $content 'MerzoStreamSuite.png'
$ico=Join-Path $content 'MerzoStreamSuite.ico'
$bmp=[System.Drawing.Bitmap]::new(256,256)
$g=[System.Drawing.Graphics]::FromImage($bmp)
try {
  $g.SmoothingMode=[System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
  $g.Clear([System.Drawing.Color]::FromArgb(4,9,17))
  $brush=[System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(35,226,208))
  $font=[System.Drawing.Font]::new('Segoe UI',138,[System.Drawing.FontStyle]::Bold,[System.Drawing.GraphicsUnit]::Pixel)
  $fmt=[System.Drawing.StringFormat]::new()
  $fmt.Alignment=[System.Drawing.StringAlignment]::Center
  $fmt.LineAlignment=[System.Drawing.StringAlignment]::Center
  $rect=[System.Drawing.RectangleF]::new(0,0,256,246)
  $g.DrawString('M',$font,$brush,$rect,$fmt)
  $bmp.Save($png,[System.Drawing.Imaging.ImageFormat]::Png)
  $h=$bmp.GetHicon()
  $icon=[System.Drawing.Icon]::FromHandle($h)
  $fs=[System.IO.File]::Create($ico)
  try { $icon.Save($fs) } finally { $fs.Dispose(); $icon.Dispose() }
  $fmt.Dispose(); $font.Dispose(); $brush.Dispose()
} finally { $g.Dispose(); $bmp.Dispose() }
Copy-Item $png (Join-Path $web 'MerzoStreamSuite.png') -Force
if((Get-Item $png).Length -lt 1000){throw 'PNG invalid'}
if((Get-Item $ico).Length -lt 100){throw 'ICO invalid'}
Write-Host "BRAND PASS PNG=$((Get-Item $png).Length) ICO=$((Get-Item $ico).Length)"
python .\merzostream\ci\restore_release_support.py
if($LASTEXITCODE -ne 0){throw 'Release support restore failed'}
