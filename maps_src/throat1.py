#!/usr/bin/env python3
"""The Throat (throat1.map), the first of the finale's two maps.

Under the Pithead's grate: the pit itself, a square well two hundred years
deep in the town's memory and two thousand units in fact, with a stair
round its walls down to the fire. Ash wraiths fill the air of it and the
congregation holds the landings. The silver key is in the old sounding
chamber off the second turn; the silver door at the bottom opens onto the
casting floor.

    python3 maps_src/throat1.py maps_src/throat1.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
SLAG = (1.0, 0.38, 0.1)
COLD = (0.62, 0.70, 0.95)
R = 512                             # the well's half width
W = 128                             # the stair's width
DROP = 256                          # each flight's fall
TURNS = 2
BOT = -DROP * 4 * TURNS             # the bottom ring


def corners():
    """The four corner landings in the order the stair visits them."""
    return [(-R, R - W), (R - W, R - W), (R - W, -R), (-R, -R)]       # NW, NE, SE, SW


def rail(L, x0, y0, x1, y1, z_from, z_to, axis):
    """A wall 40 high along a flight, from its z_from end (x0 or y0 as
    given, either way round) to its z_to end, in 64-unit lengths that step
    down with the stair."""
    a0, a1 = (x0, x1) if axis == "x" else (y0, y1)
    n = max(1, int(abs(a1 - a0) // 64))
    for k in range(n):
        t0, t1 = a0 + (a1 - a0) * k / n, a0 + (a1 - a0) * (k + 1) / n
        za, zb = z_from + (z_to - z_from) * k / n, z_from + (z_to - z_from) * (k + 1) / n
        top, base = max(za, zb) + 40, min(za, zb) - 16
        lo, hi = min(t0, t1), max(t0, t1)
        if axis == "x":
            L.solid(lo, min(y0, y1), base, hi, max(y0, y1), top, "iron_rust1")
        else:
            L.solid(min(x0, x1), lo, base, max(x0, x1), hi, top, "iron_rust1")


def build():
    L = Level(start_light=150, wad="cinder.wad", light_wait=0.6, sounds=8, message="The Throat", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=10, _range=0.6)

    L.room(-R, -R, BOT, R, R, 320, wall="vein_rock1", floor="vein_rock1", ceiling="kirk_vbrick1", floor_depth=64)
    L.add("info_player_start", (-R + 64, R - 64, 24), angle=0)
    L.add("info_player_coop", (-R + 64, R - 160, 24), angle=0)
    L.add("info_player_coop", (-R + 160, R - 64, 24), angle=0)
    L.light((-R + 64, R - 64, 200), 200, CANDLE)

    # The stair: flights along the walls between landings at each corner.
    z = 0
    order = corners()
    for turn in range(TURNS):
        for i in range(4):
            cx, cy = order[i]
            nx, ny = order[(i + 1) % 4]
            L.solid(cx, cy, z - 16, cx + W, cy + W, z, "kirk_stone1")             # the landing
            z2 = z - DROP
            if i == 0:          # east along the north wall
                L.steps(cx + W, cy, nx, cy + W, z, z2, axis="x", tex="kirk_stone1", base=z2 - 16)
            elif i == 1:        # south along the east wall
                L.steps(nx, ny + W, nx + W, cy, z2, z, axis="y", tex="kirk_stone1", base=z2 - 16)
            elif i == 2:        # west along the south wall
                L.steps(nx + W, ny, cx, ny + W, z2, z, axis="x", tex="kirk_stone1", base=z2 - 16)
            else:               # north along the west wall
                L.steps(nx, cy + W, nx + W, ny, z, z2, axis="y", tex="kirk_stone1", base=z2 - 16)
            # A low wall on the flight's well side, stepping down with it,
            # and a lamp over each landing.
            if i == 0:
                rail(L, cx + W, cy, nx, cy + 8, z, z2, "x")
            elif i == 1:
                rail(L, nx, cy, nx + 8, ny + W, z, z2, "y")
            elif i == 2:
                rail(L, cx, ny + W - 8, nx + W, ny + W, z, z2, "x")
            else:
                rail(L, nx + W - 8, cy + W, nx + W, ny, z, z2, "y")
            L.light((cx + W / 2, cy + W / 2, z + 110), 220, CANDLE)
            z = z2
    # The bottom: a ring of floor round the slag, where the fire shows.
    L.opening(-R + W, -R + W, BOT - 48, R - W, R - W, BOT)
    L.liquid(-R + W, -R + W, BOT - 48, R - W, R - W, BOT - 16, "*lava_slag1")
    for x in (-200, 200):
        for y in (-200, 200):
            L.light((x, y, BOT + 48), 380, SLAG)
    L.light((0, 0, BOT + 700), 500, EMBER)
    L.light((0, 0, -300), 400, COLD)

    # The sounding chamber off the second turn's south-east landing.
    sz = -DROP * 4 - DROP * 2
    L.opening(R, -R + 16, sz, R + 32, -R + 112, sz + 112)
    L.room(R + 32, -R - 64, sz, R + 352, -R + 192, sz + 192, wall="kirk_vbrick1", floor="floor_flag1", ceiling="kirk_stone1")
    L.solid(R + 160, -R + 32, sz, R + 256, -R + 96, sz + 48, "bronze1")
    L.add("item_key1", (R + 208, -R + 64, sz + 48), target="ash_wakes")
    L.light((R + 200, -R + 64, sz + 160), 220, EMBER)
    L.add("monster_deacon", (R + 280, -R + 140, sz + 24), angle=180)
    L.add("monster_ashen", (R + 120, -R - 20, sz + 24), angle=180)

    # The Throat's own: wraiths in the air, the congregation on the stair.
    for x, y, z in ((0, 0, -200), (200, -150, -600), (-150, 200, -900), (100, 100, -1300),
                    (-200, -150, -1600), (150, -200, -1900), (0, 250, -400)):
        L.add("monster_ash_wraith", (x, y, z), angle=180)
    L.add("monster_censer", (R - 64, R - 64, -DROP + 24), angle=270)
    L.add("monster_deacon", (R - 64, -R + 64, -DROP * 2 + 24), angle=180)
    L.add("monster_slag_hound", (-R + 64, -R + 64, -DROP * 3 + 24), angle=90)
    L.add("monster_slag_hound", (-R + 64, -R + 180, -DROP * 3 - 10), angle=90)
    L.add("monster_censer", (-R + 64, R - 64, -DROP * 4 + 24), angle=0)
    L.add("monster_ashen", (0, R - 64, -DROP * 4 - 104), angle=0)
    L.add("monster_ashen", (0, -R + 64, -DROP * 6 - 104), angle=0)
    L.add("monster_bell_ringer", (0, -R + 64, BOT + 24), angle=90)
    L.add("monster_crucible_brute", (R - 64, 0, BOT + 24), angle=180)
    L.add("monster_censer", (-220, -R + 64, BOT + 24), angle=90)

    L.add("item_shells", (-R + 64, R - 100, 0))
    L.add("item_health", (R - 64, R - 64, -DROP))
    L.add("item_rockets", (R - 64, -R + 64, -DROP * 2))
    L.add("item_health", (-R + 64, -R + 64, -DROP * 3))
    L.add("item_cells", (-R + 64, R - 64, -DROP * 4))
    L.add("item_armor2", (R - 64, R - 64, -DROP * 5))
    L.add("item_health", (-R + 64, -R + 64, -DROP * 7))
    L.add("item_spikes", (-R + 64, R - 64, BOT))
    L.add("item_health", (R - 64, R - 64, BOT), spawnflags=2)

    # The silver door at the bottom of the north wall, and the casting floor beyond.
    L.opening(-64, R, BOT, 64, R + 32, BOT + 128)
    L.brush_entity("func_door", [Box(-64, R, BOT, 64, R + 32, BOT + 128, "door_iron1")],
                   angle=-1, spawnflags=16, speed=60, wait=-1, lip=8, sounds=2)
    L.room(-96, R + 32, BOT, 96, R + 192, BOT + 192, wall="vein_rock1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((0, R + 112, BOT + 160), 160, EMBER)
    L.brush_entity("trigger_changelevel", [Box(-64, R + 64, BOT, 64, R + 160, BOT + 96, "trigger")], map="throat2")
    L.add("info_intermission", (-R + 64, R - 64, 260), mangle=(50, -45, 0))
    L.nook(864, -464, -1536, "e", ('item_armor2', 'item_health'), wall="vein_rock1", floor="vein_rock1")   # a secret behind cracked stone
    # Taking the key wakes the dead lying in the ash round it.
    L.add("monster_ashen", (480, -463, -1536 + 24), angle=4, spawnflags=64, targetname="ash_wakes")
    L.add("monster_ashen", (589, -356, -1536 + 24), angle=325, spawnflags=64, targetname="ash_wakes")
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "throat1.map")
    build().save(out)
    print(out)
