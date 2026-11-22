#!/usr/bin/env python3
"""The Bell Pit (foundry4.map), the Foundry shaft's fourth map.

The pit where the great bells are cast: terraces step down round four sides
to the mould at the bottom, a bell's cope hanging over it from the crane.
The gold key waits beside the mould; the gold door is at the top of the far
side, so the way on is down and back up again. Past it, the cage to the Pour.

    python3 maps_src/foundry4.py maps_src/foundry4.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

WARM = (1.0, 0.62, 0.32)
SLAG = (1.0, 0.42, 0.12)
COLD = (0.62, 0.72, 1.0)
CANDLE = (1.0, 0.8, 0.55)
X0, Y0, X1, Y1 = 0, -512, 1024, 512


def frame(L, inset0, inset1, top, tex, bottom=-384):
    """A ring of floor between two insets from the pit's walls, at `top`."""
    a = (X0 + inset0, Y0 + inset0, X1 - inset0, Y1 - inset0)
    b = (X0 + inset1, Y0 + inset1, X1 - inset1, Y1 - inset1)
    L.solid(a[0], a[1], bottom, a[2], b[1], top, tex)        # south
    L.solid(a[0], b[3], bottom, a[2], a[3], top, tex)        # north
    L.solid(a[0], b[1], bottom, b[0], b[3], top, tex)        # west
    L.solid(b[2], b[1], bottom, a[2], b[3], top, tex)        # east


def build():
    L = Level(start_light=190, wad="cinder.wad", light_wait=0.7, sounds=4, message="The Bell Pit", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=6, _range=0.6)

    # The cage's landing on the west side, at the top.
    L.room(-224, -96, 0, -32, 96, 192, wall="iron_rust1", floor="iron_plate1", ceiling="iron_rust1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 180, WARM)
    L.opening(-32, -64, 0, 0, 64, 128)

    # The pit: the mould's floor at -384, terraces at -256, -128 and 0, roof 448.
    L.room(X0, Y0, -384, X1, Y1, 448, wall="kirk_brick1", floor="sand_mould1", ceiling="ceil_timber1")
    frame(L, 0, 128, 0, "kirk_stone1")
    frame(L, 128, 256, -128, "kirk_stone1")
    frame(L, 256, 384, -256, "kirk_stone1")
    for inset, top in ((0, 0), (128, -128), (256, -256)):    # a carved band along each terrace's edge
        frame(L, inset + 112, inset + 128, top + 8, "kirk_trim1", bottom=top)
    L.steps(448, 256, 576, 384, -128, 0, axis="y")             # down the north side
    L.steps(768, -64, 896, 64, -256, -128)                     # down the east side
    L.steps(448, -384, 576, -256, -256, -384, axis="y")        # and the south, to the floor
    # The mould, and the bell's cope over it on the crane's chains.
    L.solid(432, -80, -384, 592, 80, -352, "sand_mould1")
    L.solid(448, -64, -352, 576, 64, -240, "bronze1")
    L.solid(464, -48, -240, 560, 48, -208, "bronze1")
    L.solid(432, -80, -96, 592, 80, -64, "bronze1")             # the cope
    L.solid(456, -56, -64, 568, 56, 16, "bronze1")
    L.solid(496, -16, 16, 528, 16, 48, "bronze1")
    for x in (480, 544):
        L.solid(x - 2, -2, 48, x + 2, 2, 400, "iron_plate1")
    L.solid(-0, -24, 400, 1024, 24, 432, "iron_rust1")         # the crane's girder
    L.add("light", (512, 120, -360), light=200, _color=SLAG)
    L.add("light", (512, -120, -360), light=200, _color=SLAG)
    L.add("item_key2", (512, 104, -360))
    L.add("item_health", (420, -100, -384))
    L.add("item_rockets", (600, -100, -384))

    L.add("item_shells", (64, 400, 0))
    L.add("item_spikes", (960, -400, 0))
    L.add("item_health", (200, 200, -128))
    L.add("item_cells", (820, 300, -128))
    L.add("weapon_rocketlauncher", (300, -300, -128))
    L.add("monster_gauger", (960, 300, 24), angle=180)
    L.add("monster_gauger", (960, -300, 24), angle=180)
    L.add("monster_clinker", (300, 300, -104), angle=270, spawnflags=2)
    L.add("monster_clinker", (700, -300, -104), angle=90, spawnflags=2)
    L.add("monster_clinker", (200, -200, -104), angle=0, spawnflags=2)
    L.add("monster_ashen", (200, 320, -104), angle=270)
    L.add("monster_ashen", (800, 320, -104), angle=270)
    L.add("monster_ashen", (200, -320, -104), angle=90)
    L.add("monster_ashen", (350, -200, -232), angle=0)
    L.add("monster_ashen", (650, 200, -232), angle=180)
    L.add("monster_slag_hound", (400, 100, -360), angle=0)
    L.add("monster_slag_hound", (620, -100, -360), angle=180)
    L.add("monster_deacon", (512, -200, -232), angle=90, spawnflags=1)
    for x, y in ((256, 256), (768, 256), (256, -256), (768, -256)):
        L.solid(x - 8, y - 8, 240, x + 8, y + 8, 272, "lamp_amber1")
        L.solid(x - 2, y - 2, 272, x + 2, y + 2, 448, "iron_plate1")
        L.light((x, y, 216), 360, WARM)
    for x in (64, 960):
        for y in (-448, 448):
            L.light((x, y, 96), 200, CANDLE)
    L.light((512, 0, 300), 300, COLD)

    # The gold door at the top of the east side, and the cage to the Pour.
    L.opening(1024, -64, 0, 1056, 64, 128)
    L.brush_entity("func_door", [Box(1024, -64, 0, 1056, 64, 128, "door_iron1")],
                   angle=-1, spawnflags=8, speed=80, wait=-1, lip=8)
    L.room(1056, -96, 0, 1184, 96, 192, wall="iron_rust1", floor="iron_plate1", ceiling="iron_rust1")
    L.light((1120, 0, 160), 160, WARM)
    L.brush_entity("trigger_changelevel", [Box(1088, -64, 0, 1168, 64, 96, "trigger")], map="foundry5")
    L.add("info_intermission", (100, -420, 300), mangle=(35, 35, 0))
    L.nook(1024, 336, 0, "e", ('item_armor1', 'item_rockets'), wall="kirk_stone1", floor="coal1")   # a secret behind cracked stone
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "foundry4.map")
    build().save(out)
    print(out)
