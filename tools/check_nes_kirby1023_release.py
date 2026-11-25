"""Exercise the linked firmware with Kirby geometry and the existing guarded return fixture."""
from binascii import crc_hqx
from pathlib import Path
import struct
import sys
import tempfile
from check_nes_tail1012 import trace_test, check_header, verify, timer_cases, check
from check_nes_sram897 import check_game_path
from cross_nes1022 import rom_path
from nes_order938 import empty_next_offer
from check_nes_opening818 import admission
from package_nes_trial704 import save, checked, ROOT

WORK=ROOT.parent/'probes/nes-kirby1023'
SRC=WORK/'link/src'
PROOF=WORK/'proof'

def widened_wire(rows):
    # Re-encode the identical lower-bank Adventure screen so its existing
    # output/EA oracle and IRQ/stack high-water probe remain usable.
    output=[]
    for tx,rx in empty_next_offer(rows):
        if tx.startswith('e101') and len(bytes.fromhex(tx))==31:
            begin=bytearray.fromhex(tx)
            assert begin[-6:-2]==struct.pack('<I',0xa58fe808)
            begin[-6:-2]=struct.pack('<I',0x248c7140)
            begin[-2:]=crc_hqx(begin[:-2],65535).to_bytes(2,'big')
            tx=begin.hex()
        if tx.startswith('d1'):
            wire=bytearray.fromhex(rx)
            assert crc_hqx(wire[1:-2],65535)==int.from_bytes(wire[-2:],'big')
            start=1
            if wire[1:3]==b'\xe0\x00':
                assert wire[5:7]==b'\x22\x33'
                wire[6]=0x34
                start+=12
            if wire[start:start+2]==b'\xff\xff':
                at=start+10
                cells=[]
                while at<len(wire)-2:
                    cmd=wire[at];at+=1
                    if cmd&128:
                        dist=(1,2,4,33)[(cmd>>5)&3]
                        for _ in range((cmd&31)+1):
                            cells.append(cells[-dist])
                    else:
                        for _ in range(cmd+1):
                            old=int.from_bytes(wire[at:at+2],'little')
                            value=(old&8191)|((old>>13)<<14)
                            cells.append(value)
                            wire[at:at+2]=value.to_bytes(2,'little')
                            at+=2
                assert len(cells)==int.from_bytes(wire[start+6:start+8],'big')
                wire[start+8:start+10]=crc_hqx(struct.pack('<%dH'%len(cells),*cells),65535).to_bytes(2,'big')
            wire[-2:]=crc_hqx(wire[1:-2],65535).to_bytes(2,'big')
            rx=wire.hex()
        output.append((tx,rx))
    return output

def run(mode):
    PROOF.mkdir(exist_ok=True)
    if mode=='run':
        cases,ram,entry=check_game_path(SRC,order=widened_wire,rom_revision=0x7c,rom_pages=12,content_crc=0x248c7140)
        save(PROOF/'sram.json',dict(cases=cases,ram=ram,entry=entry))
    elif mode=='guards':
        save(PROOF/'trace.json',trace_test(SRC,1023))
        assert check_header(SRC)==11
        verify(1023,SRC,PROOF,marker_values=(4,8,16,24))
        save(PROOF/'timer.json',timer_cases(SRC))
        save(PROOF/'menu.json',check(SRC,'1023'))
        raw=rom_path(Path.home()/'Downloads/test','kirby').read_bytes()
        loader={}
        for key,img,err in [('kirby',raw,0),('bad-last',raw[:-1]+bytes([raw[-1]^1]),4)]:
            r=admission(SRC,img,1023)
            assert r==dict(program=err==0,read_B=len(raw),error=err),r
            loader[key]=r
        save(PROOF/'loader.json',loader)
    elif mode=='base':
        recovery=Path(tempfile.mkdtemp(prefix='recovery-',dir=PROOF))/'base'
        checked('check_nes_transfer512_recovery.py',['--arm',SRC,'--revision','0x7c','--trial',1023,'--fault','none','--out',recovery],PROOF/'base.log')
        (PROOF/'base-result.json').write_bytes((recovery/'result.json').read_bytes())
    else:
        raise ValueError(mode)
    print('PASS1023',mode)

if __name__=='__main__':
    run(sys.argv[1])
