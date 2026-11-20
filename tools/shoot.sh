#!/bin/sh
# Screenshots of the game running in a virtual X display, for checking looks
# on a machine with no screen (Mesa's lavapipe is enough, just slow).
#
#   tools/shoot.sh OUT_PREFIX "SECONDS ..." [game arguments ...]
#
# Starts dist/cinderkirk on a private Xvfb, grabs the whole screen at each
# time in SECONDS (from launch) into OUT_PREFIX-<seconds>.png, then stops it.
# SIZE=1920x1080 sets the window, VK_ICD_FILENAMES picks the Vulkan driver.
# SPAWN="notarget; god; setpos X Y Z PITCH YAW 0" runs console commands once
# the player is in the level (through the engine's cl_spawncmd).
#
#   tools/shoot.sh /tmp/ck "1 12" +map start
set -eu
OUT=$(realpath -m "$1"); TIMES=$2; shift 2
SIZE=${SIZE:-1280x720}
W=${SIZE%x*}; H=${SIZE#*x}
DISPLAY_NUM=${DISPLAY_NUM:-77}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
export DISPLAY=":$DISPLAY_NUM"
export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-$(mktemp -d)}
export LD_LIBRARY_PATH="$ROOT/build/prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

Xvfb "$DISPLAY" -screen 0 "${SIZE}x24" -nolisten tcp > /dev/null 2>&1 &
XPID=$!
trap 'kill $GPID $XPID 2>/dev/null || true' EXIT
sleep 1
cd "$ROOT/dist"
if [ -n "${SPAWN:-}" ]; then
    echo "$SPAWN" | tr ';' '\n' > cinder/_spawn.cfg
    # The command line loses quotes, so set the cvar from a file.
    echo 'cl_spawncmd "exec _spawn.cfg"' > cinder/_spawnset.cfg
    set -- +exec _spawnset.cfg "$@"
fi
./cinderkirk -basedir . -width "$W" -height "$H" -window -nosound "$@" > "$OUT.log" 2>&1 &
GPID=$!
start=$(date +%s.%N)
for t in $TIMES; do
    now=$(date +%s.%N)
    left=$(echo "$t - ($now - $start)" | bc)
    case "$left" in -*) ;; *) sleep "$left" ;; esac
    import -window root "$OUT-$t.png"
    echo "$OUT-$t.png"
done
