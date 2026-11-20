#!/bin/sh
# Build what the engine needs that Ubuntu 24.04 doesn't have new enough:
# SDL3, the Vulkan headers and loader (vkQuake wants 1.4.341 or later) and a
# spirv-opt with --canonicalize-ids. Everything goes into PREFIX.
#
#   tools/deps.sh [PREFIX]          (default build/prefix)
#
# Needs: git cmake ninja-build pkg-config python3 and SDL3's usual -dev
# packages (see README.md).
set -eu
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/versions.sh"
PREFIX=$(realpath -m "${1:-build/prefix}")
SRC=$(realpath -m "${DEPS_SRC:-build/src}")
JOBS=${JOBS:-$(nproc)}
mkdir -p "$PREFIX" "$SRC"

if [ ! -f "$PREFIX/lib/pkgconfig/sdl3.pc" ]; then
    fetch "$SRC/sdl3" "$SDL3_REPO" "$SDL3_REF"
    cmake -S "$SRC/sdl3" -B "$SRC/sdl3/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_INSTALL_LIBDIR=lib \
        -DSDL_TESTS=OFF -DSDL_EXAMPLES=OFF -DSDL_WAYLAND=ON -DSDL_X11=ON
    ninja -C "$SRC/sdl3/build" -j"$JOBS" install
fi

if [ ! -f "$PREFIX/share/pkgconfig/vulkan.pc" ] && [ ! -f "$PREFIX/lib/pkgconfig/vulkan.pc" ]; then
    fetch "$SRC/vulkan-headers" "$VULKAN_HEADERS_REPO" "$VULKAN_HEADERS_REF"
    cmake -S "$SRC/vulkan-headers" -B "$SRC/vulkan-headers/build" -G Ninja \
        -DCMAKE_INSTALL_PREFIX="$PREFIX"
    ninja -C "$SRC/vulkan-headers/build" install
    fetch "$SRC/vulkan-loader" "$VULKAN_LOADER_REPO" "$VULKAN_LOADER_REF"
    cmake -S "$SRC/vulkan-loader" -B "$SRC/vulkan-loader/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX="$PREFIX" -DCMAKE_INSTALL_LIBDIR=lib \
        -DVULKAN_HEADERS_INSTALL_DIR="$PREFIX" -DBUILD_TESTS=OFF
    ninja -C "$SRC/vulkan-loader/build" -j"$JOBS" install
fi

if [ ! -x "$PREFIX/bin/spirv-opt" ]; then
    fetch "$SRC/spirv-tools" "$SPIRV_TOOLS_REPO" "$SPIRV_TOOLS_REF"
    fetch "$SRC/spirv-tools/external/spirv-headers" "$SPIRV_HEADERS_REPO" "$SPIRV_HEADERS_REF"
    cmake -S "$SRC/spirv-tools" -B "$SRC/spirv-tools/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
        -DSPIRV_SKIP_TESTS=ON -DSPIRV_WERROR=OFF -DCMAKE_INSTALL_PREFIX="$PREFIX"
    ninja -C "$SRC/spirv-tools/build" -j"$JOBS" spirv-opt
    install -D -m 755 "$SRC/spirv-tools/build/tools/spirv-opt" "$PREFIX/bin/spirv-opt"
fi
echo "deps in $PREFIX"
