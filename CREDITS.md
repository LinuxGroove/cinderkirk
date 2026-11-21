# Credits

Made by Drew, Kaden, and Ken VanDine, the LinuxGroove team.

Copyright © 2026 The LinuxGroove team. Cinderkirk's own code is under the GNU General Public License, version 2 or later (see `LICENSE`), as the engine and game code it grows from are.

## The engine

- **vkQuake** 1.37.0 by Axel Gneiting and contributors (GPL-2.0-or-later), from QuakeSpasm, FitzQuake and id Software's GPL release of Quake. The fork in `engine/` lists its changes in `engine/CINDERKIRK.md`.
- Gyro aiming, flick stick, rumble and blended order-independent transparency came to vkQuake from **Ironwail** by Andrei Drexler.
- **SDL 3** (zlib licence) and the **Vulkan loader** (Apache-2.0), built from source and shipped with the snap.

## The game code

- `quakec/` starts from **LibreQuake**'s QuakeC (GPL-2.0), which builds on id Software's GPL QuakeC.

## Art and sound

- World textures, the menu art, the console background, the icon and the first level are Cinderkirk's own, made for it in Blender and Python (`assets_src/`, `tools/`, `maps_src/`).
- Button glyphs from **Kenney**'s Input Prompts (CC0, www.kenney.nl), in `assets/glyphs/`.
- Stand-ins until Cinderkirk's own are made: the powerup models, the monsters Cinderkirk hasn't replaced yet, sounds, the classic status bar (HUD Style Classic), small fonts are from **LibreQuake** (BSD-3-Clause, see `build/librequake/COPYING.LibreQuake` after a build), fetched at a pinned commit by `tools/librequake.sh` and never stored here.
- **nanosvg** by Mikko Mononen (zlib licence, `engine/Quake/nanosvg/LICENSE.txt`) draws the HUD.
- Menu and HUD lettering in **Cinzel** by Natanael Gama (SIL Open Font License 1.1, `assets_src/fonts/OFL-Cinzel.txt`).
- Help text and the HUD's numbers in **Barlow Condensed** by The Barlow Project Authors (SIL Open Font License 1.1, `assets_src/fonts/OFL-BarlowCondensed.txt`).
- The LinuxGroove Games splash (`gfx/splash.png`) is shared by every LinuxGroove game.

## Tools

- **ericw-tools** (qbsp, vis, light) by Eric Wasylishen and contributors, and **fteqcc** from FTEQW, build the levels and game code. Neither is shipped.

Nothing from id Software's Quake data (its maps, textures, models, sounds or name) is in this repository or the game.
