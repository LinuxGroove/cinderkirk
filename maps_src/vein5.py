#!/usr/bin/env python3
"""The Founder's Mould (vein5.map), the end of the Undervein shaft.

The pit at the bottom of the vein where the Founder cast the bell from the
pit's own iron, and where he has stood since in his last mould. The casting
floor is round his pit; slag channels run along the walls, and four piers
hold the roof. The Vein Seal lies under a bronze cope in the east niche;
it lifts when the Founder dies, and so does the gate home.

    python3 maps_src/vein5.py maps_src/vein5.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402
from mine import PROP, lamp, timbers  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)
X1, Y, H = 1664, 768, 640
CX = 960                             # the casting pit's middle


def build():
    L = Level(wad="cinder.wad", message="The Founder's Mould", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=12, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="ore_rock1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, CANDLE)
    L.opening(-32, -64, 0, 0, 64, 128)
    # A short drift, so he's heard before he's seen.
    L.room(0, -96, 0, 320, 96, 160, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    timbers(L, 0, 320, -96, 96, 0, 160, every=128)
    lamp(L, 160, 0, 126)
    L.opening(320, -24, 0, 352, 24, 112)        # a squeeze he can't follow you through

    # The casting floor.
    L.room(352, -Y, 0, X1, Y, H, wall="vein_rock1", floor="sand_mould1", ceiling="ore_rock1", floor_depth=64)
    # Slag channels along the north and south walls.
    for s in (-1, 1):
        y0, y1 = (Y - 96, Y) if s > 0 else (-Y, -Y + 96)
        L.opening(352, y0, -48, X1, y1, 0)
        L.liquid(352, y0, -48, X1, y1, -16, "*slag1")
        for x in range(480, X1, 320):
            L.light((x, (y0 + y1) / 2, 40), 260, EMBER)
    # The casting pit's rim, low enough to step over, round where he stands.
    for x0, y0, x1, y1 in ((CX - 256, -256, CX + 256, -224), (CX - 256, 224, CX + 256, 256),
                           (CX - 256, -224, CX - 224, -64), (CX - 256, 64, CX - 224, 224),
                           (CX + 224, -224, CX + 256, -64), (CX + 224, 64, CX + 256, 224)):
        L.solid(x0, y0, 0, x1, y1, 16, "crypt_stone1")
    # Four piers, for cover from his iron.
    for x in (CX - 480, CX + 480):
        for y in (-400, 400):
            L.solid(x - 48, y - 48, 0, x + 48, y + 48, H, "firebrick1")
            L.solid(x - 64, y - 64, 0, x + 64, y + 64, 32, "crypt_stone1")
            L.solid(x - 64, y - 64, H - 48, x + 64, y + 64, H - 16, "iron_rust1")
    # Old moulds stacked against the walls, and a beam crane over the pit.
    for x, y in ((520, -560), (600, 560), (1450, -560), (1380, 560)):
        L.solid(x - 64, y - 64, 0, x + 64, y + 64, 112, "sand_mould1")
        L.solid(x - 48, y - 48, 112, x + 48, y + 48, 144, "sand_mould1")
    L.solid(CX - 16, -Y, H - 96, CX + 16, Y, H - 64, "iron_rust1")
    L.solid(CX - 24, -40, H - 160, CX + 24, 40, H - 96, "iron_plate1")         # the crane's block
    L.solid(CX - 2, -2, 300, CX + 2, 2, H - 160, "iron_plate1")

    # The niche in the east wall: the Vein Seal under its cope.
    N0 = X1
    L.opening(N0, -160, 0, N0 + 32, 160, 256)
    L.room(N0 + 32, -192, 0, N0 + 352, 192, 288, wall="firebrick1", floor="crypt_stone1", ceiling="iron_rust1")
    nx = N0 + 192
    L.solid(nx - 96, -96, 0, nx + 96, 96, 24, "crypt_stone1")
    cope = [Box(nx - 64, -64, 24, nx - 48, 64, 152, "bronze1"), Box(nx + 48, -64, 24, nx + 64, 64, 152, "bronze1"),
            Box(nx - 48, -64, 24, nx + 48, -48, 152, "bronze1"), Box(nx - 48, 48, 24, nx + 48, 64, 152, "bronze1"),
            Box(nx - 64, -64, 152, nx + 64, 64, 168, "bronze1")]
    L.brush_entity("func_door", cope, angle=-1, targetname="cope", speed=40, wait=-1, lip=40, sounds=2)
    L.add("item_sigil", (nx, 0, 48), spawnflags=8)
    L.light((nx, 0, 220), 240, EMBER)
    L.light((nx - 120, -140, 160), 160, CANDLE)
    L.light((nx - 120, 140, 160), 160, CANDLE)

    # The Founder, and his congregation's last few.
    L.add("monster_founder", (CX + 64, 0, 24), angle=180, target="cope")
    L.add("monster_censer", (CX + 480, -560, 24), angle=180)
    L.add("monster_censer", (CX - 480, 560, 24), angle=0)
    L.add("monster_clinker", (CX - 480, 0, H - 8), angle=180, spawnflags=2)
    L.add("monster_clinker", (CX + 300, 300, H - 8), angle=180, spawnflags=2)

    for x, y in ((CX - 480, -400), (CX - 480, 400), (CX + 480, -400), (CX + 480, 400)):
        L.light((x - 100, y, 220), 260, CANDLE)
        L.light((x + 100, y, 220), 260, CANDLE)
    L.light((CX, 120, H - 200), 420, EMBER)
    L.light((CX - 300, 0, H - 40), 420, COLD)
    L.light((CX + 300, 0, H - 40), 420, COLD)

    L.add("item_health", (420, -560, 0), spawnflags=2)
    L.add("item_health", (420, 560, 0), spawnflags=2)
    L.add("item_health", (X1 - 64, -560, 0))
    L.add("item_health", (X1 - 64, 560, 0))
    L.add("item_rockets", (CX - 480, -300, 0))
    L.add("item_rockets", (CX + 480, 300, 0))
    L.add("item_cells", (CX - 480, 300, 0))
    L.add("item_cells", (CX + 480, -300, 0))
    L.add("item_spikes", (CX, -500, 0))
    L.add("item_shells", (CX, 500, 0))
    L.add("item_armor2", (420, 0, 0))

    # The gate home, in the niche's back wall, opened with the cope.
    G = N0 + 352
    L.opening(G, -64, 0, G + 32, 64, 128)
    L.brush_entity("func_door", [Box(G, -64, 0, G + 32, 64, 128, "door_iron1")],
                   angle=-1, targetname="cope", speed=80, wait=-1, lip=8)
    L.room(G + 32, -96, 0, G + 192, 96, 192, wall="ore_rock1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((G + 112, 0, 160), 160, CANDLE)
    L.brush_entity("trigger_changelevel", [Box(G + 64, -64, 0, G + 160, 64, 96, "trigger")], map="start")
    L.add("info_intermission", (420, -680, 520), mangle=(25, 25, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "vein5.map")
    build().save(out)
    print(out)
