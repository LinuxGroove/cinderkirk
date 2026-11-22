#!/usr/bin/env python3
"""The Calcining Floor (kilns5.map), the end of the Ossuary Kilns shaft.

The kilns' last hall, where the bone ash was burned white for the bell:
a floor of hot ash round a great calciner, slag trenches across it, and
two bell-ringers tolling. The Kiln Seal lies in the calciner under a
bronze cope; break the two dampers, on the north and south galleries, and
the cope lifts. Taking the Seal opens the gate home.

    python3 maps_src/kilns5.py maps_src/kilns5.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)
X1, Y = 1792, 768
CX = 896                            # the calciner's middle
GAL = 192                           # the galleries' height


def build():
    L = Level(wad="cinder.wad", light_wait=0.7, sounds=6, message="The Calcining Floor", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=12, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, CANDLE)
    L.opening(-32, -64, 0, 0, 64, 128)

    L.room(0, -Y, 0, X1, Y, 704, wall="kiln_brick1", floor="ash_floor1", ceiling="ceil_timber1", floor_depth=64)
    # Slag trenches across the floor, east and west of the calciner, each
    # with a bridge.
    for x in (448, 1344):
        L.opening(x - 48, -Y + 160, -48, x + 48, Y - 160, 0)
        L.liquid(x - 48, -Y + 160, -48, x + 48, Y - 160, -16, "*lava_slag1")
        L.solid(x - 64, -64, -8, x + 64, 64, 8, "iron_plate1")
        for y in (-300, 300):
            L.light((x, y, 24), 220, EMBER)
    # The galleries along the north and south walls, the stairs up at the
    # west end, and the dampers at their middles.
    for s in (-1, 1):
        y0, y1 = (Y - 160, Y) if s > 0 else (-Y, -Y + 160)
        L.solid(160, y0, GAL - 16, X1 - 160, y1, GAL, "iron_plate1")
        ry = y0 if s > 0 else y1 - 8
        L.solid(160, ry, GAL, X1 - 160, ry + 8, GAL + 32, "brass_trim1")
        L.steps(0, y0, 160, y1, 0, GAL, axis="x", tex="crypt_stone1")
        wy = Y - 12 if s > 0 else -Y
        L.brush_entity("func_button", [Box(CX - 48, wy, GAL + 32, CX + 48, wy + 12, GAL + 112, "iron_rust1")],
                       angle=90 if s > 0 else 270, target="dampers", wait=-1, lip=4,
                       message=f"The {'north' if s > 0 else 'south'} damper falls open")
        L.light((CX, wy + (-56 if s > 0 else 68), GAL + 130), 200, CANDLE)
    L.add("trigger_counter", None, targetname="dampers", count=2, spawnflags=1,
          target="cope", message="The calciner draws, and the cope lifts")

    # The calciner: a brick drum open on four sides, the Seal on its hearth
    # under the cope, a flue to the roof.
    for x0, y0, x1, y1 in ((CX - 192, -192, CX - 64, -160), (CX + 64, -192, CX + 192, -160),
                           (CX - 192, 160, CX - 64, 192), (CX + 64, 160, CX + 192, 192),
                           (CX - 192, -160, CX - 160, -64), (CX - 192, 64, CX - 160, 160),
                           (CX + 160, -160, CX + 192, -64), (CX + 160, 64, CX + 192, 160)):
        L.solid(x0, y0, 0, x1, y1, 256, "kiln_brick1")
    L.solid(CX - 192, -192, 256, CX + 192, 192, 288, "kiln_brick1")
    L.solid(CX - 96, -96, 288, CX + 96, 96, 704, "kiln_brick1")
    L.solid(CX - 128, -128, 0, CX + 128, 128, 24, "crypt_stone1")
    cope = [Box(CX - 64, -80, 24, CX - 48, 80, 152, "bronze1"),
            Box(CX + 48, -80, 24, CX + 64, 80, 152, "bronze1"),
            Box(CX - 48, -80, 24, CX + 48, -64, 152, "bronze1"),
            Box(CX - 48, 64, 24, CX + 48, 80, 152, "bronze1"),
            Box(CX - 64, -80, 152, CX + 64, 80, 168, "bronze1")]
    L.brush_entity("func_door", cope, angle=-1, targetname="cope", speed=40, wait=-1, lip=64, sounds=2)
    L.add("item_sigil", (CX, 0, 48), spawnflags=4)
    L.light((CX, 0, 200), 260, EMBER)
    for x, y in ((CX - 240, 0), (CX + 240, 0), (CX, -240), (CX, 240)):
        L.light((x, y, 120), 220, EMBER)

    for x in range(192, X1, 384):
        for y in (-Y + 80, Y - 80):
            L.light((x, y, GAL + 120), 280, CANDLE)
            L.light((x, y * 0.6, 120), 240, CANDLE)
    L.light((CX + 320, 0, 640), 500, COLD)
    L.light((CX - 320, 0, 640), 400, COLD)

    L.add("monster_bell_ringer", (CX - 400, 300, 24), angle=0)
    L.add("monster_bell_ringer", (CX + 400, -300, 24), angle=180)
    for x, y, z in ((300, -400, 300), (1500, 400, 300), (CX, 500, 420), (CX, -500, 420)):
        L.add("monster_ash_wraith", (x, y, z), angle=180)
    L.add("monster_censer", (1200, Y - 80, GAL + 24), angle=180)
    L.add("monster_censer", (600, -Y + 80, GAL + 24), angle=0)
    L.add("monster_gauger", (1500, -Y + 80, GAL + 24), angle=180)
    L.add("monster_deacon", (CX + 260, 0, 24), angle=180, spawnflags=1)

    L.add("item_health", (96, 300, 0), spawnflags=2)
    L.add("item_shells", (96, -300, 0))
    L.add("item_rockets", (600, Y - 80, GAL))
    L.add("item_spikes", (1200, -Y + 80, GAL))
    L.add("item_health", (1500, Y - 80, GAL))
    L.add("item_cells", (300, -Y + 80, GAL))
    L.add("item_armor2", (1700, 0, 0))
    L.add("item_health", (700, 0, 0))
    L.add("item_health", (1100, 0, 0))

    # The gate home, opened by the cope.
    L.opening(X1, -64, 0, X1 + 32, 64, 128)
    L.brush_entity("func_door", [Box(X1, -64, 0, X1 + 32, 64, 128, "door_iron1")],
                   angle=-1, targetname="cope", speed=80, wait=-1, lip=8)
    L.room(X1 + 32, -96, 0, X1 + 192, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((X1 + 112, 0, 160), 160, CANDLE)
    L.brush_entity("trigger_changelevel", [Box(X1 + 64, -64, 0, X1 + 160, 64, 96, "trigger")], map="start")
    L.add("info_intermission", (100, -650, 450), mangle=(25, 25, 0))
    L.nook(1792, 656, 0, "e", ('item_health', 'item_rockets'), wall="crypt_stone1", floor="crypt_stone1")   # a secret behind cracked stone
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "kilns5.map")
    build().save(out)
    print(out)
