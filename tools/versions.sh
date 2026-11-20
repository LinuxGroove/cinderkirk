# Pinned versions of everything the build fetches. Sourced by the other scripts.
# Change one here, then run `make deps tools librequake` again.

SDL3_REPO=https://github.com/libsdl-org/SDL
SDL3_REF=release-3.2.24
VULKAN_HEADERS_REPO=https://github.com/KhronosGroup/Vulkan-Headers
VULKAN_HEADERS_REF=v1.4.369
VULKAN_LOADER_REPO=https://github.com/KhronosGroup/Vulkan-Loader
VULKAN_LOADER_REF=v1.4.369
SPIRV_TOOLS_REPO=https://github.com/KhronosGroup/SPIRV-Tools
SPIRV_TOOLS_REF=3c8fd35297315682906894621677f1b7003461ef
SPIRV_HEADERS_REPO=https://github.com/KhronosGroup/SPIRV-Headers
SPIRV_HEADERS_REF=fb1379425b16e58dcbdda7be0f8604a7f5cdce78
ERICW_TOOLS_REPO=https://github.com/ericwa/ericw-tools
ERICW_TOOLS_REF=36eec1da2a194467e6baac2f444c2dd04b57d266
FTEQW_REPO=https://github.com/fte-team/fteqw
FTEQW_REF=f09ac7cccd2d713ddf881d3f1324703082c2cfe4
LIBREQUAKE_REPO=https://github.com/lavenderdotpet/LibreQuake
LIBREQUAKE_REF=b8a85baa94629a5acf5f1b81aa61a1eb3f39812f

# fetch DIR REPO REF: a shallow checkout of one commit or tag.
fetch() {
    if [ -d "$1/.git" ] && [ "$(git -C "$1" rev-parse -q --verify HEAD)" = "$(cat "$1/.ref" 2>/dev/null)" ]; then
        return 0
    fi
    rm -rf "$1"
    git init -q "$1"
    git -C "$1" remote add origin "$2"
    git -C "$1" fetch -q --depth 1 origin "$3"
    git -C "$1" -c advice.detachedHead=false checkout -q FETCH_HEAD
    git -C "$1" rev-parse HEAD > "$1/.ref"
}
