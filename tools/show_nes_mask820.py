"""Display actual ARM-produced OAM/map/HDMA/CHR using a small independent 65816 DMA driver."""
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from build_nes_trace_replay import Code
from nes_patch181 import LAYOUTS
from run_nes_geometry230 import ROOT

def display(d,ref,cart,mesen,out):
    out.mkdir(parents=True,exist_ok=False)
    read=lambda key:(d/(key+".bin")).read_bytes()
    tiles=[bytearray(16384),bytearray(4096)]
    ends=[0,0]
    for _,hx in json.loads((d/"plans.json").read_text()):
        q=bytes.fromhex(hx)
        _,slot,tag,kind,mask=struct.unpack_from("<3H2B",q)
        obj=int(kind==1)
        stride=32 if obj else 16
        at=slot*stride
        ends[obj]=max(ends[obj],at+stride)
        for y,alt in enumerate(struct.unpack_from("<8H",q,24)):
            if kind!=2 and mask>>y&1:
                tiles[obj][at+y*2]=cart[(tag if alt==65535 else alt)*16+q[8+2*y]]
                tiles[obj][at+y*2+1]=cart[tag*16+8+q[9+2*y]]
    c=Code(0x8000)
    payload=bytearray()
    c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a,0xa9,0,0,0x5b,0xe2,0x20,0xa9,0,0x48,0xab)
    for a,v in [(0x2100,128),(0x4200,0),(0x420c,0),(0x2105,0),(0x2106,0),(0x2107,0x31),(0x210b,0),(0x2101,1),
                (0x212c,17),(0x212d,0),(0x212e,0),(0x212f,0),(0x2130,0),(0x2131,0),(0x2132,224),(0x2133,0),(0x2115,128)]:
        c.store(a,v)
    for a in range(0x2123,0x212c):
        c.store(a,0)
    def dma(mode,port,data):
        src=0x8000+len(payload)
        payload.extend(data)
        for a,v in enumerate((mode,port,src&255,src>>8,1,len(data)&255,len(data)>>8)):
            c.store(0x4300+a,v)
        c.store(0x420b,1)
    def vram(address,data):
        c.store(0x2116,address//2&255)
        c.store(0x2117,address//512)
        dma(1,0x18,data)
    b=LAYOUTS[0]
    patch=read("patch")
    vram(b["bg"],tiles[0][:ends[0]])
    vram(b["obj"],tiles[1][:ends[1]])
    vram(b["map"],read("map"))
    vram(b["patch"],patch[:2048])
    vram(b["patch_map"],struct.pack("<32H",*range(b["patch"]//64,b["patch"]//64+32))+bytes(1984))
    c.store(0x2121,0)
    dma(2,0x22,read("cgram"))
    c.store(0x2102,0)
    c.store(0x2103,0)
    dma(0,4,read("oam"))
    for k,(port,mode,table) in enumerate(((5,4,patch[2048:2129]),(0x2c,4,patch[2210:2291]),(0xd,3,read("hdma"))),1):
        a=0x8000+k*0x800
        for reg,v in ((0x2181,a&255),(0x2182,a>>8),(0x2183,0)):
            c.store(reg,v)
        dma(0,0x80,table)
        for j,v in enumerate((mode,port,a&255,a>>8,0x7e)):
            c.store(0x4300+k*16+j,v)
    c.label("leave");c.absolute(0xad,0x4212);c.branch(0x30,"leave")
    c.label("blank");c.absolute(0xad,0x4212);c.branch(0x10,"blank")
    c.store(0x420c,14);c.store(0x2100,15);c.store(0x7000,1)
    c.label("done");c.branch(0x80,"done")
    body=c.finish()
    assert len(payload)<0x8000 and len(body)<0x7fc0
    image=bytearray([255])*65536
    image[:len(body)]=body
    image[32768:32768+len(payload)]=payload
    image[0x7fc0:0x7fd5]=b"NES MASK820".ljust(21,b" ")
    image[0x7fd5:0x7fdc]=bytes((0x20,0,6,0,1,0,0))
    for a in range(0x7fe0,0x8000,2):
        struct.pack_into("<H",image,a,0x8000)
    image[0x7fdc:0x7fe0]=bytes((255,255,0,0))
    total=sum(image)&65535
    struct.pack_into("<HH",image,0x7fdc,total^65535,total)
    rom=out/"scene.sfc"
    rom.write_bytes(image)
    lua=out/"capture.lua"
    lua.write_text("local OUT_DIR="+json.dumps(out.as_posix())+"\n"+(ROOT/"snes/video_probe/capture_native_commands165.lua").read_text().replace("captured==2","captured==1"))
    with (out/"run.log").open("wb") as log:
        subprocess.run([mesen,"--testRunner",lua,rom,"--timeout=40","--doNotSaveSettings","--enableStdout","--snes.disableFrameSkipping=true",
            "--debug.scriptWindow.allowIoOsAccess=true"],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW,
            env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"))
    rgb=(out/"frame-1.rgb").read_bytes()[7*768:231*768]
    gold=ref.read_bytes()[8*768:232*768]
    assert len(rgb)==len(gold)==224*768
    diff=sum(any(rgb[i+j]>>3!=gold[i+j]>>3 for j in range(3)) for i in range(0,len(rgb),3))
    print(d.name,diff,flush=True)
    assert diff==0
    return int(d.name)

if __name__=="__main__":
    plans,capture,rom,mesen,out=[Path(s).resolve() for s in sys.argv[1:]]
    data=rom.read_bytes()
    done=[display(d,capture/f"frame-{d.name}.rgb",data[16+16384*data[4]:],mesen,out/d.name) for d in sorted(plans.iterdir()) if d.is_dir()]
    (out/"result.json").write_text(json.dumps(dict(frames=done,pixels=len(done)*256*224,mismatches=0)))
