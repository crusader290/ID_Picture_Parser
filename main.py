#!/usr/bin/env bash
set -euo pipefail

# make_passport_photo.sh
# Usage: ./make_passport_photo.sh input.jpg output.jpg
#
# Output: 35x45 mm (413x531 px) @ 300 DPI, plain white background, sRGB

*\\Usage

chmod +x make_passport_photo.sh
./make_passport_photo.sh headshot.jpg passport.jpg

Result: passport.jpg → 413×531 px, 300 DPI, white background, sRGB, head centered & scaled.

*//

if [ $# -ne 2 ]; then
  echo "Usage: $0 INPUT.jpg OUTPUT.jpg"
  exit 1
fi

IN="$1"
OUT="$2"

# Target size in pixels
PIX_W=413
PIX_H=531
DPI=300
HEAD_FACTOR=0.72   # head should occupy ~72% of image height
BG_COLOR="white"

MAGICK_CMD="$(command -v magick || true)"
if [ -z "$MAGICK_CMD" ]; then
  echo "Error: ImageMagick 'magick' not found."
  exit 1
fi

# Try to detect face (needs python3 + opencv-python)
FACE_BOX=$(python3 - <<'PY' "$IN" 2>/dev/null || true
import sys, cv2
infile = sys.argv[1]
img = cv2.imread(infile)
if img is None:
    sys.exit(0)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))
if len(faces)==0: sys.exit(0)
x,y,w,h = max(faces, key=lambda r:r[2]*r[3])
print(f"{x} {y} {w} {h}")
PY
)

TMP=$(mktemp -d)
trap "rm -rf $TMP" EXIT

if [ -n "$FACE_BOX" ]; then
  read FX FY FW FH <<<"$FACE_BOX"

  DESIRED_HEAD=$((PIX_H * HEAD_FACTOR))
  SCALE=$(awk -v t=$DESIRED_HEAD -v f=$FH 'BEGIN{ if (f>0) print t/f; else print 1 }')
  CROP_W=$(awk -v w=$PIX_W -v s=$SCALE 'BEGIN{printf("%d", w/s)}')
  CROP_H=$(awk -v h=$PIX_H -v s=$SCALE 'BEGIN{printf("%d", h/s)}')
  CX=$((FX + FW/2))
  CY=$((FY + FH/2))
  X=$((CX - CROP_W/2))
  Y=$((CY - CROP_H/2))
  if [ $X -lt 0 ]; then X=0; fi
  if [ $Y -lt 0 ]; then Y=0; fi
  $MAGICK_CMD "$IN" -crop "${CROP_W}x${CROP_H}+$X+$Y" +repage "$TMP/crop.png"
else
  # fallback: center-crop to 35x45 aspect ratio
  $MAGICK_CMD "$IN" -gravity center -crop 35:45 +repage "$TMP/crop.png"
fi

# Resize & clean background
$MAGICK_CMD "$TMP/crop.png" \
  -resize "${PIX_W}x${PIX_H}!" \
  -background "$BG_COLOR" -flatten \
  -colorspace sRGB -strip -density $DPI -units PixelsPerInch \
  -quality 95 "$OUT"

echo "✅ Written $OUT (413x531 px, 300 DPI passport photo)"
