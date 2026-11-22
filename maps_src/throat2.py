#!/usr/bin/env python3
"""The Casting Floor (throat2.map), the finale.

The floor the bell was cast on, built out over the pit on piers, with the
fire under it and the Throat in a square of open slag in the middle. The
cracked Great Bell hangs over that square on four chains, each held by a
brake on a dais at a corner of the floor. Nothing a stoker carries can hurt
the Throat: knock the four brakes off and the bell comes down on it.

    python3 maps_src/throat2.py maps_src/throat2.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
SLAG = (1.0, 0.38, 0.1)
COLD = (0.62, 0.70, 0.95)
R = 1024                            # the floor's half width
HOLE = 384                          # the open square's half width
LAKE = -320                         # the pit's floor, under the slag
TOP = 1344
DAIS = 48


def chain(L, x0, y0, x1, y1, z, every=20):
    """A chain of iron links from one point to another at a height, a link every so many units."""
    n = int(max(abs(x1 - x0), abs(y1 - y0)) // every)
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        y = y0 + (y1 - y0) * i / n
        w, h = (6, 10) if i % 2 else (10, 6)      # links alternate flat and upright
        L.solid(round(x - w), round(y - w), z - h, round(x + w), round(y + w), z + h, "iron_rust1")


def build():
    L = Level(wad="cinder.wad", light_wait=0.45, sounds=9, message="The Casting Floor", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=16, _range=0.6)

    # In from the Throat's stair, on the south side.
    L.room(-96, -R - 224, 0, 96, -R - 32, 192, wall="vein_rock1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (0, -R - 160, 24), angle=90)
    L.add("info_player_coop", (-48, -R - 160, 24), angle=90)
    L.add("info_player_coop", (48, -R - 160, 24), angle=90)
    L.light((0, -R - 128, 160), 160, EMBER)
    L.opening(-64, -R - 32, 0, 64, -R, 128)
    L.brush_entity("trigger_once", [Box(-64, -R - 120, 0, 64, -R - 40, 96, "trigger")],
                   message="The casting floor. Nothing you carry will stop the Throat.\nKnock the four brakes off the bell's chains.")

    L.room(-R, -R, LAKE, R, R, TOP, wall="firebrick1", floor="vein_rock1", ceiling="iron_rust1")
    L.liquid(-R, -R, LAKE, R, R, LAKE + 64, "*lava_slag1")
    # The floor, out over the slag round the open square, on its piers.
    for x0, y0, x1, y1 in ((-R, HOLE, R, R), (-R, -R, R, -HOLE), (-R, -HOLE, -HOLE, HOLE), (HOLE, -HOLE, R, HOLE)):
        L.solid(x0, y0, -16, x1, y1, 0, "iron_plate1")
    for x in (-HOLE - 64, HOLE):
        for y in (-HOLE - 64, HOLE):
            L.solid(x, y, LAKE, x + 64, y + 64, -16, "firebrick1")
    L.solid(-HOLE - 16, -HOLE - 16, 0, HOLE + 16, -HOLE, 12, "iron_rust1")       # a lip round the square
    L.solid(-HOLE - 16, HOLE, 0, HOLE + 16, HOLE + 16, 12, "iron_rust1")
    L.solid(-HOLE - 16, -HOLE, 0, -HOLE, HOLE, 12, "iron_rust1")
    L.solid(HOLE, -HOLE, 0, HOLE + 16, HOLE, 12, "iron_rust1")
    # Moulds and ingots left about the floor, for cover from its iron.
    for x, y in ((-620, -200), (620, 220), (-200, 640), (240, -640), (-640, 560), (640, -560)):
        L.solid(x - 64, y - 48, 0, x + 64, y + 48, 96, "sand_mould1")
    for x, y in ((-560, 260), (560, -260)):
        L.solid(x - 96, y - 24, 0, x + 96, y + 24, 32, "iron_rust1")

    # The bell and the Throat; the bell's four chains run under the roof
    # from the drum over it out to the brakes' rods.
    L.solid(-64, -64, TOP - 112, 64, 64, TOP, "iron_rust1")
    L.solid(-80, -80, TOP - 124, 80, 80, TOP - 112, "iron_plate1")
    for sx in (-1, 1):
        for sy in (-1, 1):
            chain(L, sx * 64, sy * 64, sx * 784, sy * 784, TOP - 72)
    L.add("misc_great_bell", (0, 0, 1100), targetname="bell", height=760, dmg=0)
    L.add("monster_throat", (0, 0, LAKE + 64 + 16))

    # The four brakes: a dais at each corner, a rod up to the roof, the
    # brake on the rod's inner face; each knocked off drops the bell and
    # opens a door in the wall behind it.
    k = 0
    for sx in (-1, 1):
        for sy in (-1, 1):
            k += 1
            cx, cy = sx * 800, sy * 800
            L.solid(cx - 128, cy - 128, 0, cx + 128, cy + 128, DAIS, "crypt_stone1")
            ix = cx - 128 * sx                                  # the dais's inner edge, and steps up to it
            if sx > 0:
                L.steps(ix - 48, cy - 96, ix, cy + 96, 0, DAIS, axis="x", tex="crypt_stone1")
            else:
                L.steps(ix, cy - 96, ix + 48, cy + 96, DAIS, 0, axis="x", tex="crypt_stone1")
            L.solid(cx - 16, cy - 16, DAIS, cx + 16, cy + 16, TOP, "iron_rust1")
            bx = cx - sx * 16 - (12 if sx > 0 else 0)
            L.brush_entity("func_button", [Box(bx, cy - 24, DAIS + 40, bx + 12, cy + 24, DAIS + 104, "iron_plate1")],
                           angle=0 if sx > 0 else 180, target="brake%d" % k, wait=-1, lip=4, sounds=3,
                           message="A brake is off, and the bell drops")
            L.add("trigger_relay", None, targetname="brake%d" % k, target="bell")
            L.light((cx - sx * 80, cy - sy * 80, DAIS + 150), 260, CANDLE)
            # The door in the side wall behind the dais, and what waits there.
            wy0, wy1 = cy - 64, cy + 64
            wx = R if sx > 0 else -R - 32
            L.opening(wx, wy0, 0, wx + 32, wy1, 128)
            L.brush_entity("func_door", [Box(wx, wy0, 0, wx + 32, wy1, 128, "door_iron1")],
                           angle=-1, targetname="brake%d" % k, speed=100, wait=-1, lip=8, sounds=2)
            ax0 = R + 32 if sx > 0 else -R - 288
            L.room(ax0, wy0 - 64, 0, ax0 + 256, wy1 + 64, 160, wall="kirk_vbrick1", floor="floor_flag1", ceiling="kirk_stone1")
            L.light((ax0 + 128, cy, 130), 160, EMBER)
            ax = ax0 + 128
            if k == 1:
                L.add("monster_deacon", (ax, cy - 40, 24), angle=0)
                L.add("monster_ashen", (ax, cy + 50, 24), angle=0)
            elif k == 2:
                L.add("monster_slag_hound", (ax, cy - 50, 24), angle=0)
                L.add("monster_slag_hound", (ax, cy + 50, 24), angle=0)
            elif k == 3:
                L.add("monster_censer", (ax, cy - 50, 24), angle=180)
                L.add("monster_crucible_brute", (ax + 40, cy + 40, 24), angle=180)
            else:
                L.add("monster_deacon", (ax, cy - 40, 24), angle=180)
                L.add("monster_censer", (ax, cy + 50, 24), angle=180)

    for x, y, z in ((-500, 0, 500), (500, 0, 600), (0, 600, 450), (0, -600, 550)):
        L.add("monster_ash_wraith", (x, y, z), angle=270)
    # Two censer-bearers guard brakes, at the daises' outer corners: one on a
    # rod stuck in it and jammed the brake's button, so the game couldn't end.
    L.add("monster_censer", (-880, 880, DAIS + 24), angle=315)
    L.add("monster_censer", (880, -880, DAIS + 24), angle=135)

    L.add("item_health", (-120, -R + 80, 0), spawnflags=2)
    L.add("item_armorInv", (120, -R + 80, 0))
    for x, y in ((-900, 0), (900, 0), (0, 900), (-900, -500), (900, 500)):
        L.add("item_health", (x, y, 0))
    for x, y in ((-700, -900), (700, 900)):
        L.add("item_rockets", (x, y, DAIS))                         # on the daises
        L.add("item_cells", (x + 100, y, DAIS))
    for x, y in ((-900, 400), (900, -400)):
        L.add("item_spikes", (x, y, 0))
        L.add("item_shells", (x, y + 80, 0))

    for x in (-HOLE, HOLE):
        for y in (-HOLE, HOLE):
            L.light((x * 0.6, y * 0.6, -40), 300, SLAG)       # above the slag, so what hangs over it isn't lit from the pit's floor
    for x in (-700, 0, 700):
        for y in (-700, 0, 700):
            if x or y:
                L.light((x, y, 220), 340, CANDLE)
    L.light((-700, 0, 700), 260, COLD)
    L.light((700, 0, 700), 260, COLD)
    L.add("info_intermission", (-760, -760, 520), mangle=(20, 45, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "throat2.map")
    build().save(out)
    print(out)
