#!/bin/sh
# Fetch LibreQuake (BSD-3 art and sound) at the commit in versions.sh, and
# copy the stand-ins Cinderkirk uses until its own are made into OUT.
# QuakeC comes from the copy in quakec/, not from here.
#
#   tools/librequake.sh [OUT] [BIN]   (default build/librequake, build/bin)
#
# The boxes (the exploding ones are still used) are little BSP models; they're compiled here
# from LibreQuake's .map sources with the tools in BIN.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/versions.sh"
OUT=$(realpath -m "${1:-build/librequake}")
BIN=$(realpath -m "${2:-build/bin}")
PYTHON=${PYTHON:-python3}
SRC=$(realpath -m "${DEPS_SRC:-build/src}")
mkdir -p "$SRC"
fetch "$SRC/librequake" "$LIBREQUAKE_REPO" "$LIBREQUAKE_REF"
LQ="$SRC/librequake/lq1"
rm -rf "$OUT"
mkdir -p "$OUT/gfx" "$OUT/progs"
cp "$LQ/gfx.wad" "$OUT/"
cp "$LQ"/gfx/*.lmp "$OUT/gfx/"
cp "$LQ"/progs/*.mdl "$LQ"/progs/*.spr "$OUT/progs/"
cp -r "$LQ/sound" "$OUT/sound"
find "$OUT/sound" -type f ! -name '*.wav' -delete
cp "$SRC/librequake/docs/COPYING" "$OUT/COPYING.LibreQuake"

# The boxes: their textures into WADs, then each map compiled (no vis).
WORK="$OUT/.boxes"
mkdir -p "$WORK/empty" "$OUT/maps"
"$PYTHON" "$HERE/wad.py" "$LQ/gfx/palette.lmp" "$WORK/lq_health_ammo.wad" \
    "$SRC/librequake/texture-wads/lq_health_ammo" --native --no-tools --qpakman-names
"$PYTHON" "$HERE/wad.py" "$LQ/gfx/palette.lmp" "$WORK/lq_dev.wad" "$WORK/empty"
for m in "$LQ"/maps/src/brushmodels/b_*.map; do
    case "$m" in *_lite.map) continue ;; esac
    b=$(basename "$m" .map)
    cp "$m" "$WORK/"
    (cd "$WORK" && "$BIN/qbsp" -wadpath "$WORK" "$b.map" > "$b.out" 2>&1 \
        && "$BIN/light" -dirt "$b.bsp" >> "$b.out" 2>&1) || { cat "$WORK/$b.out"; exit 1; }
    cp "$WORK/$b.bsp" "$OUT/maps/"
done
rm -rf "$WORK"
echo "LibreQuake stand-ins in $OUT"
