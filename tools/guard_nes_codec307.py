# SPDX-License-Identifier: MIT
"""Actual M4 serializer on71 requirements plus raw/RLE boundary vectors.
SPI calls are intercepted, so these are NOT timing/IRQ/credit measurements.
"""
import argparse,json,struct
from pathlib import Path
from probe_nes_arm264 import ARM,crc
from analyze_nes_ingress306 import decode,packets
from nes_delta231 import BASE,sha

class Sink:
    def __init__(self):self.packets=[]
    def transfer(self,b):
        assert b[0]==0xe1 and crc(b[:-2])==int.from_bytes(b[-2:],'big')
        self.packets.append(bytes(b[1:-2]));return bytes(len(b))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);sink=Sink();arm=ARM(a.source/'output.elf',sink);rows=[]
    def test(f,seal,manifest,label):
        sink.packets=[]
        for name in ('seal','requirements264','batch_bytes260'):
            arm.uc.mem_write(arm.symbols[name],bytes(4))
        arm.uc.mem_write(arm.symbols['begin'],struct.pack('<I',1))
        serial=int.from_bytes(seal[4:8],'little');generation=int.from_bytes(seal[8:10],'little')
        arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HHHHIIBBxx',0,0,0,generation,serial,0,0,0))
        arm.uc.mem_write(arm.symbols['seal289'],bytes(seal));arm.uc.mem_write(0x20028000,bytes(manifest))
        before=arm.instructions
        assert arm.call('dispatch289',[0x20028000,len(manifest)])==1
        p=sink.packets[0];assert p[0]==15
        if p[1]==1:
            assert p[40]==1;raw=p[16:40]+decode(p[41:],166)
        else:assert p[1]==0 and len(p)==206;raw=p[16:]
        assert raw==seal[16:]
        rows.append(dict(frame=f,label=label,bytes=len(p)+3,codec=p[1],instructions=arm.instructions-before))
    for f in range(905,976):
        ps=list(packets((BASE/f'probes/nes-record305/native01/frame{f}.packets').read_bytes()))
        test(f,ps[-1],next(p for p in ps if p[0] in (10,11)),'native')
    for label,req in [('zero',bytes(166)),('literal',bytes([255])*166),('alternating',bytes(i%2 for i in range(166))),('run128',bytes(128)+bytes([1])*38),('run129',bytes(129)+bytes([1])*37)]:
        seal=bytearray(ps[-1]);seal[40:]=req;test(975,seal,next(p for p in ps if p[0] in (10,11)),label)
    assert {x['codec'] for x in rows}=={0,1}
    result=dict(passed=True,cases=rows,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),actual_SPI=False,actual_ARM=True)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print('PASS actual ARM codec',len(rows),'including raw fallback')
if __name__=='__main__':main()
