#!/usr/bin/env python3
"""The Drowned Chapel (cisterns_s.map), the Cisterns shaft's secret map,
behind the cracked wall in the Long Vault's south pump room.

The foundry's first chapel, flooded when the cisterns were dug: a nave
under black water with the pews' backs showing, a gallery round the top,
and on the altar, still dry, the Quench Suit. The way on climbs from the
altar to the cage down to the settling tanks.

    python3 maps_src/cisterns_s.py maps_src/cisterns_s.map
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from mapkit import Box, Level  # noqa: E402

LAMP = (0.95, 0.80, 0.58)
DAMP = (0.55, 0.85, 0.75)
CANDLE = (1.0, 0.8, 0.55)


def build():
    L = Level(start_light=150, wad="cinder.wad", light_wait=0.6, sounds=5, message="The Drowned Chapel", worldtype=0,
              _bounce=1, _bouncescale=1.0, _minlight=4, _range=0.6)

    L.room(-224, -96, 0, -32, 96, 192, wall="cist_brick1", floor="cist_stone1", ceiling="cist_brick1")
    L.add("info_player_start", (-160, 0, 24), angle=0)
    L.add("info_player_coop", (-160, 48, 24), angle=0)
    L.add("info_player_coop", (-160, -48, 24), angle=0)
    L.light((-128, 0, 160), 160, DAMP)
    L.opening(-32, -64, 0, 0, 64, 128)

    # The nave: x 0..1152, y -320..320, its floor at -256 under water to -48;
    # a gallery round three sides at 0; the altar's dais at the east end.
    L.room(0, -320, -256, 1152, 320, 512, wall="plaster1", floor="kiln_tile1", ceiling="ceil_timber1")
    L.liquid(0, -320, -256, 1152, 320, -48, "*cistern1")
    for y0, y1 in ((-320, -224), (224, 320)):
        L.solid(0, y0, -256, 1152, y1, 0, "cist_stone1")
    L.solid(0, -224, -256, 96, 224, 0, "cist_stone1")
    L.solid(896, -224, -256, 1152, 224, 0, "cist_stone1")                 # the chancel
    L.solid(960, -96, 0, 1088, 96, 32, "kirk_stone1")                      # the altar
    L.add("item_artifact_envirosuit", (1024, 0, 32 + 24))       # powerups stand 24 over the floor
    L.steps(816, -64, 896, 64, -48, 0)
    for x in range(192, 832, 96):                                          # the pews' backs
        for y0, y1 in ((-200, -40), (40, 200)):
            L.solid(x, y0, -256, x + 16, y1, -24, "sluice_wood1")
    for x in (288, 576, 864):                                              # columns
        for y in (-224, 192):
            L.solid(x, y, -256, x + 32, y + 32, 512, "kirk_column1")
    L.solid(1120, -128, 64, 1152, 128, 384, "kirk_glyph1")                 # the east wall's carving
    for x, y in ((300, 0), (500, -120), (700, 120), (420, 140)):
        L.add("monster_leech", (x, y, -160), angle=0)
    L.add("monster_deacon", (1000, 150, 24), angle=180)
    L.add("monster_censer", (600, 270, 24), angle=270)
    L.add("monster_censer", (600, -270, 24), angle=90)
    L.add("item_health", (60, 260, 0), spawnflags=2)
    L.add("item_cells", (1100, -260, 0))
    for x in (200, 600, 1000):
        L.light((x, -270, 120), 220, CANDLE)
        L.light((x, 270, 120), 220, CANDLE)
    L.light((1024, 0, 200), 300, LAMP)
    L.light((500, 0, -150), 260, DAMP)

    # The vestry behind the altar, and the cage on.
    L.opening(1152, -64, 0, 1184, 64, 128)
    L.room(1184, -96, 0, 1344, 96, 192, wall="plaster1", floor="cist_stone1", ceiling="ceil_timber1")
    L.light((1264, 0, 160), 160, LAMP)
    L.brush_entity("trigger_changelevel", [Box(1248, -64, 0, 1328, 64, 96, "trigger")], map="cisterns3")
    L.add("info_intermission", (80, -260, 300), mangle=(25, 20, 0))
    return L


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "cisterns_s.map")
    build().save(out)
    print(out)
