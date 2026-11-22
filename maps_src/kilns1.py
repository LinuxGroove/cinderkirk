#!/usr/bin/env python3
"""The Charnel Stair (kilns1.map), the Ossuary Kilns shaft's first map.

Down from the cage through the kirk's old crypt, then a long stair between
walls of stacked bones to the charnel hall, where the dead waited for the
kilns. The ash wraiths start here. The silver key is on the bier at the
hall's south end; the silver door out is in its east wall.

    python3 maps_src/kilns1.py maps_src/kilns1.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

CANDLE = (1.0, 0.78, 0.5)
COLD = (0.62, 0.70, 0.95)
EMBER = (1.0, 0.5, 0.2)
HALL = -384                       # the charnel hall's floor


def pilasters(L, x0, x1, y0, y1, z0, z1, side, step=256):
    """Stone piers against a bone wall, every step along it."""
    if side in ("e", "w"):
        x = x1 - 24 if side == "e" else x0
        for y in range(y0 + step // 2, y1, step):
            L.solid(x, y - 24, z0, x + 24, y + 24, z1, "crypt_stone1")
    else:
        y = y1 - 24 if side == "n" else y0
        for x in range(x0 + step // 2, x1, step):
            L.solid(x - 24, y, z0, x + 24, y + 24, z1, "crypt_stone1")


def build():
    L = Level(wad="cinder.wad", light_wait=0.7, sounds=6, message="The Charnel Stair", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=8, _range=0.6)

    # The cage's landing, north of the crypt.
    L.room(-96, 640, 0, 96, 832, 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (0, 760, 24), angle=270)
    L.add("info_player_coop", (48, 760, 24), angle=270)
    L.add("info_player_coop", (-48, 760, 24), angle=270)
    L.light((0, 736, 160), 180, CANDLE)
    L.opening(-64, 608, 0, 64, 640, 128)

    # The old crypt under the kirk: low, vaulted on four piers, tombs along
    # the sides.
    L.room(-320, 256, 0, 320, 608, 224, wall="crypt_stone1", floor="floor_flag1", ceiling="crypt_stone1")
    for x in (-128, 128):
        for y in (352, 512):
            L.solid(x - 24, y - 24, 0, x + 24, y + 24, 224, "kirk_column1")
            L.solid(x - 40, y - 40, 192, x + 40, y + 40, 224, "crypt_stone1")
    for x0 in (-304, 240):
        for y in (320, 448):
            L.solid(x0, y, 0, x0 + 64, y + 96, 40, "crypt_stone1")          # tombs
            L.solid(x0 + 4, y + 4, 40, x0 + 60, y + 92, 48, "kirk_trim1")
    L.light((0, 432, 180), 260, CANDLE)
    for x in (-272, 272):
        L.light((x, 560, 80), 160, CANDLE)

    # The stair: three flights south between bone walls, landings between.
    L.room(-96, -768, HALL, 96, 256, 224, wall="ossuary1", floor="crypt_stone1", ceiling="crypt_stone1")
    L.opening(-96, 224, 0, 96, 288, 160)
    L.solid(-96, 160, HALL, 96, 256, 0, "crypt_stone1")                        # the top landing
    L.steps(-96, -96, 96, 160, -128, 0, axis="y", tex="crypt_stone1", base=HALL)
    L.solid(-96, -192, HALL, 96, -96, -128, "crypt_stone1")
    L.steps(-96, -448, 96, -192, -256, -128, axis="y", tex="crypt_stone1", base=HALL)
    L.solid(-96, -544, HALL, 96, -448, -256, "crypt_stone1")
    L.steps(-96, -768, 96, -544, HALL, -256, axis="y", tex="crypt_stone1", base=HALL)
    for y, z in ((208, 0), (-144, -128), (-496, -256)):
        for x0 in (-96, 72):
            L.solid(x0, y - 24, z, x0 + 24, y + 24, z + 160, "crypt_stone1")  # piers on the landings
        L.light((0, y, z + 128), 200, CANDLE)
    L.light((0, -680, -200), 200, CANDLE)

    # The charnel hall.
    L.room(-512, -1536, HALL, 512, -768, -64, wall="ossuary1", floor="ash_floor1", ceiling="crypt_stone1")
    L.opening(-96, -800, HALL, 96, -768, HALL + 160)
    pilasters(L, -512, 512, -1536, -768, HALL, -64, "w")
    pilasters(L, -512, 512, -1536, -768, HALL, -64, "e")
    for x in (-256, 0, 256):                                                    # the vault's piers
        for y in (-1024, -1280):
            if x == 0:
                continue
            L.solid(x - 32, y - 32, HALL, x + 32, y + 32, -64, "kirk_column1")
    # Biers in rows, and the heap of bones waiting by the kiln chute.
    for x in (-384, -160, 160, 384):
        for y in (-960, -1152, -1344):
            L.solid(x - 48, y - 24, HALL, x + 48, y + 24, HALL + 32, "oak1")
    L.solid(-64, -1504, HALL, 64, -1440, HALL + 40, "crypt_stone1")             # the bier at the south end
    L.solid(-72, -1512, HALL + 40, 72, -1432, HALL + 48, "kirk_trim1")
    L.add("item_key1", (0, -1472, HALL + 48))
    L.light((0, -1400, HALL + 120), 240, EMBER)
    for x in (-400, 400):
        for y in (-896, -1152, -1408):
            L.light((x + (-60 if x > 0 else 60), y, HALL + 200), 220, CANDLE)
    L.light((0, -1152, -96), 360, COLD)
    L.light((0, -900, -100), 260, CANDLE)

    # The congregation: Ashen in the crypt, the wraiths in the hall.
    L.add("monster_ashen", (-200, 400, 24), angle=0)
    L.add("monster_ashen", (200, 400, 24), angle=180)
    L.add("monster_censer", (0, -144, -100), angle=90)
    L.add("monster_ashen", (0, -496, -232), angle=90)
    for x, y in ((-170, -1000), (170, -1250), (0, -1400)):
        L.add("monster_ash_wraith", (x, y, HALL + 120), angle=90)
    L.add("monster_deacon", (0, -1360, HALL + 24), angle=90)
    for x, y in ((-384, -1060), (384, -1060)):
        L.add("monster_ashen", (x, y, HALL + 24), angle=90)

    L.add("item_shells", (-240, 560, 0))
    L.add("item_health", (240, 560, 0))
    L.add("item_spikes", (40, -144, -128))
    L.add("item_health", (-120, -1400, HALL))
    L.add("item_rockets", (440, -1480, HALL))
    L.add("item_armor1", (-440, -1480, HALL))
    L.add("weapon_supershotgun", (0, 352, 0))

    # The silver door in the hall's east wall, and the cage on.
    L.opening(512, -1216, HALL, 544, -1088, HALL + 128)
    L.brush_entity("func_door", [Box(512, -1216, HALL, 544, -1088, HALL + 128, "door_iron1")],
                   angle=-1, spawnflags=16, speed=60, wait=-1, lip=8, sounds=2)
    L.room(544, -1248, HALL, 704, -1056, HALL + 192, wall="crypt_stone1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((624, -1152, HALL + 160), 160, CANDLE)
    L.brush_entity("trigger_changelevel", [Box(576, -1216, HALL, 672, -1088, HALL + 96, "trigger")], map="kilns2")
    L.add("info_intermission", (-400, -800, -120), mangle=(25, -60, 0))
    L.nook(400, -1536, -384, "s", ('item_armor1', 'item_spikes'), wall="crypt_stone1", floor="crypt_stone1")   # a secret behind cracked stone
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "kilns1.map")
    build().save(out)
    print(out)
