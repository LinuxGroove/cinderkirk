#!/usr/bin/env python3
# Copyright (C) The LinuxGroove team
# SPDX-License-Identifier: GPL-2.0-or-later
"""How bright each level's player start is, from its lightmaps: the mean
light on every face within 256 units of info_player_start, on the same
0..255 scale as tools/lightstat.py.

    tools/startlight.py [map ...]      # default: every built level but the arenas

Tune a level's Level(start_light=N) until its start reads about 80, close
to the rest of the level: under 60 the first view is a dark corner, over
100 pale walls blow out to white (about 106 on screen with an NVIDIA card,
where 80 here is about 65 there). MAPS=dir reads another build's levels.
"""
import glob
import math
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lightstat as ls  # noqa: E402

ROOT = os.environ.get("MAPS", ls.ROOT)
def start(name):
    bsp=open(os.path.join(ROOT,name+'.bsp'),'rb').read()
    L=ls.lumps(bsp); off,size=L[0]
    ents=bsp[off:off+size].decode('latin1')
    for blk in re.findall(r'\{[^{}]*\}',ents):
        if '"info_player_start"' in blk:
            return tuple(map(float,re.search(r'"origin" "([^"]+)"',blk).group(1).split()))
def stat(name,R=256):
    sx,sy,sz=start(name)
    bsp=open(os.path.join(ROOT,name+'.bsp'),'rb').read()
    lit=open(os.path.join(ROOT,name+'.lit'),'rb').read()[8:]
    L=ls.lumps(bsp)
    def rows(i,fmt):
        off,size=L[i]; n=struct.calcsize(fmt)
        return [struct.unpack_from(fmt,bsp,off+k*n) for k in range(size//n)]
    verts=rows(3,"<3f"); texinfo=rows(6,"<8f2i"); faces=rows(7,"<hhihh4Bi")
    edges=rows(12,"<2H"); surf=[s[0] for s in rows(13,"<i")]; world=rows(14,"<9f7i")[0]
    tot=[];
    for f in faces[world[-2]:world[-2]+world[-1]]:
        plane,side,fe,ne,ti,s0,s1,s2,s3,ofs=f
        if ofs<0 or s0==255: continue
        pts=[verts[edges[e][0]] if e>=0 else verts[edges[-e][1]] for e in (surf[fe+k] for k in range(ne))]
        c=[sum(p[i] for p in pts)/len(pts) for i in range(3)]
        if (c[0]-sx)**2+(c[1]-sy)**2+(c[2]-sz)**2>R*R: continue
        t=texinfo[ti]; ext=[]
        for a in (0,4):
            v=[p[0]*t[a]+p[1]*t[a+1]+p[2]*t[a+2]+t[a+3] for p in pts]
            ext.append(math.ceil(max(v)/16)-math.floor(min(v)/16)+1)
        n=ext[0]*ext[1]
        tot+= [(lit[3*(ofs+k)]*3+lit[3*(ofs+k)+1]*6+lit[3*(ofs+k)+2])/10 for k in range(n) if 3*(ofs+k)+2<len(lit)]
    return sum(tot)/len(tot)
names=sys.argv[1:] or sorted(os.path.basename(p)[:-4] for p in glob.glob(ROOT+'/*.lit') if 'pit' not in p)
vals={}
for n in names:
    try: vals[n]=stat(n); print(f"{n:12s} {vals[n]:6.1f}")
    except Exception as e: print(n,'err',e)
print('mean',sum(vals.values())/len(vals))
