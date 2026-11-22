#!/usr/bin/env python3
# Copyright (C) The LinuxGroove team
# SPDX-License-Identifier: GPL-2.0-or-later
"""Loads every level in a dedicated server (no window, no GPU) and lists the
things the game code gave up on: items that fell out of the level (their box
started inside a brush, so the key, weapon or health was removed), creatures
stuck in a wall, and targets nothing answers to.

    tools/spawncheck.py [MAP ...]      every built level when none are given

tools/stuck.py only looks at origins; this asks the game itself, which knows
each thing's real size. Kilns 1's silver key once sat a few units into its
bier and was quietly removed, so the level couldn't be finished. Exits 1 if
anything is wrong.
"""

import glob
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIST = os.path.join(ROOT, "dist")
SETTLE = 2
PROBLEMS = re.compile(r"fell out of level|in wall at|can't find target", re.I)


def check(name, skill, port):
    env = dict(os.environ)
    lib = os.path.join(ROOT, "build", "prefix", "lib")
    env["LD_LIBRARY_PATH"] = lib + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
    # Each server gets its own port, so they can run side by side. It reads its console from stdin. The echo runs once the level
    # has loaded; things settle on the floor in the next second of game
    # time, so give it two more, then quit.
    cmd = ["stdbuf", "-oL", "./cinderkirk", "-basedir", ".", "-dedicated", "-port", str(port),
           "+developer", "1", "+deathmatch", "0", "+coop", "0", "+skill", str(skill),
           "+map", name]
    p = subprocess.Popen(cmd, cwd=DIST, env=env, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    p.stdin.write("echo spawncheck: loaded\n")
    p.stdin.flush()
    out = []
    deadline = time.time() + 60
    for line in p.stdout:
        out.append(line)
        if "spawncheck: loaded" in line or time.time() > deadline:
            break
    time.sleep(SETTLE)
    try:
        p.stdin.write("quit\n")
        p.stdin.flush()
    except BrokenPipeError:
        pass
    try:
        rest, _ = p.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        p.kill()
        rest, _ = p.communicate()
    out = "".join(out) + rest
    if "Couldn't spawn server" in out or "Host_Error" in out:
        return ["the level didn't load"]
    seen = []
    for line in out.splitlines():
        if PROBLEMS.search(line) and line.strip() not in seen:
            seen.append(line.strip())
    return seen


def main():
    names = sys.argv[1:] or sorted(os.path.splitext(os.path.basename(p))[0]
                                   for p in glob.glob(os.path.join(ROOT, "build", "maps", "*.bsp")))
    jobs = [(name, skill) for name in names for skill in (0, 2)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda ij: check(*ij[1], 27100 + ij[0]), enumerate(jobs)))
    bad = 0
    for (name, skill), lines in zip(jobs, results):
        for line in lines:
            print("%s (skill %d): %s" % (name, skill, line))
            bad += 1
    if bad:
        print("%d things the game removed or couldn't place" % bad)
        sys.exit(1)
    print("spawncheck: %d levels, everything in place" % len(names))


if __name__ == "__main__":
    main()
