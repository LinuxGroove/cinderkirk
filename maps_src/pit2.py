#!/usr/bin/env python3
"""The Belfry (pit2.map), a Pit fight arena.

A square bell tower with its bell long gone: a floor at the bottom and two
galleries round the open middle, each reached by a stair that climbs out
over the drop. The Founder's Mantle waits on the top gallery, and whoever
takes it is in sight of everyone below.

    python3 maps_src/pit2.py maps_src/pit2.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)
R, HOLE, H = 640, 288, 896
TIERS = (288, 576)


def ring(L, z, tex="kirk_stone1"):
    """A gallery round the open middle, its floor 16 thick at z."""
    L.solid(-R, HOLE, z - 16, R, R, z, tex)
    L.solid(-R, -R, z - 16, R, -HOLE, z, tex)
    L.solid(-R, -HOLE, z - 16, -HOLE, HOLE, z, tex)
    L.solid(HOLE, -HOLE, z - 16, R, HOLE, z, tex)


def build():
    L = Level(wad="cinder.wad", light_wait=0.6, sounds=10, message="The Belfry", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=20, _range=0.6)
    L.room(-R, -R, 0, R, R, H, wall="kirk_brick1", floor="floor_flag1", ceiling="ceil_timber1")
    for z in TIERS:
        ring(L, z)
    # The stairs: from the floor up to the first gallery on the south side, and
    # from the first to the second on the north, each climbing along the edge.
    L.steps(-HOLE + 32, -HOLE, HOLE - 64, -HOLE + 128, 0, TIERS[0], axis="x", tex="crypt_stone1")
    L.steps(-HOLE + 64, HOLE - 128, HOLE - 32, HOLE, TIERS[1], TIERS[0], axis="x", tex="crypt_stone1",
            base=TIERS[0] - 16)
    # Parapets on the galleries' inner edges, leaving the stairs' heads open.
    for z in TIERS:
        if z != TIERS[0]:
            L.solid(-HOLE, -HOLE - 16, z, HOLE, -HOLE, z + 32, "iron_rust1")
        if z != TIERS[1]:                                        # open at the east end, for the stair up
            L.solid(-HOLE, HOLE, z, HOLE - 192, HOLE + 16, z + 32, "iron_rust1")
        L.solid(-HOLE - 16, -HOLE, z, -HOLE, HOLE, z + 32, "iron_rust1")
        L.solid(HOLE, -HOLE, z, HOLE + 16, HOLE, z + 32, "iron_rust1")
    # Bell frame beams across the top, and the rope's hole.
    for y in (-96, 96):
        L.solid(-R, y - 16, H - 96, R, y + 16, H - 64, "oak1")
    # Pillars for cover on the floor.
    for x, y in ((-460, -460), (460, -460), (-460, 460), (460, 460)):
        L.solid(x - 40, y - 40, 0, x + 40, y + 40, TIERS[0] - 16, "kirk_brick1")

    sp = [(-560, -560, 45, 0), (560, -560, 135, 0), (-560, 560, 315, 0), (560, 560, 225, 0),
          (0, -480, 90, TIERS[0]), (0, 480, 270, TIERS[0]), (-480, 0, 0, TIERS[1]), (480, 0, 180, TIERS[1])]
    for x, y, a, z in sp:
        L.add("info_player_deathmatch", (x, y, z + 24), angle=a)
    L.add("info_player_start", (-560, -560, 24), angle=45)

    L.add("weapon_supershotgun", (0, 0, 0))
    L.add("weapon_nailgun", (-480, 0, 0))
    L.add("weapon_grenadelauncher", (480, 0, 0))
    L.add("weapon_supernailgun", (-480, 480, TIERS[0]))
    L.add("weapon_rocketlauncher", (480, -480, TIERS[0]))
    L.add("weapon_lightning", (0, -480, TIERS[1]))
    L.add("item_artifact_invulnerability", (0, 480, TIERS[1] + 24))
    L.add("item_armor2", (-480, -480, TIERS[1]))
    L.add("item_armor1", (0, 480, TIERS[0]))
    L.add("item_health", (480, 480, TIERS[1]), spawnflags=2)
    for x, y, z in ((-560, -300, 0), (560, 300, 0), (300, -560, TIERS[0]), (-300, 560, TIERS[1])):
        L.add("item_health", (x, y, z))
    for x, y, z, cls in ((-300, -560, 0, "item_shells"), (300, 560, 0, "item_spikes"), (-560, 300, TIERS[0], "item_rockets"),
                         (560, -300, TIERS[0], "item_cells"), (560, 300, TIERS[1], "item_rockets"), (-560, -300, TIERS[1], "item_spikes")):
        L.add(cls, (x, y, z))

    for z in (0,) + TIERS:
        for x, y in ((-460, 0), (460, 0), (0, -460), (0, 460)):
            L.light((x, y, z + 180), 260, CANDLE)
    L.light((0, 0, 140), 300, EMBER)
    L.light((0, 0, H - 120), 420, COLD)
    L.add("info_intermission", (-560, -560, TIERS[1] + 200), mangle=(30, 45, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "pit2.map")
    build().save(out)
    print(out)
