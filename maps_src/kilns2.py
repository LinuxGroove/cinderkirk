#!/usr/bin/env python3
"""The Bone Kilns (kilns2.map), the Ossuary Kilns shaft's second map.

The long firing hall: a row of brick kilns down each side, their hearths
still full of slag, carts of bones in the aisle between. The gold key sits
on the pedestal in the far north kiln, over its burning hearth; the gold
door out is in the east wall.

    python3 maps_src/kilns2.py maps_src/kilns2.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)
X1, Y = 1792, 512
KILNS = range(160, 1600, 320)       # each kiln's west side; 224 wide


def kiln(L, x0, north):
    """A brick kiln against the wall, its mouth to the aisle and a pit of
    slag for a hearth."""
    y0, y1 = (320, Y) if north else (-Y, -320)
    front = y0 if north else y1
    fy0, fy1 = (front, front + 24) if north else (front - 24, front)
    for xa, xb in ((x0, x0 + 24), (x0 + 200, x0 + 224)):
        L.solid(xa, y0, 0, xb, y1, 224, "kiln_brick1")
    L.solid(x0, y0, 224, x0 + 224, y1, 256, "kiln_brick1")
    L.solid(x0 + 24, fy0, 0, x0 + 72, fy1, 224, "kiln_brick1")
    L.solid(x0 + 152, fy0, 0, x0 + 200, fy1, 224, "kiln_brick1")
    L.solid(x0 + 72, fy0, 128, x0 + 152, fy1, 224, "kiln_brick1")
    L.solid(x0 + 64, fy0 - (8 if north else 0), 120, x0 + 160, fy1 + (0 if north else 8), 136, "kirk_trim1")
    iy0, iy1 = (fy1, y1) if north else (y0, fy0)
    L.opening(x0 + 24, iy0, -40, x0 + 200, iy1, 0)
    L.liquid(x0 + 24, iy0, -40, x0 + 200, iy1, -12, "*slag1")
    L.light((x0 + 112, (iy0 + iy1) / 2, 40), 220, EMBER)
    return x0 + 112, (iy0 + iy1) / 2


def build():
    L = Level(wad="cinder.wad", message="The Bone Kilns", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, CANDLE)
    L.opening(-32, -64, 0, 0, 64, 128)

    L.room(0, -Y, 0, X1, Y, 448, wall="kiln_brick1", floor="ash_floor1", ceiling="ceil_timber1", floor_depth=64)
    hearths = [kiln(L, x, north) for x in KILNS for north in (True, False)]
    # The gold key on a pedestal in the far north kiln's hearth.
    kx, ky = hearths[-2]
    L.solid(kx - 24, ky - 24, -40, kx + 24, ky + 24, 8, "crypt_stone1")
    L.add("item_key2", (kx, ky, 8))
    # Bone carts down the aisle, and a chute from the charnel hall above.
    for x in (320, 800, 1280):
        for y in (-128, 128):
            L.solid(x - 64, y - 40, 8, x + 64, y + 40, 56, "oak1")
            for wx in (x - 48, x + 32):
                L.solid(wx, y - 48, 0, wx + 16, y + 48, 24, "iron_rust1")
            L.solid(x - 56, y - 32, 56, x + 56, y + 32, 72, "ash_floor1")      # the load
    L.solid(-0, -96, 288, 96, 96, 448, "kiln_brick1")                          # the chute's mouth
    L.solid(0, -64, 256, 64, 64, 288, "iron_rust1")
    # Flues: a chimney over each kiln up through the roof beams.
    for x in KILNS:
        for y0, y1 in ((416, 480), (-480, -416)):
            L.solid(x + 80, y0, 256, x + 144, y1, 448, "kiln_brick1")

    for x in (400, 1000, 1500):
        L.solid(x - 8, -8, 336, x + 8, 8, 368, "lamp_amber1")
        L.solid(x - 2, -2, 368, x + 2, 2, 448, "iron_plate1")
        L.light((x, 0, 320), 380, CANDLE)
    L.light((900, 0, 420), 400, COLD)
    L.light((120, 200, 120), 200, CANDLE)
    L.light((120, -200, 120), 200, CANDLE)

    L.add("monster_ashen", (500, 250, 24), angle=180)
    L.add("monster_ashen", (700, -250, 24), angle=180)
    L.add("monster_ashen", (1100, 250, 24), angle=180)
    L.add("monster_censer", (1000, 0, 24), angle=180)
    L.add("monster_censer", (1500, -200, 24), angle=180)
    L.add("monster_crucible_brute", (1600, 0, 24), angle=180)
    for x in (600, 1200):
        L.add("monster_ash_wraith", (x, 0, 200), angle=180)
    for x in (480, 1120):
        L.add("monster_clinker", (x, 200, 440), spawnflags=2)
        L.add("monster_clinker", (x + 160, -200, 440), spawnflags=2)
    L.add("monster_deacon", (1700, 300, 24), angle=180, spawnflags=1)

    L.add("item_shells", (80, 300, 0))
    L.add("item_spikes", (80, -300, 0))
    L.add("item_health", (560, 0, 0))
    L.add("item_health", (1040, 0, 0))
    L.add("item_rockets", (1500, 260, 0))
    L.add("item_armor2", (1720, -400, 0))
    L.add("weapon_rocketlauncher", (800, 0, 0))

    # The gold door in the east wall, and the cage on.
    L.opening(X1, -64, 0, X1 + 32, 64, 128)
    L.brush_entity("func_door", [Box(X1, -64, 0, X1 + 32, 64, 128, "door_iron1")],
                   angle=-1, spawnflags=8, speed=60, wait=-1, lip=8, sounds=2)
    L.room(X1 + 32, -96, 0, X1 + 192, 96, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((X1 + 112, 0, 160), 160, CANDLE)
    L.brush_entity("trigger_changelevel", [Box(X1 + 64, -64, 0, X1 + 160, 64, 96, "trigger")], map="kilns3")
    L.add("info_intermission", (100, -420, 380), mangle=(25, 20, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "kilns2.map")
    build().save(out)
    print(out)
