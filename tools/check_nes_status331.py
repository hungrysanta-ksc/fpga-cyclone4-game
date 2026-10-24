# SPDX-License-Identifier: MIT
"""Actual ARM common response checker: CRC, counter wrap and separate credit."""
import argparse,json,struct
from pathlib import Path
from probe_nes_arm264 import ARM,crc
from nes_delta231 import sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);arm=ARM(a.source/'output.elf',None);tests=[]
    def put(n,v,size=4):arm.uc.mem_write(arm.symbols[n],v.to_bytes(size,'little'))
    def setup(sent=2,retired=1,issued=1,consumed=0):
        arm.call('reset259',[])
        arm.uc.mem_write(arm.symbols['state259'],struct.pack('<HH',sent,retired))
        put('issued312',issued,2);put('consumed312',consumed,2)
    def packet(full=True,accepted=2,retired=2,consumed=1):
        p=bytearray(25 if full else 14);p[1]=0xfb;used=(accepted-retired)&65535
        p[2]=(used!=0)|(4 if used==2 else 0);p[3:5]=accepted.to_bytes(2,'big');p[5:7]=retired.to_bytes(2,'big')
        p[7]=2;p[8]=1;p[9:11]=b'\x00\x09';p[11:13]=consumed.to_bytes(2,'big')
        if full:p[13:24]=bytes.fromhex('7856341220000407000200')
        p[-1]=crc(p[1:-1],8);return p
    def check(p,expected,label,full=True,recrc=False):
        if recrc:p[-1]=crc(p[1:-1],8)
        arm.uc.mem_write(0x20028000,bytes(p));actual=arm.call('progress331',[0x20028000,len(p),int(full)])
        assert bool(actual)==expected,(label,actual)
        tests.append(label)
    for full in (False,True):
        setup();check(packet(full),True,'valid full' if full else 'valid short',full)
        assert int.from_bytes(arm.uc.mem_read(arm.symbols['plan_accepted282'],4),'little')==9
    # Every single bit of the full prefix, identity and CRC must be covered.
    for byte in range(1,25):
        for bit in range(8):
            setup();p=packet();p[byte]^=1<<bit;check(p,False,f'CRC byte{byte} bit{bit}')
    for at,value,label in [(1,0xfc,'old tag'),(2,128,'queue fault'),(7,8,'reserved phase'),(8,3,'inconsistent plan'),(4,3,'future accepted'),(6,3,'future retired'),(12,2,'future consumed')]:
        setup();p=packet();p[at]=value;check(p,False,label,recrc=True)
    setup(0,65535,0,65535);check(packet(accepted=0,retired=0,consumed=0),True,'16bit counter wrap')
    setup();check(packet(consumed=0),True,'storage credit is not consume completion')
    assert bytes(arm.uc.mem_read(arm.symbols['consumed312'],2))==b'\0\0'
    setup();p=packet();p[24]^=1;check(p,False,'first corrupt full');check(packet(),False,'sticky failure')
    out=dict(passed=True,tests=tests,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),scope=__doc__)
    (a.out/'result.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n');print('PASS',len(tests))


if __name__=='__main__':main()
