"""Execute sparse E1 packets from the linked ARM and an instrumented 65816 receiver."""
import argparse
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import nes_page963
from build_nes_sparse995 import WORK
from build_nes_trace_replay import Code
from nes_hdma990 import PACKED
from nes_raw506 import once
from nes_ready958 import directory
from nes_sparse995 import decode, encode
from test_nes_banks557 import crc

ENTRY = 0x7ee000
RESUME = 0x7e21d7
MASK, GROUP, LENGTH, LIMIT = 0xe600, 0xe602, 0xe604, 0xe606
OUTPUT = 0xe800


def receiver():
    labels = json.loads((PACKED/"labels.json").read_bytes())
    body = (PACKED/"body.bin").read_bytes()
    assert body[RESUME-0x7e2000:RESUME-0x7e2000+3] == bytes.fromhex("ad0012")
    c = Code(ENTRY)
    def imm(op, n):
        c.emit(op); c.word(n)
    def require(branch):
        c.emit(branch, 3); c.jump("bad")
    c.emit(0x08,0xda,0x5a,0x8b)  # save status, X, Y, DBR (entry M=X=0)
    c.emit(0xe2,0x20,0xa9,0x7e,0x48,0xab,0xc2,0x20)
    c.absolute(0xad,0x120c); c.absolute(0x8d,LENGTH); c.emit(0x18); imm(0x69,16)
    c.absolute(0xcd,0x122c); require(0xf0)
    c.absolute(0xad,0x1200); imm(0xc9,0x0502); c.branch(0xd0,"seal")
    c.absolute(0xad,0x120a); imm(0xc9,0x8000+1322); require(0xf0)
    imm(0xa2,30); imm(0xa9,240); c.branch(0x80,"setup")
    c.label("seal"); imm(0xc9,3); require(0xf0)
    c.absolute(0xad,0x120a); imm(0xc9,0x8000); require(0xf0)
    imm(0xa2,21); imm(0xa9,168)
    c.label("setup"); c.absolute(0x8d,LIMIT)
    c.absolute(0xcd,LENGTH); require(0xb0)
    c.absolute(0xec,LENGTH); c.branch(0xf0,"bounds"); require(0x90)
    c.label("bounds"); c.absolute(0x9c,GROUP); imm(0xa0,0)
    c.emit(0xe2,0x20)
    c.label("group"); c.long(0xaf,0x006001); c.emit(0x10,3); c.jump("stop")
    c.emit(0xda); c.absolute(0xae,GROUP); c.long(0xbf,0x400010); c.absolute(0x8d,MASK)
    c.emit(0xfa); c.absolute(0xee,GROUP)
    c.label("byte"); c.absolute(0x4e,MASK); c.emit(0xa9,0); c.branch(0x90,"store")
    c.absolute(0xec,LENGTH); require(0x90)
    c.long(0xbf,0x400010); require(0xd0); c.emit(0xe8)
    c.label("store"); c.absolute(0x99,OUTPUT); c.emit(0xc8,0x98,0x29,7); c.branch(0xd0,"byte")
    c.absolute(0xcc,LIMIT); c.branch(0x90,"group")
    c.absolute(0xec,LENGTH); require(0xf0)
    c.emit(0xc2,0x20); c.absolute(0xad,0x120a); imm(0x29,0x7fff); c.absolute(0x8d,0x120a)
    c.absolute(0xad,LIMIT); c.absolute(0x8d,0x120c); c.emit(0x18); imm(0x69,16); c.absolute(0x8d,0x122c)
    c.label("ready"); c.emit(0xab,0x7a,0xfa,0x28)
    c.absolute(0xad,0x1200); c.absolute(0x4c,(RESUME+3)&65535)
    for name, dest in (("bad","bad_packet"),("stop","stop_packet")):
        c.label(name); c.emit(0xc2,0x30,0xab,0x7a,0xfa,0x28); c.absolute(0x4c,labels[dest]&65535)
    return c.finish(), c.labels


def lua(s):
    code, labels = receiver()
    blob = ",".join(str(b) for b in code)
    setup = f"""local canonical995
local code995={{{blob}}}
local codePlaced995=false
checkedMem527(function()
 assert(canonical995 and packet)
 local restored={{}}
 for i=0,15 do restored[#restored+1]=rd(0x1200+i) end
 for i=0,word(0x120c)-1 do restored[#restored+1]=rd({OUTPUT}+i) end
 packet=string.char(table.unpack(restored))
 assert(packet==canonical995,'65816 restoration differs from logical packet')
 canonical995=nil
 sample516('restored995')
end,emu.callbackType.exec,{labels['ready']})
checkedMem527(function()sample516('decode995')end,emu.callbackType.exec,{ENTRY})
local function loaded()"""
    s = once(s, "local function loaded()", setup)
    # The bridge exposes only physical bytes until the decoder returns. The
    # normal logical aperture then reads the checked 65816 output (no second
    # physical transmission). Its address remapping has no production cost here.
    return once(s, 'packet=requests[index];sample516("load");reads=0;', '''packet=requests[index]
 local name=string.format('%s/wire995-%04x-%04x-%08x.bin',ROOT,pw(8),pw(2),pw(4)+pw(6)*65536)
 local w=io.open(name,'rb')
 if w then
  assert(not canonical995);canonical995=packet;packet=w:read('*a');w:close()
  if not codePlaced995 then
   for i,b in ipairs(code995) do emu.write(0xdfff+i,b,emu.memType.snesWorkRam) end
   codePlaced995=true
  end
 end
 local jump=w and {0x4c,0x00,0xe0} or {0xad,0,0x12}
 for i,b in ipairs(jump) do emu.write(0x21d6+i,b,emu.memType.snesWorkRam) end
 sample516("load");reads=0;''')


def run(t,p):
    folder = directory(t,p,"995linked","cold")
    wire_log = []
    def wrap(parent):
        class Window(parent):
            def accept(self, tx, clock):
                if tx[0] == 0xe1 and tx[12] & 128:
                    assert crc(tx[:-2],16,0x1021,65535) == int.from_bytes(tx[-2:],"big")
                    h = bytearray(tx[1:17])
                    n = int.from_bytes(h[12:14],"little")
                    assert n == len(tx)-19
                    h[11] &= 127
                    k = (h[0],h[1],int.from_bytes(h[10:12],"little"))
                    size = {(2,5,1322):240,(3,0,0):168}[k]
                    raw = decode(tx[17:-2],size)
                    assert encode(raw) == tx[17:-2]
                    gen,seq,serial = (int.from_bytes(h[i:j],"little") for i,j in ((8,10),(2,4),(4,8)))
                    path = folder/f"wire995-{gen:04x}-{seq:04x}-{serial:08x}.bin"
                    assert not path.exists()
                    path.write_bytes(tx[1:-2])
                    wire_log.append([gen,h[0],size,n,clock])
                    h[12:14] = size.to_bytes(2,"little")
                    plain = bytes([0xe1])+h+raw
                    tx = plain+crc(plain,16,0x1021,65535).to_bytes(2,"big")
                return super().accept(tx,clock)
        return Window
    popen = subprocess.Popen
    def instrument(cmd,*a,**kw):
        if "--testRunner" in cmd:
            f=Path(cmd[cmd.index("--testRunner")+1])
            f.write_text(lua(f.read_text(encoding="utf8")),encoding="utf8",newline="\n")
        return popen(cmd,*a,**kw)
    with patch.object(subprocess,"Popen",instrument):
        nes_page963.simulate(t,p,"cold",True,WORK,True,tag="995linked",edition=966,feedback=wrap)
    (folder/"wire995.json").write_text(json.dumps(wire_log))


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    a=p.parse_args();run(a.temp,a.phase)
