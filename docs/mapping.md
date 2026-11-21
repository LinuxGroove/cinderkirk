# Making a level

Cinderkirk's own levels are Python (`maps_src/<map>.py`, built with `tools/mapkit.py`), but a level can just as well be drawn in [TrenchBroom](https://trenchbroom.github.io/) and dropped in as `maps_src/<map>.map`: `make` builds both kinds the same way, with the pinned ericw-tools.

## Setting up TrenchBroom

1. `make` once, then `make trenchbroom`. That writes `dist/trenchbroom/Cinderkirk/` (the game config, every entity as `Cinderkirk.fgd`, and the icon) and copies the texture WAD to `dist/cinder/cinder.wad`.
2. Copy `dist/trenchbroom/Cinderkirk/` into TrenchBroom's games folder: `~/.TrenchBroom/games/` on Linux (Preferences, Games, the folder button opens it).
3. In Preferences, Games, Cinderkirk, set the game path to this repository's `dist/` folder. TrenchBroom then reads `cinder/pak0.pak` for the creatures' and pickups' models.
4. New map, Cinderkirk, Valve format. In the Face inspector's material collections, add `dist/cinder/cinder.wad`.

Run `make trenchbroom` again whenever the game code gains an entity: the entity list is read from the `QUAKED` comments in `quakec/`.

## The rules a level keeps

- The player is 32 wide and 56 tall and steps 16.
- Textures come from the WAD, and their names say what they are. A hot liquid's name must start with `*lava` (`*lava_slag1`), or qbsp makes it water; `*water` and `*slime` are the others. `trigger`, `clip`, `skip` and `hint` work as usual.
- The WAD only fixes each texture's size in the world; the engine draws the 1024 px PNGs, normal and gloss maps over it. Keep glyph stones (`kirk_glyph1`) on their 64-unit grid.
- Powerups stand on a box that starts 24 below their origin: place them 24 above the floor, or they vanish at load.
- `worldspawn`'s `sounds` picks the music: 2 the Pithead, 3 the end of a map, 4 the Foundry, 5 the Cisterns, 6 the Kilns, 7 the Undervein, 8 the Throat, 9 the big fights, 10 Pit fights.
- Creatures take the usual skill flags (Not on Apprentice, Journeyman, Master or Founder's, Not in Pit fights). In Co-op Story the game adds more by itself, so don't add co-op only ones.
- A Story map ends with a `trigger_changelevel` whose `map` is the next one. A Pit fight arena needs several `info_player_deathmatch` and its name added to the Host a game list in `engine/Quake/menu.c`.

## Building and playing it

```sh
make                          # builds maps_src/<map>.map with the rest
make map MAP=<map> && make    # just that level, then the pak
make run ARGS="+map <map>"
make check                    # fails if any level leaks
```

qbsp's log is `build/maps/<map>.log`; a leak there also writes `build/maps/<map>.pts`, which TrenchBroom loads (File, Load Point File) to show the way out.
