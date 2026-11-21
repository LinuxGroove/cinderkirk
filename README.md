# Cinderkirk

A fast first person shooter in the old style, built for big screens and controllers. You're the last stoker at the bell foundry of Cinderkirk, built over a pit that never stopped burning, and something has come up out of it.

It's idea 25 in [game-ideas](https://github.com/LinuxGroove/game-ideas/blob/main/ideas/25-cinderkirk.md): Ken's modern Quake, made as an original game on the same tools (a vkQuake fork, QuakeC, ericw-tools) so it can ship freely. It's the first LinuxGroove game not made in Godot.

![The Casting Floor](docs/screenshots/casting-floor.jpg)

More in [docs/screenshots](docs/screenshots/): the splash, the main menu, the gatehouse, the Casting Floor from above and the silver key.

## Where it's at

**Phase 1, the engine and tool chain, with a first playable level.**

- The engine is vkQuake 1.37.0, forked in `engine/` ([what changed](engine/CINDERKIRK.md)): its own game folder (`cinder/`), name and save folder, the LinuxGroove Games splash, and opening on the main menu. vkQuake already brings SDL 3 and Wayland, gyro aiming, flick stick, rumble, a render resolution separate from the menus and HUD, ambient occlusion, and external high-resolution textures with glow maps.
- **The Foundry Gate** (`maps_src/start.py`), the first level: the gatehouse, the Casting Floor with a slag channel and a bridge, the silver key, and the belfry behind the key door. Its world textures are the 1024 px Blender bakes from the mockup, so 8 texels a unit.
- The menus, cursor, side plaque and console background are Cinderkirk's own, drawn at 4× so they stay sharp at 4K.
- Creatures, weapons, items, sounds and the status bar are **stand-ins from LibreQuake** (BSD-3) until Cinderkirk's own are made, and the game code is LibreQuake's QuakeC (GPL-2.0). The menus already use Cinderkirk's words: Story, Pit Fights, Apprentice to Bellfounder.
- Snap packaging for amd64 and arm64 (core24, strict), so it installs on Ubuntu and Ubuntu Core.

Next, from the idea's plan: Cinderkirk's own creatures (the Deacon first) and weapons as MD5 models from Blender, the Pressure gauge and its moves in QuakeC, the vector HUD and weapon wheel, normal and gloss maps in the renderer, and the four shafts of the Foundry.

## Playing it

```sh
sudo snap install cinderkirk_*.snap --dangerous   # a snap from CI's artifacts
cinderkirk
```

From source on Ubuntu 24.04 (the packages are listed in `.github/workflows/ci.yml`):

```sh
make            # first time: builds SDL 3, the Vulkan loader, spirv-opt, ericw-tools and fteqcc (a few minutes)
make run        # dist/cinderkirk -basedir dist
make run ARGS="+map start"
```

Controls: a controller just works (left stick moves, right stick or gyro looks, right trigger fires, A jumps, bumpers change weapon, the d-pad picks one). Keyboard and mouse are the usual WASD. Comfort settings are on by default: no view bob, roll or gun kick (`cinder/default.cfg`).

## Layout

| Path | What |
|---|---|
| `engine/` | The vkQuake fork (C, Vulkan, Meson) |
| `quakec/` | The game code, built with fteqcc into `build/progs.dat` |
| `maps_src/` | Levels in code: each `<map>.py` writes a `.map` (TrenchBroom opens it) with `tools/mapkit.py` |
| `assets_src/materials/` | Blender scripts that bake the world textures (`make textures`) |
| `assets_src/models/` | Blender scripts for the creatures and weapons (`make models`; not in the game yet) |
| `assets_src/fonts/` | Cinzel, for the menu lettering |
| `assets/textures/` | The baked textures: `<name>.png`, `_luma`, and `_norm` and `_gloss` for when the renderer uses them |
| `cinder/` | Loose game files: `default.cfg` (controls and comfort defaults) and `quake.rc` |
| `gfx/splash.png` | The LinuxGroove Games splash |
| `tools/` | The build's helpers: `wad.py` (texture WADs), `pak.py`, `menu_art.py`, `sfx.py` (the game's own sounds, synthesized), `make_icon.py`, `mapkit.py`, `deps.sh`, `tools.sh`, `librequake.sh`, `versions.sh` (every pinned version), `shoot.sh` (screenshots on a machine with no screen), `version.sh` |
| `snap/` | The snap: `snapcraft.yaml`, the launcher and the desktop file |
| `build/`, `dist/` | Made by `make`; `dist/` is the game, ready to run |

## How it's built

1. `tools/deps.sh` builds SDL 3, the Vulkan headers and loader (vkQuake needs 1.4.341) and `spirv-opt` into `build/prefix`; `tools/tools.sh` builds qbsp, vis, light and fteqcc into `build/bin`; `tools/librequake.sh` fetches LibreQuake's stand-ins at a pinned commit and compiles its ammo and health boxes.
2. The engine builds with Meson against `build/prefix`.
3. The QuakeC compiles to `build/progs.dat`.
4. `tools/wad.py` turns the baked textures into a small WAD for qbsp (128 px stand-ins, so a texture repeats every 128 units); the engine draws the full 1024 px PNGs from `textures/` in their place, with their `_luma` glow.
5. Each level script writes its `.map`, then qbsp, vis and light (`-extra4 -bounce -lit`) compile it.
6. `tools/menu_art.py` draws the menus; everything goes into `dist/cinder/pak0.pak`.

Screenshots on a machine with no GPU: `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json tools/shoot.sh /tmp/shot "20" +map start`, with `SPAWN="notarget; god; setpos X Y Z PITCH YAW 0"` to place the view.

## Licences

The engine and game code are GPL-2.0-or-later (`LICENSE`); see `CREDITS.md` for everything else. Nothing of id Software's Quake data is used.
