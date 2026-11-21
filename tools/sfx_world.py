#!/usr/bin/env python3
# Copyright (C) The LinuxGroove team
# SPDX-License-Identifier: GPL-2.0-or-later
"""The sounds the game code and the engine ask for by their old paths
(player/, doors/, plats/, buttons/, items/, misc/, weapons/, ambience/, and
the two hits the engine plays itself),
synthesized for Cinderkirk so none of LibreQuake's stand-ins are heard.

tools/sfx.py writes them with its own sounds: each lands at OUT_DIR/<path>.wav
over the stand-in of the same name. Moving doors, lifts and the ambient beds
loop (LOOPS); everything else plays once.
"""

import numpy as np

from sfx import (RATE, bell, clank, crackle, envelope, highpass, lay, lowpass, noise, normalise, steam, t)

# What loops: the moves of doors, lifts and trains (the stop sound on the same
# channel ends them) and the ambient beds.
LOOPS = {
    "doors/stndr1", "doors/doormv1", "doors/hydro1", "doors/ddoor1", "doors/airdoor1", "doors/basesec1",
    "doors/winch2", "plats/plat1", "plats/medplat1", "plats/train1",
    "ambience/buzz1", "ambience/comp1", "ambience/drip1", "ambience/drone6", "ambience/fire1",
    "ambience/fl_hum1", "ambience/hum1", "ambience/suck1", "ambience/swamp1", "ambience/swamp2",
    "ambience/water1", "ambience/wind2",
}

VOWELS = {  # formants (Hz) of a low male voice
    "ah": (700, 1150, 2500), "uh": (560, 1100, 2400), "eh": (520, 1800, 2500),
    "oh": (520, 850, 2400), "oo": (330, 800, 2300), "hh": (900, 1600, 2600),
}


def reson(x, f, q):
    """A two-pole resonator at f Hz (f may be an array), bandwidth f / q."""
    f = np.broadcast_to(np.asarray(f, float), x.shape)
    r = np.exp(-np.pi * f / q / RATE)
    c = 2 * r * np.cos(2 * np.pi * f / RATE)
    g = (1 - r) * np.sqrt(np.maximum(1 - 2 * r * np.cos(4 * np.pi * f / RATE) + r * r, 1e-6))
    y = np.empty_like(x)
    y1 = y2 = 0.0
    for i in range(len(x)):
        v = g[i] * x[i] + c[i] * y1 - r[i] * r[i] * y2
        y2, y1 = y1, v
        y[i] = v
    return y


def voice(seconds, seed, f0, f1, vowel="uh", breath=0.3, vowel2=None):
    """The stoker's voice: a glottal buzz swept from f0 to f1 through three
    formants (gliding to vowel2 if given), with breath under it."""
    tt = t(seconds)
    rng = np.random.default_rng(seed)
    f = np.geomspace(f0, f1, len(tt)) * (1 + 0.02 * rng.standard_normal(len(tt)).cumsum() / np.sqrt(len(tt)))
    ph = np.cumsum(f) / RATE
    buzz = lowpass(2 * (ph % 1.0) - 1, 1800)
    src = buzz * (1 - breath) + noise(seconds, seed + 7) * breath * 0.6
    a = np.array(VOWELS[vowel], float)
    b = np.array(VOWELS[vowel2 or vowel], float)
    k = np.linspace(0, 1, len(tt))[:, None]
    fm = a * (1 - k) + b * k
    out = reson(src, fm[:, 0], 6) + 0.6 * reson(src, fm[:, 1], 8) + 0.25 * reson(src, fm[:, 2], 10)
    return highpass(out, 90)


def thud(seconds, f0, f1, decay, seed, grit=0.3):
    """A heavy body landing: a falling sine with a little dirt in it."""
    tt = t(seconds)
    body = np.sin(2 * np.pi * np.cumsum(np.geomspace(f0, f1, len(tt))) / RATE) * np.exp(-tt * decay)
    return body + grit * lowpass(noise(seconds, seed), 900) * np.exp(-tt * decay * 1.5)


def rumble(seconds, seed, cutoff, wobble=0.3, rate=0.7):
    """Stone or iron dragged: low noise that swells and falls unevenly."""
    tt = t(seconds)
    rng = np.random.default_rng(seed)
    x = lowpass(lowpass(noise(seconds, seed), cutoff), cutoff)
    shake = 1 + wobble * np.sin(2 * np.pi * rate * tt + rng.uniform(0, 6)) * np.sin(2 * np.pi * rate * 2.7 * tt)
    return x * shake


def ticks(seconds, every, seed, freqs, jitter=0.1, decay=60):
    """A ratchet or chain: struck iron again and again."""
    rng = np.random.default_rng(seed)
    out = np.zeros(len(t(seconds)))
    at = 0.0
    while at < seconds:
        k = clank(0.12, [fr * rng.uniform(0.95, 1.05) for fr in freqs], int(rng.integers(1 << 30)))
        k *= np.exp(-t(0.12) * decay) * rng.uniform(0.6, 1.0)
        i = int(at * RATE)
        out[i:i + len(k)] += k[:len(out) - i]
        at += every * rng.uniform(1 - jitter, 1 + jitter)
    return out


def splash(seconds, seed, low, high, decay):
    """Water thrown about: noise through a falling band with bubbles."""
    tt = t(seconds)
    x = highpass(lowpass(noise(seconds, seed), np.geomspace(high, low, len(tt))), 250) * np.exp(-tt * decay)
    return x + 0.3 * bubbles(seconds, seed + 1, 30, decay)


def bubbles(seconds, seed, rate, decay=0.0):
    """Little rising tones, as bubbles burst or slag pops."""
    rng = np.random.default_rng(seed)
    n = len(t(seconds))
    out = np.zeros(n)
    for _ in range(int(rate * seconds)):
        at = rng.uniform(0, seconds)
        d = rng.uniform(0.02, 0.07)
        f = rng.uniform(300, 1200)
        bt = t(d)
        b = np.sin(2 * np.pi * np.cumsum(f * (1 + 2.5 * bt / d)) / RATE) * np.exp(-bt / d * 4)
        i = int(at * RATE)
        out[i:i + len(b)] += b[:n - i] * np.exp(-at * decay) * rng.uniform(0.3, 1)
    return out


def seamless(x, fade=0.25):
    """Crossfades the tail into the head so the sound loops without a click."""
    n = int(fade * RATE)
    out = x[:-n].copy()
    ramp = np.linspace(0, 1, n)
    out[:n] = x[:n] * ramp + x[-n:] * (1 - ramp)
    return out


def chord(seconds, freqs, decay, seed):
    """Struck bronze bars: a soft chime."""
    tt = t(seconds)
    rng = np.random.default_rng(seed)
    out = np.zeros_like(tt)
    for i, f in enumerate(freqs):
        for ratio, amp in ((1, 1), (2.76, 0.25), (5.4, 0.08)):
            out += amp * np.sin(2 * np.pi * f * ratio * tt + rng.uniform(0, 6)) * np.exp(-tt * decay * ratio ** 0.5)
    return out / len(freqs)


def pain(seed, f0, vowel, seconds=0.3):
    tt = t(seconds)
    return voice(seconds, seed, f0, f0 * 0.7, vowel, 0.35, "uh") * envelope(len(tt), 0.01, 6)


def sounds():
    n = normalise
    # The stoker: grunts, gasps and death in a hoarse voice.
    for i, (f0, v, s) in enumerate(((150, "ah", 0.32), (165, "uh", 0.26), (140, "eh", 0.3),
                                    (175, "ah", 0.28), (155, "oh", 0.3), (185, "uh", 0.25))):
        yield "player/pain%d" % (i + 1), n(pain(300 + i, f0, v, s), 0.7)
    for i, (f0, f1, v, s) in enumerate(((170, 70, "ah", 1.0), (190, 90, "oh", 0.8), (150, 60, "uh", 1.0),
                                        (200, 80, "eh", 1.1), (160, 55, "ah", 1.2))):
        tt = t(s)
        cry = voice(s, 310 + i, f0, f1, v, 0.4, "uh") * envelope(len(tt), 0.02, 3.5, hold=0.15)
        yield "player/death%d" % (i + 1), n(lay((cry, 0), (thud(0.4, 90, 45, 10, 320 + i) * 0.4, s * 0.7)), 0.75)
    gore = lowpass(noise(0.9, 330), 1500) * envelope(len(t(0.9)), 0.003, 5)
    yield "player/udeath", n(lay((gore, 0), (crackle(1.0, 331, 0.03, 4), 0), (thud(0.5, 110, 40, 8, 332), 0),
                                 (steam(0.9, 333, 600, 4000, 0.01, 5) * 0.5, 0.05)))
    yield "player/gib", n(lay((lowpass(noise(0.5, 334), 1100) * envelope(len(t(0.5)), 0.002, 8), 0),
                              (lowpass(noise(0.4, 335), 900) * envelope(len(t(0.4)), 0.002, 9) * 0.7, 0.25),
                              (crackle(1.2, 336, 0.02, 3), 0.1)))
    yield "player/tornoff2", n(lay((lowpass(noise(0.4, 337), 1400) * envelope(len(t(0.4)), 0.005, 8), 0),
                                   (thud(0.3, 120, 60, 14, 338) * 0.5, 0.15)))
    yield "player/teledth1", n(lay((steam(0.9, 339, 400, 9000, 0.002, 4), 0), (thud(0.6, 140, 40, 7, 340), 0),
                                   (lowpass(noise(0.6, 341), 1200) * envelope(len(t(0.6)), 0.002, 6), 0.02)))
    yield "player/plyrjmp8", n(voice(0.22, 342, 170, 210, "hh", 0.6, "uh") * envelope(len(t(0.22)), 0.01, 7), 0.45)
    # Boots on iron grating: a soft step, and a hard landing with a grunt.
    yield "player/land", n(lay((thud(0.25, 120, 70, 22, 343, 0.6), 0), (clank(0.2, [520, 1270], 344) * 0.15, 0)), 0.5)
    yield "player/land2", n(lay((thud(0.4, 100, 50, 14, 345, 0.6), 0), (clank(0.3, [430, 1010], 346) * 0.25, 0),
                                (pain(347, 150, "uh", 0.22) * 0.6, 0.03)), 0.7)
    yield "player/axhit1", n(lay((lowpass(noise(0.3, 348), 1300) * envelope(len(t(0.3)), 0.002, 12), 0),
                                 (thud(0.25, 160, 80, 20, 349), 0)), 0.8)
    yield "player/axhit2", n(lay((clank(0.4, [1150, 2630, 4100], 350), 0),
                                 (highpass(noise(0.05, 351), 3000) * envelope(len(t(0.05)), 0.0, 20), 0)), 0.7)
    # Slag and scald: a hiss on skin and a cry through teeth.
    for i in (1, 2):
        yield "player/lburn%d" % i, n(lay((steam(0.6, 352 + i, 1500, 8000, 0.002, 5), 0),
                                         (pain(354 + i, 160 + 20 * i, "eh", 0.3) * 0.7, 0.03)), 0.7)
    yield "player/slimbrn2", n(lay((steam(0.8, 357, 800, 4000, 0.01, 4), 0), (bubbles(0.8, 358, 25, 2) * 0.5, 0),
                                   (pain(359, 145, "uh", 0.3) * 0.6, 0.05)), 0.7)
    yield "player/inlava", n(lay((steam(1.1, 360, 400, 7000, 0.003, 2.5), 0), (bubbles(1.1, 361, 40, 2), 0),
                                 (thud(0.4, 80, 40, 9, 362) * 0.6, 0)), 0.8)
    # Water: in, out, swimming, and running out of breath.
    yield "player/inh2o", n(lay((splash(0.9, 363, 300, 3500, 4), 0), (thud(0.3, 90, 50, 14, 364) * 0.5, 0)), 0.7)
    yield "player/h2ojump", n(splash(0.7, 365, 400, 5000, 5), 0.7)
    yield "misc/h2ohit1", n(lay((splash(0.9, 366, 250, 5000, 4), 0), (thud(0.35, 85, 45, 12, 367) * 0.6, 0)), 0.8)
    yield "misc/outwater", n(splash(0.7, 368, 600, 4000, 6) + 0.4 * bubbles(0.7, 369, 15, 6), 0.55)
    for i in (1, 2):
        tt = t(0.5)
        stroke = highpass(lowpass(noise(0.5, 370 + i), 1800), 200) * np.sin(np.pi * tt / 0.5) ** 2
        yield "misc/water%d" % i, n(stroke + 0.3 * bubbles(0.5, 372 + i, 12), 0.35)
    yield "player/gasp1", n(voice(0.6, 374, 120, 110, "hh", 0.9, "ah") * envelope(len(t(0.6)), 0.15, 4), 0.5)
    yield "player/gasp2", n(lay((voice(0.5, 375, 125, 115, "hh", 0.9, "ah") * envelope(len(t(0.5)), 0.12, 5), 0),
                                (voice(0.5, 376, 120, 110, "hh", 0.9, "oh") * envelope(len(t(0.5)), 0.12, 5) * 0.7, 0.6)), 0.5)
    for i, s in ((1, 0.7), (2, 0.35)):
        choke = voice(s, 377 + i, 140, 100, "uh", 0.5, "oo") * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 9 * t(s))))
        yield "player/drown%d" % i, n(lay((choke * envelope(len(t(s)), 0.01, 4), 0), (bubbles(s, 379 + i, 40), 0)), 0.6)
    yield "player/h2odeath", n(lay((voice(1.2, 381, 150, 60, "oo", 0.5) * envelope(len(t(1.2)), 0.02, 3), 0),
                                   (bubbles(3.0, 382, 30, 1.0), 0)), 0.65)

    # Doors. Iron on rollers, hydraulic rams, dragged stone, pneumatic hatches.
    rollers = rumble(2.6, 400, 220, 0.4) + 0.35 * ticks(2.6, 0.31, 401, [380, 870], 0.15, 40)
    yield "doors/doormv1", n(seamless(rollers), 0.45)
    yield "doors/drclos4", n(lay((thud(0.9, 75, 38, 5, 402), 0), (clank(1.2, [210, 497, 1130], 403) * 0.6, 0),
                                 (rumble(0.4, 404, 300) * envelope(len(t(0.4)), 0.0, 6) * 0.5, 0)), 0.8)
    tt = t(1.6)
    ram = steam(1.6, 405, 600, 1200, 0.1, 0.1, 1.3) * 0.5 + np.sin(2 * np.pi * 62 * tt) * 0.3 + rumble(1.6, 406, 160) * 0.8
    yield "doors/hydro1", n(seamless(ram, 0.3), 0.45)
    yield "doors/hydro2", n(lay((steam(0.8, 407, 400, 5000, 0.002, 5), 0), (thud(0.5, 80, 45, 9, 408), 0),
                                (clank(0.6, [300, 720], 409) * 0.3, 0)), 0.75)
    yield "doors/stndr1", n(seamless(rumble(3.4, 410, 140, 0.6, 0.45) + 0.25 * crackle(3.4, 411, 0.004, 0), 0.4), 0.5)
    yield "doors/stndr2", n(lay((thud(1.2, 60, 32, 4, 412, 0.5), 0), (crackle(1.4, 413, 0.02, 3) * 0.4, 0.05)), 0.85)
    yield "doors/ddoor1", n(seamless(rumble(1.0, 414, 300, 0.3) + 0.3 * ticks(1.0, 0.17, 415, [640, 1500], 0.1), 0.15), 0.4)
    yield "doors/ddoor2", n(lay((thud(0.4, 110, 60, 12, 416), 0), (clank(0.4, [520, 1240], 417) * 0.4, 0)), 0.7)
    yield "doors/airdoor1", n(seamless(steam(3.8, 418, 900, 2200, 0.2, 0.1, 3.4) * 0.6 + rumble(3.8, 419, 200), 0.35), 0.4)
    yield "doors/airdoor2", n(lay((steam(1.4, 420, 300, 6000, 0.003, 3), 0), (thud(0.5, 90, 50, 10, 421), 0.05),
                                  (clank(0.5, [460, 1090], 422) * 0.3, 0.05)), 0.75)
    yield "doors/basesec1", n(seamless(rumble(1.6, 423, 180, 0.5) + 0.2 * crackle(1.6, 424, 0.006, 0) +
                                       0.25 * ticks(1.6, 0.4, 425, [300, 700], 0.3), 0.25), 0.5)
    yield "doors/basesec2", n(lay((thud(0.8, 70, 36, 6, 426), 0), (crackle(0.8, 427, 0.02, 4) * 0.4, 0)), 0.8)
    yield "doors/winch2", n(seamless(ticks(1.4, 0.09, 428, [900, 2100], 0.05, 70) + rumble(1.4, 429, 250) * 0.6, 0.12), 0.45)
    yield "doors/latch2", n(lay((clank(0.5, [700, 1640], 430), 0), (clank(0.4, [520, 1250], 431) * 0.7, 0.12)), 0.7)
    # Locked: the handle rattles. Unlocked: a key turns and the bolt draws.
    for name, seed, freqs in (("base", 432, [820, 1900]), ("med", 435, [640, 1520]), ("rune", 438, [520, 1310])):
        rattle = ticks(0.5, 0.06, seed, freqs, 0.3, 50)
        yield "doors/%stry" % name, n(lay((rattle, 0), (thud(0.2, 140, 90, 25, seed + 1) * 0.4, 0)), 0.6)
        turn = lay((ticks(0.3, 0.05, seed + 2, [f * 1.5 for f in freqs], 0.2, 80) * 0.6, 0),
                   (clank(0.6, freqs, seed + 3), 0.3), (thud(0.3, 120, 70, 16, seed + 4) * 0.4, 0.3))
        yield "doors/%suse" % name, n(turn, 0.7)

    # Lifts and carts.
    tt = t(1.2)
    yield "plats/plat1", n(seamless(rumble(1.5, 450, 200, 0.2) + 0.3 * ticks(1.5, 0.25, 451, [440, 990], 0.05)
                                    + 0.15 * np.sin(2 * np.pi * 55 * t(1.5)), 0.2), 0.45)
    yield "plats/plat2", n(lay((thud(0.7, 85, 42, 7, 452), 0), (clank(0.7, [330, 800], 453) * 0.4, 0)), 0.75)
    yield "plats/medplat1", n(seamless(ticks(0.8, 0.08, 454, [760, 1800], 0.05, 70) + rumble(0.8, 455, 260) * 0.5, 0.1), 0.45)
    yield "plats/medplat2", n(lay((clank(0.8, [260, 610, 1400], 456), 0), (thud(0.5, 95, 50, 10, 457) * 0.6, 0)), 0.75)
    cart = rumble(1.6, 458, 180, 0.2) + 0.5 * ticks(1.6, 0.4, 459, [300, 710], 0.02, 30)
    yield "plats/train1", n(seamless(cart, 0.2), 0.45)
    yield "plats/train2", n(lay((thud(0.8, 80, 40, 6, 460), 0), (clank(0.9, [240, 560, 1300], 461) * 0.5, 0),
                                (steam(0.6, 462, 500, 2500, 0.01, 6) * 0.3, 0.1)), 0.75)

    # Levers and buttons: a heavy throw, a clack, a valve.
    yield "buttons/switch02", n(lay((clank(0.6, [420, 980], 470), 0), (thud(0.3, 130, 70, 16, 471) * 0.5, 0.0),
                                    (ticks(0.3, 0.07, 472, [1300, 2900], 0.1) * 0.3, 0.1)), 0.7)
    yield "buttons/switch04", n(lay((clank(0.4, [880, 2050], 473), 0), (clank(0.3, [600, 1420], 474) * 0.6, 0.09)), 0.6)
    yield "buttons/switch21", n(lay((ticks(0.35, 0.05, 475, [1100, 2500], 0.1, 70), 0),
                                    (clank(0.5, [500, 1180], 476), 0.25)), 0.65)
    yield "buttons/airbut1", n(lay((clank(0.3, [700, 1650], 477) * 0.6, 0), (steam(1.1, 478, 400, 5000, 0.01, 3), 0.05)), 0.65)

    # Pickups.
    yield "items/health1", n(lay((steam(0.25, 480, 2000, 6000, 0.002, 12) * 0.5, 0),
                                 (chord(0.8, [523, 784], 4, 481), 0.02)), 0.6)
    yield "items/r_item1", n(chord(0.6, [659, 988], 5, 482), 0.55)
    yield "items/r_item2", n(lay((chord(1.2, [392, 587, 784], 2.2, 483), 0), (bell(1.2, 196, 484, 2.5) * 0.4, 0),
                                 (steam(0.6, 485, 800, 5000, 0.1, 4) * 0.25, 0)), 0.7)
    yield "items/armor1", n(lay((clank(0.7, [240, 610, 1330], 486), 0), (clank(0.5, [330, 790], 487) * 0.6, 0.11),
                                (thud(0.3, 110, 60, 14, 488) * 0.4, 0)), 0.75)
    yield "items/itembk2", n(lay((steam(0.9, 489, 400, 4000, 0.3, 4), 0), (crackle(0.9, 490, 0.02, 3) * 0.5, 0.1),
                                 (chord(0.5, [880], 8, 491) * 0.2, 0.3)), 0.5)
    yield "weapons/lock4", n(lay((clank(0.25, [1200, 2700], 492), 0), (clank(0.2, [900, 2100], 493) * 0.7, 0.07)), 0.6)
    yield "weapons/pkup", n(lay((clank(0.4, [520, 1240], 494), 0), (ticks(0.25, 0.04, 495, [1600, 3300], 0.1, 90) * 0.4, 0.12),
                                (clank(0.4, [380, 900], 496) * 0.8, 0.25)), 0.7)
    for name, seed, notes in (("basekey", 497, [784, 1175]), ("medkey", 499, [659, 988, 1319]), ("runekey", 501, [523, 784, 1047])):
        yield "misc/" + name, n(lay((chord(1.4, notes, 2.5, seed), 0), (clank(0.3, [notes[0] * 1.5], seed + 1) * 0.3, 0)), 0.6)

    # The world talking: secrets, messages, powerups ending, teleports.
    yield "misc/secret", n(lay((bell(2.4, 330, 503, 1.2) * 0.6, 0), (chord(2.0, [494, 740, 988], 1.6, 504), 0.15)), 0.65)
    yield "misc/trigger1", n(lay((bell(1.4, 440, 505, 2.2) * 0.6, 0), (chord(1.2, [660], 3, 506) * 0.4, 0.05)), 0.55)
    yield "misc/talk", n(lay((clank(0.25, [1500, 3100], 507), 0), (chord(0.35, [1175], 9, 508) * 0.6, 0)), 0.45)
    tt = t(2.0)
    yield "misc/power", n(bell(2.0, 110, 509, 1.0) * 0.5 + steam(2.0, 510, 300, 3000, 0.3, 2) * 0.6, 0.6)
    for i in range(5):
        s = 1.2 + 0.15 * i
        tt = t(s)
        whoosh = steam(s, 511 + i, 300 + 80 * i, 7000 - 500 * i, 0.15, 3)
        hum = np.sin(2 * np.pi * np.cumsum(np.geomspace(90 + 10 * i, 260 + 30 * i, len(tt))) / RATE) * envelope(len(tt), 0.2, 4)
        yield "misc/r_tele%d" % (i + 1), n(whoosh + 0.4 * hum + 0.3 * crackle(s, 520 + i, 0.02, 2), 0.65)
    # The menus: a soft tick, a heavier click to choose, a step back.
    yield "misc/menu1", n(clank(0.12, [2200, 4300], 525) * envelope(len(t(0.12)), 0.0, 9), 0.35)
    yield "misc/menu2", n(lay((clank(0.25, [900, 2100], 526), 0), (thud(0.15, 200, 120, 30, 527) * 0.5, 0)), 0.5)
    yield "misc/menu3", n(clank(0.18, [1500, 3400], 528) * envelope(len(t(0.18)), 0.0, 7), 0.35)
    yield "misc/null", np.zeros(int(0.05 * RATE))

    # Weapons. The Pick, the Scattergun, the Steam Gun, the Spitter, the Bolt
    # Caster, the Crucible, the Mortar and the Toll.
    yield "weapons/ax1", n(steam(0.25, 530, 600, 3000, 0.04, 9), 0.4)
    tt = t(0.9)
    boom = lowpass(noise(0.9, 531), np.geomspace(5000, 300, len(tt))) * envelope(len(tt), 0.001, 7)
    yield "weapons/guncock", n(lay((boom, 0), (thud(0.6, 120, 45, 9, 532), 0), (clank(0.6, [310, 760], 533) * 0.25, 0.02),
                                   (steam(0.5, 534, 800, 4000, 0.02, 6) * 0.25, 0.08)), 0.85)
    boom2 = lowpass(noise(1.0, 535), np.geomspace(6000, 250, len(t(1.0)))) * envelope(len(t(1.0)), 0.001, 5)
    yield "weapons/shotgn2", n(lay((boom2, 0), (thud(0.8, 100, 38, 7, 536), 0), (boom * 0.6, 0.03),
                                   (steam(0.9, 537, 500, 6000, 0.03, 4) * 0.5, 0.1)), 0.9)
    spit = highpass(lowpass(noise(0.18, 538), 4000), 500) * envelope(len(t(0.18)), 0.001, 14)
    yield "weapons/rocket1i", n(lay((spit, 0), (thud(0.12, 220, 110, 30, 539) * 0.6, 0), (clank(0.12, [1700], 540) * 0.2, 0)), 0.6)
    yield "weapons/spike2", n(lay((thud(0.3, 160, 70, 18, 541), 0), (clank(0.4, [880, 2030, 3300], 542) * 0.6, 0),
                                  (steam(0.3, 543, 1000, 6000, 0.002, 10) * 0.5, 0)), 0.7)
    yield "weapons/grenade", n(lay((thud(0.5, 140, 55, 10, 544), 0), (lowpass(noise(0.5, 545), 900) * envelope(len(t(0.5)), 0.003, 9), 0),
                                   (bubbles(0.5, 546, 30, 5) * 0.3, 0.03)), 0.75)
    whoomp = lay((thud(0.8, 90, 35, 6, 547), 0), (steam(1.2, 548, 300, 6000, 0.01, 3), 0.02))
    yield "weapons/sgun1", n(lay((whoomp, 0), (clank(0.8, [190, 450], 549) * 0.3, 0)), 0.85)
    yield "weapons/bounce", n(lay((clank(0.3, [600, 1420], 550), 0), (thud(0.2, 160, 90, 25, 551) * 0.5, 0)), 0.55)
    tt = t(1.3)
    yield "weapons/lstart", n(lay((bell(1.3, 220, 552, 1.2), 0), (steam(1.3, 553, 2000, 8000, 0.05, 3) * 0.3, 0.05)), 0.7)
    tt = t(0.6)
    drone = sum(np.sin(2 * np.pi * f * tt) * a for f, a in ((110, 1), (220, 0.5), (331, 0.35), (442, 0.2)))
    yield "weapons/lhit", n(drone * (0.7 + 0.3 * np.sin(2 * np.pi * 17 * tt)) + 0.5 * crackle(0.6, 554, 0.06, 0), 0.55)
    tt = t(1.6)
    blast = lowpass(noise(1.6, 555), np.geomspace(6000, 150, len(tt))) * envelope(len(tt), 0.002, 4)
    yield "weapons/r_exp3", n(lay((blast, 0), (thud(1.2, 70, 28, 4, 556), 0), (crackle(1.6, 557, 0.04, 2.5) * 0.8, 0.05),
                                  (steam(1.2, 558, 300, 4000, 0.05, 3) * 0.3, 0.1)), 0.9)
    # Creatures' bolts hitting a wall (the engine plays these itself).
    yield "wizard/hit", n(lay((steam(0.4, 562, 1500, 7000, 0.002, 9), 0), (crackle(0.4, 563, 0.03, 8) * 0.6, 0)), 0.55)
    yield "hknight/hit", n(lay((steam(0.5, 564, 800, 6000, 0.002, 7), 0), (thud(0.2, 180, 90, 25, 565) * 0.5, 0),
                               (crackle(0.5, 566, 0.03, 6) * 0.6, 0)), 0.6)
    yield "weapons/tink1", n(clank(0.12, [2900, 5100], 559) * envelope(len(t(0.12)), 0.0, 12), 0.4)
    for i in range(3):
        s = 0.45 + 0.25 * i
        tt = t(s)
        f = np.geomspace(3200 - 400 * i, 1700 - 200 * i, len(tt))
        whine = np.sin(2 * np.pi * np.cumsum(f) / RATE) * envelope(len(tt), 0.005, 5)
        yield "weapons/ric%d" % (i + 1), n(lay((clank(0.15, [2400 + 300 * i], 560 + i) * 0.6, 0), (whine * 0.5, 0.02)), 0.5)

    # The beds the maps lay under everything.
    tt = t(4.0)
    yield "ambience/buzz1", n(seamless(steam(4.3, 570, 1800, 2600, 0.01, 0.01, 4.2) * 0.6 +
                                       0.25 * np.sin(2 * np.pi * 120 * t(4.3)) * (1 + 0.2 * np.sin(2 * np.pi * 0.5 * t(4.3))), 0.3), 0.4)
    pist = np.zeros(len(t(4.8)))
    for k in range(8):
        h = thud(0.5, 70, 45, 9, 571 + k, 0.5) + 0.4 * steam(0.5, 580 + k, 700, 3000, 0.05, 6)
        i = int(k * 0.6 * RATE)
        pist[i:i + len(h)] += h[:len(pist) - i]
    yield "ambience/comp1", n(seamless(pist + 0.3 * rumble(4.8, 590, 150), 0.3), 0.5)
    drips = np.zeros(len(t(8.4)))
    rng = np.random.default_rng(591)
    for _ in range(14):
        at = rng.uniform(0, 8.0)
        d = t(0.6)
        f = rng.uniform(700, 1500)
        p = np.sin(2 * np.pi * np.cumsum(f * (1 + 1.5 * np.exp(-d * 40))) / RATE) * np.exp(-d * 14)
        echo = lay((p, 0), (p * 0.35, 0.13), (p * 0.15, 0.29))
        i = int(at * RATE)
        drips[i:i + len(echo)] += echo[:len(drips) - i] * rng.uniform(0.4, 1)
    yield "ambience/drip1", n(seamless(drips + 0.05 * rumble(8.4, 592, 120), 0.4), 0.45)
    tt = t(2.0)
    yield "ambience/drone6", n(seamless(np.sin(2 * np.pi * 55 * tt) + 0.5 * np.sin(2 * np.pi * 82.7 * tt) +
                                        0.3 * rumble(2.0, 593, 200), 0.2), 0.4)
    roar = rumble(4.6, 594, 350, 0.3, 0.3) + 0.6 * crackle(4.6, 595, 0.01, 0) + 0.2 * steam(4.6, 596, 600, 900, 0.01, 0.01, 4.5)
    yield "ambience/fire1", n(seamless(roar, 0.35), 0.45)
    tt = t(4.3)
    yield "ambience/fl_hum1", n(seamless(np.sin(2 * np.pi * 98 * tt) * 0.6 + np.sin(2 * np.pi * 196.4 * tt) * 0.3 +
                                         0.15 * steam(4.3, 597, 2000, 2500, 0.01, 0.01, 4.2), 0.3), 0.35)
    tt = t(6.3)
    yield "ambience/hum1", n(seamless((np.sin(2 * np.pi * 73.4 * tt) + 0.4 * np.sin(2 * np.pi * 110.2 * tt)) *
                                      (0.8 + 0.2 * np.sin(2 * np.pi * 0.33 * tt)) + 0.2 * rumble(6.3, 598, 300), 0.3), 0.4)
    yield "ambience/suck1", n(seamless(steam(4.8, 599, 250, 1200, 0.01, 0.01, 4.7) * (1 + 0.4 * np.sin(2 * np.pi * 0.5 * t(4.8)))
                                       + rumble(4.8, 600, 120), 0.3), 0.45)
    for i, s in ((1, 6.4), (2, 8.4)):
        slag = bubbles(s, 601 + i, 9 + 4 * i) * 0.6 + rumble(s, 603 + i, 110, 0.4, 0.2) + 0.3 * crackle(s, 605 + i, 0.003, 0)
        yield "ambience/swamp%d" % i, n(seamless(slag, 0.4), 0.45)
    tt = t(6.0)
    yield "ambience/thunder1", n(lay((rumble(6.0, 607, 90, 0.8, 0.25) * envelope(len(tt), 0.4, 3), 0),
                                     (thud(2.0, 45, 25, 2, 608, 0.6), 0.5), (crackle(4.0, 609, 0.01, 1.5) * 0.4, 0.4)), 0.7)
    flow = highpass(lowpass(noise(6.4, 610), 1400), 200) * (0.8 + 0.2 * np.sin(2 * np.pi * 0.4 * t(6.4))) + 0.3 * bubbles(6.4, 611, 20)
    yield "ambience/water1", n(seamless(flow, 0.4), 0.35)
    tt = t(16.5)
    gust = lowpass(noise(16.5, 612), 500 + 400 * (1 + np.sin(2 * np.pi * tt / 16.5 * 3) * np.sin(2 * np.pi * tt / 16.5 * 5)))
    yield "ambience/wind2", n(seamless(highpass(gust, 80), 0.5), 0.4)
    yield "ambience/windfly", n(steam(2.0, 613, 300, 2500, 0.3, 2.5, 0.6), 0.5)
