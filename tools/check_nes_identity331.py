# SPDX-License-Identifier: MIT
"""Execute ARM tile dispatch against explicit full-response identity faults."""
import argparse,json,struct
from pathlib import Path
from probe_nes_arm264 import ARM,crc
from unicorn.arm_const import UC_ARM_REG_R0
from nes_delta231 import sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    class Endpoint:
        def transfer(self,tx):
            self.commands.append(tx[0])
            if tx[0]==0xe0:assert len(tx)==25;return bytes(self.response)
            assert tx[0]==0xe1 and self.valid
            assert tx[17:21]==bytes.fromhex('78563412'),'wrong identity token offset'
            # The ARM hook below returns transport failure after observing E1.
            return bytes(len(tx))
    class CheckedARM(ARM):
        def hook(self,uc,address,size,user):
            issuing=address==(self.symbols['io259']&~1) and uc.mem_read(uc.reg_read(UC_ARM_REG_R0),1)==b'\xe1'
            super().hook(uc,address,size,user)
            if issuing:uc.reg_write(UC_ARM_REG_R0,0)
    ep=Endpoint();arm=CheckedARM(a.source/'output.elf',ep);rows=[]
    def put(n,v):arm.uc.mem_write(arm.symbols[n],v.to_bytes(4,'little'))
    cases=[(7,0,'not ready'),(7,6,'map owner'),(17,32,'length'),(18,1,'length high'),(19,4,'bank'),(19,1,'kind'),(20,1,'slot'),(21,1,'slot high'),(22,2,'generation'),(23,1,'generation high'),(None,None,'valid identity reaches E1')]
    for at,value,label in cases:
        arm.call('reset259',[]);put('begin',1);put('seal',0);put('batch_bytes260',0)
        arm.uc.mem_write(arm.symbols['state259']+6,struct.pack('<HI',1,1))
        arm.uc.mem_write(arm.symbols['status259'],bytes(7)+b'\x02'+bytes(18))
        ep.commands=[];ep.valid=at is None;ep.response=bytearray(25)
        p=ep.response;p[1]=0xfb;p[7]=2;p[8]=1;p[13:17]=bytes.fromhex('78563412');p[17]=16;p[22]=1
        if at is not None:p[at]=value
        p[24]=crc(p[1:24],8)
        packet=bytearray(20);packet[0]=7;packet[4]=1;packet[8]=1;packet[12]=4;packet[14]=16
        arm.uc.mem_write(0x20028000,bytes(packet))
        assert not arm.call('dispatch289',[0x20028000,20]),label
        assert ep.commands==([0xe0,0xe1] if ep.valid else [0xe0]),(label,ep.commands)
        rows.append(label)
    out=dict(passed=True,cases=rows,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),scope=__doc__)
    (a.out/'result.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n');print('PASS',len(rows))


if __name__=='__main__':main()
