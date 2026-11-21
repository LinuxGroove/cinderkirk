#!/usr/bin/env python3
"""Pack a folder into a Quake PAK file.

    tools/pak.py OUT.pak DIR

Every file under DIR goes in under its path relative to DIR (56 characters
at most), in sorted order so the same input always makes the same pak.
"""

import os
import struct
import sys


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    out, root = sys.argv[1], sys.argv[2]
    files = []
    for d, _, names in os.walk(root):
        for n in names:
            full = os.path.join(d, n)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if len(rel) > 55:
                sys.exit(f"{rel}: pak paths are 55 characters at most")
            files.append((rel, full))
    files.sort()
    body = bytearray()
    entries = []
    for rel, full in files:
        data = open(full, "rb").read()
        entries.append((rel, 12 + len(body), len(data)))
        body += data
    table = b"".join(struct.pack("<56sII", r.encode(), at, size) for r, at, size in entries)
    with open(out, "wb") as f:
        f.write(b"PACK" + struct.pack("<II", 12 + len(body), len(table)))
        f.write(body)
        f.write(table)
    print(f"{out}: {len(files)} files, {(12 + len(body) + len(table)) // 1024} KiB")


if __name__ == "__main__":
    main()
