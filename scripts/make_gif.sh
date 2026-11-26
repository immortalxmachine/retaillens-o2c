#!/usr/bin/env bash
# Convert the Playwright demo video into docs/screenshots/demo.gif (<= 20 s, <= 5 MB).
# Two-pass ffmpeg: build an optimised palette, then encode the GIF with it.
set -euo pipefail
cd "$(dirname "$0")/../docs/screenshots"
FILTERS="fps=8,scale=960:-1:flags=lanczos"
# keep the LAST 19.5 s (the first seconds are the page loading)
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 _demo.webm)
START=$(python -c "print(max(0.0, float('$DUR') - 19.5))")
ffmpeg -y -loglevel error -ss "$START" -t 19.5 -i _demo.webm -vf "$FILTERS,palettegen=max_colors=128" _palette.png
ffmpeg -y -loglevel error -ss "$START" -t 19.5 -i _demo.webm -i _palette.png \
  -lavfi "$FILTERS [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5" demo.gif
rm -f _palette.png
ls -l demo.gif
