#!/usr/bin/env bash
# Convert the Playwright demo video into docs/screenshots/demo.gif (<= 20 s, <= 5 MB).
# Two-pass ffmpeg: build an optimised palette, then encode the GIF with it.
set -euo pipefail
cd "$(dirname "$0")/../docs/screenshots"
FILTERS="fps=8,scale=960:-1:flags=lanczos"
ffmpeg -y -loglevel error -t 20 -i _demo.webm -vf "$FILTERS,palettegen=max_colors=128" _palette.png
ffmpeg -y -loglevel error -t 20 -i _demo.webm -i _palette.png \
  -lavfi "$FILTERS [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5" demo.gif
rm -f _palette.png
ls -l demo.gif
