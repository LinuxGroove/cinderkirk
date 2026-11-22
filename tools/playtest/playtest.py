#!/usr/bin/env python3
# Copyright (C) The LinuxGroove team
# SPDX-License-Identifier: GPL-2.0-or-later
"""Plays every level and the finale with nobody at the keys, on this
machine's GPU, and fails on anything that goes wrong:

    tools/playtest/playtest.py [--maps start,throat2] [--skill 1] [--no-levels] [--no-finale]

1. The levels, one after another in one copy of the game: load it, spawn,
   then (god mode, every weapon) stand a moment at each of its starts,
   pickups and creatures, firing a different weapon at each, so the
   creatures wake and fight. setpos flies there in noclip, which still
   touches triggers: it picks things up and opens doors, so places inside a
   trigger_changelevel are left out. A level fails on a Host_Error, a PF_
   warning, a QuakeC run warning, anything not precached, a crash or a hang,
   and on a changelevel to a level that isn't in the pak. After a crash or a
   Host_Error the game starts again at the next level.
2. The finale (throat2), in a copy of its own: shoot the Throat (nothing you
   carry hurts it), walk into the four brakes, watch the bell come down and
   stop the Throat, the intermission, the epilogue, and back to the Pithead.
   Each step is checked in the engine's own edict dumps or its log.

The game runs from dist/ (make it first) on a private Xvfb at 640x360, one
copy at a time: two don't fit in the GPU's memory. The logs and report.md go
to build/playtest/. Exits 1 if anything failed. Not for CI: it wants a real
GPU. VK_ICD_FILENAMES picks the Vulkan driver (NVIDIA's when it's installed).
"""

import argparse
import collections
import math
import os
import queue
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DIST = os.path.join(ROOT, "dist")
PAK = os.path.join(DIST, "cinder", "pak0.pak")
NVIDIA_ICD = "/usr/share/vulkan/icd.d/nvidia_icd.json"
FPS = 60                 # host_maxfps: a "wait" is one frame, so this sets the script's pace
WEAPONS = 8              # impulses 1-8
LOAD_TIMEOUT = 90        # seconds from "map" to the player in the level (the first also starts the engine)

# A line that ends the level's run: the server is gone or the game is.
FATAL = [
    (re.compile(r"Host_Error: (.*)"), "Host_Error"),
    (re.compile(r"QUAKE ERROR: (.*)"), "crash"),
    (re.compile(r"(Couldn't spawn server .*)"), "no level"),
]
# A line that fails the level, though the game goes on.
FAILS = [
    re.compile(r"Warning: (PF_.*)"),
    re.compile(r"Warning: (NAN in .*)"),
    re.compile(r"(.*not precached.*)"),
    re.compile(r"(ED_Alloc: .*)"),
]
WARNING = re.compile(r"Warning: (.*)")
GAMES = []               # the copies running, to stop on the way out


# ------------------------------------------------------------ the pak and its levels

def pak_index(path):
    with open(path, "rb") as f:
        magic, ofs, size = struct.unpack("<4sii", f.read(12))
        if magic != b"PACK":
            sys.exit(f"{path} isn't a pak")
        f.seek(ofs)
        d = f.read(size)
    files = {}
    for i in range(0, size, 64):
        name, o, n = struct.unpack_from("<56sii", d, i)
        files[name.split(b"\0")[0].decode("latin-1")] = (o, n)
    return files


def pak_read(path, files, name):
    o, n = files[name]
    with open(path, "rb") as f:
        f.seek(o)
        return f.read(n)


def parse_entities(text):
    ents, cur = [], None
    for m in re.finditer(r'"([^"]*)"\s*"([^"]*)"|\{|\}', text):
        if m.group(0) == "{":
            cur = {}
        elif m.group(0) == "}":
            if cur is not None:
                ents.append(cur)
            cur = None
        elif cur is not None:
            cur[m.group(1)] = m.group(2)
    return ents


CONTENTS_SOLID, CONTENTS_SKY = -2, -6


class Level:
    """A level's entities, its brush models' (mins, maxs), and what's at a point."""

    def __init__(self, data):
        lumps = struct.unpack_from("<30i", data, 4)
        lump = lambda n: (lumps[2 * n], lumps[2 * n + 1])
        eo, en = lump(0)
        self.ents = parse_entities(data[eo:eo + en].split(b"\0")[0].decode("latin-1"))
        mo, mn = lump(14)
        self.models = []
        for i in range(mo, mo + mn, 64):
            f = struct.unpack_from("<6f", data, i)
            self.models.append((f[0:3], f[3:6]))
        self.headnode = struct.unpack_from("<i", data, mo + 36)[0]
        po, pn = lump(1)
        self.planes = [struct.unpack_from("<4f", data, i) for i in range(po, po + pn, 20)]
        # BSP29's nodes and leafs, or BSP2's; anything else can't say what's solid.
        fmt = {b"\x1d\0\0\0": ("<ihh", 24, 28), b"BSP2": ("<iii", 44, 44)}.get(data[:4])
        self.nodes = self.leafs = None
        if fmt:
            no, nn = lump(5)
            lo, ln = lump(10)
            self.nodes = [struct.unpack_from(fmt[0], data, i) for i in range(no, no + nn, fmt[1])]
            self.leafs = [struct.unpack_from("<i", data, i)[0] for i in range(lo, lo + ln, fmt[2])]

    def contents(self, p):
        if self.nodes is None:
            return -1
        n = self.headnode
        while n >= 0:
            plane, front, back = self.nodes[n]
            nx, ny, nz, d = self.planes[plane]
            n = front if nx * p[0] + ny * p[1] + nz * p[2] - d >= 0 else back
        return self.leafs[-n - 1]

    def open(self, p):
        return self.contents(p) not in (CONTENTS_SOLID, CONTENTS_SKY)

    def clear(self, a, b, step=8):
        n = max(1, int(math.dist(a, b) / step))
        return all(self.open([a[i] + (b[i] - a[i]) * k / n for i in range(3)]) for k in range(n + 1))


def level_names():
    src = os.path.join(ROOT, "maps_src")
    return sorted({f.rsplit(".", 1)[0] for f in os.listdir(src) if f.endswith((".py", ".map"))})


def campaign_order(names, info):
    """Start first, then each level as the changelevels reach it; the rest after."""
    order, seen, todo = [], set(), collections.deque(["start"] if "start" in names else [])
    while todo:
        m = todo.popleft()
        if m in seen or m not in names:
            continue
        seen.add(m)
        order.append(m)
        for e in info[m].ents:
            if e.get("classname") == "trigger_changelevel" and e.get("map"):
                todo.append(e["map"])
    return order + [m for m in names if m not in seen]


def origin(e):
    return tuple(float(v) for v in e["origin"].split())


PLACES = ("info_player_start", "info_player_coop", "info_player_deathmatch", "info_player_start2",
          "info_intermission", "info_teleport_destination")


def stand_off(level, m):
    """A spot in the open with a clear shot at the creature at m, and the (pitch, yaw) of the shot."""
    target = (m[0], m[1], m[2] + 8)
    for dist in (192, 128, 96):
        for k in range(8):
            a = math.radians(k * 45)
            p = (m[0] + dist * math.cos(a), m[1] + dist * math.sin(a), m[2] + 8)
            eye = (p[0], p[1], p[2] + 22)
            if all(level.open((p[0], p[1], p[2] + dz)) for dz in (-24, 0, 32)) and level.clear(eye, target):
                pitch = -math.degrees(math.atan2(target[2] - eye[2], dist))
                return p, pitch, (k * 45 + 180) % 360
    return None


def exits(level):
    """The boxes of the level's trigger_changelevels, grown by a player's size."""
    out = []
    for e in level.ents:
        if e.get("classname") == "trigger_changelevel" and e.get("model", "").startswith("*"):
            mins, maxs = level.models[int(e["model"][1:])]
            out.append(([mins[0] - 32, mins[1] - 32, mins[2] - 48], [maxs[0] + 32, maxs[1] + 32, maxs[2] + 40]))
    return out


def places(level, n):
    """Where to stand: the start, then up to n-1 of the creatures, pickups and other
    starts. Each is (what, x, y, z, pitch, yaw); a creature is shot from a spot nearby."""
    start, rest = [], []
    boxes = exits(level)
    leaves = lambda x, y, z: any(all(lo[i] <= v <= hi[i] for i, v in enumerate((x, y, z))) for lo, hi in boxes)
    for e in level.ents:
        c = e.get("classname", "")
        if "origin" not in e or not (c.startswith(("monster_", "item_", "weapon_")) or c in PLACES):
            continue
        x, y, z = origin(e)
        if c.startswith(("item_", "weapon_")):
            z += 24                     # a pickup lies on the floor; stand eye-high over it
        if leaves(x, y, z):
            continue
        p = (c, x, y, z, 0, float(e.get("angle", -1)))
        (start if c == "info_player_start" and not start else rest).append(p)
    if len(rest) > n - 1:
        rest = [rest[i * len(rest) // (n - 1)] for i in range(n - 1)]
    out = []
    for k, (c, x, y, z, pitch, yaw) in enumerate(start + rest):
        shot = stand_off(level, (x, y, z)) if c.startswith("monster_") else None
        if shot and leaves(*shot[0]):
            shot = None
        if shot:
            (x, y, z), pitch, yaw = shot
        elif yaw < 0:
            yaw = (k * 45) % 360
        out.append((c, x, y, z, pitch, yaw))
    return out


# ------------------------------------------------------------ running the game

def waits(n):
    return ";".join(["wait"] * max(1, int(n)))


# The client drops its first two moves in a level (cl_input.c), and an
# impulse with them: wait before the first.
SETTLE = waits(10)


class Game:
    """One copy of the game on the private display, its output line by line."""

    def __init__(self, opts, userdir, boot, first, log):
        env = dict(os.environ)
        lib = os.path.join(ROOT, "build", "prefix", "lib")
        env["LD_LIBRARY_PATH"] = lib + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
        if "VK_ICD_FILENAMES" not in env and os.path.exists(NVIDIA_ICD):
            env["VK_ICD_FILENAMES"] = NVIDIA_ICD
        env["PATH"] = opts.bin + ":" + env.get("PATH", "")
        env["DISPLAY"] = opts.display
        env.setdefault("XDG_RUNTIME_DIR", "/run/user/%d" % os.getuid())
        w, h = opts.size.split("x")
        cmd = ["stdbuf", "-oL", "-eL", "./cinderkirk", "-basedir", ".", "-userdir", userdir,
               "-width", w, "-height", h, "-window", "-nosound", "+exec", boot,
               # The map on the command line, or the engine opens the main menu, and a menu pauses the game.
               "+map", first]
        self.log = log
        log.write("\n#### %s\n" % " ".join(cmd))
        log.flush()
        self.proc = subprocess.Popen(cmd, cwd=DIST, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, start_new_session=True)
        GAMES.append(self)
        self.lines = queue.Queue()
        self.eof = False
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        for raw in self.proc.stdout:
            self.lines.put(raw.decode("utf-8", "replace").rstrip("\r\n"))
        self.lines.put(None)

    def next_line(self, timeout=0.5):
        """The next line; "" when none came in time; None once the game has gone."""
        if self.eof or self.log.closed:
            return None
        try:
            line = self.lines.get(timeout=timeout)
        except queue.Empty:
            return ""
        if line is None:
            self.eof = True
        else:
            self.log.write(line + "\n")
        return line

    def kill(self):
        if self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
                self.proc.wait(5)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                try:
                    os.killpg(self.proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        return self.wait()

    def wait(self, timeout=30):
        try:
            rc = self.proc.wait(timeout)
        except subprocess.TimeoutExpired:
            return self.kill()
        while self.next_line(0.2) is not None:      # whatever it printed last
            pass
        if not self.log.closed:
            self.log.flush()
        return rc


def describe_exit(rc):
    if rc is None:
        return "still running"
    if rc < 0:
        try:
            return "killed by " + signal.Signals(-rc).name
        except ValueError:
            return "killed by signal %d" % -rc
    if rc > 128:                       # the engine's own signal handler exits 128 + the signal
        try:
            return "exit %d, %s" % (rc, signal.Signals(rc - 128).name)
        except ValueError:
            pass
    return "exit %d" % rc


class Result:
    def __init__(self, name):
        self.name = name
        self.problems = []           # what failed it, shortest first
        self.warnings = collections.Counter()
        self.context = []            # log excerpts for the report
        self.done = False
        self.steps = 0
        self.load_s = self.play_s = None

    def fail(self, what, context=()):
        if what not in self.problems:
            self.problems.append(what)
            if context and len(self.context) < 3:
                self.context.append((what, list(context)))

    @property
    def ok(self):
        return self.done and not self.problems

    def summary(self):
        if self.ok:
            n = sum(self.warnings.values())
            return "ok" + (", %d warning%s" % (n, "s" * (n > 1)) if n else "")
        if not self.problems:
            return "didn't finish"
        fatal = [p for p in self.problems if p.startswith(("Host_Error", "crash", "hung", "no level", "the game"))]
        first = fatal[0] if fatal else self.problems[0]
        more = len(self.problems) - 1
        return first + (" (and %d more: see the report)" % more if more else "")


def qc_message(context):
    """PR_RunError prints the QuakeC message just before Host_Error's stack trace."""
    lines = list(context)
    for i in range(len(lines) - 1, 0, -1):
        if lines[i].startswith("================ STACK TRACE"):
            for j in range(i - 1, -1, -1):
                if lines[j].strip():
                    return lines[j].strip()
    return ""


def scan(line, res, ctx):
    """Checks one log line against the failures; returns "fatal" when the run is over."""
    for rx, kind in FATAL:
        m = rx.search(line)
        if m:
            msg = m.group(1).strip()
            if kind == "Host_Error" and msg == "Program error":
                qc = qc_message(ctx)
                msg = "Program error: " + qc if qc else msg
            res.fail("%s: %s" % (kind, msg), ctx)
            return "fatal"
    for rx in FAILS:
        m = rx.search(line)
        if m:
            res.fail(m.group(1).strip(), ctx)
            return None
    m = WARNING.search(line)
    if m:
        res.warnings[m.group(1).strip()] += 1
    return None


# ------------------------------------------------------------ 1. the levels

def level_cfg(name, nxt, pts, opts):
    aim = opts.dwell // 4
    out = ["echo PT_SPAWN %s" % name, "god", SETTLE, "impulse 9", waits(FPS)]
    for k, (cls, x, y, z, pitch, yaw) in enumerate(pts):
        out += ["echo PT_AT %d %s" % (k, cls), "setpos %.0f %.0f %.0f %.1f %.0f 0" % (x, y, z, pitch, yaw),
                "impulse %d" % (k % WEAPONS + 1), waits(aim), "+attack", waits(opts.dwell - aim), "-attack"]
    if opts.dump:
        out.append("edicts")
    out.append("echo PT_END %s" % name)
    if nxt:
        out += ['cl_spawncmd "exec pt_%s.cfg"' % nxt, "echo PT_LOAD %s" % nxt, "map %s" % nxt]
    else:
        out += ["echo PT_ALLDONE", "quit"]
    return "\n".join(out) + "\n"


def boot_cfg(first, opts):
    return "\n".join(["host_maxfps %d" % FPS, "con_logcenterprint 1", "developer 0", "skill %d" % opts.skill,
                      'cl_spawncmd "exec pt_%s.cfg"' % first, "echo PT_LOAD %s" % first]) + "\n"


def play_levels(maps, info, opts, log):
    results = {m: Result(m) for m in maps}
    names = set(level_names())
    for m in maps:
        for e in info[m].ents:
            if e.get("classname") == "trigger_changelevel" and e.get("map") and e["map"] not in names:
                results[m].fail("changelevel to %s, which isn't a level" % e["map"])
    plan = {m: places(info[m], opts.points) for m in maps}
    gamedir = os.path.join(opts.user, "cinder")
    todo = list(maps)
    while todo:
        for i, m in enumerate(todo):
            with open(os.path.join(gamedir, "pt_%s.cfg" % m), "w") as f:
                f.write(level_cfg(m, todo[i + 1] if i + 1 < len(todo) else None, plan[m], opts))
        with open(os.path.join(gamedir, "pt_boot.cfg"), "w") as f:
            f.write(boot_cfg(todo[0], opts))
        game = Game(opts, opts.user, "pt_boot.cfg", todo[0], log)
        cur, res, alldone, fatal = None, Result("startup"), False, False
        ctx = collections.deque(maxlen=40)
        t_load = t_spawn = None
        deadline = time.time() + LOAD_TIMEOUT
        while True:
            line = game.next_line()
            now = time.time()
            if line is None:
                break
            if line:
                ctx.append(line)
                word = line.split(" ", 2)
                if word[0] == "PT_LOAD" and len(word) > 1:
                    cur, res = word[1], results[word[1]]
                    t_load, deadline = now, now + LOAD_TIMEOUT
                    ctx.clear()
                elif word[0] == "PT_SPAWN":
                    t_spawn = now
                    res.load_s = now - t_load
                    deadline = now + (FPS + len(plan[cur]) * opts.dwell) / FPS * 3 + 30
                elif word[0] == "PT_AT":
                    res.steps += 1
                elif word[0] == "PT_END":
                    res.done = True
                    res.play_s = now - t_spawn
                    print("  %-12s %s" % (cur, res.summary()), flush=True)
                elif word[0] == "PT_ALLDONE":
                    alldone, deadline = True, now + 30
                elif scan(line, res, ctx) == "fatal":
                    fatal = True
                    if "QUAKE ERROR" in line:     # the stack trace follows; the game exits itself
                        deadline = now + 10
                        continue
                    break
            if now > deadline:
                if alldone:
                    res.fail("hung on quit")
                elif cur is None:
                    pass
                elif t_spawn is None or t_spawn < t_load:
                    res.fail("hung loading (no spawn in %d s)" % LOAD_TIMEOUT, ctx)
                else:
                    res.fail("hung playing (%d of %d places)" % (res.steps, len(plan[cur])), ctx)
                fatal = True
                break
        rc = game.kill() if fatal or not alldone else game.wait()
        if cur is None:
            for m in todo:
                results[m].fail("the game didn't start (%s)" % describe_exit(rc), ctx)
            print("  the game didn't start (%s); see levels.log" % describe_exit(rc), flush=True)
            break
        if alldone:
            if rc != 0:
                results[todo[-1]].fail("crashed on quit (%s)" % describe_exit(rc), ctx)
            break
        if not res.done:
            if not res.problems:
                res.fail("crashed (%s)" % describe_exit(rc), ctx)
            print("  %-12s %s" % (cur, res.summary()), flush=True)
        todo = todo[todo.index(cur) + 1:]
    return [results[m] for m in maps]


# ------------------------------------------------------------ 2. the finale

def qc_define(name):
    with open(os.path.join(ROOT, "quakec", "localized_text.qc"), encoding="utf-8") as f:
        m = re.search(r'#define\s+%s\s+"((?:[^"\\]|\\.)*)"' % name, f.read())
    return m.group(1) if m else ""


def finale_cfg(ents, models, opts):
    """The finale's script, and what the runner needs to check it."""
    bell = next(e for e in ents if e.get("classname") == "misc_great_bell")
    throat = next(e for e in ents if e.get("classname") == "monster_throat")
    by_name = collections.defaultdict(list)
    for e in ents:
        if e.get("targetname"):
            by_name[e["targetname"]].append(e)

    def reaches_bell(target, depth=0):
        if not target or depth > 4:
            return False
        if target == bell.get("targetname"):
            return True
        return any(reaches_bell(e.get("target"), depth + 1) for e in by_name[target])

    brakes = sorted((e for e in ents if e.get("classname") == "func_button" and reaches_bell(e.get("target"))),
                    key=lambda e: e.get("target", ""))
    tx, ty, tz = origin(throat)
    stands = []
    for e in brakes:
        mins, maxs = models[int(e["model"][1:])]
        c = [(a + b) / 2 for a, b in zip(mins, maxs)]
        a = math.radians(float(e.get("angle", 0)))
        d = (math.cos(a), math.sin(a))
        half = abs(d[0]) * (maxs[0] - mins[0]) / 2 + abs(d[1]) * (maxs[1] - mins[1]) / 2
        back = half + 16 + 24                     # the player's half width and a step
        stands.append((c[0] - d[0] * back, c[1] - d[1] * back, c[2] - 4, float(e.get("angle", 0))))

    # The fight, from the first brake's dais, looking at the Throat's chest.
    fx, fy, fz, _ = stands[0]
    yaw = math.degrees(math.atan2(ty - fy, tx - fx))
    pitch = -math.degrees(math.atan2(tz + 200 - (fz + 22), math.hypot(tx - fx, ty - fy)))
    out = ["echo PT_SPAWN throat2", "god", "notarget", SETTLE, "impulse 9", waits(FPS),
           "setpos %g %g %g %g %g 0" % (fx, fy, fz, pitch, yaw), "impulse 2", waits(4 * FPS),
           "echo PT_FIGHT", "+attack", waits(2 * FPS), "-attack", waits(FPS // 2),
           "echo PT_DUMP fight", "edicts"]
    for k, (x, y, z, ang) in enumerate(stands, 1):
        # setpos turns noclip on; turn it off again so the brake feels the push.
        out += ["setpos %g %g %g 0 %g 0" % (x, y, z, ang), "noclip", waits(FPS // 3),
                "echo PT_BRAKE %d" % k, "+forward", waits(FPS // 2), "-forward", waits(FPS),
                "echo PT_DUMP brake%d" % k, "edicts"]
    ix, iy, iz = next(origin(e) for e in ents if e.get("classname") == "info_intermission")
    out += ["setpos %g %g %g 20 45 0" % (ix, iy, iz), waits(3 * FPS), "echo PT_DUMP landed", "edicts",
            # The Throat ends the level 6 s after it dies; the intermission waits 2 s for a button.
            waits(9 * FPS), "echo PT_JUMP 1", "+jump", waits(FPS // 6), "-jump", waits(2 * FPS),
            # The next jump changes level, appended to the command buffer: nothing may wait after it.
            'cl_spawncmd "exec pt_after.cfg"', "echo PT_JUMP 2", "+jump", waits(FPS // 6), "-jump"]
    after = "echo PT_AFTER\n%s\necho PT_DUMP after\nedicts\nquit\n" % waits(FPS)
    return "\n".join(out) + "\n", after, len(brakes)


def parse_dump(lines):
    ents, cur = [], None
    for line in lines:
        m = re.match(r"EDICT\s+(\d+):\s*$", line)
        if m:
            cur = {"_num": int(m.group(1))}
            ents.append(cur)
        elif line.startswith(("EDICT", "Free-list", "Total:")):
            cur = None
        elif cur is not None and line.strip():
            k, _, v = line.strip().partition(" ")
            cur[k] = v.strip()
    return ents


def num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def vec(v):
    return [num(x) for x in (v or "0 0 0").strip("'").split()]


def play_finale(info, opts, log):
    res = Result("throat2 finale")
    script, after, n_brakes = finale_cfg(info["throat2"].ents, info["throat2"].models, opts)
    if n_brakes != 4:
        res.fail("throat2 has %d brakes that reach the bell, not 4" % n_brakes)
    epilogue = qc_define("LOC_EPILOGUE_END").split("\\n")[0].strip()
    start_title = next((e.get("message", "") for e in info["start"].ents if e.get("classname") == "worldspawn"), "")
    gamedir = os.path.join(opts.user, "cinder")
    for name, text in (("pt_finale.cfg", script), ("pt_after.cfg", after),
                       ("pt_boot.cfg", "\n".join(["host_maxfps %d" % FPS, "con_logcenterprint 1", "skill %d" % opts.skill,
                                                  'cl_spawncmd "exec pt_finale.cfg"']) + "\n")):
        with open(os.path.join(gamedir, name), "w") as f:
            f.write(text)
    game = Game(opts, opts.user, "pt_boot.cfg", "throat2", log)
    ctx = collections.deque(maxlen=40)
    dumps, dump, seen = {}, None, collections.Counter()
    jumped, last = 0, "the start"
    deadline = time.time() + LOAD_TIMEOUT + 60
    fatal = hung = False
    while True:
        line = game.next_line()
        if line is None:
            break
        now = time.time()
        if line:
            ctx.append(line)
            if dump is not None:
                if line.startswith("Total:"):
                    dumps[dump[0]] = parse_dump(dump[1])
                    dump = None
                else:
                    dump[1].append(line)
                continue
            if line.startswith("PT_"):
                last = line.strip()
            if line.startswith("PT_DUMP "):
                dump = (line.split()[1], [])
            elif line.startswith("PT_SPAWN"):
                deadline = now + 120
            elif line.startswith("PT_JUMP "):
                jumped = int(line.split()[1])
                if jumped == 2:
                    seen["epilogue-before-jump-2"] = seen["epilogue"]
                    deadline = now + LOAD_TIMEOUT
            elif line.startswith("PT_AFTER"):
                seen["after"] += 1
                deadline = now + 30
            elif epilogue and epilogue in line:
                seen["epilogue"] += 1
            elif "Nothing you carry can hurt it" in line:
                seen["unhurt"] += 1
            elif start_title and line.strip() == start_title and jumped == 2:
                seen["start"] += 1
            elif scan(line, res, ctx) == "fatal":
                fatal = True
                if "QUAKE ERROR" in line:
                    deadline = now + 10
                    continue
                break
        if time.time() > deadline:
            fatal = hung = True
            res.fail("hung after %s" % last, ctx)
            break
    rc = game.kill() if fatal or not seen["after"] else game.wait()
    if rc not in (0, None) and not hung and not any(p.startswith(("crash", "Host_Error")) for p in res.problems):
        res.fail("crashed (%s)" % describe_exit(rc), ctx)

    def find(d, cls):
        return next((e for e in dumps.get(d, []) if e.get("classname") == cls), None)

    steps = []
    t = find("fight", "monster_throat")
    if t is None:
        res.fail("no Throat in the edicts (did the level load?)", ctx)
    elif t.get("takedamage", "DAMAGE_NO") in ("DAMAGE_NO", "0") or num(t.get("modelindex")) == 0:
        res.fail("the Throat didn't rise")
    else:
        steps.append("the Throat rose")
        if seen["unhurt"]:
            steps.append("shrugged off the scattergun")
        else:
            res.warnings["no \"Nothing you carry can hurt it\" after shooting the Throat"] += 1
    for k in range(1, n_brakes + 1):
        b = find("brake%d" % k, "misc_great_bell")
        stage = num(b.get("bell_stage")) if b else -1
        if b is None:
            res.fail("no dump after brake %d" % k, ctx)
            break
        if stage != k:
            res.fail("brake %d didn't go off (the bell is at stage %d)" % (k, stage))
            break
    else:
        steps.append("%d brakes off" % n_brakes)
    b, t = find("landed", "misc_great_bell"), find("landed", "monster_throat")
    if b is not None and t is not None:
        z, floor = vec(b.get("origin"))[2], num(b.get("bell_floor"))
        if num(b.get("bell_stage")) < 4 or any(vec(b.get("velocity"))) or abs(z - floor) > 64:
            res.fail("the bell didn't come down (stage %g, z %g, the Throat's mouth at %g)"
                     % (num(b.get("bell_stage")), z, floor))
        elif num(t.get("health")) > 0:
            res.fail("the bell came down but the Throat lives (health %g)" % num(t.get("health")))
        else:
            steps.append("bell down" + (" (%.0f short)" % (z - floor) if z - floor > 8 else "") + ", the Throat stopped")
    elif not res.problems:
        res.fail("no dump after the bell's fall", ctx)
    if seen["epilogue-before-jump-2"]:
        steps.append("the epilogue")
    elif not res.problems:
        res.fail("no epilogue (\"%s\") after the intermission" % epilogue, ctx)
    if seen["after"] and seen["start"]:
        steps.append("back to %s" % start_title)
    elif not res.problems:
        res.fail("didn't go back to %s after the epilogue" % (start_title or "start"), ctx)
    res.done = bool(seen["after"])
    res.steps = len(steps)
    res.finale_steps = steps
    return res


# ------------------------------------------------------------ the report

def report(results, opts, path):
    commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    lines = ["# Play-test", "", "Commit %s, skill %d, %d places a level, %d frames each, at %d fps."
             % (commit or "?", opts.skill, opts.points, opts.dwell, FPS), "",
             "| Level | Result | Load | Play |", "|---|---|---|---|"]
    for r in results:
        s = r.summary()
        if r.ok and getattr(r, "finale_steps", None):
            s = "ok: " + ", ".join(r.finale_steps)
        lines.append("| %s | %s | %s | %s |" % (r.name, s.replace("|", "\\|"),
                                                "%.1f s" % r.load_s if r.load_s else "",
                                                "%.0f s" % r.play_s if r.play_s else ""))
    warned = collections.defaultdict(list)
    for r in results:
        for w, n in r.warnings.items():
            warned[w].append(r.name + (" x%d" % n if n > 1 else ""))
    if warned:
        lines += ["", "## Warnings (not failures)", ""] + ["- %s: %s" % (w, ", ".join(m)) for w, m in sorted(warned.items())]
    for r in results:
        if len(r.problems) > 1:
            lines += ["", "## %s: everything that failed it" % r.name, ""] + ["- " + p for p in r.problems]
        for what, ctx in r.context:
            lines += ["", "## %s: %s" % (r.name, what), "", "```"] + ctx[-30:] + ["```"]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def start_xvfb(size):
    r, w = os.pipe()
    x = subprocess.Popen(["Xvfb", "-displayfd", str(w), "-screen", "0", size + "x24", "-nolisten", "tcp"],
                         pass_fds=(w,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.close(w)
    ready, _, _ = select.select([r], [], [], 15)
    n = os.read(r, 32).strip() if ready else b""
    os.close(r)
    if not n:
        x.kill()
        sys.exit("Xvfb didn't start")
    return x, ":" + n.decode()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--maps", help="levels to play, comma separated (default: all, in campaign order)")
    ap.add_argument("--skill", type=int, default=1, help="0 Apprentice to 3 Founder's (default 1)")
    ap.add_argument("--points", type=int, default=20, help="places to stand in each level (default 20)")
    ap.add_argument("--dwell", type=int, default=40, help="frames at each place, the last 3/4 firing (default 40)")
    ap.add_argument("--ents", help="a folder of <map>.ent entity lumps to load over the pak's (to try a fix without a rebuild)")
    ap.add_argument("--dump", action="store_true", help="dump the edicts into levels.log at the end of each level")
    ap.add_argument("--no-levels", action="store_true", help="only the finale")
    ap.add_argument("--no-finale", action="store_true", help="only the levels")
    # Through Xvfb, copying each frame out bounds the frame rate: 1280x720 makes
    # 32 fps on an RTX laptop, and the script's waits are frames.
    ap.add_argument("--size", default="640x360", help="the window (default 640x360, which keeps up with 60 fps)")
    ap.add_argument("--display", help="an X display to use instead of a private Xvfb")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "playtest"), help="logs and report (default build/playtest)")
    opts = ap.parse_args()

    if not os.path.exists(os.path.join(DIST, "cinderkirk")) or not os.path.exists(PAK):
        sys.exit("no dist/cinderkirk or dist/cinder/pak0.pak: run make first")
    if subprocess.run(["pgrep", "-x", "cinderkirk"], capture_output=True).returncode == 0:
        print("playtest: another copy of the game is running; two may not fit in the GPU's memory", file=sys.stderr)
    files = pak_index(PAK)
    names = level_names()
    missing = [m for m in names if "maps/%s.bsp" % m not in files]
    if missing:
        sys.exit("not in the pak: %s (run make)" % ", ".join(missing))
    info = {m: Level(pak_read(PAK, files, "maps/%s.bsp" % m)) for m in names}
    maps = campaign_order(names, info)
    if opts.maps:
        want = opts.maps.split(",")
        bad = [m for m in want if m not in names]
        if bad:
            sys.exit("no such level: %s" % ", ".join(bad))
        maps = [m for m in maps if m in want]

    os.makedirs(opts.out, exist_ok=True)
    opts.user = os.path.join(opts.out, "user")
    shutil.rmtree(opts.user, ignore_errors=True)
    os.makedirs(os.path.join(opts.user, "cinder", "maps"))
    if opts.ents:
        for f in os.listdir(opts.ents):
            if f.endswith(".ent"):
                shutil.copy(os.path.join(opts.ents, f), os.path.join(opts.user, "cinder", "maps", f))
    # The engine's error box (SDL asks zenity): answered at once, so a crash
    # ends the game instead of waiting for a click.
    opts.bin = os.path.join(opts.out, "bin")
    os.makedirs(opts.bin, exist_ok=True)
    with open(os.path.join(opts.bin, "zenity"), "w") as f:
        f.write('#!/bin/sh\n[ "$1" = --version ] && echo 4.0.1\nexit 0\n')
    os.chmod(os.path.join(opts.bin, "zenity"), 0o755)

    xvfb = None
    if not opts.display:
        xvfb, opts.display = start_xvfb(opts.size)
    results = []
    try:
        if not opts.no_levels:
            print("playtest: %d levels, skill %d" % (len(maps), opts.skill), flush=True)
            with open(os.path.join(opts.out, "levels.log"), "w") as log:
                results += play_levels(maps, info, opts, log)
        if not opts.no_finale:
            print("playtest: the finale", flush=True)
            with open(os.path.join(opts.out, "finale.log"), "w") as log:
                r = play_finale(info, opts, log)
            print("  %-12s %s" % ("finale", ("ok: " + ", ".join(r.finale_steps)) if r.ok else r.summary()), flush=True)
            results.append(r)
    finally:
        for g in GAMES:
            if g.proc.poll() is None:
                g.kill()
        if xvfb:
            xvfb.terminate()
            xvfb.wait()
    path = os.path.join(opts.out, "report.md")
    report(results, opts, path)
    bad = [r for r in results if not r.ok]
    shown = os.path.relpath(path, ROOT) if path.startswith(ROOT + os.sep) else path
    print("playtest: %d of %d ok; report in %s" % (len(results) - len(bad), len(results), shown))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
