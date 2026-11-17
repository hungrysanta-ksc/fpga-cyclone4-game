"""Independently decode the linked ARM's SNES map, OAM and planar tiles."""
import json
import struct
import sys
from pathlib import Path

def words(b):
    return struct.unpack("<%dH"%(len(b)//2),b)

def compare(folder, capture, rom, f):
    d=folder/str(f)
    def read(key):
        return (d/(key+".bin")).read_bytes()
    gfx={}
    for _,h in json.loads((d/"plans.json").read_text()):
        q=bytes.fromhex(h)
        _,slot,tag,kind,mask=struct.unpack_from("<HHHBB",q)
        alt=words(q[24:])
        rows=[]
        for y in range(8):
            t=alt[y] if alt[y]!=65535 else tag
            rows.append((rom[t*16+q[8+y*2]],rom[tag*16+8+q[9+y*2]]) if mask>>y&1 and kind!=2 else (0,0))
        gfx[kind==1,slot]=rows
    def pix(obj,slot,x,y):
        a,b=gfx[obj,slot][y]
        return (a>>(7-x)&1)+2*(b>>(7-x)&1)
    geo=read("geometry")
    raster=struct.unpack_from("<224Q",geo,3872)
    mem=words(read("map"))
    cx,cy=words(read("hofs")),words(read("vofs"))
    cg=words(read("cgram"))
    obj=read("oam")
    patch=read("patch")
    ref=(capture/f"frame-{f}.rgb").read_bytes()
    result=[]
    for y,r in enumerate(raster):
        raw=r>>49&1
        active=[]
        for i in range(128):
            x,top,slot,at=obj[i*4:i*4+4]
            ry=(y-top)&255
            if ry<8:
                active.append((x,slot,at,7-ry if at&128 else ry))
        bad=[]
        for x in range(256):
            if raw:
                p=x//8*64+(r>>50&7)*2
                idx=sum(((patch[p+k//2*16+k%2]>>(7-x%8))&1)<<k for k in range(8))
            else:
                sx=(x+cx[y])%512
                sy=(y+1+cy[y])%256
                w=mem[sx//256*1024+sy//8*32+sx%256//8]
                bg=pix(False,w&1023,sx%8,sy%8)
                idx=4*(w>>10&7)+bg if bg else 0
                for ox,slot,at,ry in active:
                    if ox<=x<ox+8:
                        dx=x-ox
                        c=pix(True,slot,7-dx if at&64 else dx,ry)
                        if c:
                            if at&16 or not bg:idx=128+(at>>1&7)*16+c
                            break
            pos=((y+8)*256+x)*3
            rr,gg,bb=ref[pos:pos+3]
            if cg[idx]!=(rr>>3|(gg>>3)<<5|(bb>>3)<<10):
                bad.append(x)
        result.append(len(bad))
    return dict(frame=f,raw=[y for y,r in enumerate(raster) if r>>49&1],errors=sum(result),seam=result[183:186],below=sum(result[185:]),rows=result)

if __name__=="__main__":
    plans,capture,cart,out=map(Path,sys.argv[1:])
    cart=cart.read_bytes()
    chr=cart[16+16384*cart[4]:]
    rows=[compare(plans,capture,chr,f) for f in sorted(int(d.name) for d in plans.iterdir() if d.is_dir())]
    out.write_text(json.dumps(rows))
    for r in rows:
        print({k:v for k,v in r.items() if k!="rows"})
        assert r["errors"]==0, r["frame"]
