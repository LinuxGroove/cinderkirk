"""Levels in code: write Quake .map files from boxes and entities.

A level script builds a `Level`: rooms are boxes of air carved out of solid
shells, so neighbouring rooms share walls and doorways are just more air.
Everything is axis-aligned boxes for now (stairs are boxes too), in Quake
units: the player is 32 wide and 56 tall, a step is 16, a doorway 128.
X runs east, Y north, Z up.

The .map it writes is the ordinary Quake format, so TrenchBroom opens it for
hand work; the script stays the source until a level is taken over by hand.
"""

from dataclasses import dataclass, field


@dataclass
class Box:
    x0: float
    y0: float
    z0: float
    x1: float
    y1: float
    z1: float
    tex: str = "kirk_brick1"

    def overlaps(self, o):
        return (self.x0 < o.x1 and o.x0 < self.x1 and self.y0 < o.y1 and o.y0 < self.y1
                and self.z0 < o.z1 and o.z0 < self.z1)

    def minus(self, o):
        """This box with `o` cut out, as up to six boxes."""
        if not self.overlaps(o):
            return [self]
        out = []
        x0, x1, y0, y1, z0, z1 = self.x0, self.x1, self.y0, self.y1, self.z0, self.z1
        if o.x0 > x0:
            out.append(Box(x0, y0, z0, o.x0, y1, z1, self.tex))
            x0 = o.x0
        if o.x1 < x1:
            out.append(Box(o.x1, y0, z0, x1, y1, z1, self.tex))
            x1 = o.x1
        if o.y0 > y0:
            out.append(Box(x0, y0, z0, x1, o.y0, z1, self.tex))
            y0 = o.y0
        if o.y1 < y1:
            out.append(Box(x0, o.y1, z0, x1, y1, z1, self.tex))
            y1 = o.y1
        if o.z0 > z0:
            out.append(Box(x0, y0, z0, x1, y1, o.z0, self.tex))
        if o.z1 < z1:
            out.append(Box(x0, y0, o.z1, x1, y1, z1, self.tex))
        return out


def _num(v):
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def brush_text(b, textures=None):
    """A box brush. `textures` can name a texture per face: -x, +x, -y, +y, -z, +z."""
    t = textures or {}
    x0, y0, z0, x1, y1, z1 = map(_num, (b.x0, b.y0, b.z0, b.x1, b.y1, b.z1))
    faces = [
        ("-x", f"( {x0} 0 0 ) ( {x0} 1 0 ) ( {x0} 0 1 )"),
        ("+x", f"( {x1} 0 0 ) ( {x1} 0 1 ) ( {x1} 1 0 )"),
        ("-y", f"( 0 {y0} 0 ) ( 0 {y0} 1 ) ( 1 {y0} 0 )"),
        ("+y", f"( 0 {y1} 0 ) ( 1 {y1} 0 ) ( 0 {y1} 1 )"),
        ("-z", f"( 0 0 {z0} ) ( 1 0 {z0} ) ( 0 1 {z0} )"),
        ("+z", f"( 0 0 {z1} ) ( 0 1 {z1} ) ( 1 0 {z1} )"),
    ]
    lines = ["{"]
    for key, pts in faces:
        lines.append(f"{pts} {t.get(key, b.tex)} 0 0 0 1 1")
    lines.append("}")
    return "\n".join(lines)


# Skill spawnflags the engine reads: left out on Apprentice, Journeyman, or
# Master and Founder's.
NOT_EASY, NOT_NORMAL, NOT_HARD = 256, 512, 1024
BOSSES = ("monster_founder", "monster_throat")


@dataclass
class Entity:
    classname: str
    keys: dict = field(default_factory=dict)
    brushes: list = field(default_factory=list)

    def text(self):
        lines = ["{", f'"classname" "{self.classname}"']
        for k, v in self.keys.items():
            if isinstance(v, (tuple, list)):
                v = " ".join(_num(c) for c in v)
            elif isinstance(v, float):
                v = _num(v)
            lines.append(f'"{k}" "{v}"')
        for b in self.brushes:
            lines.append(brush_text(b))
        lines.append("}")
        return "\n".join(lines)


class Level:
    """Solid boxes, air boxes cut out of them, extra brushes and entities."""

    WALL = 32

    def __init__(self, **worldspawn):
        self.light_wait = worldspawn.pop("light_wait", 1)
        self.world = dict(worldspawn)
        self.solids = []
        self.air = []
        self.details = []   # placed after carving: stairs, beams, liquids
        self.entities = []

    # Building blocks

    def room(self, x0, y0, z0, x1, y1, z1, wall="kirk_brick1", floor="floor_flag1",
             ceiling="kirk_stone1", floor_depth=None, ceiling_depth=None):
        """A room: air inside, a shell of walls, floor and ceiling around it."""
        t = self.WALL
        fd = floor_depth or t
        cd = ceiling_depth or t
        self.solids += [
            Box(x0 - t, y0 - t, z0, x0, y1 + t, z1, wall),
            Box(x1, y0 - t, z0, x1 + t, y1 + t, z1, wall),
            Box(x0, y0 - t, z0, x1, y0, z1, wall),
            Box(x0, y1, z0, x1, y1 + t, z1, wall),
            Box(x0 - t, y0 - t, z0 - fd, x1 + t, y1 + t, z0, floor),
            Box(x0 - t, y0 - t, z1, x1 + t, y1 + t, z1 + cd, ceiling),
        ]
        self.air.append(Box(x0, y0, z0, x1, y1, z1))

    def opening(self, x0, y0, z0, x1, y1, z1):
        """Air through walls: doorways, arches, windows."""
        self.air.append(Box(x0, y0, z0, x1, y1, z1))

    def solid(self, x0, y0, z0, x1, y1, z1, tex):
        """A box of world that isn't carved: pillars, steps, ledges, beams."""
        self.details.append(Box(x0, y0, z0, x1, y1, z1, tex))

    def steps(self, x0, y0, x1, y1, z_from, z_to, axis="x", tex="kirk_stone1", base=None):
        """Stairs between two heights, 16 a step, along x or y (from the 0 end)."""
        n = max(1, int(abs(z_to - z_from) // 16))
        rise = (z_to - z_from) / n
        bottom = min(z_from, z_to) if base is None else base
        length = (x1 - x0) if axis == "x" else (y1 - y0)
        run = length / n
        for i in range(n):
            top = z_from + rise * (i + 1) if rise > 0 else z_from + rise * i
            if axis == "x":
                self.solid(x0 + run * i, y0, bottom, x0 + run * (i + 1), y1, top, tex)
            else:
                self.solid(x0, y0 + run * i, bottom, x1, y0 + run * (i + 1), top, tex)

    def nook(self, x, y, z, side, items=(), w=96, d=96, h=96, wall="kirk_stone1", floor="coal1",
             light=(1.0, 0.82, 0.62)):
        """A secret closet behind cracked stone. (x, y) is the middle of the
        room's wall face, z its floor, and `side` the way out through the
        wall: "n", "s", "e" or "w". The Pick's Overpressure blow breaks the
        crack; walking in counts the secret. `items` are classnames, set out
        along the closet's back."""
        t = self.WALL
        hw = w / 2
        if side in ("n", "s"):
            sy = 1 if side == "n" else -1
            crack = Box(x - hw, min(y, y + sy * t), z, x + hw, max(y, y + sy * t), z + h, "kirk_crack1")
            y0, y1 = sorted((y + sy * t, y + sy * (t + d)))
            inner = Box(x - hw, y0, z, x + hw, y1, z + h)
            back = [(x - hw + (i + 1) * w / (len(items) + 1), y + sy * (t + d - 28)) for i in range(len(items))]
        else:
            sx = 1 if side == "e" else -1
            crack = Box(min(x, x + sx * t), y - hw, z, max(x, x + sx * t), y + hw, z + h, "kirk_crack1")
            x0, x1 = sorted((x + sx * t, x + sx * (t + d)))
            inner = Box(x0, y - hw, z, x1, y + hw, z + h)
            back = [(x + sx * (t + d - 28), y - hw + (i + 1) * w / (len(items) + 1)) for i in range(len(items))]
        self.opening(crack.x0, crack.y0, crack.z0, crack.x1, crack.y1, crack.z1)
        self.brush_entity("func_cracked", [crack])
        self.room(inner.x0, inner.y0, inner.z0, inner.x1, inner.y1, inner.z1, wall=wall, floor=floor)
        self.brush_entity("trigger_secret", [Box(inner.x0 + 8, inner.y0 + 8, z, inner.x1 - 8, inner.y1 - 8, z + 56, "trigger")])
        for cls, (ix, iy) in zip(items, back):
            self.add(cls, (ix, iy, z))
        self.light(((inner.x0 + inner.x1) / 2, (inner.y0 + inner.y1) / 2, z + h - 24), 180, light)

    def liquid(self, x0, y0, z0, x1, y1, z1, tex="*lava_slag1"):
        self.details.append(Box(x0, y0, z0, x1, y1, z1, tex))

    def add(self, classname, origin=None, **keys):
        if origin is not None:
            keys = {"origin": origin, **keys}
        e = Entity(classname, keys)
        self.entities.append(e)
        return e

    def brush_entity(self, classname, boxes, **keys):
        e = Entity(classname, keys, list(boxes))
        self.entities.append(e)
        return e

    def light(self, origin, light=300, colour=(1.0, 0.75, 0.5), **keys):
        # A dark level's lights reach further (Level(light_wait=0.6)), so the
        # floors under lights hung high aren't left black.
        if self.light_wait != 1:
            keys.setdefault("wait", self.light_wait)
        return self.add("light", origin, light=light, _color=colour, **keys)

    # Output

    def world_brushes(self):
        boxes = list(self.solids)
        for a in self.air:
            nxt = []
            for b in boxes:
                nxt += b.minus(a)
            boxes = nxt
        return [b for b in boxes if b.x1 > b.x0 and b.y1 > b.y0 and b.z1 > b.z0] + self.details

    def skill_flags(self):
        """Apprentice leaves out every third ordinary creature (the engine
        drops entities with spawnflags 256 on skill 0). Bosses, creatures
        that fire or are fired by something, and creatures a map has already
        given skill flags are left as they are. Master and Founder's add
        creatures in the game code (coop.qc), not here."""
        n = 0
        for e in self.entities:
            if not e.classname.startswith("monster_") or e.classname in BOSSES:
                continue
            if any(k in e.keys for k in ("target", "targetname", "killtarget")):
                continue
            flags = int(e.keys.get("spawnflags", 0))
            if flags & (NOT_EASY | NOT_NORMAL | NOT_HARD):
                continue
            n += 1
            if n % 3 == 0:
                e.keys["spawnflags"] = flags | NOT_EASY

    def text(self):
        self.skill_flags()
        world = Entity("worldspawn", self.world, self.world_brushes())
        return "\n".join([world.text()] + [e.text() for e in self.entities]) + "\n"

    def save(self, path):
        with open(path, "w") as f:
            f.write(self.text())
