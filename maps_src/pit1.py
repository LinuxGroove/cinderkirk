#!/usr/bin/env python3
"""The Cooling Yard (pit1.map), a Pit fight arena.

The yard where the Foundry's castings were stood to cool: an open floor
of iron plate with stacks of ingots and moulds for cover, a gantry along
the north wall reached by stairs at both ends. The Forge Heart sits in
the middle of the gantry.

    python3 maps_src/pit1.py maps_src/pit1.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)
X, Y, H = 1024, 768, 512
G = 224                              # the gantry's height


def build():
    L = Level(wad="cinder.wad", sounds=10, message="The Cooling Yard", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=20, _range=0.6)
    L.room(-X, -Y, 0, X, Y, H, wall="firebrick1", floor="iron_plate1", ceiling="iron_rust1")

    # The gantry along the north wall, with stairs up at both ends.
    L.solid(-X + 192, Y - 192, G - 16, X - 192, Y, G, "iron_grid1")
    L.steps(-X, Y - 192 - 14 * 16, -X + 192, Y - 192, 0, G, axis="y", tex="crypt_stone1")
    L.solid(-X, Y - 192, 0, -X + 192, Y, G, "crypt_stone1")
    L.steps(X - 192, Y - 192 - 14 * 16, X, Y - 192, 0, G, axis="y", tex="crypt_stone1")
    L.solid(X - 192, Y - 192, 0, X, Y, G, "crypt_stone1")
    for x in range(-X + 256, X - 192, 256):                     # its legs
        L.solid(x - 12, Y - 180, 0, x + 12, Y - 156, G - 16, "iron_rust1")
    L.solid(-X + 192, Y - 200, G, X - 192, Y - 192, G + 40, "iron_rust1")      # its rail

    # Stacks of ingots and moulds for cover.
    for x, y, w, d, h in ((-560, -300, 160, 96, 96), (520, -340, 96, 192, 128), (-120, -520, 224, 64, 64),
                          (0, 80, 128, 128, 160), (-640, 220, 96, 96, 64), (640, 180, 160, 64, 96),
                          (300, -40, 64, 64, 48), (-300, -40, 64, 64, 48)):
        L.solid(x - w // 2, y - d // 2, 0, x + w // 2, y + d // 2, h, "sand_mould1" if h > 64 else "iron_rust1")

    for i, (x, y, a) in enumerate(((-900, -650, 45), (900, -650, 135), (-900, 300, 0), (900, 300, 180),
                                   (0, -680, 90), (0, 620 - 192, 270), (-600, Y - 96, 0), (600, Y - 96, 180))):
        z = G + 24 if y > Y - 192 else 24
        L.add("info_player_deathmatch", (x, y, z), angle=a)
    L.add("info_player_start", (0, -680, 24), angle=90)

    L.add("weapon_supershotgun", (-560, -180, 0))
    L.add("weapon_nailgun", (560, -180, 0))
    L.add("weapon_supernailgun", (-760, 0, 0))
    L.add("weapon_grenadelauncher", (760, 0, 0))
    L.add("weapon_rocketlauncher", (0, -360, 0))
    L.add("weapon_lightning", (-500, Y - 96, G))
    L.add("item_artifact_super_damage", (0, Y - 96, G + 24))
    L.add("item_armor2", (500, Y - 96, G))
    L.add("item_armor1", (0, 240, 0))
    L.add("item_health", (0, -100, 160), spawnflags=2)
    for x, y in ((-880, -680), (880, -680), (-880, 160), (880, 160)):
        L.add("item_health", (x, y, 0))
    for x, y, cls in ((-300, -650, "item_shells"), (300, -650, "item_spikes"), (-300, 300, "item_rockets"),
                      (300, 300, "item_cells"), (-800, -400, "item_spikes"), (800, -400, "item_shells"),
                      (-200, Y - 96, "item_cells"), (200, Y - 96, "item_rockets")):
        L.add(cls, (x, y, G if y > Y - 192 else 0))

    for x in (-700, 0, 700):
        for y in (-500, 100):
            L.light((x, y, 300), 380, CANDLE)
    for x in (-600, 0, 600):
        L.light((x, Y - 96, G + 140), 260, EMBER)
        L.light((x, Y - 300, 60), 200, EMBER)
    L.light((0, 0, H - 40), 500, COLD)
    L.add("info_intermission", (-900, -650, 400), mangle=(25, 35, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "pit1.map")
    build().save(out)
    print(out)
