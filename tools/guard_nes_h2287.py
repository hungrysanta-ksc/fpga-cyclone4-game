# SPDX-License-Identifier: MIT
"""Actual native-view H2 checks before send; transport is verified separately."""
import argparse,json,struct,binascii
from pathlib import Path
from probe_nes_live287 import ARM
from probe_nes_arm264 import plans,u16
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_PC,UC_ARM_REG_LR
from nes_delta231 import BASE,sha

class View(ARM):
    captured=None
    def hook(self,uc,address,size,user):
        if address==(self.symbols['drain']&~1):
            self.instructions+=1;uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
        if address==(self.symbols['send']&~1):
            assert uc.reg_read(UC_ARM_REG_R0)==48
            self.captured=bytes(uc.mem_read(self.symbols['wire259']+17,32))
            uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,0x0800fff1);return
        super().hook(uc,address,size,user)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();d=a.out;d.mkdir(parents=True,exist_ok=False)
    arm=View(a.source/'output.elf',None);oracle,groups=plans();pp=groups[1];blob=b''.join(len(p).to_bytes(2,'little')+p for p in pp)
    arm.uc.mem_write(0x20010000,blob);layout=[arm.call('layout285',[i]) for i in range(3)];v=arm.symbols['video285'];meta=(oracle/'expected-1.bin').read_bytes()
    at=0
    for off,n in [(layout[0],4096),(layout[1],512),(layout[2],544),(layout[1]+512,1121),(0,2291),(2292,6)]:arm.uc.mem_write(v+off,meta[at:at+n]);at+=n
    arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',v));saved=bytes(arm.uc.mem_read(0x20000000,0x40000));checks=[]
    expected=bytes.fromhex((BASE/'probes/nes-joint284/test04/prelude905.hex').read_text())[16:48]
    cases=[('valid native view',None,None,True),('native padding ignored',2291,b'\xa5',True),
           ('invalid scroll repeat',layout[1]+512,b'\x80',False),('invalid raw mode',2049,b'\x02\x00',False),
           ('invalid bank0 map base',2051,b'\x99\x00',False),('mismatched bank1 repeat',2129,b'\x00',False),
           ('invalid raw length',2292,b'\x00\x00',False)]
    for name,off,data,valid in cases:
        arm.uc.mem_write(0x20000000,saved);arm.captured=None
        if off is not None:
            assert bytes(arm.uc.mem_read(v+off,len(data)))!=data,(name,'mutation must change bytes')
            arm.uc.mem_write(v+off,data)
        ok=arm.call('frame259',[0x20010000,len(blob),1,u16(pp[0],8)])
        if valid:assert ok==1 and arm.captured==expected,(name,arm.captured)
        else:assert ok==0 and arm.captured is None and arm.uc.mem_read(arm.symbols['state259']+17,1)==b'\x13',name
        checks.append(name)
    # raw0 H2 excludes all expired raw tables, including native padding.
    arm.uc.mem_write(0x20000000,saved);arm.captured=None
    zero=bytearray(blob);seal_at=len(blob)-len(pp[-1]);assert pp[-1][0]==3
    zero[seal_at+38:seal_at+40]=b'\x00\x00';arm.uc.mem_write(0x20010000,bytes(zero))
    arm.uc.mem_write(v+2048,b'\xa5'*250)
    expected0=bytearray(expected);expected0[16:19]=b'\x00'*3;expected0[20]=0
    scroll=int.from_bytes(expected0[14:16],'little');expected0[22:24]=binascii.crc_hqx(meta[5152:5152+scroll],65535).to_bytes(2,'little')
    expected0[24:26]=scroll.to_bytes(2,'little');expected0[30:32]=binascii.crc_hqx(expected0[:30],65535).to_bytes(2,'little')
    assert arm.call('frame259',[0x20010000,len(zero),1,u16(pp[0],8)])==1 and arm.captured==bytes(expected0)
    checks.append('raw0 exact H2 with poisoned expired raw tables')
    r=dict(passed=True,checks=checks,scope=__doc__,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)))
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))

if __name__=='__main__':main()
