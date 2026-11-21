"""Writes MD3 models: the vertex-animated format vkQuake loads in place of an
.mdl, with one surface per skin and every frame stored whole.

    write(path, surfaces, frame_names)

surfaces is a list of dicts: name (the skin's name: the engine loads
progs/<name>.png and <name>_luma.png), tris (n x 3 vertex indices), st (v x 2
texture coordinates, 0 at the image's top), and frames (f x v x 3 positions
in Quake units, and f x v x 3 unit normals as "normals").

Copyright (C) The LinuxGroove team. GPL-2.0-or-later.
"""
import struct

import numpy as np

SCALE = 64.0


def _latlong(n):
    """Unit normals to the two bytes MD3 keeps: latitude from +Z, longitude round it."""
    n = n / np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-9)
    lat = np.arccos(np.clip(n[..., 2], -1, 1)) * 255 / (2 * np.pi)
    lng = np.arctan2(n[..., 1], n[..., 0]) * 255 / (2 * np.pi)
    lat = np.round(lat).astype(np.int64) & 255
    lng = np.round(lng).astype(np.int64) & 255
    return lat.astype(np.uint8), lng.astype(np.uint8)


def _name(s, n):
    b = s.encode("ascii")[: n - 1]
    return b + b"\0" * (n - len(b))


def _surface(s, nframes):
    tris = np.asarray(s["tris"], dtype="<i4")
    st = np.asarray(s["st"], dtype="<f4")
    pos = np.asarray(s["frames"], dtype=np.float64)
    nrm = np.asarray(s["normals"], dtype=np.float64)
    nv = st.shape[0]
    assert pos.shape == (nframes, nv, 3), pos.shape
    xyz = np.clip(np.round(pos * SCALE), -32768, 32767).astype("<i2")
    lat, lng = _latlong(nrm)
    verts = np.zeros((nframes, nv), dtype=[("xyz", "<i2", 3), ("lat", "u1"), ("lng", "u1")])
    verts["xyz"], verts["lat"], verts["lng"] = xyz, lat, lng
    head = 4 + 64 + 4 * 10
    shaders = _name(s["name"], 64) + struct.pack("<i", 0)
    o_tris = head
    o_shaders = o_tris + tris.nbytes
    o_st = o_shaders + len(shaders)
    o_xyz = o_st + st.nbytes
    o_end = o_xyz + verts.nbytes
    out = b"IDP3" + _name(s["name"], 64) + struct.pack(
        "<10i", 0, nframes, 1, nv, len(tris), o_tris, o_shaders, o_st, o_xyz, o_end)
    return out + tris.tobytes() + shaders + st.tobytes() + verts.tobytes()


def write(path, surfaces, frame_names, flags=0):
    nframes = len(frame_names)
    frames = b""
    for f, fname in enumerate(frame_names):
        allp = np.concatenate([np.asarray(s["frames"])[f] for s in surfaces])
        lo, hi = allp.min(axis=0), allp.max(axis=0)
        radius = float(np.linalg.norm(allp, axis=1).max())
        frames += struct.pack("<10f", *lo, *hi, 0, 0, 0, radius) + _name(fname, 16)
    surfs = b"".join(_surface(s, nframes) for s in surfaces)
    head = 4 + 4 + 64 + 4 * 9
    o_frames = head
    o_tags = o_frames + len(frames)
    o_surfs = o_tags
    o_end = o_surfs + len(surfs)
    data = b"IDP3" + struct.pack("<i", 15) + _name("cinderkirk", 64) + struct.pack(
        "<9i", flags, nframes, 0, len(surfaces), 0, o_frames, o_tags, o_surfs, o_end) + frames + surfs
    with open(path, "wb") as fh:
        fh.write(data)
    return len(data)
