#!/usr/bin/env python3
"""The Slag Run (pit3.map), a Pit fight arena.

A long hall split down the middle by a run of open slag, crossed by three
iron bridges. Each bank has a raised firing step along its wall, and the
Soot Veil lies on the middle bridge, over the heat.

    python3 maps_src/pit3.py maps_src/pit3.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
SLAG = (1.0, 0.38, 0.1)
X, Y, H = 1152, 704, 448
RUN = 128                            # the slag run's half width
STEP = 96                            # the firing steps' height


def build():
    L = Level(wad="cinder.wad", sounds=10, message="The Slag Run", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=20, _range=0.6)
    L.room(-X, -Y, 0, X, Y, H, wall="firebrick1", floor="iron_plate1", ceiling="iron_rust1", floor_depth=96)
    # The run of slag down the middle, sunk into the floor.
    L.opening(-X, -RUN, -64, X, RUN, 0)
    L.liquid(-X, -RUN, -64, X, RUN, -24, "*lava_slag1")
    L.solid(-X, -RUN - 16, 0, X, -RUN, 12, "iron_rust1")                     # kerbs
    L.solid(-X, RUN, 0, X, RUN + 16, 12, "iron_rust1")
    for x in (-640, 0, 640):                                                 # the bridges
        L.solid(x - 64, -RUN - 16, -8, x + 64, RUN + 16, 12, "iron_grid1")
    # Firing steps along both long walls, with stairs at their ends.
    for sy in (-1, 1):
        y0, y1 = (Y - 160, Y) if sy > 0 else (-Y, -Y + 160)
        L.solid(-X + 192, y0, 0, X - 192, y1, STEP, "crypt_stone1")
        L.steps(-X + 64, y0, -X + 192, y1, 0, STEP, axis="x", tex="crypt_stone1")
        L.steps(X - 192, y0, X - 64, y1, STEP, 0, axis="x", tex="crypt_stone1")
    # Ingot stacks on each bank.
    for x, y in ((-880, 300), (-320, -320), (320, 320), (880, -300), (-420, 360), (420, -360)):
        L.solid(x - 48, y - 48, 0, x + 48, y + 48, 72, "sand_mould1")

    for x, y, a, z in ((-1000, -420, 0, 0), (1000, 420, 180, 0), (-1000, 420, 0, 0), (1000, -420, 180, 0),
                       (-600, Y - 80, 270, STEP), (600, -Y + 80, 90, STEP), (0, 420, 270, 0), (0, -420, 90, 0)):
        L.add("info_player_deathmatch", (x, y, z + 24), angle=a)
    L.add("info_player_start", (-1000, -420, 24), angle=0)

    L.add("weapon_supershotgun", (-880, -300, 0))
    L.add("weapon_nailgun", (880, 300, 0))
    L.add("weapon_supernailgun", (-640, 300, 0))
    L.add("weapon_grenadelauncher", (640, -300, 0))
    L.add("weapon_rocketlauncher", (0, Y - 80, STEP))
    L.add("weapon_lightning", (0, -Y + 80, STEP))
    L.add("item_artifact_invisibility", (0, 0, 12 + 24))
    L.add("item_armor2", (-900, Y - 80, STEP))
    L.add("item_armor1", (900, -Y + 80, STEP))
    L.add("item_health", (900, Y - 80, STEP), spawnflags=2)
    for x, y in ((-640, -400), (640, 400), (-200, 280), (200, -280)):
        L.add("item_health", (x, y, 0))
    for x, y, z, cls in ((-300, Y - 80, STEP, "item_rockets"), (300, -Y + 80, STEP, "item_cells"), (-1000, 0 + 300, 0, "item_shells"),
                         (1000, -300, 0, "item_spikes"), (-200, -300, 0, "item_spikes"), (200, 300, 0, "item_shells")):
        L.add(cls, (x, y, z))

    for x in range(-960, X, 320):
        L.light((x, 0, 40), 300, SLAG)
    for x in (-800, 0, 800):
        for y in (-480, 480):
            L.light((x, y, 260), 320, CANDLE)
    L.add("info_intermission", (-1100, -650, 380), mangle=(25, 30, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "pit3.map")
    build().save(out)
    print(out)
