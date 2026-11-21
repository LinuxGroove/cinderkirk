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
| `Quake/sbar.c` | HUD style 3, the Foundry bar, is the default and calls `sbar_foundry.c`; the classic and modern bars keep a strip for Pressure (the game code's stat 32) |
| `Quake/sbar_foundry.c` (new) | The Foundry status bar: full width, armour, health, the Pressure dial, ammo, keys, secrets (frags in Pit fights), the weapon row above it and kills, secrets and time on `+showscores`; laid out in the mockup's 1280x720 units and scaled to the screen (`hud_scale`) |
| `Quake/hud_svg.c` (new), `Quake/nanosvg/` | SVG pictures from `gfx/hud/`, rasterised with [nanosvg](https://github.com/memononen/nanosvg) (zlib licence, commit 239e102) at the size they're drawn and kept for the last three sizes. **Upstream:** a general way to ship a sharp HUD |
| `Quake/wheel.c` (new) | The weapon wheel: hold `+wheel` (LB, Q) and point with the right stick, the gyro or the mouse; letting go sends `impulse <slot>`, a tap goes back to the last weapon, and single player runs at `wheel_slowmo` (a third) while it's open. `wheel_select N` points it from a key. **Upstream:** with the slots as a cvar |
| `Quake/gl_draw.c` | `Draw_PicFromRGBA`, `Draw_FreePic` and `Draw_PicRotated` (the dial's needle, the wheel's wedges). **Upstream** |
| `Quake/in_sdl.c` | While the wheel is open the look stick, the gyro and the mouse point at it instead of turning the view |
| `Quake/host.c` | The frame time is scaled by the wheel's slow motion |
| `Quake/menu.c`, `Quake/gl_screen.c` | HUD Style offers Foundry, and `scr_style` starts at 3 |
| `Quake/cl_main.c` | `cl_spawncmd`: console commands to run each time the player enters a level (`tools/shoot.sh` uses it for screenshots) |
| `Misc/vq_pak/` | The built-in pak keeps only the crosshairs: vkQuake's console background (which carries id's logo), menus and fixes for id's maps are gone, so Cinderkirk's own are used |
| `meson_options.txt` | User folders are on by default |

## Building

`make engine` from the top of the repository builds SDL 3, the Vulkan headers and loader and `spirv-opt` into `build/prefix` (`tools/deps.sh`), then this with Meson into `build/engine`, and copies it to `dist/cinderkirk`.
