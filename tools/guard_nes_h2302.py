# SPDX-License-Identifier: MIT
"""Final native H2 must equal the early immutable certificate before SEAL."""
import argparse,binascii,json,struct
from pathlib import Path
from probe_nes_native289 import Producer
from probe_nes_decode280 import records,chunks
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_PC
from nes_delta231 import BASE,sha


class Check(Producer):
    capture=False;passed_h2=False
    def hook(self,uc,address,size,user):
        if self.capture and address==(self.symbols['tiles290']&~1):
            self.passed_h2=True;uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,0x0800fff1);return
        super().hook(uc,address,size,user)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out;d.mkdir(parents=True,exist_ok=False);arm=Check(a.source/'output.elf',None)
    for n in ('reset259','reset285','reset280'):arm.call(n,[])
    arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
    for b in chunks(records(BASE/'probes/nes-joint284/test04/frame905.records')):
        arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
    for n in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286','begin_native290'):assert arm.call(n,[])
    for _ in range(2048):
        ok=arm.call('next_step286',[]);assert ok;assert arm.call('tiles290',[0])
        if ok==2:break
    else:raise AssertionError('planner bound')
    cert=bytes(arm.uc.mem_read(arm.symbols['certificate286'],32));serial=int.from_bytes(cert[8:12],'little');generation=int.from_bytes(cert[12:14],'little')
    arm.uc.mem_write(arm.symbols['state259']+6,struct.pack('<HI',generation,serial));arm.uc.mem_write(arm.symbols['state259']+16,cert[3:4])
    arm.uc.mem_write(arm.symbols['material259'],struct.pack('<I',arm.symbols['video285']));arm.uc.mem_write(arm.symbols['started290'],struct.pack('<I',1))
    saved=bytes(arm.uc.mem_read(0x20000000,0x40000));ctx=arm.uc.context_save();checks=[];arm.capture=True
    for off in (None,3,4,8,12,14,20,22,30):
        arm.uc.mem_write(0x20000000,saved);arm.uc.context_restore(ctx);arm.passed_h2=False
        if off is not None:arm.uc.mem_write(arm.symbols['certificate286']+off,bytes([cert[off]^1]))
        ok=arm.call('frame259',[0,0,serial,generation])
        if off is None:assert ok and arm.passed_h2
        else:assert not ok and not arm.passed_h2 and arm.uc.mem_read(arm.symbols['state259']+17,1)==b'\x13'
        assert not arm.call('commit285',[]);checks.append('matching H2' if off is None else f'changed certificate byte {off}')
    r=dict(passed=True,checks=checks,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),scope=__doc__)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))


if __name__=='__main__':main()
