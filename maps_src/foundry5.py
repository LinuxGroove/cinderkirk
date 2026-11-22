#!/usr/bin/env python3
"""The Pour (foundry5.map), the end of the Foundry shaft.

The great casting hall, where the Deacons are pouring the new bell's mould.
Galleries run round the top; slag runs from the furnace mouth in the east
wall down a channel to the mould on its dais in the middle, under the cope.
Free the crane's two chains, one from each gallery, and the cope lifts off
the Foundry Seal. Taking it opens the cage home to the Pithead.

    python3 maps_src/foundry5.py maps_src/foundry5.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

WARM = (1.0, 0.62, 0.32)
SLAG = (1.0, 0.42, 0.12)
COLD = (0.62, 0.72, 1.0)
CANDLE = (1.0, 0.8, 0.55)
X0, Y0, X1, Y1 = 0, -640, 1536, 640
FLOOR, GAL = -256, 0


def build():
    L = Level(wad="cinder.wad", light_wait=0.7, sounds=4, message="The Pour", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    # The cage's landing on the west side, at gallery height.
    L.room(-224, -96, 0, -32, 96, 192, wall="iron_rust1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 180, WARM)
    L.opening(-32, -64, 0, 0, 64, 128)

    # The hall: casting floor at -256 over a channel cut to -320, galleries at 0, roof 576.
    L.room(X0, Y0, -320, X1, Y1, 576, wall="kirk_brick1", floor="ash_floor1", ceiling="ceil_timber1")
    L.solid(X0, Y0, -320, X1, -64, FLOOR, "firebrick1")                 # the floor either side of the channel
    L.solid(X0, 64, -320, X1, Y1, FLOOR, "firebrick1")
    L.solid(X0, -64, -320, 896, 64, FLOOR, "firebrick1")                # the channel stops at the mould
    L.liquid(896, -64, -320, X1, 64, -288)
    # The west gallery you come in on, and the two long ones.
    L.solid(X0, -448, FLOOR, 192, 448, GAL, "kirk_stone1")
    for y0, y1 in ((Y0, -448), (448, Y1)):
        L.solid(X0, y0, FLOOR, X1, y1, GAL, "kirk_stone1")
        L.solid(X0, y0, GAL, X1, y1, GAL + 8, "iron_plate1")
    L.solid(X0, -448, GAL, 192, 448, GAL + 8, "iron_plate1")
    for x0, y0, x1, y1 in ((192, -448, 208, -128), (192, 128, 208, 448),   # rails
                           (192, -464, X1, -448), (192, 448, X1, 464)):
        L.solid(x0, y0, GAL + 8, x1, y1, GAL + 40, "brass_trim1")
    L.steps(192, -128, 448, 128, GAL, FLOOR)                            # down to the floor from the west
    L.steps(1280, 320, 1408, 448, FLOOR, GAL, axis="y")                  # and back up at the east end
    L.steps(1280, -448, 1408, -320, GAL, FLOOR, axis="y")

    # The furnace mouth in the east wall, the channel running out of it.
    for y0, y1 in ((-224, -64), (64, 224)):
        L.solid(1408, y0, FLOOR, X1, y1, 256, "firebrick1")
    L.solid(1408, -64, -160, X1, 64, 256, "firebrick1")
    L.solid(1392, -240, 256, X1, 240, 288, "kirk_trim1")
    for x in (1024, 1216):                                              # bridges over the channel
        L.solid(x, -96, FLOOR - 8, x + 64, 96, FLOOR, "iron_plate1")
    for x in range(960, 1408, 128):
        L.add("light", (x + 32, 0, -270), light=180, _color=SLAG)
    L.add("light", (1460, 0, -200), light=260, _color=SLAG)

    # The mould on its dais, and the cope hanging from the crane over it.
    L.solid(640, -160, FLOOR, 896, 160, FLOOR + 32, "kirk_stone1")
    L.steps(576, -64, 640, 64, FLOOR, FLOOR + 32)
    L.solid(672, -128, FLOOR + 32, 864, 128, FLOOR + 48, "sand_mould1")
    cope = [Box(704, -80, FLOOR + 48, 720, 80, FLOOR + 176, "bronze1"),     # hollow, over the Seal
            Box(816, -80, FLOOR + 48, 832, 80, FLOOR + 176, "bronze1"),
            Box(720, -80, FLOOR + 48, 816, -64, FLOOR + 176, "bronze1"),
            Box(720, 64, FLOOR + 48, 816, 80, FLOOR + 176, "bronze1"),
            Box(704, -80, FLOOR + 176, 832, 80, FLOOR + 192, "bronze1"),
            Box(720, -64, FLOOR + 192, 816, 64, FLOOR + 224, "bronze1")]
    L.brush_entity("func_door", cope,
                   angle=-1, targetname="cope", speed=40, wait=-1, lip=-160,
                   sounds=2)
    L.add("item_sigil", (768, 0, FLOOR + 72), spawnflags=1)
    for y in (-48, 48):
        L.solid(766, y - 2, FLOOR + 224, 770, y + 2, 544, "iron_plate1")   # the chains
    L.solid(X0, -24, 544, X1, 24, 576, "iron_rust1")                       # the crane's girder
    L.add("light", (768, 0, FLOOR + 260), light=220, _color=WARM)
    for y in (-200, 200):
        L.add("light", (768, y, FLOOR + 64), light=180, _color=SLAG)

    # The chain releases, one on each gallery wall. Both free the cope.
    for y, side in ((Y1 - 12, "north"), (Y0, "south")):
        L.brush_entity("func_button", [Box(752, y, 48, 784, y + 12, 96, "brass_trim1")],
                       angle=90 if y > 0 else 270, target="chains", wait=-1, lip=4,
                       message=f"The {side} chain runs free")
        L.light((768, y + (-48 if y > 0 else 60), 112), 140, CANDLE)
    L.add("trigger_counter", None, targetname="chains", count=2, spawnflags=1,
          target="cope", message="The cope lifts off the mould")

    # Pick-ups.
    L.add("item_health", (96, 300, GAL + 8), spawnflags=2)
    L.add("item_shells", (96, -300, GAL + 8))
    L.add("item_rockets", (600, 560, GAL + 8))
    L.add("item_spikes", (600, -560, GAL + 8))
    L.add("item_cells", (1100, 560, GAL + 8))
    L.add("item_health", (1100, -560, GAL + 8))
    L.add("item_armor2", (1480, 560, GAL + 8))
    L.add("item_health", (300, 300, FLOOR))
    L.add("item_health", (300, -300, FLOOR))
    L.add("item_rockets", (1100, 300, FLOOR))
    L.add("item_shells", (1100, -300, FLOOR))

    # The congregation.
    for x in (500, 1000, 1400):
        L.add("monster_censer", (x, 560, GAL + 32), angle=270)
        L.add("monster_censer", (x, -560, GAL + 32), angle=90)
    L.add("monster_crucible_brute", (1080, 260, FLOOR + 24), angle=180)
    L.add("monster_crucible_brute", (1080, -260, FLOOR + 24), angle=180)
    for x in (700, 1300):
        L.add("monster_gauger", (x, 540, GAL + 32), angle=270)
    L.add("monster_deacon", (768, 300, FLOOR + 24), angle=270)
    L.add("monster_deacon", (768, -300, FLOOR + 24), angle=90)
    L.add("monster_deacon", (1350, 0, FLOOR + 24), angle=180, spawnflags=1)
    for x, y in ((450, 250), (450, -250), (1200, 380), (1200, -380)):
        L.add("monster_ashen", (x, y, FLOOR + 24), angle=180)
    for x, y in ((900, 400), (900, -400), (1300, 200), (1300, -200)):
        L.add("monster_slag_hound", (x, y, FLOOR + 24), angle=180, spawnflags=1)

    # Light: lamps hung from the roof over the floor, candles on the galleries.
    for x in (320, 768, 1216):
        for y in (-256, 256):
            L.solid(x - 8, y - 8, 384, x + 8, y + 8, 416, "lamp_amber1")
            L.solid(x - 2, y - 2, 416, x + 2, y + 2, 576, "iron_plate1")
            L.light((x, y, 360), 400, WARM)
        for y in (-560, 560):
            L.light((x, y, 120), 220, CANDLE)
    L.light((768, 0, 480), 400, COLD)
    L.light((96, 0, 120), 220, CANDLE)

    # The cage home, behind a gate in the east end of the south gallery that the cope opens.
    L.opening(X1, -608, GAL, X1 + 32, -480, GAL + 128)
    L.brush_entity("func_door", [Box(X1, -608, GAL, X1 + 32, -480, GAL + 128, "door_iron1")],
                   angle=-1, targetname="cope", speed=80, wait=-1, lip=8)
    L.room(X1 + 32, -640, GAL, X1 + 192, -448, GAL + 192, wall="iron_rust1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((X1 + 112, -544, GAL + 160), 160, WARM)
    L.brush_entity("trigger_changelevel", [Box(X1 + 64, -608, GAL, X1 + 160, -480, GAL + 96, "trigger")], map="start")
    L.add("info_intermission", (100, -400, 300), mangle=(30, 30, 0))
    L.nook(1536, 528, 8, "e", ('item_armor2', 'item_health'), wall="kirk_stone1", floor="coal1")   # a secret behind cracked stone
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "foundry5.map")
    build().save(out)
    print(out)
