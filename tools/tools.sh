#!/bin/sh
# Build the level and game code compilers: ericw-tools (qbsp, vis, light)
# and fteqcc, at the commits in versions.sh, into BIN.
#
#   tools/tools.sh [BIN]            (default build/bin)
#
# Needs: git cmake ninja-build libembree-dev libtbb-dev zlib1g-dev
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/versions.sh"
BIN=$(realpath -m "${1:-build/bin}")
SRC=$(realpath -m "${DEPS_SRC:-build/src}")
JOBS=${JOBS:-$(nproc)}
mkdir -p "$BIN" "$SRC"

if [ ! -x "$BIN/qbsp" ] || [ ! -x "$BIN/vis" ] || [ ! -x "$BIN/light" ]; then
    fetch "$SRC/ericw-tools" "$ERICW_TOOLS_REPO" "$ERICW_TOOLS_REF"
    git -C "$SRC/ericw-tools" submodule update -q --init --depth 1
    cmake -S "$SRC/ericw-tools" -B "$SRC/ericw-tools/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
        -DSKIP_TBB_INSTALL=ON -DSKIP_EMBREE_INSTALL=ON -DDISABLE_TESTS=ON -DDISABLE_DOCS=ON
    ninja -C "$SRC/ericw-tools/build" -j"$JOBS" qbsp vis light
    for t in qbsp vis light; do
        install -m 755 "$SRC/ericw-tools/build/$t/$t" "$BIN/$t"
    done
fi

if [ ! -x "$BIN/fteqcc" ]; then
    fetch "$SRC/fteqw" "$FTEQW_REPO" "$FTEQW_REF"
    cmake -S "$SRC/fteqw" -B "$SRC/fteqw/build" -G Ninja -DCMAKE_BUILD_TYPE=Release
    ninja -C "$SRC/fteqw/build" -j"$JOBS" fteqcc
    install -m 755 "$SRC/fteqw/build/fteqcc" "$BIN/fteqcc"
fi
echo "tools in $BIN"
