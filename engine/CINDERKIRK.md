# Cinderkirk's engine

This folder is [vkQuake](https://github.com/Novum/vkQuake) at tag **1.37.0**, with Cinderkirk's changes on top. Windows-only files, the AppImage packaging and GitHub workflows were left out. Changes that would help vkQuake itself (controller and big-screen work) should go upstream as well.

## Changes from 1.37.0

| Where | What |
|---|---|
| `Quake/quakedef.h` | The game folder is `cinder` (`GAMENAME`), the config `cinderkirk.cfg`, screenshots `cinderkirk-*`, and `GAME_TITLE` "Cinderkirk" |
| `Quake/common.c`, `Quake/console.c` | SDL's preference path and the error box use Cinderkirk's name |
| `Quake/sys_sdl_unix.c` | The user folder is `~/.cinderkirk` (the snap passes `-userdir` instead) |
| `Quake/gl_vidsdl.c`, `Quake/steam.c` | The window title and Vulkan application name are Cinderkirk |
| `Quake/gl_screen.c` | The LinuxGroove Games splash (`gfx/splash.png`, scaled to cover the screen) for 1.5 s at start-up, fading out; `-nosplash` skips it |
| `Quake/host.c` | The game opens on the main menu unless the command line starts a map, a save, a demo or a connection |
| `Quake/menu.c` | How to Play has Cinderkirk's three pages (`NUM_HELP_PAGES`), drawn by `tools/menu_art.py` |
| `Quake/sbar.c` | A Pressure gauge above the status bar, from the game code's stat 32 (a stand-in for the vector status bar's dial) |
| `Quake/cl_main.c` | `cl_spawncmd`: console commands to run each time the player enters a level (`tools/shoot.sh` uses it for screenshots) |
| `Misc/vq_pak/` | The built-in pak keeps only the crosshairs: vkQuake's console background (which carries id's logo), menus and fixes for id's maps are gone, so Cinderkirk's own are used |
| `meson_options.txt` | User folders are on by default |

## Building

`make engine` from the top of the repository builds SDL 3, the Vulkan headers and loader and `spirv-opt` into `build/prefix` (`tools/deps.sh`), then this with Meson into `build/engine`, and copies it to `dist/cinderkirk`.
