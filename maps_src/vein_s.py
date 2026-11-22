#!/usr/bin/env python3
"""The Lode (vein_s.map), the Undervein shaft's secret map.

Behind the cracked wall in the old workings: the pocket of pure iron the
Founder found and kept to himself, its walls still bright with ore, his
pick and his own tally stone in the middle, and the Founder's Mantle that
was cast from it. The way on comes out in the Hot Workings.

    python3 maps_src/vein_s.py maps_src/vein_s.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402
from mine import PROP, lamp, timbers  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)


def build():
    L = Level(start_light=180, wad="cinder.wad", light_wait=0.6, sounds=7, message="The Lode", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=8, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 140, EMBER)
    L.opening(-32, -64, 0, 0, 64, 128)

    # A low crawl, then the lode: a round-ish pocket stepped out of the
    # rock in ledges, the ore heaped where he left it.
    L.room(0, -80, 0, 448, 80, 112, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    timbers(L, 0, 448, -80, 80, 0, 112, every=128)
    lamp(L, 220, 0, 84)
    L.opening(448, -64, 0, 480, 64, 112)
    C0, C1, R = 480, 1248, 384
    L.room(C0, -R, 0, C1, R, 448, wall="ore_rock1", floor="ore_rock1", ceiling="vein_rock1")
    cx = (C0 + C1) / 2
    # Ledges round the walls, rising to the back, as a chamber would be
    # stepped out of the lode.
    for i, (inset, h) in enumerate(((0, 48), (96, 96))):
        for x0, y0, x1, y1 in ((C0, -R, C1, -R + 128 - inset), (C0, R - 128 + inset, C1, R)):
            L.solid(x0 + 160, y0, 0, x1, y1, h, "ore_rock1")
        L.solid(C1 - 160 + inset, -R, 0, C1, R, h, "ore_rock1")
    L.steps(C1 - 256, -64, C1 - 160, 64, 0, 48, axis="x", tex="ore_rock1")
    L.steps(C1 - 160, -64, C1 - 64, 64, 48, 96, axis="x", tex="ore_rock1", base=0)
    # His pick and tally stone in the middle, and the Mark on the stone.
    L.solid(cx - 48, -48, 0, cx + 48, 48, 40, "crypt_stone1")
    L.solid(cx - 4, 40, 40, cx + 4, 48, 120, PROP)
    L.solid(cx - 28, 36, 112, cx + 28, 52, 124, "iron_rust1")
    L.add("item_artifact_invulnerability", (cx, 0, 40 + 24))       # powerups stand 24 over the floor
    for x, y in ((cx - 220, -200), (cx + 160, 220), (cx - 60, 240)):
        for i in range(3):
            k = 80 - i * 24
            L.solid(x - k, y - k * 0.7, 0, x + k, y + k * 0.7, 14 * (i + 1), "ore_rock1")

    L.light((cx, 0, 400), 320, COLD)
    L.light((cx, 0, 150), 220, EMBER)
    for x, y in ((C0 + 120, -260), (C0 + 120, 260), (C1 - 80, -260), (C1 - 80, 260), (cx, -300), (cx, 300)):
        L.light((x, y, 200), 220, CANDLE)

    L.add("monster_crucible_brute", (cx + 60, 0, 24), angle=180)
    L.add("monster_censer", (cx + 200, -300, 72), angle=90)
    L.add("monster_censer", (cx - 200, 300, 72), angle=270)
    L.add("monster_clinker", (cx, -160, 430), angle=180, spawnflags=2)
    L.add("monster_clinker", (cx, 160, 430), angle=180, spawnflags=2)
    L.add("item_health", (60, 50, 0), spawnflags=2)
    L.add("item_rockets", (C0 + 60, -300, 0))
    L.add("item_cells", (C0 + 60, 300, 0))

    # The way on, out of the back of the lode.
    L.opening(C1, -64, 96, C1 + 32, 64, 224)
    L.room(C1 + 32, -96, 96, C1 + 192, 96, 288, wall="ore_rock1", floor="ore_rock1", ceiling="ore_rock1")
    L.light((C1 + 112, 0, 256), 160, CANDLE)
    L.brush_entity("trigger_changelevel", [Box(C1 + 64, -64, 96, C1 + 160, 64, 192, "trigger")], map="vein4")
    L.add("info_intermission", (C0 + 60, -320, 380), mangle=(25, 25, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "vein_s.map")
    build().save(out)
    print(out)
