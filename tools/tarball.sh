#!/bin/sh
# Copyright (C) The LinuxGroove team
# SPDX-License-Identifier: GPL-2.0-or-later
# Packs the built game into dist/cinderkirk-VERSION-linux-ARCH.tar.gz: the
# engine, the libraries it links that a player's system may lack (SDL 3, the
# Vulkan loader, the music codecs), the pak, a launcher and the licences.
#
#   tools/tarball.sh DIST BUILD PREFIX    after make
set -eu
dist=$1 build=$2 prefix=$3
# No "+" in the name: the engine reads a "+" in its -basedir as a command.
version=$(tools/version.sh | tr + -)
arch=$(uname -m)
name="cinderkirk-$version-linux-$arch"
root="$build/tarball/$name"
rm -rf "$build/tarball"
mkdir -p "$root/bin" "$root/lib" "$root/cinder"
install -m 755 "$dist/cinderkirk" "$root/bin/cinderkirk"
install -m 644 "$dist/cinder/pak0.pak" "$root/cinder/pak0.pak"
install -m 755 tools/tarball/cinderkirk tools/tarball/install-desktop-entry "$root/"
install -m 644 tools/tarball/README.txt LICENSE CREDITS.md "$root/"
install -m 644 snap/gui/cinderkirk.png "$root/cinderkirk.png"
# Every library the engine links except glibc's own and the graphics and
# sound stacks, which must come from the player's system.
LD_LIBRARY_PATH="$prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ldd "$dist/cinderkirk" |
	awk '$2 == "=>" && $3 ~ /^\// { print $3 }' |
	grep -Ev '/(libc|libm|libdl|libpthread|librt|libresolv|ld-linux[^/]*)\.so' |
	while read -r lib; do cp -L "$lib" "$root/lib/$(basename "$lib")"; done
# SDL 3 and the loader dlopen by their full sonames too.
cp -a "$prefix"/lib/libSDL3.so* "$prefix"/lib/libvulkan.so* "$root/lib/"
tar -C "$build/tarball" -czf "$dist/$name.tar.gz" "$name"
echo "$dist/$name.tar.gz"
