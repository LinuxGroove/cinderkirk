# Cinderkirk

A first person shooter in the old style on a vkQuake fork, with QuakeC game code and levels compiled by ericw-tools. The concept is idea 25 in [game-ideas](https://github.com/LinuxGroove/game-ideas/blob/main/ideas/25-cinderkirk.md). Unlike the other LinuxGroove games it is **not Godot** and doesn't use the shared add-on; see the README for the layout and how the build works.

## Commands

```sh
make                       # engine, progs.dat, levels, dist/cinder/pak0.pak (first run builds the deps)
make run ARGS="+map start" # play from the Pithead (+map foundry1 for the Foundry Gate)
make map MAP=start         # one level again
make check                 # scripts compile, no level leaks, nothing the game drops at load (tools/spawncheck.py)
make playtest              # with a GPU, not in CI: every level and the finale played unattended (PLAYTEST="--maps throat2"); build/playtest/report.md
make textures              # bake the world textures in Blender (BLENDER=..., TEXRES=2048 for more)
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json tools/shoot.sh /tmp/shot "3 20" +map start   # screenshots with no GPU
SPAWN="notarget; god; noclip; setpos 700 -300 250 35 20 0" tools/shoot.sh /tmp/shot "20" +map foundry1  # from a chosen view (one at a time: runs share a spawn file)
```

Run `make` and `make check` before every commit, and look at a screenshot after changing a level or anything you can see. On lavapipe the first frames take a few seconds; the engine sometimes crashes inside Mesa's shader compiler on a cold shader cache, so run it again before suspecting the game.

## Rules

- **Nothing from id's Quake data**: no maps, textures, models, sounds, names or logos. LibreQuake (BSD-3) is the only stand-in source, fetched at the commit in `tools/versions.sh`, never committed. vkQuake's built-in pak had id's logo in the console background; keep it out.
- **Every version is pinned** in `tools/versions.sh`; change versions there only.
- **Levels are code** for now: a level is `maps_src/<map>.py` building a `mapkit.Level` (rooms as air carved from shells, `opening`, `solid`, `steps`, `liquid`, entities). X east, Y north, Z up; the player is 32 wide and 56 tall, steps 16. Keep glyph stones and other single-motif textures on the grid of their WAD size (`WAD_SIZES` in the Makefile).
- **Textures**: names are 15 characters at most, liquids start with `*` in maps and `#` on disk. The WAD only fixes each texture's size in the world; the engine draws the PNG.
- **Engine changes** are listed in `engine/CINDERKIRK.md`; keep that table current, and mark anything vkQuake could take upstream.
- **Comfort** (Ken gets motion sick): no view bob, roll, gun kick or camera shake by default (`cinder/default.cfg`).
- **Controller first**: every action works on a pad; the keyboard and mouse always work too.
- Player-facing text is plain and short, in the game's words (the Foundry, the Pit, Story, Pit Fights, stokers, slag).

## Releases

Pushing to `main` builds the snap for amd64 and arm64 in `snap.yml`; publishing to the store waits on the `cinderkirk` name being registered, the `STORE_LOGIN` secret and the `PUBLISH_SNAP` variable. Versions come from `tools/version.sh` (`vYYYY.WW.MINOR` tags, as the other games).
