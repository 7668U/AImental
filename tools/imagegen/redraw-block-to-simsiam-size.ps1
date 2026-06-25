param(
  [string]$Out = "output\imagegen\block-unified-739x799.png"
)

Add-Type -AssemblyName System.Drawing

$width = 739
$height = 799
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$outPath = if ([System.IO.Path]::IsPathRooted($Out)) { $Out } else { Join-Path $root $Out }
$outDir = Split-Path -Parent $outPath
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$bmp = New-Object System.Drawing.Bitmap $width, $height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$g.Clear([System.Drawing.Color]::White)

function Color([string]$hex) {
  return [System.Drawing.ColorTranslator]::FromHtml($hex)
}

function Brush([string]$hex) {
  return New-Object System.Drawing.SolidBrush (Color $hex)
}

function Pen([string]$hex, [float]$width = 2) {
  return New-Object System.Drawing.Pen (Color $hex), $width
}

function ArrowPen([string]$hex = "#000000", [float]$width = 2.2) {
  $pen = Pen $hex $width
  $cap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap 5, 6, $true
  $pen.CustomEndCap = $cap
  return $pen
}

function RoundRectPath([float]$x, [float]$y, [float]$w, [float]$h, [float]$r) {
  $path = New-Object System.Drawing.Drawing2D.GraphicsPath
  $d = $r * 2
  $path.AddArc($x, $y, $d, $d, 180, 90)
  $path.AddArc($x + $w - $d, $y, $d, $d, 270, 90)
  $path.AddArc($x + $w - $d, $y + $h - $d, $d, $d, 0, 90)
  $path.AddArc($x, $y + $h - $d, $d, $d, 90, 90)
  $path.CloseFigure()
  return $path
}

function TextFormat() {
  $fmt = New-Object System.Drawing.StringFormat
  $fmt.Alignment = [System.Drawing.StringAlignment]::Center
  $fmt.LineAlignment = [System.Drawing.StringAlignment]::Center
  return $fmt
}

$fmt = TextFormat
$fontMain = New-Object System.Drawing.Font "Arial", 24, ([System.Drawing.FontStyle]::Regular), ([System.Drawing.GraphicsUnit]::Pixel)
$fontSmall = New-Object System.Drawing.Font "Arial", 22, ([System.Drawing.FontStyle]::Regular), ([System.Drawing.GraphicsUnit]::Pixel)
$fontItalic = New-Object System.Drawing.Font "Arial", 24, ([System.Drawing.FontStyle]::Italic), ([System.Drawing.GraphicsUnit]::Pixel)
$fontWhite = New-Object System.Drawing.Font "Arial", 23, ([System.Drawing.FontStyle]::Bold), ([System.Drawing.GraphicsUnit]::Pixel)

function DrawCenteredText([string]$text, [System.Drawing.RectangleF]$rect, [System.Drawing.Font]$font, [string]$color = "#000000") {
  $brush = Brush $color
  $g.DrawString($text, $font, $brush, $rect, $fmt)
  $brush.Dispose()
}

function DrawRoundBox([float]$x, [float]$y, [float]$w, [float]$h, [float]$r, [string]$fill, [string]$stroke, [string]$text, [System.Drawing.Font]$font, [string]$textColor = "#000000", [float]$strokeWidth = 2) {
  $path = RoundRectPath $x $y $w $h $r
  $brush = Brush $fill
  $pen = Pen $stroke $strokeWidth
  $g.FillPath($brush, $path)
  $g.DrawPath($pen, $path)
  DrawCenteredText $text ([System.Drawing.RectangleF]::new($x, $y, $w, $h)) $font $textColor
  $brush.Dispose()
  $pen.Dispose()
  $path.Dispose()
}

function DrawEllipseBox([float]$x, [float]$y, [float]$w, [float]$h, [string]$fill, [string]$stroke, [string]$text, [System.Drawing.Font]$font, [string]$textColor = "#000000", [float]$strokeWidth = 2) {
  $brush = Brush $fill
  $pen = Pen $stroke $strokeWidth
  $rect = [System.Drawing.RectangleF]::new($x, $y, $w, $h)
  $g.FillEllipse($brush, $rect)
  $g.DrawEllipse($pen, $rect)
  DrawCenteredText $text $rect $font $textColor
  $brush.Dispose()
  $pen.Dispose()
}

function DrawArrow([float]$x1, [float]$y1, [float]$x2, [float]$y2) {
  $pen = ArrowPen
  $g.DrawLine($pen, $x1, $y1, $x2, $y2)
  $pen.Dispose()
}

function DrawBezierArrow([float]$x1, [float]$y1, [float]$cx1, [float]$cy1, [float]$cx2, [float]$cy2, [float]$x2, [float]$y2) {
  $pen = ArrowPen
  $g.DrawBezier($pen, $x1, $y1, $cx1, $cy1, $cx2, $cy2, $x2, $y2)
  $pen.Dispose()
}

# Outer EdgeConv-style block.
$outer = RoundRectPath 42 112 655 672 92
$outerBrush = Brush "#f7f7f7"
$outerPen = Pen "#6f6f6f" 2.2
$g.FillPath($outerBrush, $outer)
$g.DrawPath($outerPen, $outer)
$outerBrush.Dispose()
$outerPen.Dispose()
$outer.Dispose()

# Top inputs.
DrawEllipseBox 122 28 205 76 "#e5d7ee" "#9372aa" "coordinates" $fontSmall
DrawEllipseBox 382 28 205 76 "#e5d7ee" "#9372aa" "features" $fontSmall

# k-NN branch.
DrawRoundBox 122 135 205 45 7 "#a8cbc4" "#000000" "k-NN" $fontItalic
DrawEllipseBox 124 212 205 62 "#f8dad5" "#bd5a56" "k-NN indices" $fontSmall

# Edge features.
DrawEllipseBox 383 212 205 62 "#dc6f69" "#bd5a56" "edge features" $fontWhite "#ffffff"

# Processing chain.
$cx = 485
$boxW = 210
$boxH = 34
$x = $cx - ($boxW / 2)
$rows = @(
  @{ y = 282; fill = "#fae7cc"; stroke = "#df9c22"; text = "Linear" },
  @{ y = 322; fill = "#e3efff"; stroke = "#6d91cf"; text = "BatchNorm" },
  @{ y = 362; fill = "#dcebd8"; stroke = "#82ad6e"; text = "ReLU" },
  @{ y = 410; fill = "#fae7cc"; stroke = "#df9c22"; text = "Linear" },
  @{ y = 450; fill = "#e3efff"; stroke = "#6d91cf"; text = "BatchNorm" },
  @{ y = 490; fill = "#dcebd8"; stroke = "#82ad6e"; text = "ReLU" },
  @{ y = 538; fill = "#fae7cc"; stroke = "#df9c22"; text = "Linear" },
  @{ y = 578; fill = "#e3efff"; stroke = "#6d91cf"; text = "BatchNorm" },
  @{ y = 618; fill = "#dcebd8"; stroke = "#82ad6e"; text = "ReLU" },
  @{ y = 660; fill = "#f8dad8"; stroke = "#bd5a56"; text = "Aggregation" }
)

foreach ($row in $rows) {
  DrawRoundBox $x $row.y $boxW $boxH 7 $row.fill $row.stroke $row.text $fontSmall
}

# Arrows in the left/top branches.
DrawArrow 224 104 224 135
DrawArrow 224 180 224 212
DrawArrow 329 243 383 243
DrawArrow 485 104 485 212

# Arrows in the main processing chain.
DrawArrow 485 274 485 282
for ($i = 0; $i -lt $rows.Count - 1; $i++) {
  $fromY = [float]$rows[$i].y + $boxH
  $toY = [float]$rows[$i + 1].y
  DrawArrow 485 $fromY 485 $toY
}

# Plus node and output.
$plusCenterX = 485
$plusCenterY = 720
$plusR = 21
$plusPen = Pen "#000000" 2.4
$g.DrawEllipse($plusPen, $plusCenterX - $plusR, $plusCenterY - $plusR, $plusR * 2, $plusR * 2)
$g.DrawLine($plusPen, $plusCenterX - $plusR + 4, $plusCenterY, $plusCenterX + $plusR - 4, $plusCenterY)
$g.DrawLine($plusPen, $plusCenterX, $plusCenterY - $plusR + 4, $plusCenterX, $plusCenterY + $plusR - 4)
$plusPen.Dispose()

DrawArrow 485 694 485 699
DrawArrow 485 741 485 748
DrawRoundBox 380 748 210 34 7 "#dcebd8" "#82ad6e" "ReLU" $fontSmall
DrawArrow 485 782 485 798

# Residual connection from features to plus node.
$plainPen = Pen "#000000" 2.2
$g.DrawLine($plainPen, 485, 104, 485, 154)
$plainPen.Dispose()
DrawBezierArrow 485 154 650 158 670 642 507 720

$bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)

$fontMain.Dispose()
$fontSmall.Dispose()
$fontItalic.Dispose()
$fontWhite.Dispose()
$g.Dispose()
$bmp.Dispose()

Write-Output $outPath
