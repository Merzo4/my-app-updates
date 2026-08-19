param([switch]$BrandOnly)
$ErrorActionPreference='Stop'
if(-not $env:MERZO_SRC){throw 'MERZO_SRC missing'}
Add-Type -AssemblyName System.Drawing

$content=Join-Path $env:MERZO_SRC 'content'
$web=Join-Path $env:MERZO_SRC 'ui\web'
New-Item -ItemType Directory -Force -Path $content,$web | Out-Null
$png=Join-Path $content 'MerzoStreamSuite.png'
$ico=Join-Path $content 'MerzoStreamSuite.ico'

function New-RoundedPath([float]$x,[float]$y,[float]$w,[float]$h,[float]$r){
  $p=[System.Drawing.Drawing2D.GraphicsPath]::new()
  $d=$r*2
  $p.AddArc($x,$y,$d,$d,180,90)
  $p.AddArc($x+$w-$d,$y,$d,$d,270,90)
  $p.AddArc($x+$w-$d,$y+$h-$d,$d,$d,0,90)
  $p.AddArc($x,$y+$h-$d,$d,$d,90,90)
  $p.CloseFigure()
  return $p
}

function New-BrandBitmap([int]$size){
  $bmp=[System.Drawing.Bitmap]::new($size,$size,[System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
  $g=[System.Drawing.Graphics]::FromImage($bmp)
  try {
    $g.SmoothingMode=[System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.CompositingQuality=[System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.InterpolationMode=[System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.Clear([System.Drawing.Color]::FromArgb(255,3,8,16))

    $s=[float]$size/256.0
    $outer=New-RoundedPath (9*$s) (9*$s) (238*$s) (238*$s) (40*$s)
    try {
      $bg=[System.Drawing.Drawing2D.LinearGradientBrush]::new(
        [System.Drawing.RectangleF]::new(9*$s,9*$s,238*$s,238*$s),
        [System.Drawing.Color]::FromArgb(255,5,17,29),
        [System.Drawing.Color]::FromArgb(255,10,6,23),
        35.0)
      try { $g.FillPath($bg,$outer) } finally { $bg.Dispose() }

      foreach($spec in @(
        @(18,28,221,230,9.0),
        @(26,26,226,238,5.8),
        @(60,22,224,255,2.8)
      )){
        $pen=[System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb([int]$spec[0],[int]$spec[1],[int]$spec[2],[int]$spec[3]),[float]$spec[4]*$s)
        try { $g.DrawPath($pen,$outer) } finally { $pen.Dispose() }
      }

      $cyan=[System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(235,0,229,255),2.7*$s)
      $mag=[System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(220,177,62,255),2.7*$s)
      try {
        $g.DrawArc($cyan,14*$s,14*$s,228*$s,228*$s,135,178)
        $g.DrawArc($mag,14*$s,14*$s,228*$s,228*$s,-45,178)
      } finally { $cyan.Dispose(); $mag.Dispose() }
    } finally { $outer.Dispose() }

    $pts=[System.Drawing.PointF[]]@(
      [System.Drawing.PointF]::new(55*$s,184*$s),
      [System.Drawing.PointF]::new(55*$s,70*$s),
      [System.Drawing.PointF]::new(86*$s,70*$s),
      [System.Drawing.PointF]::new(128*$s,126*$s),
      [System.Drawing.PointF]::new(170*$s,70*$s),
      [System.Drawing.PointF]::new(201*$s,70*$s),
      [System.Drawing.PointF]::new(201*$s,184*$s),
      [System.Drawing.PointF]::new(169*$s,184*$s),
      [System.Drawing.PointF]::new(169*$s,120*$s),
      [System.Drawing.PointF]::new(128*$s,174*$s),
      [System.Drawing.PointF]::new(87*$s,120*$s),
      [System.Drawing.PointF]::new(87*$s,184*$s)
    )
    $mp=[System.Drawing.Drawing2D.GraphicsPath]::new()
    $mp.AddPolygon($pts)
    try {
      foreach($w in @(15,10,6)){
        $glow=[System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb([int](12+(15-$w)*3),12,211,255),$w*$s)
        try { $g.DrawPath($glow,$mp) } finally { $glow.Dispose() }
      }
      $grad=[System.Drawing.Drawing2D.LinearGradientBrush]::new(
        [System.Drawing.RectangleF]::new(50*$s,65*$s,156*$s,125*$s),
        [System.Drawing.Color]::FromArgb(255,12,238,255),
        [System.Drawing.Color]::FromArgb(255,150,73,255),
        18.0)
      try { $g.FillPath($grad,$mp) } finally { $grad.Dispose() }
      $edge=[System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(235,118,244,255),1.6*$s)
      try { $g.DrawPath($edge,$mp) } finally { $edge.Dispose() }
    } finally { $mp.Dispose() }

    $shine=[System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(125,235,255,255),1.2*$s)
    try { $g.DrawLine($shine,61*$s,76*$s,61*$s,171*$s) } finally { $shine.Dispose() }
  } finally { $g.Dispose() }
  return $bmp
}

$main=New-BrandBitmap 512
try { $main.Save($png,[System.Drawing.Imaging.ImageFormat]::Png) } finally { $main.Dispose() }

$sizes=@(16,24,32,48,64,128,256)
$frames=New-Object System.Collections.Generic.List[byte[]]
foreach($sz in $sizes){
  $b=New-BrandBitmap $sz
  try {
    $ms=[System.IO.MemoryStream]::new()
    try { $b.Save($ms,[System.Drawing.Imaging.ImageFormat]::Png); $frames.Add($ms.ToArray()) } finally { $ms.Dispose() }
  } finally { $b.Dispose() }
}
$fs=[System.IO.File]::Create($ico)
$bw=[System.IO.BinaryWriter]::new($fs)
try {
  $bw.Write([UInt16]0); $bw.Write([UInt16]1); $bw.Write([UInt16]$frames.Count)
  $offset=6 + 16*$frames.Count
  for($i=0;$i -lt $frames.Count;$i++){
    $sz=$sizes[$i]
    $bw.Write([byte]($(if($sz -ge 256){0}else{$sz})))
    $bw.Write([byte]($(if($sz -ge 256){0}else{$sz})))
    $bw.Write([byte]0); $bw.Write([byte]0)
    $bw.Write([UInt16]1); $bw.Write([UInt16]32)
    $bw.Write([UInt32]$frames[$i].Length); $bw.Write([UInt32]$offset)
    $offset += $frames[$i].Length
  }
  foreach($frame in $frames){ $bw.Write($frame) }
} finally { $bw.Dispose(); $fs.Dispose() }

Copy-Item $png (Join-Path $web 'MerzoStreamSuite.png') -Force
if((Get-Item $png).Length -lt 6000){throw 'Branded PNG invalid'}
if((Get-Item $ico).Length -lt 8000){throw 'Branded ICO invalid'}
Write-Host "BRAND Q PASS PNG=$((Get-Item $png).Length) ICO=$((Get-Item $ico).Length)"

if(-not $BrandOnly){
  python .\merzostream\ci\restore_release_support.py
  if($LASTEXITCODE -ne 0){throw 'Release support restore failed'}
}
