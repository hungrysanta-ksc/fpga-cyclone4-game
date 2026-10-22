# SPDX-License-Identifier: MIT
"""Actual ARM progress parser: CRC, conservative credits, wrap and faults."""
import argparse,json,shutil,struct
from pathlib import Path
from nes_delta231 import sha
from probe_nes_arm264 import ARM,crc


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    shutil.copyfile(a.source/'output.elf',d/'output.elf');arm=ARM(d/'output.elf',None);cases=[]
    def setup(sent,retired):
        arm.call('reset259',[]);arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HH',sent,retired))
    def packet(accepted,retired,phase=0,planflags=1,planaccepted=0):
        used=(accepted-retired)&65535
        p=bytes([0,250,(1 if used else 0)|(4 if used==4 else 0),accepted>>8,accepted&255,retired>>8,retired&255,phase,planflags,planaccepted>>8,planaccepted&255])
        return p+bytes([crc(p[1:],8)])
    def run(name,sent,retired,p,ok):
        setup(sent,retired);arm.uc.mem_write(0x20010000,p);before=arm.instructions
        actual=arm.call('progress282',[0x20010000,len(p)])
        assert bool(actual)==ok,name
        state=bytes(arm.uc.mem_read(arm.symbols['state259'],20));new_retired=int.from_bytes(state[2:4],'little')
        assert new_retired==(int.from_bytes(p[5:7],'big') if ok else retired),name
        cases.append(dict(name=name,passed=True,accepted=ok,instructions=arm.instructions-before))
    run('empty',0,0,packet(0,0),True)
    run('partial retirement',10,6,packet(10,8,2,0,4),True)
    run('full credit wrap',2,65534,packet(2,65534),True)
    run('retire across wrap',2,65534,packet(2,1,1,2,7),True)
    run('command response cannot include current acceptance',10,9,packet(11,10),False)
    run('future retire',10,9,packet(10,11),False)
    run('stale retire',10,9,packet(10,8),False)
    run('overfull local credit',10,5,packet(10,6),False)
    good=packet(10,9)
    for name,i,mask in [('reply tag',1,1),('output fault',2,128),('full flag mismatch',2,4),('used flag mismatch',2,1),('phase reserved',7,128),('plan fault',8,128)]:
        p=bytearray(good);p[i]^=mask;p[-1]=crc(p[1:-1],8);run(name,10,9,bytes(p),False)
    for i in range(1,12):
        p=bytearray(good);p[i]^=1;run(f'wire CRC byte{i}',10,9,bytes(p),False)
    setup(10,9);p=bytearray(good);p[-1]^=1;arm.uc.mem_write(0x20010000,bytes(p));assert arm.call('progress282',[0x20010000,12])==0
    arm.uc.mem_write(0x20010000,good);assert arm.call('progress282',[0x20010000,12])==0
    assert arm.uc.mem_read(arm.symbols['state259']+17,1)[0]!=0
    result=dict(passed=True,cases=cases,sticky_error=True,ELF_sha256=sha(d/'output.elf'),script_sha256=sha(Path(__file__)),hardware_cycles=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,cases=len(cases),sticky_error=True)))


if __name__=='__main__':main()
