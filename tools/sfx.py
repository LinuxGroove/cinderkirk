#!/usr/bin/env python3
"""Synthesize Cinderkirk's own sounds from fixed seeds, so the build makes the
same files every time.

    tools/sfx.py OUT_DIR        writes OUT_DIR/cinder/*.wav

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


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = os.path.join(sys.argv[1], "cinder")
    os.makedirs(out, exist_ok=True)
    for name, x in sounds():
        write(os.path.join(out, name + ".wav"), x, loop=name.endswith("_loop"))
    print(f"sounds in {out}")


if __name__ == "__main__":
    main()
