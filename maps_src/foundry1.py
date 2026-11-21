#!/usr/bin/env python3
"""The Foundry Gate (foundry1.map): the Foundry shaft's first map, about fifteen minutes.

The gatehouse where you come in, steps down to the Casting Floor with a slag
channel across it and an iron bridge; the pattern shop off its north side,
with the silver key up on the mezzanine and cracked stone hiding a closet;
the pouring gallery above its south side, where a ladle pours slag and a steam
vent throws you up to a hidden ledge; the key door to the quench pit, a black
tank of water with a button to open the belfry, where the way down opens.

    python3 maps_src/foundry1.py maps_src/foundry1.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Level  # noqa: E402

WARM = (1.0, 0.62, 0.32)
SLAG = (1.0, 0.42, 0.12)
COLD = (0.62, 0.72, 1.0)
CANDLE = (1.0, 0.8, 0.55)


def build():
    L = Level(wad="cinder.wad", message="The Foundry Gate", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    # The gatehouse: x 0..512, floor 0, ceiling 256.
    L.room(0, -256, 0, 512, 256, 256, ceiling="ceil_timber1")
    # Pillars 64 wide on the 64 grid, so each glyph stone shows one whole mark.
    for y in (-256, 224):
        for x in (128, 320):
            L.solid(x, y, 0, x + 64, y + 32, 256, "kirk_column1")
            gy0, gy1 = (y + 32, y + 34) if y < 0 else (y - 2, y)
            L.solid(x, gy0, 64, x + 64, gy1, 128, "kirk_glyph1")
    for x in (64, 192, 320, 448):
        L.solid(x, -256, 208, x + 24, 256, 232, "oak_beam1")
    L.add("info_player_start", (48, 0, 24), angle=0)
    L.add("info_player_deathmatch", (48, 128, 24), angle=0)
    L.add("info_player_deathmatch", (48, -128, 24), angle=0)
    L.add("item_shells", (256, 160, 0))
    L.add("item_health", (256, -192, 0))
    L.add("item_shells", (400, 64, 0))
    for x in (160, 416):
        L.light((x, 0, 176), 240, WARM)
    L.light((256, 200, 120), 160, CANDLE)
    L.light((256, -200, 120), 160, CANDLE)

    # First lessons as you cross the gatehouse, with the button for the device in hand.
    for x0, x1, text in ((112, 144, "{impulse 20} Dash: a burst of steam that spends Pressure"),
                         (272, 304, "Hold {+wheel} for the weapon wheel"),
                         (464, 496, "{impulse 21} Overpressure: your weapon's second fire")):
        L.brush_entity("trigger_once", [_box(x0, -224, 0, x1, 224, 128, "trigger")], message=text)

    # The arch down to the Casting Floor.
    L.opening(512, -96, 0, 544, 96, 192)

    # The Casting Floor: x 544..1568, floor -64, ceiling 384.
    L.room(544, -384, -64, 1568, 384, 384, ceiling="ceil_timber1", floor_depth=128)
    # Sooted brick to chest height and a carved band along both long walls,
    # broken for the door to the pattern shop.
    for (x0, x1) in ((640, 1568),):
        L.solid(x0, -384, -64, x1, -376, 32, "kirk_brick2")
        L.solid(x0, -384, 32, x1, -372, 64, "kirk_trim1")
    for (x0, x1) in ((640, 1136), (1216, 1568)):
        L.solid(x0, 376, -64, x1, 384, 32, "kirk_brick2")
        L.solid(x0, 372, 32, x1, 384, 64, "kirk_trim1")
    L.steps(544, -96, 640, 96, 0, -64, base=-64)
    L.solid(544, -384, -64, 640, -96, 0, "kirk_stone1")   # the landing either side
    L.solid(544, 96, -64, 640, 384, 0, "kirk_stone1")
    # The slag channel across the hall, 96 deep, and the bridge over it.
    L.opening(928, -384, -160, 1120, 384, -64)
    L.solid(928, -416, -192, 1120, 416, -160, "kirk_stone1")
    L.liquid(928, -384, -160, 1120, 384, -112)
    L.solid(928, -64, -80, 1120, 64, -64, "iron_grid1")
    for y0 in (-64, 56):
        L.solid(928, y0, -64, 1120, y0 + 8, -24, "iron_rust1")
        for x in (928, 1016, 1104):
            L.solid(x, y0, -64, x + 16, y0 + 8, 0, "bronze1")
    # Pillars with glyph stones, and the tie beams.
    for x in (704, 832, 1216, 1344, 1472):
        for y in (-384, 352):
            L.solid(x, y, -64, x + 64, y + 32, 384, "kirk_stone1")
            gy0, gy1 = (y + 32, y + 34) if y < 0 else (y - 2, y)
            L.solid(x, gy0, 0, x + 64, gy1, 64, "kirk_glyph1")
        L.solid(x + 16, -384, 300, x + 48, 384, 332, "oak_beam1")
    # The plinth at the far end, with slag on it.
    L.solid(1440, -48, -64, 1536, 48, -32, "bronze1")
    L.solid(1436, -52, -36, 1540, 52, -32, "brass_trim1")   # its brass rim
    L.add("item_spikes", (1488, 0, -32))
    L.add("item_spikes", (1360, 256, -64))
    L.add("item_armor1", (720, 300, -64))
    L.add("item_health", (1200, -300, -64))
    # Who's waiting.
    # The cult, its dead and a pack of slag hounds, all facing the plinth: they
    # notice you on the floor, not from the gatehouse.
    L.add("monster_censer", (800, 120, -40), angle=0)
    L.add("monster_censer", (800, -160, -40), angle=0)
    L.add("monster_ashen", (860, 260, -40), angle=0)
    L.add("monster_ashen", (860, -280, -40), angle=0)
    L.add("monster_slag_hound", (1250, 0, -40), angle=0)
    L.add("monster_slag_hound", (1300, 200, -40), angle=0)
    L.add("monster_slag_hound", (1300, -200, -40), angle=0)
    L.add("monster_deacon", (1390, 0, -40), angle=0)
    L.add("monster_censer", (1450, -250, -40), angle=0)
    L.add("monster_ashen", (1420, 120, -40), angle=0)
    L.add("monster_ashen", (1420, -120, -40), angle=0)
    # Light: the slag, braziers along the walls, cold light from high up.
    L.add("light", (1024, 0, -100), light=200, _color=SLAG, _surface="*lava_slag1",
          _surface_offset=12)
    for x in (760, 1260, 1440):
        L.light((x, -300, 64), 260, WARM)
        L.light((x, 300, 64), 260, WARM)
    for x in (700, 1024, 1350):
        L.light((x, 0, 340), 220, COLD, wait=2)
    for x in (820, 1240):                     # lamps hung over the middle of the floor
        L.light((x, 0, 128), 300, WARM)
    L.light((1488, 0, 48), 200, (0.85, 0.85, 1.0))
    for y in (-110, 110):
        L.light((1540, y, 40), 220, WARM)
    for x in (960, 1088):
        L.light((x, 0, 40), 180, WARM)

    # The pattern shop, off the north side of the hall: x 1088..1536, floor -64.
    L.opening(1136, 384, -64, 1216, 416, 96)
    L.room(1088, 416, -64, 1536, 864, 256, wall="plaster1", floor="oak1", ceiling="ceil_timber1")
    for y in (544, 672):                      # racks of wooden patterns, chest high
        for x0, x1 in ((1120, 1296), (1344, 1440)):
            L.solid(x0, y, -64, x1, y + 16, 16, "oak1")
            L.solid(x0, y - 16, -8, x1, y + 32, 0, "oak1")
            L.solid(x0, y - 16, 16, x1, y + 32, 24, "oak1")
            for px in range(x0 + 16, x1 - 32, 56):      # patterns on the shelves: bells and wheels
                L.solid(px, y - 8, 24, px + 32, y + 24, 56, "oak1" if (px // 56) % 2 else "bronze1")
    L.solid(1088, 768, 80, 1536, 864, 96, "oak1")          # the mezzanine
    L.solid(1328, 432, -64, 1472, 512, -52, "oak1")         # a moulding box, half rammed
    L.solid(1336, 440, -52, 1464, 504, -50, "sand_mould1")
    L.steps(1472, 560, 1536, 768, -64, 96, axis="y", tex="oak1")
    for x in (1152, 1312, 1456):
        L.solid(x, 760, -64, x + 16, 776, 80, "oak1")        # its posts
    L.add("item_key1", (1180, 816, 120))      # keys stand on their middle
    L.add("item_health", (1500, 460, -64))
    L.add("item_shells", (1120, 460, -64))
    L.add("monster_ashen", (1200, 610, -40), angle=270)
    L.add("monster_ashen", (1380, 610, -40), angle=270)
    L.add("monster_ashen", (1250, 730, -40), angle=270)
    L.add("monster_censer", (1300, 816, 120), angle=270)
    L.add("monster_censer", (1480, 820, 120), angle=270)
    for x in (1200, 1440):                    # lamps hung from the ceiling
        L.solid(x - 8, 472, 136, x + 8, 488, 168, "lamp_amber1")
        L.solid(x - 2, 478, 168, x + 2, 482, 256, "iron_plate1")
        L.light((x, 480, 116), 220, WARM)
    L.light((1300, 816, 200), 200, CANDLE)
    L.light((1180, 816, 150), 160, (0.85, 0.85, 1.0))
    L.light((1300, 640, 200), 180, WARM)

    # Cracked stone in the shop's west wall, and the closet behind it (secret).
    L.opening(1056, 592, -64, 1088, 688, 32)
    L.brush_entity("func_cracked", [_box(1056, 592, -64, 1088, 688, 32, "kirk_crack1")])
    L.room(960, 576, -64, 1056, 704, 64, wall="kirk_stone1", floor="coal1")
    L.brush_entity("trigger_secret", [_box(968, 584, -64, 1048, 696, 0, "trigger")])
    L.add("item_armor2", (1000, 640, -64))
    L.add("item_health", (1000, 600, -64), spawnflags=2)
    L.light((1008, 640, 40), 200, (1.0, 0.82, 0.62))   # whiter, so the pickups show their colours

    # The pouring gallery, above the south side: x 560..1504, its floor at 128.
    L.opening(560, -448, 0, 640, -384, 112)
    L.room(560, -800, 0, 1504, -448, 384, wall="firebrick1", floor="iron_plate1", ceiling="ceil_timber1")
    L.solid(656, -800, 0, 1504, -448, 124, "kirk_stone1")
    L.solid(656, -800, 124, 1504, -448, 128, "ash_floor1")
    L.solid(560, -800, 0, 656, -608, 128, "kirk_stone1")
    L.steps(560, -608, 656, -448, 128, 0, axis="y", base=0)
    for x in (960, 1160):                                  # windows down onto the hall
        L.opening(x, -448, 176, x + 96, -384, 256)
    # The ladle's pour: slag falling into a basin cut into the floor.
    L.opening(1376, -704, 64, 1472, -608, 128)
    L.liquid(1376, -704, 64, 1472, -608, 104)
    L.liquid(1408, -672, 104, 1440, -640, 340)
    L.solid(1392, -688, 340, 1456, -624, 384, "bronze1")     # the ladle's lip
    for x in (720, 880, 1040):                              # crucibles cooling
        L.solid(x, -780, 128, x + 64, -716, 176, "bronze1")
    L.add("weapon_nailgun", (760, -560, 136))
    L.add("item_spikes", (900, -560, 128))
    L.add("item_health", (1240, -520, 128))
    L.add("monster_censer", (1100, -620, 152), angle=180)
    L.add("monster_censer", (1300, -520, 152), angle=180)
    L.add("monster_slag_hound", (900, -640, 152), angle=180)
    L.add("monster_slag_hound", (960, -580, 152), angle=180)
    L.add("monster_deacon", (1250, -700, 152), angle=180)
    L.add("light", (1424, -656, 200), light=260, _color=SLAG)
    for x in (760, 1080):
        L.light((x, -560, 300), 240, WARM)
    L.light((620, -520, 80), 160, CANDLE)
    # The vent, and the ledge it throws you up to (secret).
    L.solid(1248, -720, 128, 1312, -656, 132, "vent_grate1")
    L.brush_entity("trigger_vent", [_box(1252, -716, 132, 1308, -660, 164, "trigger")], speed=620)
    L.solid(1184, -800, 288, 1376, -736, 304, "iron_plate1")
    L.brush_entity("trigger_secret", [_box(1184, -800, 304, 1376, -736, 360, "trigger")])
    L.add("item_health", (1280, -768, 304), spawnflags=2)
    L.add("item_shells", (1220, -768, 304))
    L.light((1280, -768, 360), 120, COLD)

    # The key door to the quench pit.
    L.opening(1568, -64, -64, 1600, 64, 64)
    L.brush_entity("func_door", [_box(1568, -64, -64, 1600, 64, 64, "door_iron1")],
                   angle=-1, spawnflags=16, speed=80, wait=-1, lip=8)

    # The quench pit: x 1600..2240, floor -192, a tank of black water.
    L.room(1600, -320, -192, 2240, 320, 384, wall="kirk_stone1", floor="floor_flag1",
           floor_depth=160)
    L.solid(1600, -320, -192, 1728, 320, -64, "kirk_stone1")   # the landing by the door
    L.steps(1728, -320, 1856, -224, -64, -192)
    L.steps(1728, 224, 1856, 320, -64, -192)
    L.opening(1888, -224, -320, 2176, 224, -192)
    L.liquid(1888, -224, -320, 2176, 224, -216, "*water1")
    for x in (1888, 2144):                                    # the tank's iron lip
        L.solid(x, -224, -192, x + 32, 224, -184, "iron_rust1")
    L.add("monster_fish", (2000, -100, -280))
    L.add("monster_fish", (2060, 120, -280))
    L.add("monster_censer", (2200, -260, -168), angle=180)
    L.add("monster_censer", (2200, 260, -168), angle=180)
    L.add("monster_ashen", (1950, 270, -168), angle=180)
    L.add("monster_ashen", (1950, -270, -168), angle=180)
    L.add("monster_deacon", (2180, 0, -168), angle=180)
    L.add("item_health", (1650, 260, -64))
    L.add("item_spikes", (1650, -260, -64))
    L.add("light", (2032, 0, -200), light=90, _color=(0.4, 0.6, 0.7), _surface="*water1")
    for y in (-260, 260):
        L.light((2032, y, 200), 300, COLD)
        L.light((1660, y, 80), 240, WARM)
        L.light((2200, y, -100), 220, WARM)
    L.light((1780, 0, -120), 220, WARM)
    for y in (-312, 296):                                   # copper pipes feeding the tank
        L.solid(1728, y, 160, 2240, y + 16, 176, "copper1")
    # A vent in the far corner up to a balcony with ammo.
    L.solid(2176, 240, -192, 2240, 304, -188, "vent_grate1")
    L.brush_entity("trigger_vent", [_box(2180, 244, -188, 2236, 300, -156, "trigger")], speed=640)
    L.solid(2112, 240, 80, 2240, 320, 96, "iron_plate1")
    L.add("item_shells", (2176, 290, 96))
    L.add("item_spikes", (2136, 290, 96))
    # The button that lifts the belfry gate.
    L.brush_entity("func_button", [_box(2232, -32 - 160, -144, 2240, 32 - 160, -112, "bronze1")],
                   angle=0, target="belfry_gate", wait=-1, lip=4)
    L.light((2200, -160, -100), 120, (0.85, 0.85, 1.0))
    L.opening(2240, -64, -192, 2272, 64, -64)
    L.brush_entity("func_door", [_box(2240, -64, -192, 2272, 64, -64, "door_iron1")],
                   angle=-1, targetname="belfry_gate", speed=100, wait=-1, lip=8)

    # The belfry: x 2272..2656, floor -192, tall.
    L.room(2272, -192, -192, 2656, 192, 384, floor="kiln_tile1", ceiling="ceil_timber1")
    for x in (2336, 2528):
        L.solid(x, -192, 280, x + 32, 192, 312, "oak_beam1")
    L.solid(2440, -8, 200, 2456, 8, 296, "iron_plate1")          # the bell's hanger
    L.solid(2400, -48, 120, 2496, 48, 200, "bronze1")            # and the bell
    L.solid(2384, -64, 104, 2512, 64, 120, "bronze1")
    L.add("monster_censer", (2432, 96, -168), angle=180)
    L.add("monster_ashen", (2432, -96, -168), angle=180)
    L.add("item_health", (2600, 120, -192))
    L.light((2464, 0, 240), 380, WARM)
    for y in (-150, 150):
        L.light((2380, y, -40), 220, CANDLE)
    L.light((2592, 0, -96), 200, SLAG)
    L.brush_entity("trigger_changelevel", [_box(2592, -64, -192, 2656, 64, -64, "trigger")],
                   map="foundry2")
    L.add("info_intermission", (1024, -300, 160), mangle=(20, 30, 0))
    return L


def _box(*a):
    from mapkit import Box
    return Box(*a)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "start.map")
    build().save(out)
    print(out)
