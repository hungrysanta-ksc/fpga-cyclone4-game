"""Measure OAM acceptance and compare checked ROM DMA with generic WRAM word stores."""
import argparse
from pathlib import Path

from build_nes_trace_replay import Code
from check_nes_plan975 import read
from nes_dma1000 import ORIGIN, PACKED, once
from nes_overlap1002 import run as replay


# The 978 loader occupies 5032 bytes; the next 24 bytes precede its vectors.
TEMPLATE_SIZE = 24
PATTERN = bytes.fromhex("00 f0 00 00")


def assemble(variant="dma",stage=False):
    l = read(PACKED/"labels.json")
    body = (PACKED/"body.bin").read_bytes()
    build = read(PACKED/"build.json")
    offset = build["loader_B"]+build["encoded_B"]
    assert offset+TEMPLATE_SIZE==5056 and build["physical_free_B"]==TEMPLATE_SIZE
    bus = 0x8000+offset
    site = ORIGIN+body.index(bytes.fromhex("8b a6 7a a5 7a 18 69 04 00"),l["literal_length227"]-ORIGIN)
    mvn = ORIGIN+body.index(bytes.fromhex("54 7f 7f ab"),site-ORIGIN)
    post = mvn+4
    assert body[post-ORIGIN:post-ORIGIN+3]==bytes.fromhex("20 19 36")
    extra=0
    if stage:
        from nes_stage1001 import candidate
        extra=len(candidate(False)[ORIGIN+len(body)])
    c=Code(ORIGIN+len(body)+extra)
    def imm(op,n):
        c.emit(op);c.word(n)
    def near(op,addr):
        c.absolute(op,addr&65535)
    c.label("entry")
    if variant=="words":
        # Restore the 4..60-byte prefix with the checked seed, then write
        # 64-byte groups using both arbitrary 16-bit words of this packet.
        c.emit(0x8b,0xa6,0x7a,0xa5,0x7a,0x18);imm(0x69,4);c.emit(0xa8)
        near(0xad,0x120c);c.emit(0x38);imm(0xe9,4);c.emit(0x48)
        imm(0x29,63);c.branch(0xf0,"aligned");c.emit(0x3a,0x54,0x7f,0x7f)
        c.label("aligned");c.emit(0x68,*(0x4a,)*6,0x85,0x60,0xab,0xbb)
        c.label("batch");near(0x20,l["service"]);c.branch(0xf0,"live");near(0x4c,l["stop_packet"])
        c.label("live");c.emit(0xa5,0x60);c.branch(0xd0,"write");near(0x4c,l["accepted"])
        c.label("write");c.emit(0x8b,0xf4,0x7f,0x7f,0xab,0xab)
        for half in (0,2):
            c.long(0xaf,0x400010+half)
            for off in range(half,64,4):
                near(0x9d,off)
        c.emit(0xab,0x8a,0x18);imm(0x69,64);c.emit(0xaa,0xc6,0x60);c.jump("batch")
        return offset,site,mvn,post,{site:bytes([0x4c,c.base&255,c.base>>8&255]),c.base:c.finish()},c.labels
    # Original four seed bytes have already arrived by DMA. Compare every
    # word of the immutable A-bus source against those received bytes.
    c.emit(0xa6,0x7a);c.long(0xbf,0x7f0000);c.emit(0x85,0x60)
    c.long(0xbf,0x7f0002);c.emit(0x85,0x62)
    imm(0xa2,TEMPLATE_SIZE-4)
    c.label("check")
    c.long(0xbf,bus);c.emit(0xc5,0x60);c.branch(0xd0,"generic")
    c.long(0xbf,bus+2);c.emit(0xc5,0x62);c.branch(0xd0,"generic")
    c.emit(0xca,0xca,0xca,0xca);c.branch(0x10,"check")
    c.label("verified")
    near(0xad,0x120c);c.emit(0x38);imm(0xe9,4);c.emit(0x85,0x60)
    # DMA channel 0 still targets $2180 in incrementing mode. Its B-bus
    # WRAM pointer stands immediately after the first four bytes.
    c.emit(0xe2,0x20);near(0x9c,0x4304);c.emit(0xc2,0x20)
    c.label("batch")
    near(0x20,l["service"]);c.branch(0xf0,"live");near(0x4c,l["stop_packet"])
    c.label("live");c.emit(0xa5,0x60);c.branch(0xf0,"done")
    imm(0xc9,TEMPLATE_SIZE);c.branch(0x90,"short");imm(0xa9,TEMPLATE_SIZE)
    c.label("short");near(0x8d,0x4305)
    c.emit(0x49,0xff,0xff,0x38,0x65,0x60,0x85,0x60)
    imm(0xa9,bus);near(0x8d,0x4302)
    c.emit(0xe2,0x20);c.store(0x420b,1);c.emit(0xc2,0x20);c.branch(0x80,"batch")
    c.label("done");near(0x4c,l["accepted"])
    c.label("generic");c.emit(0x8b,0xa6,0x7a);near(0x4c,site+3)
    patch={site:bytes([0x4c,c.base&255,c.base>>8&255]),c.base:c.finish()}
    return offset,site,mvn,post,patch,c.labels


def run(temp,phase,mode,variant,fault=None,stage=False,joint=False):
    offset,site,mvn,post,patch,labels=assemble(variant,stage)
    stock=variant=="stock"
    l=read(PACKED/"labels.json")
    out=temp/(f"nes-oam1003-{variant}-{mode}-p{phase}"+("-"+fault if fault else "")+("-stage" if stage else ""))
    rom=bytearray((PACKED/"sink165.sfc").read_bytes())
    assert rom[offset:offset+TEMPLATE_SIZE]==bytes([255])*TEMPLATE_SIZE
    if variant in ("dma","fallback"):
        rom[offset:offset+TEMPLATE_SIZE]=PATTERN*(TEMPLATE_SIZE//4)
        if variant=="fallback":rom[offset+TEMPLATE_SIZE-1]^=1
    fixture=out.with_suffix(".sfc")
    if not joint:
        fixture.write_bytes(rom)

    def observe(lua):
        stages={"header":l["ordinary547"],"shape":l["repeat227"],"range":l["data"],
                "dest":l["data_size_ok"],"dma_setup":l["literal1814"],
                "dma":l["literal_length227"],"copied":l["literal_length227"]+7,
                "repeat":site,"mvn":mvn,"post":post,"accepted":l["accepted"],"reply":l["reply"]}
        if variant=="words":stages.update({k:labels[k] for k in ("batch","write")})
        elif not stock:stages.update({k:labels[k] for k in ("verified","generic","done")})
        hook="""
local seen1003={}
local chunks1003=0
local function isOAM1003()return packet and pw(8)==912 and pb(1)==4 and (pb(0)==8 or pb(0)==2)end
local function tap1003(name)
 if not isOAM1003() then return end
 local key=index..name
 if seen1003[key] then return end
 seen1003[key]=true;sample516('oam_'..name)
 if name=='accepted' then
  local at=0x10000+word(0x1020)+0x6200+pw(10)
  local n=pb(0)==8 and pw(14) or pw(12)
  for i=0,n-1 do assert(rd(at+i)==pb(16+(i%pw(12))),'OAM data mismatch at receipt') end
 end
end
"""
        for k,addr in stages.items():
            hook+=f"checkedMem527(function()tap1003('{k}')end,emu.callbackType.exec,{addr})\n"
        lua=once(lua,"local function step920(key)",hook+"local function step920(key)")
        anchor='packet=requests[index];sample516("load");'
        if not stock:
            writes=";".join(f"emu.write({addr+i-0x7e0000},{v},emu.memType.snesWorkRam)" for addr,b in patch.items() for i,v in enumerate(b))
            lua=once(lua,anchor,anchor+"if pw(8)==912 and pb(0)==1 then "+writes+" end;")
        if fault=="bad_range":
            lua=once(lua,anchor,anchor+"if pw(8)==912 and pb(0)==8 then packet=packet:sub(1,14)..string.pack('<I2',364)..packet:sub(17) end;")
        if fault=="alt_stop":
            lua=once(lua,anchor,anchor+"if isOAM1003() and pb(0)==8 then packet=packet:sub(1,16)..string.char(41,204,22,147) end;")
            lua=once(lua," if a==0x6001 then",""" if a==0x6001 then
  if isOAM1003() and seen1003[index..'write'] and word(0x60)==0 then
   for i=0,pw(14)-1 do assert(rd(0x10000+word(0x7a)+i)==pb(16+i%4)) end
   sample516('arbitrary_checked',pw(14));return 128
  end""")
        if fault=="mid_stop" and variant=="words":
            lua=once(lua," if a==0x6001 then"," if a==0x6001 then\n  if isOAM1003() and seen1003[index..'write'] then return 128 end")
        elif fault=="mid_stop":
            lua=once(lua," if a==0x6001 then"," if a==0x6001 then\n  if isOAM1003() and chunks1003>0 then return 128 end")
        lua=once(lua,"local function write(a,v)","""local function write(a,v)
 if a==0x420b and v==1 and isOAM1003() and pb(0)==8 and regs[0x4304]==0 then
  local n=regs[0x4305]+256*regs[0x4306]
  assert(regs[0x4301]==0x80 and regs[0x4300]==0 and regs[0x4302]+256*regs[0x4303]==BUS)
  assert(n==math.min(SIZE,pw(14)-4-chunks1003))
  chunks1003=chunks1003+n;sample516('template_dma',n)
 end""".replace("BUS",str(offset+32768)).replace("SIZE",str(TEMPLATE_SIZE)))
        return lua

    guard={"mid_stop":"stop_decode","alt_stop":"stop_decode","bad_range":"bad_seal"}.get(fault,fault)
    if joint:
        import subprocess
        from unittest.mock import patch as mock_patch
        import nes_page963
        from nes_hdma990 import BASE
        assert variant=="words" and not fault and not stage
        tag="1003wordsB"
        from check_nes_blank959 import directory
        target=directory(temp,phase,tag,"cold")
        launched=[]
        launch=subprocess.Popen
        def traced(args,*rest,**kwargs):
            paths=[Path(str(v)) for v in args]
            if target/"capture.lua" in paths:
                script=target/"capture.lua"
                source=observe(script.read_text(encoding="utf8"))
                anchor="local sequence=0;"
                pc=l["group_ready538"]
                source=once(source,anchor,f"checkedMem527(function()sample516('group1002')end,emu.callbackType.exec,{pc})\n"+anchor)
                script.write_text(source,encoding="utf8",newline="\n");launched.append(True)
            return launch(args,*rest,**kwargs)
        with mock_patch.object(subprocess,"Popen",traced),mock_patch.object(nes_page963,"PACKED",PACKED):
            nes_page963.simulate(temp,phase,"cold",True,BASE,True,tag=tag,edition=966)
        assert launched==[True]
        return
    replay(temp,phase,mode,guard,stage=stage,destination=out,extra=observe,rom=fixture)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("mode",choices=("reference","arb","tail"));p.add_argument("variant",choices=("stock","dma","fallback","words"))
    p.add_argument("--joint",action="store_true");p.add_argument("--stage",action="store_true");p.add_argument("--fault",choices=("bad_seal","bad_range","mid_stop","alt_stop"))
    a=p.parse_args();run(a.temp.resolve(),a.phase,a.mode,a.variant,a.fault,a.stage,a.joint)
