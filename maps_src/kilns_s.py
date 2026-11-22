#!/usr/bin/env python3
"""The Reliquary (kilns_s.map), the Ossuary Kilns shaft's secret map.

Behind the cracked wall in the Ash Galleries: the chapel where the kirk
kept its founders' bones, walled and vaulted in bone, a reliquary of
bronze at the crossing with the Soot Veil inside it. Its keepers are
still here. The way on comes out in the Sorting House.

    python3 maps_src/kilns_s.py maps_src/kilns_s.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
EMBER = (1.0, 0.45, 0.15)
COLD = (0.62, 0.70, 0.95)


def build():
    L = Level(start_light=170, wad="cinder.wad", light_wait=0.6, sounds=6, message="The Reliquary", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="ossuary1", floor="crypt_stone1", ceiling="crypt_stone1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 140, EMBER)
    L.opening(-32, -64, 0, 0, 64, 128)

    # A cross: the nave east-west, the transepts north and south at the
    # crossing, all in bone.
    L.room(0, -192, 0, 1024, 192, 384, wall="ossuary1", floor="crypt_stone1", ceiling="crypt_stone1")
    L.room(384, -576, 0, 768, -224, 320, wall="ossuary1", floor="crypt_stone1", ceiling="crypt_stone1")
    L.room(384, 224, 0, 768, 576, 320, wall="ossuary1", floor="crypt_stone1", ceiling="crypt_stone1")
    L.opening(384, -224, 0, 768, -192, 320)
    L.opening(384, 192, 0, 768, 224, 320)
    for x in (384, 736):
        for y in (-224, 192):
            L.solid(x, y, 0, x + 32, y + 32, 384, "crypt_stone1")            # the crossing's piers
    for x in range(96, 384, 96):
        for y in (-192, 168):
            L.solid(x, y, 0, x + 24, y + 24, 384, "kirk_column1")
    # The reliquary at the crossing: a bronze house on a stepped plinth.
    L.solid(480, -96, 0, 672, 96, 16, "crypt_stone1")
    L.solid(496, -80, 16, 656, 80, 32, "crypt_stone1")
    for x0, y0, x1, y1 in ((624, -64, 640, 64), (512, -64, 624, -48), (512, 48, 624, 64)):       # open to the west
        L.solid(x0, y0, 32, x1, y1, 144, "bronze1")
    L.solid(504, -72, 144, 648, 72, 160, "bronze1")
    L.solid(528, -40, 160, 624, 40, 192, "bronze1")
    L.add("item_artifact_invisibility", (576, 0, 32 + 24))       # powerups stand 24 over the floor
    # Ossuary niches with candles down the transepts.
    for y in (-520, 520):
        L.solid(512, y - 16, 0, 640, y + 16, 48, "crypt_stone1")
        L.light((576, y + (40 if y < 0 else -40), 100), 200, CANDLE)

    L.light((576, 0, 300), 300, COLD)
    L.light((576, 0, 80), 200, EMBER)
    for x in (128, 320, 860):
        L.light((x, -140, 160), 200, CANDLE)
        L.light((x, 140, 160), 200, CANDLE)

    for x, y in ((576, -420), (576, 420), (300, 0), (860, 0)):
        L.add("monster_ash_wraith", (x, y, 180), angle=180)
    L.add("monster_deacon", (900, 100, 24), angle=180)
    L.add("monster_ashen", (576, -480, 24), angle=90)
    L.add("monster_ashen", (576, 480, 24), angle=270)
    L.add("item_health", (60, 140, 0), spawnflags=2)
    L.add("item_rockets", (700, 500, 0))
    L.add("item_cells", (450, -500, 0))

    # The way on, past the east end.
    L.opening(1024, -64, 0, 1056, 64, 128)
    L.room(1056, -96, 0, 1216, 96, 192, wall="ossuary1", floor="crypt_stone1", ceiling="crypt_stone1")
    L.light((1136, 0, 160), 160, CANDLE)
    L.brush_entity("trigger_changelevel", [Box(1120, -64, 0, 1200, 64, 96, "trigger")], map="kilns4")
    L.add("info_intermission", (80, -150, 300), mangle=(20, 10, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "kilns_s.map")
    build().save(out)
    print(out)
