#!/usr/bin/env python3
"""The Ash Pit (foundry_s.map), the Foundry shaft's secret map, reached through
the cracked wall behind the Furnace Row's coal store.

Where the furnaces dump their ash: a deep pit of it under clinker pillars,
glowing where the embers still live, with a slag hound pack that dens there.
A ledge round the top holds the Forge Heart; the way out climbs the ash
heaps at the far end to the cage down to the bell pit.

    python3 maps_src/foundry_s.py maps_src/foundry_s.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

WARM = (1.0, 0.62, 0.32)
SLAG = (1.0, 0.42, 0.12)
COLD = (0.62, 0.72, 1.0)
CANDLE = (1.0, 0.8, 0.55)


def build():
    L = Level(wad="cinder.wad", light_wait=0.6, sounds=4, message="The Ash Pit", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=4, _range=0.6)

    # The chute you came down, ending on a ledge above the pit.
    L.room(0, -96, 192, 192, 96, 384, wall="kirk_stone1", floor="ash_floor1", ceiling="kirk_brick2")
    L.add("info_player_start", (64, 0, 216), angle=0)
    L.add("info_player_coop", (64, 48, 216), angle=0)
    L.add("info_player_coop", (64, -48, 216), angle=0)
    L.light((96, 0, 340), 160, CANDLE)
    L.opening(192, -64, 192, 224, 64, 320)

    # The pit: x 224..1248, y -512..512, ash at 0, the ledges at 192, roof 640.
    L.room(224, -512, 0, 1248, 512, 640, wall="kirk_brick2", floor="ash_floor1", ceiling="kirk_brick2")
    L.solid(224, -96, 0, 352, 96, 192, "kirk_stone1")                       # the landing below the chute
    L.steps(352, -64, 544, 64, 192, 0, base=0)
    for y0, y1 in ((-512, -416), (416, 512)):                               # ledges round the top
        L.solid(224, y0, 0, 1248, y1, 192, "kirk_stone1")
    for x, y in ((512, -224), (768, 192), (960, -160), (640, 32)):          # clinker pillars
        L.solid(x, y, 0, x + 96, y + 96, 640, "kirk_vbrick1")
    for x, y, h in ((448, 288, 32), (864, -352, 24), (1056, 256, 40), (704, -96, 16)):   # ash heaps with embers in them
        L.solid(x, y, 0, x + 128, y + 96, h, "ash_floor1")
        L.add("light", (x + 64, y + 48, h + 24), light=140, _color=SLAG)
    # The far end: heaps that climb to the ledge, and the cage.
    L.steps(1056, -96, 1248, 96, 0, 192, base=0, tex="ash_floor1")
    L.solid(1248 - 64, -416, 0, 1248, 416, 192, "kirk_stone1")
    L.opening(1248, -64, 192, 1280, 64, 320)
    L.room(1280, -96, 192, 1408, 96, 384, wall="iron_rust1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((1344, 0, 320), 160, WARM)
    L.brush_entity("trigger_changelevel", [Box(1312, -64, 192, 1392, 64, 288, "trigger")], map="foundry4")
    # Steps from the floor to the north ledge, and the Forge Heart at its end.
    L.steps(1120, 256, 1184, 416, 0, 192, axis="y", base=0, tex="kirk_stone1")
    L.add("item_artifact_super_damage", (360, 464, 192 + 24))       # powerups stand 24 over the floor
    L.add("item_health", (300, 464, 192), spawnflags=2)
    L.add("item_spikes", (300, -464, 192))
    L.add("item_rockets", (600, -464, 192))
    L.add("item_shells", (900, -464, 192))
    L.add("item_armor2", (1000, 464, 192))
    L.add("weapon_grenadelauncher", (700, 0, 0))
    for i, (x, y) in enumerate(((600, -300), (850, 0), (1000, -300), (1100, 100))):
        L.add("monster_slag_hound", (x, y, 24), angle=180)
    for x, y in ((600, -40), (700, -300), (900, 200), (900, -100)):
        L.add("monster_clinker", (x, y, 24), angle=180, spawnflags=2)
    L.add("monster_censer", (800, 460, 216), angle=270)
    L.add("monster_censer", (1100, -460, 216), angle=90)
    L.add("monster_deacon", (980, 40, 24), angle=180)
    for x in (400, 800, 1150):
        L.light((x, 0, 560), 380, COLD)
        L.light((x, -464, 300), 200, CANDLE)
        L.light((x, 464, 300), 200, CANDLE)
    L.add("info_intermission", (300, -400, 400), mangle=(30, 30, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "foundry_s.map")
    build().save(out)
    print(out)
