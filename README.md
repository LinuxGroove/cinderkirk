# Cinderkirk

A fast first person shooter in the old style, built for big screens and controllers. You're the last stoker at the bell foundry of Cinderkirk, built over a pit that never stopped burning, and something has come up out of it.

It's idea 25 in [game-ideas](https://github.com/LinuxGroove/game-ideas/blob/main/ideas/25-cinderkirk.md): Ken's modern Quake, made as an original game on the same tools (a vkQuake fork, QuakeC, ericw-tools) so it can ship freely. It's the first LinuxGroove game not made in Godot.

![The Casting Floor](docs/screenshots/casting-floor.jpg)

More in [docs/screenshots](docs/screenshots/): the splash, the main menu, the gatehouse, the Casting Floor from above, the pattern shop, the pouring gallery, the quench pit, a Deacon with two Ashen, the status bar, the weapon wheel, all eight weapons in hand (`weapons.jpg`), a pack of slag hounds (`slag-hounds.jpg`), and the pickups: ammunition, health, armour and a weapon on the floor (`pickups.jpg`).

## Where it's at

**Phase 1, the engine and tool chain, with a first playable level.**

- The engine is vkQuake 1.37.0, forked in `engine/` ([what changed](engine/CINDERKIRK.md)): its own game folder (`cinder/`), name and save folder, the LinuxGroove Games splash, and opening on the main menu. vkQuake already brings SDL 3 and Wayland, gyro aiming, flick stick, rumble, a render resolution separate from the menus and HUD, ambient occlusion, and external high-resolution textures with glow maps.
- **The Foundry Gate** (`maps_src/start.py`), the first level: the gatehouse, the Casting Floor with a slag channel and a bridge, the silver key, and the belfry behind the key door. Its world textures are the 1024 px Blender bakes from the mockup, so 8 texels a unit.
- The menus, cursor, side plaque and console background are Cinderkirk's own, drawn at 4× so they stay sharp at 4K.
- **Rumble** is designed, not loudness: each weapon's shot, a hit taken, the dash, Overpressure, a vent, a pickup and a secret have their own short pattern (`engine/Quake/rumble.c`), sent by the game code to the one player it happens to (`quakec/cinder/rumble.qc`).
- **The status bar and the weapon wheel** are vector art: `tools/hud_svg.py` writes them as SVG (text turned to paths from the game's fonts) and the engine rasterises them with nanosvg at the screen's own resolution, so they're as sharp at 4K as at 720p. The Pressure dial sits in the middle of the bar, with the eight weapons in a row above it. Hold LB (or Q) for the wheel: the right stick, the gyro or the mouse points, letting go equips, a tap goes back to the last weapon, and time slows to a third while it's open in single player.
- **Button glyphs** follow the device used last: the keyboard and mouse, or an Xbox, PlayStation, Switch or Steam Deck pad (Kenney's Input Prompts, `tools/glyphs.py`). Messages name a command in braces, `{+jump}`, and show the button bound to it; the gatehouse teaches the dash, the wheel and Overpressure that way (`docs/screenshots/glyphs.jpg`).
- **Normal and gloss maps** on the world: ericw-tools' light also writes the direction light comes from at each lightmap sample, so stone and brick show their relief against the level's real lights and gloss catches them as you move (`docs/screenshots/normal-maps.jpg`).
- The Ashen, Censer-bearers, Deacons, slag hounds, the weapons and the pickups (health, ammunition, armour, keys, the backpack) are Cinderkirk's own; the powerups, the other monsters and some sounds are still **stand-ins from LibreQuake** (BSD-3) until Cinderkirk's own are made, and the game code is LibreQuake's QuakeC (GPL-2.0). The menus already use Cinderkirk's words: Story, Pit Fights, Apprentice to Bellfounder.
- Snap packaging for amd64 and arm64 (core24, strict), so it installs on Ubuntu and Ubuntu Core.

Next, from the idea's plan: the four shafts of the Foundry.

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

Controls: a controller just works (left stick moves, right stick or gyro looks, right trigger fires, A jumps, hold LB for the weapon wheel or tap it for the last weapon, RB changes weapon, the d-pad picks one). Keyboard and mouse are the usual WASD. Comfort settings are on by default: no view bob, roll or gun kick (`cinder/default.cfg`).

## Layout

| Path | What |
|---|---|
| `engine/` | The vkQuake fork (C, Vulkan, Meson) |
| `quakec/` | The game code, built with fteqcc into `build/progs.dat` |
| `maps_src/` | Levels in code: each `<map>.py` writes a `.map` (TrenchBroom opens it) with `tools/mapkit.py` |
| `assets_src/materials/` | Blender scripts that bake the world textures (`make textures`) |
| `assets_src/models/` | `creatures.py` builds, rigs, animates and skins the creatures in Blender and writes them as MD3 (`make models`; `PREVIEW=dir` adds a sheet of their frames); `weapons.py` builds the weapons the player holds, with the stoker's glove, the same way (`make -j8 weapons`, one Blender run each, side by side; `VIEWSHOT=dir` shows them from the eye, `WORLD=1` builds them as they lie on the floor); `pickups.py` builds health, ammunition, armour, keys and the backpack (`make -j8 pickups`, which also runs `weapons.py` with `WORLD=1`); `models.py` is the idea's mockup |
| `assets/models/` | The creatures and the view models (`v_*`) as the game loads them: `<name>.md3`, its skin and `_luma` glow, and `.frames` (the frame order their QuakeC lists) |
| `assets_src/fonts/` | Cinzel and Barlow Condensed, for the menus and the HUD |
| `assets/textures/` | The baked textures: `<name>.png`, `_luma`, and `_norm` and `_gloss`, which the renderer shades with the light's direction from each map's `.lux` (`r_normalmaps`, `r_glossmaps`) |
| `cinder/` | Loose game files: `default.cfg` (controls and comfort defaults) and `quake.rc` |
| `gfx/splash.png` | The LinuxGroove Games splash |
| `tools/` | The build's helpers: `wad.py` (texture WADs), `pak.py`, `menu_art.py`, `hud_svg.py` (the status bar and weapon wheel as SVG), `sfx.py` (the game's own sounds, synthesized), `make_icon.py`, `mapkit.py`, `deps.sh`, `tools.sh`, `librequake.sh`, `versions.sh` (every pinned version), `shoot.sh` (screenshots on a machine with no screen), `version.sh` |
| `snap/` | The snap: `snapcraft.yaml`, the launcher and the desktop file |
| `build/`, `dist/` | Made by `make`; `dist/` is the game, ready to run |

## How it's built

1. `tools/deps.sh` builds SDL 3, the Vulkan headers and loader (vkQuake needs 1.4.341) and `spirv-opt` into `build/prefix`; `tools/tools.sh` builds qbsp, vis, light and fteqcc into `build/bin`; `tools/librequake.sh` fetches LibreQuake's stand-ins at a pinned commit and compiles its little box models (the exploding barrels still use them).
2. The engine builds with Meson against `build/prefix`.
3. The QuakeC compiles to `build/progs.dat`.
4. `tools/wad.py` turns the baked textures into a small WAD for qbsp (128 px stand-ins, so a texture repeats every 128 units); the engine draws the full 1024 px PNGs from `textures/` in their place, with their `_luma` glow.
5. Each level script writes its `.map`, then qbsp, vis and light (`-extra4 -bounce -lit`) compile it.
6. `tools/menu_art.py` draws the menus, `tools/hud_svg.py` writes the HUD's SVG into `gfx/hud/`, and `tools/sfx.py` synthesizes the sounds; everything, with the creatures from `assets/models/` in `progs/`, goes into `dist/cinder/pak0.pak`.

Screenshots on a machine with no GPU: `VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json tools/shoot.sh /tmp/shot "20" +map start`, with `SPAWN="notarget; god; setpos X Y Z PITCH YAW 0"` to place the view.

## Licences

The engine and game code are GPL-2.0-or-later (`LICENSE`); see `CREDITS.md` for everything else. Nothing of id Software's Quake data is used.
