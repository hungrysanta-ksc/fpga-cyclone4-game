# SPDX-License-Identifier: MIT
"""Independent proposed-envelope guards, explicitly not FPGA fault injection."""
import argparse,binascii,json
from pathlib import Path
from probe_nes_abi364 import Converter,envelopes,normalized_semantics,packet
from probe_nes_arm264 import crc
from nes_delta231 import BASE,sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    c=Converter(a.arm/'abi364.elf',1)
    # All eight sparse ALT fields, both END kinds, and the partial-BG marker.
    p=bytes([0,255,1,0,2,0,3,0,255])+bytes.fromhex('40226d646bff')+bytes([1])+bytes(range(16))
    payload=p+bytes([0x82,1,0,0x83,1,0,0x87,1,0]);tx=bytes([0xe9])+len(payload).to_bytes(2,'little')+bytes([4])+payload
    tx+=binascii.crc_hqx(payload,65535).to_bytes(2,'big');tx+=bytes([crc(tx,8),165]);b,ins,n=c.convert(tx,1)
    records,_=envelopes(b,1,0);assert n==1 and len(records[0][2])==128
    tests=[]
    def bad(label,record):
        try:normalized_semantics([record])
        except AssertionError:tests.append(label)
        else:raise AssertionError(('guard escaped',label))
    m=(0xfffffffe).to_bytes(4,'little')+bytes([2])+bytes([0,0,2,0,2,0,0,0,0x12,0x34])*2
    bad('token wrap',(14,5,m))
    for label,at,value in [('zero span',7,0),('odd start',5,1),('encoded length',9,4),('format',11,1),('region',12,1)]:
        v=bytearray((1).to_bytes(4,'little')+bytes([1])+bytes([0,0,2,0,2,0,0,0,0x12,0x34]));v[at]=value;bad(label,(14,5,v))
    bad('metadata overrun',(11,3,bytes([255,0,1,2])))
    bad('descriptor format',(8,6,bytes([0,0,4,0,4,0,1,0,1,2,3,4])))
    # Sequence wrap is rejected instead of silently reusing a packet namespace.
    c.arm.uc.mem_write(c.arm.symbols['sequence364'],(65536).to_bytes(4,'little'))
    t=packet(3,0,1,0,0,b'');c.arm.uc.mem_write(0x20010000,t)
    assert c.arm.call('convert364',[0x20010000,len(t),1,1])==0;tests.append('sequence exhaustion')
    stack=0
    for mode in (0,1):
        cv=Converter(a.arm/'abi364.elf',mode)
        for f in range(905,908):
            for t in json.loads((BASE/f'probes/nes-execute362/keepwindow01/arm{f}.json').read_text())['transfers']:
                tx=bytes.fromhex(t['tx'])
                if tx and tx[0] in (0xe1,0xe9):cv.convert(tx,f-904)
        stack=max(stack,0x2003f000-cv.arm.low_sp)
    r=dict(passed=True,cases=tests,full_ALT_and_ENDs=True,full_ALT_instructions=ins,all_observed_stack_bytes=stack,ELF_sha256=sha(a.arm/'abi364.elf'),scope='Producer and Python semantic oracle only; unchanged reference STOP/final/CRC guards are separately hash-bound. No new receiver safety proof.')
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
