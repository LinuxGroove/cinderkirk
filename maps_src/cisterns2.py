#!/usr/bin/env python3
"""The Long Vault (cisterns2.map), the Cisterns shaft's second map.

A brick vault two hundred yards long over the feed channel, walkways down
either side and side chambers off them. The gold key lies on the bottom of
the channel at the far end, among the leeches; the gold door is back near
the start. A cracked wall in the south pump room hides the way to the
Drowned Chapel (the secret map).

    python3 maps_src/cisterns2.py maps_src/cisterns2.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

LAMP = (0.95, 0.80, 0.58)
COLD = (0.62, 0.72, 1.0)
DAMP = (0.55, 0.85, 0.75)
X1 = 2048


def build():
    L = Level(wad="cinder.wad", light_wait=0.8, sounds=5, message="The Long Vault", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    # The landing at the west end.
    L.room(-224, -96, 0, -32, 96, 192, wall="cist_brick1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 180, LAMP)
    L.opening(-32, -64, 0, 0, 64, 128)

    # The vault: x 0..2048, y -256..256; walkways at 0 either side of the
    # channel (y -96..96), whose water stands 32 below them and runs 224 deep.
    L.room(0, -256, -256, X1, 256, 320, wall="cist_brick1", floor="cist_stone1", ceiling="cist_brick1")
    for y0, y1 in ((-256, -96), (96, 256)):
        L.solid(0, y0, -256, X1, y1, 0, "cist_stone1")
        L.solid(0, y0 + (0 if y0 < 0 else 144), 0, X1, y0 + (16 if y0 < 0 else 160), 8, "kirk_trim1")
    L.solid(0, -96, -256, 160, 96, 0, "cist_stone1")                    # the landing's end
    L.liquid(160, -96, -256, X1, 96, -32, "*cistern1")
    # The vault's curve, stepped in from the walls, and ribs every 256.
    for i, (inset, z) in enumerate(((32, 256), (80, 288))):
        for y0, y1 in ((-256, -256 + inset), (256 - inset, 256)):
            L.solid(0, y0, z, X1, y1, 320, "cist_brick1")
    for x in range(256, X1, 256):
        for y0, y1 in ((-256, -224), (224, 256)):
            L.solid(x - 16, y0, 0, x + 16, y1, 320, "cist_stone1")
    # Bridges across the channel.
    for x in (512, 1280):
        L.solid(x, -96, -8, x + 96, 96, 0, "iron_plate1")
    L.solid(X1 - 160, -96, -256, X1, 96, 0, "cist_stone1")              # the far end, where the channel comes in
    L.solid(X1 - 176, -96, -256, X1 - 160, 96, -16, "cist_drain1")

    # The gold key on the channel's bottom near the far end.
    L.add("item_key2", (1700, 0, -232))
    L.add("item_health", (1600, 40, -232))
    for x, y in ((1450, 40), (1650, -50), (1800, 30), (1200, -30), (900, 40)):
        L.add("monster_leech", (x, y, -140), angle=180)

    # The north pump room: pipes, a Gauger, and ammunition.
    L.opening(704, 256, 0, 832, 288, 128)
    L.room(640, 288, 0, 896, 544, 256, wall="cist_tile1", floor="cist_stone1", ceiling="cist_brick1")
    for x in (672, 864):
        L.solid(x - 16, 480, 0, x + 16, 544, 256, "verdigris1")
    L.solid(704, 448, 0, 832, 544, 96, "tank_iron1")
    L.add("monster_gauger", (768, 380, 24), angle=270)
    L.add("item_spikes", (700, 320, 0))
    L.add("item_shells", (840, 320, 0))
    L.light((768, 400, 220), 260, LAMP)

    # The south pump room, with the cracked wall in its back.
    L.opening(1152, -288, 0, 1280, -256, 128)
    L.room(1088, -544, 0, 1344, -288, 256, wall="cist_tile1", floor="cist_stone1", ceiling="cist_brick1")
    L.solid(1120, -400, 0, 1312, -320, 64, "tank_iron1")
    L.add("monster_gauger", (1216, -440, 24), angle=90)
    L.add("item_health", (1150, -500, 0))
    L.light((1216, -420, 220), 240, LAMP)
    L.opening(1184, -576, 0, 1248, -544, 96)
    L.brush_entity("func_cracked", [Box(1184, -576, 0, 1248, -544, 96, "kirk_crack1")])
    L.room(1152, -768, 0, 1280, -576, 160, wall="cist_brick1", floor="cist_stone1", ceiling="cist_brick1")
    L.brush_entity("trigger_secret", [Box(1160, -660, 0, 1272, -584, 96, "trigger")])
    L.brush_entity("trigger_changelevel", [Box(1152, -768, 0, 1280, -736, 128, "trigger")], map="cisterns_s")
    L.light((1216, -680, 120), 140, DAMP)

    # The congregation on the walkways.
    for x, y in ((400, 180), (1000, -180), (1500, 180), (1900, -180)):
        L.add("monster_ashen", (x, y, 24), angle=180)
    L.add("monster_censer", (1100, 180, 24), angle=180)
    L.add("monster_censer", (1750, 180, 24), angle=180)
    L.add("monster_deacon", (1950, 160, 24), angle=180)
    L.add("item_rockets", (1950, -200, 0))
    L.add("weapon_nailgun", (300, -180, 0))

    # Light: lamps on the ribs, the water lit from below.
    for x in range(256, X1, 512):
        for y in (-200, 200):
            L.solid(x - 8, y - 8, 200, x + 8, y + 8, 232, "lamp_amber1")
            L.light((x, y, 176), 300, LAMP)
    for x in range(384, X1, 512):
        if x < 1900:
            L.light((x, 0, -120), 220, DAMP)
        L.light((x, 0, 260), 220, COLD)

    # The gold door off the north walkway near the start, and the cage on.
    L.opening(256, 256, 0, 352, 288, 128)
    L.brush_entity("func_door", [Box(256, 256, 0, 352, 288, 128, "sluice_wood1")],
                   angle=-1, spawnflags=8, speed=60, wait=-1, lip=8, sounds=2)
    L.room(224, 288, 0, 384, 448, 192, wall="cist_brick1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((304, 368, 160), 160, LAMP)
    L.brush_entity("trigger_changelevel", [Box(256, 336, 0, 352, 432, 96, "trigger")], map="cisterns3")
    L.add("info_intermission", (100, -200, 200), mangle=(20, 20, 0))
    L.nook(2048, 144, 0, "e", ('item_health', 'item_shells'), wall="cist_brick1", floor="cist_stone1")   # a secret behind cracked stone
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "cisterns2.map")
    build().save(out)
    print(out)
