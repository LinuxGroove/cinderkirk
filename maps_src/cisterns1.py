#!/usr/bin/env python3
"""The Quench House (cisterns1.map), the Cisterns shaft's first map.

The cage comes down into the quench house, where castings were dropped
into tanks to cool: white tile gone yellow, iron tanks in a row, and a
floor that's sunk into the water below. The silver key is up on the
crane's gantry; the sluice gate it opens leads down to the long vault.

    python3 maps_src/cisterns1.py maps_src/cisterns1.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

WARM = (0.95, 0.80, 0.58)   # the lamps, paler in the damp
COLD = (0.62, 0.72, 1.0)
DAMP = (0.55, 0.85, 0.75)
CANDLE = (1.0, 0.8, 0.55)


def build():
    L = Level(wad="cinder.wad", light_wait=0.8, sounds=5, message="The Quench House", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    # The cage's landing, north of the house.
    L.room(-96, 640, 0, 96, 832, 192, wall="cist_tile1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (0, 760, 24), angle=270)
    L.add("info_player_coop", (48, 760, 24), angle=270)
    L.add("info_player_coop", (-48, 760, 24), angle=270)
    L.light((0, 736, 160), 180, WARM)
    L.opening(-64, 608, 0, 64, 640, 128)

    # The quench house: x -512..512, y -384..608. A tiled floor at 0 along the
    # north half; the south half has sunk into the water, which runs at -64.
    L.room(-512, -384, -256, 512, 608, 384, wall="cist_tile1", floor="cist_stone1", ceiling="ceil_timber1")
    L.solid(-512, 128, -256, 512, 608, 0, "cist_tile1")                # the floor that held
    L.liquid(-512, -384, -256, 512, 128, -64, "*cistern1")
    for x0, y0, x1, y1 in ((-512, -384, -384, 128), (384, -384, 512, 128)):   # ledges along the sides
        L.solid(x0, y0, -256, x1, y1, 0, "cist_stone1")
    L.steps(-64, 96, 64, 128, 0, -48, axis="y", tex="cist_stone1")       # a slip of step into the water
    # The tanks: four iron boxes in the water, their rims a hop apart.
    for x in (-288, -96, 96, 288):
        for b in ((x - 64, -256, x - 48, -128), (x + 48, -256, x + 64, -128),
                  (x - 48, -256, x + 48, -240), (x - 48, -144, x + 48, -128)):
            L.solid(b[0], b[1], -256, b[2], b[3], 16, "tank_iron1")
        L.liquid(x - 48, -240, -256, x + 48, -144, 0, "*water1")
        L.solid(x - 64, -256, 16, x + 64, -240, 24, "brass_trim1")
    # The gantry over the tanks, reached by the ladder-stair on the east ledge.
    L.solid(-448, -320, 192, 448, -224, 208, "iron_plate1")
    L.steps(400, 128, 496, 320, 0, 192, axis="y", tex="iron_plate1", base=0)
    L.solid(400, -224, 192, 496, 128, 208, "iron_plate1")                # the walk along the east side
    L.solid(-480, -384, 192, -288, -320, 208, "iron_plate1")             # out to the sluice gate
    L.add("item_key1", (-400, -272, 208))
    L.add("item_health", (-300, -272, 208))
    for x in (-320, 0, 320):
        L.solid(x - 2, -274, 208, x + 2, -270, 384, "iron_plate1")       # hangers
    # Copper pipes along the north wall, a gauge, and the quench tank's valve wheel.
    for z in (160, 192):
        L.solid(-512, 584, z, 512, 600, z + 16, "verdigris1")
    L.solid(-512, 560, 0, 512, 608, 32, "cist_lime1")                    # lime crust along the wall's foot

    L.add("weapon_supershotgun", (-200, 300, 0))
    L.add("item_shells", (200, 300, 0))
    L.add("item_spikes", (-440, -100, 0))
    L.add("item_health", (440, -100, 0))
    L.add("monster_gauger", (-300, 400, 24), angle=270)
    L.add("monster_gauger", (300, 200, 24), angle=180)
    L.add("monster_ashen", (-400, 0, 24), angle=90)
    L.add("monster_ashen", (420, -40, 24), angle=90)
    for x, y in ((-200, -40), (0, -340), (200, -40)):
        L.add("monster_leech", (x, y, -160), angle=90)
    L.add("monster_censer", (0, -280, 232), angle=90)

    for x in (-256, 256):
        for y in (-128, 384):
            L.solid(x - 8, y - 8, 288, x + 8, y + 8, 320, "lamp_amber1")
            L.solid(x - 2, y - 2, 320, x + 2, y + 2, 384, "iron_plate1")
            L.light((x, y, 264), 340, WARM)
    L.light((0, -150, -100), 260, DAMP)
    L.light((0, 0, 300), 300, COLD)

    # The sluice gate in the south wall, at the gantry's west end, and the
    # stair down behind it to the cage for the long vault.
    L.opening(-448, -416, 208, -320, -384, 336)
    L.brush_entity("func_door", [Box(-448, -416, 208, -320, -384, 336, "sluice_wood1")],
                   angle=-1, spawnflags=16, speed=60, wait=-1, lip=8, sounds=2)
    L.room(-480, -640, 208, -288, -416, 400, wall="cist_brick1", floor="iron_plate1", ceiling="cist_brick1")
    L.light((-384, -528, 360), 200, DAMP)
    L.brush_entity("trigger_changelevel", [Box(-448, -608, 208, -320, -480, 304, "trigger")], map="cisterns2")
    L.add("info_intermission", (400, 500, 300), mangle=(30, 225, 0))
    L.nook(512, -272, 0, "e", ('item_armor1', 'item_shells'), wall="cist_tile1", floor="cist_stone1")   # a secret behind cracked stone
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "cisterns1.map")
    build().save(out)
    print(out)
