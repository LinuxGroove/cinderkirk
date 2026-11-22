#!/usr/bin/env python3
# Copyright (C) The LinuxGroove team
# SPDX-License-Identifier: GPL-2.0-or-later
"""Plays every level and the finale with nobody at the keys, on this
machine's GPU, and fails on anything that goes wrong:

    tools/playtest/playtest.py [--maps start,throat2] [--skill 1] [--no-levels] [--no-finale]
    tools/playtest/playtest.py --record ~/Videos/ck --pits 180     # a video of the whole Story and the Pits

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

3. With --pits SECONDS, each Pit fight in deathmatch with three bots at skill 2,
   the player running and shooting on a loop.

--record DIR films it all, a file per run (levels.mp4, finale.mp4, pit1.mp4
...) with a chapter per level and the game's sound. The sound never reaches
the speakers: SDL's disk driver writes it to a file in real time, laid under
the picture from the moments the game opens and closes it. Filming also slows
the tour down for watching: 1280x720 at 30 fps (through Xvfb the game can't
keep up with more), 3 s at each place, a run between places where the floor
allows (--walk), and out of each level by its own way out, through the
intermission and a shaft's epilogue (--exits). The Story runs shaft by shaft,
in the epilogues' order, each level in a copy of the game of its own, and the
finale ends it.

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
FPS = 60                 # host_maxfps: a "wait" is one frame, so this sets the script's pace (--fps)
RUN = 320                # how far a player runs in a second (sv_maxspeed)
BYTES_PER_S = 44100 * 4  # the game's sound: s16le, 44.1 kHz, stereo
# Seconds to hold the sound back from the moment SDL says it opened: a flash (bf)
# and a shot played together came out with the sound 13-40 ms early.
SOUND_LAG = 0.03
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


def epilogue_maps():
    """The levels that end a shaft with an epilogue, in the story's order (client.qc)."""
    with open(os.path.join(ROOT, "quakec", "client.qc"), encoding="utf-8") as f:
        return re.findall(r'\{\s*"maps/(\w+)\.bsp"', f.read())


def story_order(names, info):
    """The Pithead, then each shaft in the epilogues' order (its levels by name, the
    secret one last), then the rest the changelevels reach. The Pits are left out."""
    reach = reach_from_start(info, names)
    order = ["start"] if "start" in reach else []
    for e in epilogue_maps():
        shaft = re.sub(r"\d+$", "", e)
        order += sorted(m for m in reach if m.startswith(shaft) and m not in order and re.match(re.escape(shaft) + r"(\d+|_s)$", m))
    return order + sorted(m for m in reach if m not in order)


def reach_from_start(info, names):
    seen, todo = set(), ["start"]
    while todo:
        m = todo.pop()
        if m in seen or m not in names:
            continue
        seen.add(m)
        todo += [e["map"] for e in info[m].ents if e.get("classname") == "trigger_changelevel" and e.get("map")]
    return seen


def origin(e):
    return tuple(float(v) for v in e["origin"].split())


def ground(level, p):
    """Where a player over p comes to stand: dropped until the feet (24 below) meet the floor."""
    x, y, z = p
    for k in range(0, 200, 4):
        if not level.open((x, y, z - 24 - k)):
            return (x, y, z - k + 2)
    return p


def walkable(level, a, b):
    """True when a player can run straight from a to b: room for the body all
    the way, a floor under the feet, and no slime or lava."""
    d = math.dist(a[:2], b[:2])
    if d < 48 or d > 1400 or abs(a[2] - b[2]) > 40:
        return False
    n = int(d / 24) + 1
    for k in range(n + 1):
        p = [a[i] + (b[i] - a[i]) * k / n for i in range(3)]
        if not all(level.open((p[0], p[1], p[2] + dz)) for dz in (-6, 12, 28)):
            return False
        below = [level.contents((p[0], p[1], p[2] - 24 - dz)) for dz in (4, 20, 36, 52)]
        if CONTENTS_SOLID not in below or any(c in (-4, -5) for c in below[:2]):
            return False
    return True


def heading(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))


def setpos(p, pitch, yaw):
    return "setpos %.0f %.0f %.0f %.1f %.0f 0" % (p[0], p[1], p[2], pitch, yaw)


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


def places(level, n, walk=False):
    """Where to stand: the start, then up to n-1 of the creatures, pickups and other
    starts. Each is (what, x, y, z, pitch, yaw); a creature is shot from a spot nearby.
    To walk between them, each is set on the floor and they go nearest first."""
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
        if walk:
            x, y, z = ground(level, (x, y, z))
        out.append((c, x, y, z, pitch, yaw))
    if walk and out:
        tour, rest = [out[0]], out[1:]
        while rest:
            near = min(rest, key=lambda p: math.dist(p[1:4], tour[-1][1:4]))
            rest.remove(near)
            tour.append(near)
        out = tour
    return out


# ------------------------------------------------------------ running the game

def waits(n):
    return ";".join(["wait"] * max(1, int(n)))


# The client drops its first two moves in a level (cl_input.c), and an
# impulse with them: wait before the first.
SETTLE = waits(10)


class Game:
    """One copy of the game on the private display, its output line by line."""

    def __init__(self, opts, userdir, boot, first, log, extra=(), rec=None):
        env = dict(os.environ)
        lib = os.path.join(ROOT, "build", "prefix", "lib")
        env["LD_LIBRARY_PATH"] = lib + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
        if "VK_ICD_FILENAMES" not in env and os.path.exists(NVIDIA_ICD):
            env["VK_ICD_FILENAMES"] = NVIDIA_ICD
        env["PATH"] = opts.bin + ":" + env.get("PATH", "")
        env["DISPLAY"] = opts.display
        env.setdefault("XDG_RUNTIME_DIR", "/run/user/%d" % os.getuid())
        # Filming, the sound goes to a file (in real time), never to the speakers.
        self.take = rec.take() if rec else None
        if self.take:
            env.update(SDL_AUDIO_DRIVER="disk", SDL_AUDIO_DISK_OUTPUT_FILE=self.take["raw"])
        w, h = opts.size.split("x")
        # A film shows the splash once, the first time the game starts.
        quiet = ["-nosplash"] if getattr(opts, "splashed", False) else []
        opts.splashed = bool(self.take)
        cmd = ["stdbuf", "-oL", "-eL", "./cinderkirk", "-basedir", ".", "-userdir", userdir,
               "-width", w, "-height", h, "-window"] + ([] if self.take else ["-nosound"]) + quiet + [
               "+exec", boot] + list(extra) + [
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
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if self.take:                # when the sound file starts and stops, on the film's clock
                if line.startswith("SDL audio initialized"):
                    self.take["start"] = self.take["rec"].clock()
                elif line.startswith("Shutting down SDL sound"):
                    self.take["end"] = self.take["rec"].clock()
            self.lines.put(line)
        if self.take and self.take.get("start") is not None and self.take.get("end") is None:
            self.take["end"] = self.take["rec"].clock()
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


class Recorder:
    """ffmpeg filming the private display to an .mp4 with a chapter per level, the game's sound laid under it at the end."""

    def __init__(self, opts, path):
        self.path, self.part, self.marks = path, path + ".part.mp4", []
        if opts.encoder == "h264_nvenc":
            video = ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "21", "-b:v", "0"]
        else:
            video = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21"]
        self.takes = []
        cmd = ["ffmpeg", "-y", "-loglevel", "warning", "-thread_queue_size", "512", "-f", "x11grab", "-draw_mouse", "0",
               "-framerate", str(FPS), "-video_size", opts.size, "-i", opts.display]
        cmd += video + ["-g", str(2 * FPS), "-pix_fmt", "yuv420p", self.part]
        self.log = open(path + ".log", "w")
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=self.log, stderr=subprocess.STDOUT,
                                     env=dict(os.environ, DISPLAY=opts.display))
        self.t0 = time.time()

    def clock(self):
        return time.time() - self.t0

    def mark(self, title):
        self.marks.append((self.clock(), title))

    def take(self):
        """A file for one copy of the game's sound."""
        t = {"rec": self, "raw": "%s.take%d.raw" % (self.path, len(self.takes)), "start": None, "end": None}
        self.takes.append(t)
        return t

    def sound(self):
        """The game's sound as one track under the whole film (raw s16le, 44.1 kHz, stereo):
        each take stretched to the time it really took (the disk driver's clock drifts a
        little) and laid where it was heard, with silence between. None if there's none."""
        track = self.path + ".sound.raw"
        with open(track, "wb") as out:
            for t in self.takes:
                if t["start"] is None or not os.path.exists(t["raw"]) or os.path.getsize(t["raw"]) < BYTES_PER_S:
                    continue
                heard = os.path.getsize(t["raw"]) / BYTES_PER_S
                took = (t["end"] or self.clock()) - t["start"]
                tempo = min(2.0, max(0.5, heard / took)) if took > 1 else 1.0
                stretched = t["raw"] + ".fit"
                subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-f", "s16le", "-ar", "44100", "-ac", "2",
                                "-i", t["raw"], "-af", "atempo=%.6f" % tempo, "-f", "s16le", stretched],
                               stdin=subprocess.DEVNULL)
                at = int((t["start"] + SOUND_LAG) * 44100) * 4
                if at > out.tell():
                    out.write(bytes(at - out.tell()))
                with open(stretched, "rb") as f:
                    if at < out.tell():          # overlaps the last take: drop the overlap
                        f.seek(out.tell() - at)
                    shutil.copyfileobj(f, out)
                os.remove(stretched)
        if os.path.getsize(track) == 0:
            os.remove(track)
            return None
        return track

    def stop(self):
        """Ends the film and writes its chapters; returns [(start s, end s, title)]."""
        try:
            self.proc.communicate(b"q", timeout=60)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.log.close()
        end = time.time() - self.t0
        chapters = [(t, self.marks[i + 1][0] if i + 1 < len(self.marks) else end, title)
                    for i, (t, title) in enumerate(self.marks)]
        meta = self.path + ".chapters"
        with open(meta, "w") as f:
            f.write(";FFMETADATA1\n")
            for t0, t1, title in chapters:
                f.write("[CHAPTER]\nTIMEBASE=1/1000\nSTART=%d\nEND=%d\ntitle=%s\n"
                        % (t0 * 1000, t1 * 1000, re.sub(r"([=;#\\])", r"\\\1", title)))
        track = self.sound()
        cmd = ["ffmpeg", "-nostdin", "-y", "-loglevel", "warning", "-i", self.part]
        if track:
            cmd += ["-f", "s16le", "-ar", "44100", "-ac", "2", "-i", track]
        n = 2 if track else 1
        cmd += ["-i", meta, "-map_metadata", str(n), "-map_chapters", str(n), "-map", "0:v"]
        if track:
            cmd += ["-map", "1:a", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-c:v", "copy", "-movflags", "+faststart", self.path]
        with open(self.path + ".log", "a") as log:
            log.write("\n#### %s\n" % " ".join(cmd))
            log.flush()
            done = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT).returncode == 0
        if done:
            os.remove(self.part)
            for f in [t["raw"] for t in self.takes] + [self.path + ".sound.raw"]:
                if os.path.exists(f):
                    os.remove(f)
        else:
            os.replace(self.part, self.path)
        return chapters


def pick_encoder():
    for enc in ("h264_nvenc", "libx264"):
        test = ["ffmpeg", "-nostdin", "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=1280x720:rate=30",
                "-frames:v", "10", "-c:v", enc, "-f", "null", "-"]
        if subprocess.run(test, capture_output=True, stdin=subprocess.DEVNULL).returncode == 0:
            return enc
    sys.exit("ffmpeg can encode neither h264_nvenc nor libx264")


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

def level_cfg(name, nxt, pts, opts, level):
    dwell = max(2, round(opts.dwell * FPS))
    aim = dwell // 4
    out = ["echo PT_SPAWN %s" % name, "god", SETTLE, "impulse 9", waits(FPS)]
    prev = None
    for k, (cls, x, y, z, pitch, yaw) in enumerate(pts):
        here = (x, y, z)
        out.append("echo PT_AT %d %s" % (k, cls))
        if opts.walk and prev and walkable(level, prev, here):
            # setpos flies (noclip); turn that off and run there instead.
            out += [setpos(prev, 0, heading(prev, here)), "noclip", "+forward",
                    waits((math.dist(prev[:2], here[:2]) / RUN + 0.15) * FPS), "-forward"]
        out.append(setpos(here, pitch, yaw))
        if opts.walk:
            out.append("noclip")
        out += ["impulse %d" % (k % WEAPONS + 1), waits(aim), "+attack", waits(dwell - aim), "-attack"]
        prev = here
    if opts.dump:
        out.append("edicts")
    out.append("echo PT_END %s" % name)
    steps, moves_on = exit_steps(level, name, nxt, opts) if opts.exits else ([], False)
    out += steps
    if moves_on:
        pass                             # the game changes level itself, once this script has run out
    elif nxt:
        out += ['cl_spawncmd "exec pt_%s.cfg"' % nxt, "echo PT_LOAD %s" % nxt, "map %s" % nxt]
    else:
        out += ["echo PT_ALLDONE", "quit"]
    return "\n".join(out) + "\n"


def exit_steps(level, name, nxt, opts):
    """Into the level's way out (the one to nxt if there is one): the intermission,
    and a shaft's epilogue. Returns (commands, True when the game then changes
    level by itself, which happens once the script has run out: a changelevel
    waits at the end of the command buffer)."""
    ways = [e for e in level.ents if e.get("classname") == "trigger_changelevel" and e.get("model", "").startswith("*")]
    if not ways:
        return [], False
    ways.sort(key=lambda e: e.get("map") != nxt)
    e = ways[0]
    lo, hi = level.models[int(e["model"][1:])]
    inside = ((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2] + 26)
    onward = bool(nxt) and e.get("map") == nxt
    chain = ['cl_spawncmd "exec pt_%s.cfg"' % nxt, "echo PT_LOAD %s" % nxt] if onward else []
    if int(e.get("spawnflags", "0")) & 1:            # no intermission: it changes level at once
        return (chain + ["echo PT_EXIT %s" % e.get("map"), setpos(inside, 0, 0), "noclip"], True) if onward else ([], False)
    out = ["echo PT_EXIT %s" % e.get("map"), setpos(inside, 0, 0), "noclip", waits(3.5 * FPS)]
    if name in epilogue_maps():
        return out + ["+jump", waits(FPS // 5), "-jump", waits(9 * FPS)], False
    if onward:
        return out + chain + ["+jump", waits(FPS // 5), "-jump"], True
    return out, False


def boot_cfg(first, opts, spawn=None):
    out = ["host_maxfps %d" % FPS, "con_logcenterprint 1", "developer 0", "skill %d" % opts.skill,
           'cl_spawncmd "exec %s"' % (spawn or "pt_%s.cfg" % first), "echo PT_LOAD %s" % first]
    if opts.record:                      # the runner's own lines off the screen
        out += ["con_notifytime -1", "scr_showfps 0"]
    return "\n".join(out) + "\n"


def title(level):
    return next((e.get("message", "") for e in level.ents if e.get("classname") == "worldspawn"), "").split("\n")[0]


def play_levels(maps, info, opts, log, rec=None):
    results = {m: Result(m) for m in maps}
    names = set(level_names())
    for m in maps:
        for e in info[m].ents:
            if e.get("classname") == "trigger_changelevel" and e.get("map") and e["map"] not in names:
                results[m].fail("changelevel to %s, which isn't a level" % e["map"])
    plan = {m: places(info[m], opts.points, opts.walk) for m in maps}
    gamedir = os.path.join(opts.user, "cinder")
    frames = {}
    # A film starts the game again for each level, so each level's sound is laid in on its own.
    for chain in ([[m] for m in maps] if opts.record else [list(maps)]):
        todo = chain
        while todo:
            for i, m in enumerate(todo):
                text = level_cfg(m, todo[i + 1] if i + 1 < len(todo) else None, plan[m], opts, info[m])
                frames[m] = text.count("wait")
                with open(os.path.join(gamedir, "pt_%s.cfg" % m), "w") as f:
                    f.write(text)
            with open(os.path.join(gamedir, "pt_boot.cfg"), "w") as f:
                f.write(boot_cfg(todo[0], opts))
            game = Game(opts, opts.user, "pt_boot.cfg", todo[0], log, rec=rec)
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
                        if rec:
                            rec.mark("%s: %s" % (cur, title(info[cur])))
                    elif word[0] == "PT_SPAWN":
                        t_spawn = now
                        res.load_s = now - t_load
                        deadline = now + frames[cur] / FPS * 2.5 + 30
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

    slow = 2 if opts.record else 1       # a film lingers
    # The fight, from the first brake's dais, looking at the Throat's chest.
    fx, fy, fz, _ = stands[0]
    yaw = math.degrees(math.atan2(ty - fy, tx - fx))
    pitch = -math.degrees(math.atan2(tz + 200 - (fz + 22), math.hypot(tx - fx, ty - fy)))
    out = ["echo PT_SPAWN throat2", "god", "notarget", SETTLE, "impulse 9", waits(FPS),
           "setpos %g %g %g %g %g 0" % (fx, fy, fz, pitch, yaw), "impulse 2", waits(4 * FPS),
           "echo PT_FIGHT", "+attack", waits(2 * slow * FPS), "-attack", waits(FPS // 2),
           "echo PT_DUMP fight", "edicts"]
    for k, (x, y, z, ang) in enumerate(stands, 1):
        # setpos turns noclip on; turn it off again so the brake feels the push.
        out += ["setpos %g %g %g 0 %g 0" % (x, y, z, ang), "noclip", waits(FPS // 3),
                "echo PT_BRAKE %d" % k, "+forward", waits(FPS // 2), "-forward", waits(slow * FPS),
                "echo PT_DUMP brake%d" % k, "edicts"]
    view = next(e for e in ents if e.get("classname") == "info_intermission")
    mangle = [float(v) for v in view.get("mangle", "20 45 0").split()]
    out += [setpos(origin(view), mangle[0], mangle[1]), waits(3 * FPS), "echo PT_DUMP landed", "edicts",
            # The Throat ends the level 6 s after it dies; the intermission waits 2 s for a button.
            waits(9 * FPS), "echo PT_JUMP 1", "+jump", waits(FPS // 6), "-jump", waits(2 * (slow + 1) * FPS),
            # The next jump changes level, appended to the command buffer: nothing may wait after it.
            'cl_spawncmd "exec pt_after.cfg"', "echo PT_JUMP 2", "+jump", waits(FPS // 6), "-jump"]
    after = "echo PT_AFTER\n%s\necho PT_DUMP after\nedicts\nquit\n" % waits(FPS * (6 if opts.record else 1))
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


def play_finale(info, opts, log, rec=None):
    res = Result("throat2 finale")
    script, after, n_brakes = finale_cfg(info["throat2"].ents, info["throat2"].models, opts)
    if n_brakes != 4:
        res.fail("throat2 has %d brakes that reach the bell, not 4" % n_brakes)
    epilogue = qc_define("LOC_EPILOGUE_END").split("\\n")[0].strip()
    start_title = next((e.get("message", "") for e in info["start"].ents if e.get("classname") == "worldspawn"), "")
    gamedir = os.path.join(opts.user, "cinder")
    for name, text in (("pt_finale.cfg", script), ("pt_after.cfg", after),
                       ("pt_boot.cfg", boot_cfg("throat2", opts, spawn="pt_finale.cfg"))):
        with open(os.path.join(gamedir, name), "w") as f:
            f.write(text)
    if rec:
        rec.mark("throat2: %s, the finale" % title(info["throat2"]))
    game = Game(opts, opts.user, "pt_boot.cfg", "throat2", log, rec=rec)
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


# ------------------------------------------------------------ 3. the Pits

PIT_ARGS = ["-listen", "4", "+deathmatch", "1", "+bots", "3", "+skill", "2", "+fraglimit", "0", "+timelimit", "0"]


def pit_cfg(name, seconds):
    """Runs, turns, jumps and shoots on a loop for about seconds; a death respawns on the next shot.
    (Cheats and setpos are off in deathmatch.)"""
    t = lambda sec: waits(sec * FPS)
    cycle = ["+forward", "+attack", t(1.2), "-attack", "+right", t(0.25), "-right", "+jump", t(0.2), "-jump",
             t(0.6), "+moveleft", t(0.5), "-moveleft", "+attack", t(0.8), "-attack", "-forward", "+left", t(0.35), "-left"]
    out = ["echo PT_SPAWN %s" % name, t(1)] + cycle * max(1, round(seconds / 3.9)) + ["echo PT_END %s" % name, "quit"]
    return "\n".join(out) + "\n"


def play_pits(pits, info, opts, log):
    results = []
    gamedir = os.path.join(opts.user, "cinder")
    for m in pits:
        res = Result("%s (bots)" % m)
        with open(os.path.join(gamedir, "pt_pit.cfg"), "w") as f:
            f.write(pit_cfg(m, opts.pits))
        with open(os.path.join(gamedir, "pt_boot.cfg"), "w") as f:
            f.write(boot_cfg(m, opts, spawn="pt_pit.cfg"))
        rec = Recorder(opts, os.path.join(opts.record, m + ".mp4")) if opts.record else None
        if rec:
            rec.mark("%s: %s, against three bots" % (m, title(info[m])))
        game = Game(opts, opts.user, "pt_boot.cfg", m, log, PIT_ARGS, rec=rec)
        ctx = collections.deque(maxlen=40)
        t_load, deadline, fatal = time.time(), time.time() + LOAD_TIMEOUT, False
        while True:
            line = game.next_line()
            now = time.time()
            if line is None:
                break
            if line:
                ctx.append(line)
                if line.startswith("PT_SPAWN"):
                    res.load_s, t_spawn, deadline = now - t_load, now, now + opts.pits * 2.5 + 30
                elif line.startswith("PT_END"):
                    res.done, res.play_s, deadline = True, now - t_spawn, now + 30
                elif scan(line, res, ctx) == "fatal":
                    fatal = True
                    if "QUAKE ERROR" in line:
                        deadline = now + 10
                        continue
                    break
            if now > deadline:
                res.fail("hung" if not res.done else "hung on quit", ctx)
                fatal = True
                break
        rc = game.kill() if fatal or not res.done else game.wait()
        if rc not in (0, None) and not res.problems:
            res.fail("crashed (%s)" % describe_exit(rc), ctx)
        if rec:
            res.film = (rec.path, rec.stop())
        print("  %-12s %s" % (res.name, res.summary()), flush=True)
        results.append(res)
    return results


# ------------------------------------------------------------ the report

def report(results, opts, path):
    commit = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    lines = ["# Play-test", "", "Commit %s, skill %d, %d places a level, %.1f s each, at %d fps%s%s."
             % (commit or "?", opts.skill, opts.points, opts.dwell, FPS, ", walking" if opts.walk else "",
                ", out through each level's exit" if opts.exits else ""), "",
             "| Level | Result | Load | Play |", "|---|---|---|---|"]
    for r in results:
        s = r.summary()
        if r.ok and getattr(r, "finale_steps", None):
            s = "ok: " + ", ".join(r.finale_steps)
        lines.append("| %s | %s | %s | %s |" % (r.name, s.replace("|", "\\|"),
                                                "%.1f s" % r.load_s if r.load_s else "",
                                                "%.0f s" % r.play_s if r.play_s else ""))
    films = [r.film for r in results if getattr(r, "film", None)] + getattr(opts, "films", [])
    if films:
        lines += ["", "## Films", ""]
        for film, chapters in films:
            lines.append("- %s" % film)
            lines += ["  - %d:%02d %s" % (t0 // 60, t0 % 60, name) for t0, t1, name in chapters]
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
    ap.add_argument("--points", type=int, help="places to stand in each level (default 20; 16 when recording)")
    ap.add_argument("--dwell", type=float, help="seconds at each place, the last 3/4 firing (default 0.67; 3 when recording)")
    ap.add_argument("--fps", type=int, help="the frame rate the script is paced in (default 60; 30 when recording)")
    ap.add_argument("--walk", action="store_true", help="run between places where the floor allows, instead of flying")
    ap.add_argument("--exits", action="store_true", help="end each level in its way out: the intermission and any epilogue")
    ap.add_argument("--pits", type=float, default=0, metavar="SECONDS",
                    help="also play each Pit fight in deathmatch against three bots for SECONDS")
    ap.add_argument("--record", metavar="DIR", help="film it all into DIR (levels.mp4, finale.mp4, pitN.mp4), with sound")
    ap.add_argument("--ents", help="a folder of <map>.ent entity lumps to load over the pak's (to try a fix without a rebuild)")
    ap.add_argument("--dump", action="store_true", help="dump the edicts into levels.log at the end of each level")
    ap.add_argument("--no-levels", action="store_true", help="only the finale")
    ap.add_argument("--no-finale", action="store_true", help="only the levels")
    # Through Xvfb, copying each frame out bounds the frame rate: 1280x720 makes
    # 32 fps on an RTX laptop, and the script's waits are frames.
    ap.add_argument("--size", help="the window (default 640x360, which keeps up with 60 fps; 1280x720 when recording)")
    ap.add_argument("--display", help="an X display to use instead of a private Xvfb")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "playtest"), help="logs and report (default build/playtest)")
    opts = ap.parse_args()
    global FPS
    film = bool(opts.record)
    FPS = opts.fps or (30 if film else 60)
    opts.dwell = opts.dwell if opts.dwell is not None else (3.0 if film else 40 / 60)
    opts.points = opts.points or (16 if film else 20)
    opts.size = opts.size or ("1280x720" if film else "640x360")
    opts.walk, opts.exits = opts.walk or film, opts.exits or film

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
    pits = sorted(m for m in names if m not in reach_from_start(info, names))
    if film:                         # the Story as a player meets it; the finale and the Pits come after
        maps = [m for m in story_order(names, info) if m != "throat2"]
    else:
        maps = campaign_order(names, info)
    if opts.maps:
        want = opts.maps.split(",")
        bad = [m for m in want if m not in names]
        if bad:
            sys.exit("no such level: %s" % ", ".join(bad))
        maps = [m for m in maps if m in want]
        pits = [m for m in pits if m in want]

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
    results, opts.films = [], []
    if film:
        opts.record = os.path.abspath(os.path.expanduser(opts.record))
        os.makedirs(opts.record, exist_ok=True)
        opts.encoder = pick_encoder()
        print("playtest: filming into %s (%s)" % (opts.record, opts.encoder), flush=True)
    rec = None
    try:
        if not opts.no_levels and maps:
            print("playtest: %d levels, skill %d" % (len(maps), opts.skill), flush=True)
            rec = Recorder(opts, os.path.join(opts.record, "levels.mp4")) if film else None
            with open(os.path.join(opts.out, "levels.log"), "w") as log:
                results += play_levels(maps, info, opts, log, rec)
            if rec:
                opts.films.append((rec.path, rec.stop()))
                rec = None
        if not opts.no_finale:
            print("playtest: the finale", flush=True)
            rec = Recorder(opts, os.path.join(opts.record, "finale.mp4")) if film else None
            with open(os.path.join(opts.out, "finale.log"), "w") as log:
                r = play_finale(info, opts, log, rec)
            if rec:
                opts.films.append((rec.path, rec.stop()))
                rec = None
            print("  %-12s %s" % ("finale", ("ok: " + ", ".join(r.finale_steps)) if r.ok else r.summary()), flush=True)
            results.append(r)
        if opts.pits and pits:
            print("playtest: the Pits, %d s each against three bots" % opts.pits, flush=True)
            with open(os.path.join(opts.out, "pits.log"), "w") as log:
                results += play_pits(pits, info, opts, log)
    finally:
        for g in GAMES:
            if g.proc.poll() is None:
                g.kill()
        if rec:
            rec.stop()
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
