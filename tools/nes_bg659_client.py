"""Link the direct-job consumer into the verified 637 client."""
import argparse,json,struct
from pathlib import Path
from unittest.mock import patch
from nes_head637 import head_map
import nes_rom636


def job_code(origin):
    c=bytearray();labels={};jumps=[]
    def e(*v):c.extend(v)
    def lab(k):labels[k]=origin+len(c)
    def jump(k):e(0x4c,0,0);jumps.append((len(c)-2,k))
    def cond(op,k):e(op^0x20,3);jump(k)
    def ab(op,addr):e(op,addr&255,addr>>8)
    def ext(op,addr):e(op,addr&255,addr>>8&255,addr>>16)
    def src(at):ext(0xbf,0x7f0000+at)
    e(0x08,0xda,0x5a) # entry M=8, X/Y=16 at each selected $420b write
    ab(0xad,0x4304);e(0xc9,0x7f);cond(0xd0,"plain")
    ab(0xad,0x4301);e(0xc9,0x18);cond(0xd0,"plain")
    ab(0xad,0x4303);e(0x29,0x40);cond(0xd0,"plain") # BG staging quadrants
    ext(0xaf,0x540000);cond(0xf0,"plain")
    # Preserve direct-page temporary, also on a successful tail return.
    e(0xa5,0xe2,0x48,0xc2,0x20,0xa5,0xe0,0x48)
    ab(0xad,0x4305);e(0x4a,0x4a,0x4a,0x4a,0xa8);ab(0xae,0x4302)
    lab("tile");e(0xe2,0x20);src(3);e(0xc9,0xd6);cond(0xf0,"descriptor")
    # The sole data tile in this ABI is the explicitly generated blank slot zero.
    e(0xc2,0x20,0x8a,0x29,0xff,0x3f);cond(0xd0,"fail")
    for off in range(0,16,2):src(off);cond(0xd0,"fail")
    ab(0x8e,0x4302);e(0xe2,0x20,0xa9,0x7f);ab(0x8d,0x4304);jump("launch")
    lab("descriptor");src(2);e(0xc9,0x50);cond(0x90,"fail");e(0xc9,0x52);cond(0xb0,"fail")
    ab(0x8d,0x4304);e(0x18,0x69,2,0x85,0xe2)
    src(14);ext(0x5f,0x7f0002);e(0xc9,255);cond(0xd0,"fail")
    src(15);e(0xc9,0x29);cond(0xd0,"fail")
    e(0xc2,0x20);src(6);ab(0xcd,0x1226);cond(0xd0,"fail")
    ext(0x5f,0x7f000a);e(0x1a);cond(0xd0,"fail")
    e(0x8a,0x29,255,0x3f,0x4a,0x4a,0x4a,0x4a);ext(0xdf,0x7f0008);cond(0xd0,"fail")
    ext(0x5f,0x7f000c);e(0x1a);cond(0xd0,"fail")
    src(0);e(0x85,0xe0);ab(0x8d,0x4302);e(0x29,15,0);cond(0xd0,"fail")
    src(4);e(0x45,0xe0,0x1a);cond(0xd0,"fail")
    e(0xe2,0x20,0x87,0xe0)
    lab("poll");ab(0xad,0x4212);cond(0x10,"fail");e(0xa7,0xe0);cond(0x30,"fail");e(0x29,1);cond(0xf0,"poll")
    lab("launch");e(0xc2,0x20,0xa9,16,0);ab(0x8d,0x4305);e(0xe2,0x20,0xa9,1);ab(0x8d,0x420b)
    ab(0xad,0x4304);e(0xc9,0x7f);cond(0xf0,"next");e(0xa7,0xe0,0xc9,2);cond(0xd0,"fail")
    lab("next");e(0xc2,0x20,0x8a,0x18,0x69,16,0,0xaa,0x88);cond(0xd0,"tile")
    e(0x68,0x85,0xe0,0xe2,0x20,0x68,0x85,0xe2,0xa9,0x7f);ab(0x8d,0x4304);jump("return")
    lab("fail");e(0xe2,0x20,0xa9,1);ext(0x8f,0x546000);lab("halt");e(0x80,0xfe)
    lab("plain");e(0xa9,1);ab(0x8d,0x420b)
    lab("return");e(0x7a,0xfa,0x28,0xa9,1,0x60)
    for at,k in jumps:c[at:at+2]=struct.pack("<H",labels[k])
    return bytes(c)

def build(a):
    original=(a.client/"body.bin").read_bytes()
    def modify(body,labels):
        assert head_map(body,labels)==original
        old=bytearray(original);entry=0x2000+len(old)
        # The only $7f -> VRAM workflows are the main and early tile uploads.
        # Keep the original instruction length and capture the pre-existing A=1.
        pattern=bytes.fromhex("a9018d0b42")
        sites=[i+2 for i in range(len(old)) if old[i:i+5]==pattern]
        for i in sites:old[i:i+3]=b"\x20"+struct.pack("<H",entry)
        return bytes(old)+job_code(entry)
    for blocks in (5,6):
        try:
            with patch.object(nes_rom636,"STORED",blocks*1024-64):
                nes_rom636.build(a.base,a.out,edit_body=modify,allow_extension=True)
            break
        except ValueError as err:
            if blocks!=5 or str(err)!="ROM capacity":raise
    meta=json.loads((a.out/"build.json").read_bytes())
    meta.update(physical_ROM_B=blocks*1024,program_bytes=blocks*1024,extension_B=len(job_code(0x3680)),body_capacity=0x1900,body_free=0x1900-meta["body_bytes"])
    (a.out/"build.json").write_text(json.dumps(meta,indent=2)+"\n",newline="\n")
    print(blocks,meta["physical_free_B"],meta["extension_B"])

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for n in ("base","client","out"):p.add_argument("--"+n,type=Path,required=True)
    build(p.parse_args())
