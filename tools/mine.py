"""The Undervein's mine furniture for mapkit levels: timber sets, rails,
ore carts and lamps, shared by the vein maps."""

PROP = "mine_prop1"
LAMP = (1.0, 0.72, 0.42)


def timbers(L, x0, x1, y0, y1, z, h, every=160, axis="x"):
    """Timber sets along a drift: a post at each wall and a cap under the
    roof, every `every` units from x0 to x1 (or y0 to y1 along y)."""
    if axis == "x":
        for x in range(int(x0) + 48, int(x1) - 32, every):
            L.solid(x, y0, z, x + 16, y0 + 16, z + h, PROP)
            L.solid(x, y1 - 16, z, x + 16, y1, z + h, PROP)
            L.solid(x, y0, z + h - 16, x + 16, y1, z + h, PROP)
    else:
        for y in range(int(y0) + 48, int(y1) - 32, every):
            L.solid(x0, y, z, x0 + 16, y + 16, z + h, PROP)
            L.solid(x1 - 16, y, z, x1, y + 16, z + h, PROP)
            L.solid(x0, y, z + h - 16, x1, y + 16, z + h, PROP)


def rails(L, x0, x1, y0, y1, z=0, axis="x"):
    """A narrow-gauge track: sleepers every 48 and two iron rails on them,
    centred on y0..y1's middle (or x0..x1's along y)."""
    if axis == "x":
        c = (y0 + y1) / 2
        for x in range(int(x0) + 8, int(x1) - 8, 48):
            L.solid(x, c - 36, z, x + 12, c + 36, z + 4, PROP)
        for s in (-1, 1):
            L.solid(x0, c + s * 24 - 2, z + 4, x1, c + s * 24 + 2, z + 8, "iron_rust1")
    else:
        c = (x0 + x1) / 2
        for y in range(int(y0) + 8, int(y1) - 8, 48):
            L.solid(c - 36, y, z, c + 36, y + 12, z + 4, PROP)
        for s in (-1, 1):
            L.solid(c + s * 24 - 2, y0, z + 4, c + s * 24 + 2, y1, z + 8, "iron_rust1")


def cart(L, x, y, z=8, axis="x", full=True):
    """An ore tub on the rails, heaped with ore if `full`."""
    hx, hy = (40, 28) if axis == "x" else (28, 40)
    L.solid(x - hx, y - hy, z + 8, x + hx, y + hy, z + 48, "iron_rust1")
    for dx in (-hx + 8, hx - 16):
        L.solid(x + dx if axis == "x" else x - hx, y - hy if axis == "x" else y + dx,
                z, x + dx + 8 if axis == "x" else x + hx, y + hy if axis == "x" else y + dx + 8, z + 8, "iron_plate1")
    if full:
        L.solid(x - hx + 8, y - hy + 8, z + 48, x + hx - 8, y + hy - 8, z + 60, "ore_rock1")


def lamp(L, x, y, z, light=220, wall=None):
    """A caged pit lamp hung at (x, y, z), and its light just below it."""
    L.solid(x - 6, y - 6, z, x + 6, y + 6, z + 14, "lamp_amber1")
    L.light((x, y, z - 18), light, LAMP)
