#!/usr/bin/env python3
"""The Flowstone Stair (cisterns4.map), the Cisterns shaft's fourth map.

A square well a thousand feet of lime has grown over: four flights run down
its walls, one to a side, from the cage at the top to a pool at the bottom.
The gold key lies in the pool among the leeches; the gold gate out is in the
east wall at the foot.

    python3 maps_src/cisterns4.py maps_src/cisterns4.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

LAMP = (0.95, 0.80, 0.58)
COLD = (0.62, 0.72, 1.0)
DAMP = (0.55, 0.85, 0.75)
CANDLE = (1.0, 0.8, 0.55)
R, W = 384, 128          # the well's half width, and a flight's width
BOTTOM, TOP = -1024, 0


def build():
    L = Level(wad="cinder.wad", light_wait=1.0, sounds=5, message="The Flowstone Stair", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=14, _range=0.6)

    # The cage, north of the top landing.
    L.room(-R, R + 32, TOP, -R + W, R + 192, TOP + 192, wall="cist_lime1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-R + 64, R + 120, TOP + 24), angle=270)
    L.add("info_player_coop", (-R + 32, R + 140, TOP + 24), angle=270)
    L.add("info_player_coop", (-R + 96, R + 140, TOP + 24), angle=270)
    L.light((-R + 64, R + 112, TOP + 160), 160, LAMP)
    L.opening(-R, R, TOP, -R + W, R + 32, TOP + 128)

    # The well, with a pool cut into its floor.
    L.room(-R, -R, BOTTOM, R, R, 256, wall="cist_lime1", floor="cist_stone1", ceiling="cist_stone1",
           floor_depth=96)
    L.opening(-192, -192, BOTTOM - 72, 192, 192, BOTTOM)
    L.liquid(-192, -192, BOTTOM - 72, 192, 192, BOTTOM - 8, "*cistern1")
    for x0, y0, x1, y1 in ((-208, -208, 208, -192), (-208, 192, 208, 208),
                           (-208, -192, -192, 192), (192, -192, 208, 192)):
        L.solid(x0, y0, BOTTOM, x1, y1, BOTTOM + 16, "cist_drain1")       # the pool's kerb

    # The landings in the corners and the flights between them: north wall
    # east, east wall south, south wall west, west wall north to the floor.
    a, b = -R + W, R - W
    L.solid(-R, b, TOP - 32, a, R, TOP, "cist_stone1")                       # the top landing
    L.solid(b, b, -288, R, R, -256, "cist_stone1")
    L.solid(b, -R, -544, R, a, -512, "cist_stone1")
    L.solid(-R, -R, -800, a, a, -768, "cist_stone1")
    L.steps(a, b, b, R, TOP, -256, axis="x", tex="cist_stone1", base=-288)
    L.steps(b, a, R, b, -512, -256, axis="y", tex="cist_stone1", base=-544)
    L.steps(a, -R, b, a, -768, -512, axis="x", tex="cist_stone1", base=-800)
    L.steps(-R, a, a, b, -768, BOTTOM, axis="y", tex="cist_stone1", base=BOTTOM)
    # Flowstone: lime curtains hanging under each flight, and the column in
    # the middle where the drip comes down.
    for x0, y0, x1, y1, z in ((a + 64, R - 48, b - 64, R, -320), (R - 48, a + 64, R, b - 64, -576),
                              (a + 64, -R, b - 64, -R + 48, -832)):
        L.solid(x0, y0, z - 96, x1, y1, z, "cist_lime1")
    L.solid(-40, -40, 128, 40, 40, 256, "cist_lime1")
    L.solid(-24, -24, 64, 24, 24, 128, "cist_lime1")
    L.solid(-48, -48, BOTTOM - 72, 48, 48, BOTTOM + 96, "cist_lime1")
    L.solid(-24, -24, BOTTOM + 96, 24, 24, BOTTOM + 192, "cist_lime1")

    # Light: a lamp on each landing, cold light from the top, the pool's glow.
    for x, y, z in ((-R + 64, R - 64, TOP), (R - 64, R - 64, -256), (R - 64, -R + 64, -512),
                    (-R + 64, -R + 64, -768), (-R + 64, R - 64, BOTTOM)):
        L.light((x, y, z + 96), 300, CANDLE)
    for x, y, z in ((0, R - 96, -64), (R - 96, 0, -320), (0, -R + 96, -576), (-R + 96, 0, -832)):
        L.light((x, y, z), 320, LAMP)                                       # over each flight
    for z in (-128, -384, -640, -896):
        L.light((120, 120, z), 360, LAMP)
    L.light((100, -100, 200), 500, COLD)
    L.light((120, -120, BOTTOM + 24), 260, DAMP)

    # The congregation, a few on every flight and the leeches in the pool.
    L.add("monster_ashen", (100, R - 64, -120), angle=180)
    L.add("monster_censer", (-100, R - 64, -10), angle=180)
    L.add("monster_gauger", (R - 64, R - 64, -220), angle=270)
    L.add("monster_ashen", (R - 64, 0, -320), angle=90)
    L.add("monster_clinker", (R - 64, -100, 240), spawnflags=2)
    L.add("monster_gauger", (R - 64, -R + 64, -476), angle=180)
    L.add("monster_slag_hound", (0, -R + 64, -570), angle=0)
    L.add("monster_censer", (-150, -R + 64, -650), angle=0)
    L.add("monster_crucible_brute", (-R + 64, -R + 64, -740), angle=90)
    L.add("monster_ashen", (-R + 64, 0, -850), angle=270)
    for x, y in ((-100, -100), (100, -100), (100, 100), (-100, 120)):
        L.add("monster_leech", (x, y, BOTTOM - 40), angle=90)
    L.add("monster_deacon", (250, 0, BOTTOM + 24), angle=180)

    L.add("item_key2", (120, 60, BOTTOM - 64))
    L.add("item_health", (-R + 64, R - 64, TOP))
    L.add("item_shells", (R - 64, R - 64, -256))
    L.add("item_health", (R - 64, -R + 64, -512))
    L.add("item_spikes", (-R + 64, -R + 64, -768))
    L.add("item_rockets", (-R + 64, R - 64, BOTTOM))
    L.add("item_armor1", (-R + 32, -R + 32, -768))

    # The gold gate in the east wall at the foot, and the cage on.
    L.opening(R, -64, BOTTOM, R + 32, 64, BOTTOM + 128)
    L.brush_entity("func_door", [Box(R, -64, BOTTOM, R + 32, 64, BOTTOM + 128, "sluice_wood1")],
                   angle=-1, spawnflags=8, speed=60, wait=-1, lip=8, sounds=2)
    L.room(R + 32, -96, BOTTOM, R + 192, 96, BOTTOM + 192, wall="cist_lime1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((R + 112, 0, BOTTOM + 160), 160, LAMP)
    L.brush_entity("trigger_changelevel", [Box(R + 64, -64, BOTTOM, R + 160, 64, BOTTOM + 96, "trigger")],
                   map="cisterns5")
    L.add("info_intermission", (-300, 300, 200), mangle=(45, -45, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "cisterns4.map")
    build().save(out)
    print(out)
