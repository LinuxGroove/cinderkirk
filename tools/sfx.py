#!/usr/bin/env python3
"""Synthesize Cinderkirk's own sounds from fixed seeds, so the build makes the
same files every time.

    tools/sfx.py OUT_DIR        writes OUT_DIR/cinder/*.wav, and the sounds the
                                game asks for by their old paths (OUT_DIR/doors/,
                                player/ and the rest, from tools/sfx_world.py)

16-bit mono at 22050 Hz, as the engine mixes. A sound whose name ends in
_loop gets a cue point at its start, which tells the engine to loop it.
"""

import os
import struct
import sys

import numpy as np

RATE = 22050


def t(seconds):
    return np.arange(int(seconds * RATE)) / RATE


def noise(seconds, seed):
    return np.random.default_rng(seed).standard_normal(len(t(seconds)))


def lowpass(x, cutoff):
    """One-pole low pass; cutoff may be an array (a sweep)."""
    a = np.exp(-2 * np.pi * np.broadcast_to(cutoff, x.shape) / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a[i]) * v + a[i] * acc
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def envelope(n, attack, release, hold=0.0):
    a, h = int(attack * RATE), int(hold * RATE)
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a) if a else 1
    r = n - a - h
    env[a + h:] = np.exp(-np.linspace(0, release, r)) if r > 0 else 1
    return env


def steam(seconds, seed, low, high, attack, release, hold=0.0):
    """A hiss: noise band-passed by a sweep from high to low."""
    x = noise(seconds, seed)
    sweep = np.geomspace(high, low, len(x))
    x = highpass(lowpass(x, sweep), 400)
    return x * envelope(len(x), attack, release, hold)


def clank(seconds, freqs, seed):
    """Struck iron: a few inharmonic partials that ring down."""
    tt = t(seconds)
    rng = np.random.default_rng(seed)
    out = np.zeros_like(tt)
    for i, f in enumerate(freqs):
        out += np.sin(2 * np.pi * f * tt + rng.uniform(0, 6.28)) * np.exp(-tt * (6 + 3 * i)) / (1 + i)
    return out


def groan(seconds, seed, f0, f1, rasp=0.6):
    """A dry throat: a buzzing source swept from f0 to f1 Hz, through two
    vowel-ish resonances, with breath noise and a slow shake."""
    tt = t(seconds)
    rng = np.random.default_rng(seed)
    f = np.geomspace(f0, f1, len(tt)) * (1 + 0.03 * np.sin(2 * np.pi * 5.5 * tt + rng.uniform(0, 6)))
    ph = np.cumsum(f) / RATE
    buzz = 2 * (ph % 1.0) - 1
    breath = noise(seconds, seed + 100)
    src = buzz * (1 - rasp) + breath * rasp * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * ph)))
    x = highpass(lowpass(src, 900), 180) + 0.5 * highpass(lowpass(src, 2400), 1400)
    return x * (0.8 + 0.2 * np.sin(2 * np.pi * 3.1 * tt))


def crackle(seconds, seed, density, decay):
    """Ash and embers giving way: sparse clicks, thinning out."""
    rng = np.random.default_rng(seed)
    n = len(t(seconds))
    x = np.zeros(n)
    hits = rng.random(n) < density * np.exp(-np.arange(n) / RATE * decay)
    x[hits] = rng.standard_normal(hits.sum()) * rng.uniform(0.3, 1.0, hits.sum())
    return highpass(lowpass(x, 5000), 600)


def bell(seconds, f, seed, decay=1.5):
    """A cast bell: a hum, a prime, a minor third, a fifth and an octave, each
    ringing down at its own rate, with the strike's click."""
    tt = t(seconds)
    rng = np.random.default_rng(seed)
    out = np.zeros_like(tt)
    for ratio, amp, d in ((0.5, 0.6, 0.6), (1.0, 1.0, 1.0), (1.19, 0.5, 1.4), (1.5, 0.35, 1.8), (2.0, 0.4, 2.2),
                          (2.51, 0.2, 3.0), (2.98, 0.15, 3.6)):
        fr = f * ratio * (1 + rng.uniform(-0.003, 0.003))
        out += amp * np.sin(2 * np.pi * fr * tt + rng.uniform(0, 6.28)) * np.exp(-tt * decay * d)
    click = highpass(noise(seconds, seed + 1), 2000) * np.exp(-tt * 200) * 0.4
    return out + click


def chant(seconds, seed, f0, voices=3):
    """Low voices on one note, a little apart: the cult's drone."""
    out = 0
    for v in range(voices):
        out = out + groan(seconds, seed + v, f0 * (1 + 0.012 * v), f0 * (1 + 0.012 * v) * 0.98, 0.25)
    return out


def lay(*parts):
    """Mixes (sound, start in seconds) pairs into one, as long as it needs."""
    n = max(int(at * RATE) + len(x) for x, at in parts)
    out = np.zeros(n)
    for x, at in parts:
        i = int(at * RATE)
        out[i:i + len(x)] += x
    return out


def normalise(x, peak=0.8):
    return x / (np.abs(x).max() + 1e-9) * peak


def write(path, x, loop=False):
    data = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    fmt = struct.pack("<HHIIHH", 1, 1, RATE, RATE * 2, 2, 16)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    if loop:
        cue = struct.pack("<II", 1, 0) + struct.pack("<II4sIII", 0, 0, b"data", 0, 0, 0)
        chunks += b"cue " + struct.pack("<I", len(cue)) + cue
    chunks += b"data" + struct.pack("<I", len(data)) + data
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks)


def sounds():
    yield "dash", normalise(steam(0.45, 1, 500, 6000, 0.01, 6) + 0.25 * clank(0.45, [180, 431], 2))
    yield "vent", normalise(steam(0.9, 3, 300, 7000, 0.005, 4, hold=0.15))
    yield "scald", normalise(steam(0.3, 4, 2500, 9000, 0.002, 9) *
                             (1 + 0.6 * np.sign(np.sin(2 * np.pi * 37 * t(0.3))))) * 0.8
    yield "empty", normalise(clank(0.25, [900, 1730], 5) + 0.3 * steam(0.25, 6, 1500, 3000, 0.002, 14)) * 0.6
    tt = t(0.6)
    whistle = np.sin(2 * np.pi * np.cumsum(np.linspace(900, 1500, len(tt))) / RATE)
    yield "redline", normalise(whistle * envelope(len(tt), 0.05, 4) + 0.3 * steam(0.6, 7, 1500, 5000, 0.05, 4))
    # A soft hiss for vents to sit in: its tail is faded into its head, so it loops without a seam.
    x = highpass(lowpass(noise(2.25, 8), 2200), 300)
    n, fade = int(2.0 * RATE), int(0.25 * RATE)
    ramp = np.linspace(0, 1, fade)
    loop = x[:n].copy()
    loop[:fade] = x[:fade] * ramp + x[n:n + fade] * (1 - ramp)
    yield "vent_loop", normalise(loop, 0.5)

    # The Ashen.
    yield "ashen_idle", normalise(groan(1.4, 20, 85, 70, 0.7) * envelope(len(t(1.4)), 0.3, 3), 0.6)
    yield "ashen_sight", normalise(groan(1.0, 21, 90, 150, 0.5) * envelope(len(t(1.0)), 0.08, 3, hold=0.4))
    yield "ashen_pain", normalise(groan(0.35, 22, 140, 95, 0.4) * envelope(len(t(0.35)), 0.01, 6))
    yield "ashen_death", normalise(lay((groan(0.5, 24, 120, 60, 0.6) * envelope(len(t(0.5)), 0.01, 4) * 0.7, 0),
                                       (crackle(1.1, 25, 0.004, 2.5), 0.3), (steam(1.4, 23, 300, 2500, 0.02, 3) * 0.4, 0)))
    tt = t(0.8)
    thump = np.sin(2 * np.pi * np.cumsum(np.geomspace(120, 40, len(tt))) / RATE) * np.exp(-tt * 9)
    yield "ashen_burst", normalise(thump + crackle(0.8, 26, 0.02, 4) + 0.5 * steam(0.8, 27, 400, 5000, 0.002, 6))
    rise = lay((steam(1.6, 28, 2500, 300, 0.6, 1, hold=0.5) * 0.4, 0), (crackle(1.6, 29, 0.003, -0.8), 0),
               (groan(0.7, 30, 60, 95, 0.6) * envelope(len(t(0.7)), 0.2, 3), 0.9))
    yield "ashen_rise", normalise(rise)
    yield "ashen_swipe", normalise(steam(0.35, 31, 700, 3500, 0.12, 8), 0.5)
    tt = t(0.3)
    hit = np.sin(2 * np.pi * 75 * tt) * np.exp(-tt * 18) + 0.5 * highpass(noise(0.3, 32), 800) * np.exp(-tt * 40)
    yield "ashen_hit", normalise(hit)

    # The Censer-bearers and Deacons.
    n = lambda d: envelope(len(t(d)), 0.15, 2.5, hold=d * 0.4)
    yield "censer_sight", normalise(chant(1.2, 40, 110) * n(1.2))
    yield "censer_pain", normalise(groan(0.4, 41, 160, 120, 0.4) * envelope(len(t(0.4)), 0.01, 6))
    yield "censer_death", normalise(groan(0.9, 42, 150, 70, 0.5) * envelope(len(t(0.9)), 0.01, 3))
    tt = t(0.5)
    rattle = crackle(0.5, 43, 0.01, 6) * 0.6
    yield "censer_swing", normalise(steam(0.5, 44, 500, 2500, 0.15, 5) + rattle + 0.3 * clank(0.5, [1300, 2210], 45))
    yield "coal_throw", normalise(steam(0.4, 46, 900, 3000, 0.05, 7) + crackle(0.4, 47, 0.008, 5), 0.6)
    yield "coal_hit", normalise(lay((steam(0.6, 48, 2000, 8000, 0.002, 6), 0), (crackle(0.6, 49, 0.02, 6), 0)), 0.7)
    yield "deacon_sight", normalise(lay((chant(1.6, 50, 73, 4) * n(1.6), 0), (bell(1.6, 620, 51, 2.0) * 0.5, 0.1)))
    yield "deacon_pain", normalise(groan(0.5, 52, 95, 80, 0.4) * envelope(len(t(0.5)), 0.01, 5))
    yield "deacon_death", normalise(lay((groan(1.4, 53, 90, 45, 0.5) * envelope(len(t(1.4)), 0.01, 2.5), 0),
                                        (bell(1.4, 600, 54, 3.0) * 0.4, 0.5)))
    yield "deacon_bell", normalise(lay(*[(bell(1.2, 640, 55 + i, 1.6) * (1 - 0.15 * i), 0.22 * i) for i in range(4)]))
    # Slag hounds: growls through a hot throat, snapping jaws of stone.
    yield "hound_idle", normalise(groan(0.9, 70, 70, 62, 0.75) * envelope(len(t(0.9)), 0.1, 4), 0.5)
    snarl = groan(0.8, 71, 120, 210, 0.65) * (0.7 + 0.3 * np.sign(np.sin(2 * np.pi * 23 * t(0.8))))
    yield "hound_sight", normalise(lay((snarl * envelope(len(t(0.8)), 0.04, 3, hold=0.3), 0),
                                       (steam(0.7, 72, 1500, 6000, 0.02, 5) * 0.35, 0.1)))
    tt = t(0.22)
    snap = clank(0.22, [520, 1170, 2290], 73) * 0.7 + highpass(noise(0.22, 74), 1500) * np.exp(-tt * 60)
    yield "hound_bite", normalise(snap)
    yield "hound_leap", normalise(lay((groan(0.45, 75, 160, 260, 0.6) * envelope(len(t(0.45)), 0.02, 6), 0),
                                      (steam(0.5, 76, 600, 4000, 0.05, 6) * 0.5, 0)))
    yield "hound_pain", normalise(groan(0.3, 77, 420, 260, 0.35) * envelope(len(t(0.3)), 0.005, 9))
    yield "hound_death", normalise(lay((groan(0.7, 78, 300, 90, 0.5) * envelope(len(t(0.7)), 0.01, 4), 0),
                                       (crackle(1.2, 79, 0.006, 2.0), 0.4), (steam(1.2, 80, 2500, 300, 0.1, 2) * 0.4, 0.3)))
    tt = t(0.7)
    burst = np.sin(2 * np.pi * np.cumsum(np.geomspace(140, 45, len(tt))) / RATE) * np.exp(-tt * 10)
    yield "hound_burst", normalise(burst + crackle(0.7, 81, 0.03, 5) + 0.6 * steam(0.7, 82, 800, 7000, 0.002, 6))
    # Gaugers: a man behind an iron mask, and a steam lance's valve and jet.
    yield "gauger_idle", normalise(groan(0.8, 90, 110, 100, 0.6) * envelope(len(t(0.8)), 0.1, 4) +
                                   0.2 * steam(0.8, 91, 1500, 3000, 0.2, 3), 0.5)
    yield "gauger_sight", normalise(lay((groan(0.7, 92, 130, 180, 0.55) * envelope(len(t(0.7)), 0.03, 4, hold=0.2), 0),
                                        (clank(0.5, [410, 1020], 93) * 0.4, 0.05)))
    tt = t(0.8)
    valve = steam(0.8, 94, 4000, 9000, 0.6, 1, hold=0.15) * (1 + 0.25 * np.sin(2 * np.pi * 31 * tt))
    yield "gauger_hiss", normalise(lay((clank(0.2, [1600, 2850], 95) * 0.5, 0), (valve, 0.05)))
    yield "gauger_fire", normalise(lay((steam(0.5, 96, 300, 8000, 0.003, 6), 0), (0.4 * clank(0.3, [220, 530], 97), 0)))
    yield "gauger_jab", normalise(clank(0.3, [380, 910, 1760], 98) + 0.5 * steam(0.3, 99, 2000, 6000, 0.002, 12))
    yield "gauger_pain", normalise(groan(0.35, 100, 170, 120, 0.4) * envelope(len(t(0.35)), 0.01, 7))
    yield "gauger_death", normalise(lay((groan(0.9, 101, 150, 70, 0.5) * envelope(len(t(0.9)), 0.01, 3), 0),
                                        (steam(1.2, 102, 6000, 800, 0.05, 2) * 0.5, 0.2)))
    # Crucible Brutes: big, slow, the slag in the crucible slopping.
    yield "brute_idle", normalise(groan(1.2, 110, 52, 46, 0.8) * envelope(len(t(1.2)), 0.2, 3), 0.6)
    yield "brute_sight", normalise(lay((groan(1.3, 111, 55, 95, 0.75) * envelope(len(t(1.3)), 0.06, 2.5, hold=0.5), 0),
                                       (crackle(1.0, 112, 0.01, 3), 0.2)))
    tt = t(0.4)
    yield "brute_step", normalise(lay((np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 14), 0), (0.2 * clank(0.4, [160, 370], 113), 0)), 0.6)
    yield "brute_pour", normalise(lay((steam(1.4, 114, 600, 3500, 0.1, 1.5, hold=0.6), 0), (crackle(1.4, 115, 0.03, 1.5), 0),
                                      (groan(1.0, 116, 60, 50, 0.9) * envelope(len(t(1.0)), 0.1, 3) * 0.5, 0)))
    yield "brute_swing", normalise(steam(0.6, 117, 300, 1800, 0.2, 5) + 0.3 * crackle(0.6, 118, 0.01, 4))
    tt = t(0.6)
    yield "brute_hit", normalise(np.sin(2 * np.pi * np.cumsum(np.geomspace(90, 35, len(tt))) / RATE) * np.exp(-tt * 8)
                                 + clank(0.6, [210, 480, 1130], 119) * 0.6 + crackle(0.6, 120, 0.03, 5))
    yield "brute_pain", normalise(groan(0.5, 121, 90, 65, 0.6) * envelope(len(t(0.5)), 0.01, 5))
    yield "brute_death", normalise(groan(1.6, 122, 80, 30, 0.7) * envelope(len(t(1.6)), 0.02, 2))
    tt = t(1.0)
    yield "brute_fall", normalise(lay((np.sin(2 * np.pi * 38 * tt) * np.exp(-tt * 6), 0), (clank(0.8, [140, 330], 123) * 0.5, 0),
                                      (steam(1.0, 124, 400, 5000, 0.01, 3) * 0.5, 0.05), (crackle(1.0, 125, 0.03, 3), 0.05)))
    # Clinkers: stone legs on stone, a hiss as they swell, and the burst.
    yield "clinker_skitter", normalise(lay((crackle(0.4, 130, 0.05, 2), 0), (0.3 * clank(0.4, [2400, 3900], 131), 0)), 0.4)
    yield "clinker_sight", normalise(lay((crackle(0.5, 132, 0.08, 3), 0), (steam(0.5, 133, 2000, 7000, 0.02, 6) * 0.4, 0)))
    yield "clinker_drop", normalise(lay((crackle(0.3, 134, 0.06, 6), 0), (clank(0.3, [700, 1900], 135) * 0.6, 0.25)))
    tt = t(0.8)
    swell = steam(0.8, 136, 800, 7000, 0.7, 2, hold=0.1) * (1 + 0.5 * np.sin(2 * np.pi * np.cumsum(np.linspace(6, 22, len(tt))) / RATE))
    yield "clinker_swell", normalise(swell + crackle(0.8, 137, 0.02, -1))
    tt = t(0.8)
    pop = np.sin(2 * np.pi * np.cumsum(np.geomspace(180, 50, len(tt))) / RATE) * np.exp(-tt * 12)
    yield "clinker_burst", normalise(pop + crackle(0.8, 138, 0.05, 5) + 0.6 * steam(0.8, 139, 1000, 8000, 0.002, 7))
    # Cistern leeches: wet, under water, and the sucker.
    tt = t(0.6)
    gulp = lowpass(noise(0.6, 140), 600) * envelope(len(tt), 0.05, 4)
    yield "leech_sight", normalise(gulp + 0.4 * groan(0.6, 141, 70, 110, 0.3) * envelope(len(tt), 0.1, 5))
    tt = t(0.35)
    yield "leech_bite", normalise(lowpass(noise(0.35, 142), 900) * np.exp(-tt * 9) + 0.5 * np.sin(2 * np.pi * 85 * tt) * np.exp(-tt * 12))
    tt = t(0.5)
    yield "leech_feed", normalise(lowpass(noise(0.5, 143), 400) * (0.6 + 0.4 * np.sin(2 * np.pi * 5 * tt)) * envelope(len(tt), 0.05, 4), 0.5)
    yield "leech_pain", normalise(lowpass(noise(0.3, 144), 1200) * envelope(len(t(0.3)), 0.01, 9))
    yield "leech_death", normalise(lay((lowpass(noise(0.8, 145), 500) * envelope(len(t(0.8)), 0.01, 4), 0),
                                       (groan(0.6, 146, 90, 40, 0.3) * envelope(len(t(0.6)), 0.05, 4) * 0.4, 0.1)))
    # Ash wraiths: a breath of ash, a dry rising shriek when they swoop.
    tt = t(1.2)
    yield "wraith_idle", normalise(steam(1.2, 150, 200, 1400, 0.4, 2, 0.3) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.8 * tt)), 0.4)
    yield "wraith_sight", normalise(lay((steam(0.9, 151, 400, 3000, 0.2, 3), 0), (groan(0.8, 152, 160, 240, 0.8) * 0.5, 0.05)))
    tt = t(0.7)
    shriek = np.sin(2 * np.pi * np.cumsum(np.geomspace(300, 900, len(tt))) / RATE) * envelope(len(tt), 0.1, 3)
    yield "wraith_swoop", normalise(shriek * 0.4 + steam(0.7, 153, 1500, 7000, 0.15, 3))
    yield "wraith_claw", normalise(steam(0.25, 154, 2500, 9000, 0.005, 14) + 0.3 * crackle(0.25, 155, 0.02, 12))
    yield "wraith_pain", normalise(lay((groan(0.4, 156, 260, 180, 0.9), 0), (steam(0.3, 157, 800, 4000, 0.01, 8) * 0.5, 0)))
    yield "wraith_death", normalise(lay((groan(1.0, 158, 220, 60, 0.9) * envelope(len(t(1.0)), 0.02, 2), 0),
                                        (steam(1.4, 159, 200, 2500, 0.3, 2, 0.4) * 0.7, 0.2)))
    # Bell-ringers: the great toll, deep and long; a groan of iron when they see you.
    yield "ringer_toll", normalise(lay((bell(3.0, 98, 160, 0.7), 0), (bell(2.5, 196, 161, 1.0) * 0.4, 0.0),
                                       (lowpass(noise(0.4, 162), 300) * envelope(len(t(0.4)), 0.001, 8) * 0.8, 0)))
    yield "ringer_sight", normalise(lay((groan(1.4, 163, 55, 80, 0.7), 0), (bell(1.4, 140, 164, 2.0) * 0.4, 0.2)))
    yield "ringer_swing", normalise(steam(0.4, 165, 200, 1500, 0.05, 6) + 0.4 * groan(0.4, 166, 90, 60, 0.5))
    yield "ringer_pain", normalise(lay((groan(0.6, 167, 70, 50, 0.8), 0), (bell(0.6, 220, 168, 4.0) * 0.3, 0)))
    yield "ringer_death", normalise(lay((groan(1.6, 169, 70, 30, 0.8) * envelope(len(t(1.6)), 0.02, 2), 0),
                                        (bell(2.5, 92, 170, 0.9) * 0.6, 0.6)))
    # The Founder: a voice like a furnace door, iron poured and slammed.
    yield "founder_sight", normalise(lay((groan(2.2, 171, 48, 70, 0.8), 0), (bell(2.0, 74, 172, 1.2) * 0.35, 0.3),
                                         (steam(2.0, 173, 150, 900, 0.3, 2, 0.5) * 0.4, 0)))
    yield "founder_idle", normalise(groan(1.6, 174, 45, 55, 0.6) * envelope(len(t(1.6)), 0.3, 2), 0.5)
    tt = t(1.6)
    yield "founder_pour", normalise(steam(1.6, 175, 300, 3000, 0.1, 2, 0.8) * (0.8 + 0.2 * np.sin(2 * np.pi * 9 * tt))
                                    + crackle(1.6, 176, 0.03, 2) * 0.7)
    yield "founder_hurl", normalise(lay((groan(0.5, 177, 70, 50, 0.7), 0), (steam(0.6, 178, 400, 2500, 0.02, 6) * 0.7, 0.15)))
    yield "founder_slam", normalise(lay((lowpass(noise(0.9, 179), 220) * envelope(len(t(0.9)), 0.002, 5), 0),
                                        (clank(1.2, [90, 233, 410], 180) * 0.6, 0), (crackle(0.8, 181, 0.04, 4) * 0.5, 0.05)))
    yield "founder_pain", normalise(lay((groan(0.8, 182, 60, 42, 0.9), 0), (crackle(0.5, 183, 0.05, 6) * 0.4, 0)))
    yield "founder_death", normalise(lay((groan(3.0, 184, 55, 24, 0.9) * envelope(len(t(3.0)), 0.05, 1.2), 0),
                                         (crackle(2.5, 185, 0.06, 1.5) * 0.6, 0.4), (bell(3.0, 61, 186, 0.6) * 0.5, 1.2)))
    # The powerups: the Forge Heart beats, the Founder's Mantle rings deep, the
    # Soot Veil breathes ash, and the Quench Suit hisses its air.
    tt = t(1.4)
    beat = np.zeros(len(tt))
    for at in (0.0, 0.22, 0.7, 0.92):
        i = int(at * RATE)
        k = lowpass(noise(0.18, 200 + i), 120) * envelope(int(0.18 * RATE), 0.004, 14)
        beat[i:i + len(k)] += k[:len(beat) - i]
    yield "heart", normalise(lay((beat, 0), (steam(1.4, 201, 200, 1800, 0.05, 2.5) * 0.35, 0), (bell(1.2, 330, 202, 2.5) * 0.25, 0)))
    yield "heart_fade", normalise(lay((beat[:int(0.5 * RATE)] * 0.8, 0), (steam(0.5, 203, 150, 900, 0.01, 7) * 0.3, 0)), 0.6)
    yield "heart_hit", normalise(lay((clank(0.35, [140, 377], 204), 0), (lowpass(noise(0.3, 205), 300) * envelope(len(t(0.3)), 0.002, 12), 0)))
    yield "mantle", normalise(lay((bell(2.8, 82, 206, 0.8), 0), (bell(2.2, 164, 207, 1.2) * 0.35, 0.05), (chant(2.0, 208, 110) * 0.15, 0.3)))
    yield "mantle_fade", normalise(bell(1.2, 82, 209, 2.5) * 0.7, 0.6)
    yield "mantle_hit", normalise(lay((bell(0.8, 247, 210, 4.0), 0), (clank(0.3, [500, 1210], 211) * 0.4, 0)), 0.7)
    tt = t(1.6)
    yield "veil", normalise(lowpass(noise(1.6, 212), 1400) * np.sin(np.pi * tt / 1.6) ** 2 + crackle(1.6, 213, 0.01, 3) * 0.3, 0.6)
    yield "veil_fade", normalise(lowpass(noise(0.7, 214), 900) * envelope(len(t(0.7)), 0.2, 4), 0.5)
    tt = t(1.2)
    yield "veil_idle", normalise(lowpass(noise(1.2, 215), 600) * np.sin(np.pi * tt / 1.2) ** 2, 0.35)
    yield "suit", normalise(lay((clank(0.4, [300, 820], 216) * 0.5, 0), (steam(1.2, 217, 400, 5000, 0.02, 2, 0.4), 0.1)))
    yield "suit_fade", normalise(steam(0.6, 218, 600, 3000, 0.01, 5) * (1 + 0.8 * np.sign(np.sin(2 * np.pi * 6 * t(0.6)))), 0.6)
    yield "deacon_throw", normalise(steam(0.6, 60, 300, 2000, 0.2, 4) + crackle(0.6, 61, 0.01, 4) * 0.6)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = os.path.join(sys.argv[1], "cinder")
    os.makedirs(out, exist_ok=True)
    for name, x in sounds():
        write(os.path.join(out, name + ".wav"), x, loop=name.endswith("_loop"))
    import sfx_world
    for name, x in sfx_world.sounds():
        path = os.path.join(sys.argv[1], name + ".wav")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        write(path, x, loop=name in sfx_world.LOOPS)
    print(f"sounds in {sys.argv[1]}")


if __name__ == "__main__":
    main()
