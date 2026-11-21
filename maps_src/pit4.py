#!/usr/bin/env python3
"""The Charnel Kiln (pit4.map), a Pit fight arena.

Nine bays of an old bone kiln, three by three, joined by arches: tight
corners for close fighting, the firebox in the middle bay under a
grating, with the Quench Suit on it, and a gallery over the south bays
for whoever wants the high ground.

    python3 maps_src/pit4.py maps_src/pit4.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
B = 448                              # a bay's width
W = 32                               # the walls between bays
H = 320
GAL = 176                            # the gallery's height


def build():
    L = Level(wad="cinder.wad", message="The Charnel Kiln", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=22, _range=0.6)
    half = B * 3 // 2
    L.room(-half, -half, 0, half, half, H, wall="kiln_brick1", floor="floor_flag1", ceiling="kiln_tile1")
    # Walls between the bays, with an arch through each.
    for k in (-1, 1):
        c = k * B // 2
        for i in range(3):
            a = -half + i * B
            a0 = a + 128 if i == 0 else a                  # the south gallery runs over the first bays' walls
            L.solid(c - W // 2, a0, 0, c + W // 2, a + B // 2 - 80, H, "kiln_brick1")
            L.solid(c - W // 2, a + B // 2 + 80, 0, c + W // 2, a + B, H, "kiln_brick1")
            L.solid(c - W // 2, a + B // 2 - 80, 192, c + W // 2, a + B // 2 + 80, H, "kiln_brick1")
            L.solid(a, c - W // 2, 0, a + B // 2 - 80, c + W // 2, H, "kiln_brick1")
            L.solid(a + B // 2 + 80, c - W // 2, 0, a + B, c + W // 2, H, "kiln_brick1")
            L.solid(a + B // 2 - 80, c - W // 2, 192, a + B // 2 + 80, c + W // 2, H, "kiln_brick1")
    # The firebox: a grating over embers in the middle bay.
    L.solid(-160, -160, 0, 160, 160, 8, "iron_grid1")
    L.light((0, 0, 20), 200, EMBER)
    # A gallery along the south wall over the three south bays, stairs at each end.
    L.solid(-half + 128, -half, GAL - 16, half - 128, -half + 128, GAL, "kirk_stone1")
    L.solid(-half, -half, 0, -half + 128, -half + 128, GAL, "kirk_stone1")
    L.solid(half - 128, -half, 0, half, -half + 128, GAL, "kirk_stone1")
    L.steps(-half, -half + 128, -half + 128, -half + 128 + 176, GAL, 0, axis="y", tex="kirk_stone1")
    L.steps(half - 128, -half + 128, half, -half + 128 + 176, GAL, 0, axis="y", tex="kirk_stone1")

    for i, (x, y) in enumerate(((-B, -B + 60), (B, -B + 60), (-B, B), (B, B), (0, B), (-B, 0), (B, 0), (0, -B + 60))):
        L.add("info_player_deathmatch", (x, y, 24), angle=90 if y < 0 else 270)
    L.add("info_player_start", (-B, B, 24), angle=270)

    L.add("weapon_supershotgun", (-B, B - 100, 0))
    L.add("weapon_nailgun", (B, B - 100, 0))
    L.add("weapon_supernailgun", (-B, 100, 0))
    L.add("weapon_grenadelauncher", (B, 100, 0))
    L.add("weapon_rocketlauncher", (0, B + 100, 0))
    L.add("weapon_lightning", (0, -half + 64, GAL))
    L.add("item_artifact_envirosuit", (0, 0, 8 + 24))
    L.add("item_artifact_super_damage", (-B, -half + 64, GAL + 24))
    L.add("item_armor2", (B, -half + 64, GAL))
    L.add("item_armor1", (0, B - 100, 0))
    L.add("item_health", (0, -B + 60, 0), spawnflags=2)
    for x, y in ((-B - 150, B + 150), (B + 150, B + 150), (-B - 150, -50), (B + 150, -50)):
        L.add("item_health", (x, y, 0))
    for x, y, cls in ((-B + 120, B + 150, "item_shells"), (B - 120, B + 150, "item_spikes"), (-B - 150, 150, "item_rockets"),
                      (B + 150, 150, "item_cells"), (-150, -B - 50, "item_spikes"), (150, -B - 50, "item_shells")):
        L.add(cls, (x, y, 0))

    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            if i or j:
                L.light((i * B, j * B, 220), 280, CANDLE if (i + j) % 2 else EMBER)
    L.add("info_intermission", (-half + 64, -half + 64, GAL + 100), mangle=(20, 45, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "pit4.map")
    build().save(out)
    print(out)
