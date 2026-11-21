#!/usr/bin/env python3
# Copyright (C) The LinuxGroove team
# SPDX-License-Identifier: GPL-2.0-or-later
"""TrenchBroom's game config for Cinderkirk, from the game code.

    python3 tools/trenchbroom.py OUT_DIR

Writes OUT_DIR/Cinderkirk/: GameConfig.cfg, Cinderkirk.fgd (every entity the
game code knows, from its QUAKED comments: size, colour, spawnflags, what it's
for, and the model it shows where the code sets one) and Icon.png. Copy that
folder into TrenchBroom's games folder (~/.TrenchBroom/games on Linux) and
point the game path at dist/.
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

QUAKED = re.compile(r"/\*QUAKED\s+(\w+)\s+\(([^)]*)\)\s+(\?|\(([^)]*)\)\s*\(([^)]*)\))?([^\n]*)\n(.*?)\*/", re.S)
MODEL = re.compile(r'"(progs/[\w/]+\.(?:md3|mdl|bsp))"')

# Keys most entities take, as TrenchBroom base classes.
BASES = '''@BaseClass = Targetname [ targetname(target_source) : "Name" ]
@BaseClass = Target [
	target(target_destination) : "Target"
	killtarget(target_destination) : "Kill target"
]
@BaseClass = Angle [ angle(integer) : "Facing (degrees)" : 0 ]
'''

# The engine leaves these out by skill and in Pit fights.
SKILL_FLAGS = [(256, "Not on Apprentice"), (512, "Not on Journeyman"),
               (1024, "Not on Master or Founder's"), (2048, "Not in Pit fights")]

WORLDSPAWN = '''@SolidClass = worldspawn : "The level" [
	message(string) : "Level name"
	wad(string) : "Texture WAD" : "cinder.wad"
	sounds(integer) : "Music track (2 Pithead, 3 end of map, 4 Foundry, 5 Cisterns, 6 Kilns, 7 Undervein, 8 Throat, 9 big fights, 10 Pit fights)" : 4
	worldtype(choices) : "Keys" : 0 = [ 0 : "Silver and gold" ]
	_sunlight(integer) : "Sun brightness" : 0
	_minlight(integer) : "Lowest light" : 0
]
'''


def body_after(src, end):
    """The QuakeC function after a QUAKED comment, up to its closing brace."""
    m = re.search(r"\n};", src[end:])
    return src[end:end + m.end()] if m else ""


def entities():
    seen = {}
    for qc in sorted(ROOT.glob("quakec/**/*.qc")):
        src = qc.read_text(errors="replace")
        for m in QUAKED.finditer(src):
            name, colour, shape, mins, maxs, flags, text = m.groups()
            if name == "worldspawn":
                continue
            model = MODEL.search(body_after(src, m.end()))
            seen[name] = dict(name=name, colour=colour.split(), solid=shape == "?",
                              mins=mins, maxs=maxs, flags=flags.split(),
                              text=" ".join(text.split()), model=model.group(1) if model else None)
    return [seen[k] for k in sorted(seen)]


def fgd_string(s):
    return s.replace('"', "'")


def fgd(ents):
    out = ["// Cinderkirk's entities for TrenchBroom, made by tools/trenchbroom.py from the", "// QUAKED comments in quakec/. Make it again rather than editing it.", "", BASES, WORLDSPAWN]
    for e in ents:
        colour = " ".join(e["colour"][:3]) if len(e["colour"]) >= 3 else "0.6 0.6 0.6"
        bases = ["Targetname", "Target"]
        if not e["solid"]:
            bases.append("Angle")
        head = "@%sClass base(%s) color(%s)" % ("Solid" if e["solid"] else "Point", ", ".join(bases), colour)
        if not e["solid"] and e["mins"]:
            head += " size(%s, %s)" % (e["mins"].strip(), e["maxs"].strip())
        if e["model"] and e["model"].endswith(".md3"):
            head += ' model({ "path": "%s" })' % e["model"]
        out.append('%s = %s : "%s"' % (head, e["name"], fgd_string(e["text"] or e["name"])))
        out.append("[")
        flags = [(1 << i, f) for i, f in enumerate(e["flags"][:8]) if f.lower() not in ("-", "x")]
        if e["name"].startswith(("monster_", "item_", "weapon_")):
            flags += SKILL_FLAGS
        if flags:
            out.append("\tspawnflags(flags) = [")
            for bit, f in flags:
                out.append('\t\t%d : "%s" : 0' % (bit, fgd_string(f)))
            out.append("\t]")
        if e["solid"] or e["name"].startswith("trigger_"):
            out.append('\tmessage(string) : "Message"')
        out.append("]")
        out.append("")
    return "\n".join(out) + "\n"


CONFIG = '''{
    "version": 9,
    "name": "Cinderkirk",
    "icon": "Icon.png",
    "fileformats": [
        { "format": "Valve" },
        { "format": "Standard" }
    ],
    "filesystem": {
        "searchpath": "cinder",
        "packageformat": { "extension": ".pak", "format": "idpak" }
    },
    "materials": {
        "root": "textures",
        "extensions": [".D"],
        "palette": "gfx/palette.lmp",
        "attribute": "wad"
    },
    "entities": {
        "definitions": [ "Cinderkirk.fgd" ],
        "defaultcolor": "0.6 0.6 0.6 1.0"
    },
    "tags": {
        "brush": [
            { "name": "Trigger", "attribs": [ "transparent" ], "match": "classname", "pattern": "trigger*", "material": "trigger" }
        ],
        "brushface": [
            { "name": "Clip", "attribs": [ "transparent" ], "match": "material", "pattern": "clip" },
            { "name": "Skip", "attribs": [ "transparent" ], "match": "material", "pattern": "skip" },
            { "name": "Hint", "attribs": [ "transparent" ], "match": "material", "pattern": "hint*" },
            { "name": "Liquid", "match": "material", "pattern": "\\\\**" }
        ]
    },
    "softMapBounds": "-8192 -8192 -8192 8192 8192 8192",
    "compilationTools": [
        { "name": "qbsp", "description": "ericw-tools' qbsp (build/prefix/bin/qbsp)" },
        { "name": "vis", "description": "ericw-tools' vis" },
        { "name": "light", "description": "ericw-tools' light (run it with -lux for the normal maps)" }
    ]
}
'''


def main():
    out = Path(sys.argv[1]) / "Cinderkirk"
    out.mkdir(parents=True, exist_ok=True)
    ents = entities()
    (out / "Cinderkirk.fgd").write_text(fgd(ents))
    (out / "GameConfig.cfg").write_text(CONFIG)
    shutil.copy(ROOT / "icon.png", out / "Icon.png")
    print("%s: %d entities" % (out, len(ents)))


if __name__ == "__main__":
    main()
