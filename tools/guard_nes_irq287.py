# SPDX-License-Identifier: MIT
"""Bounded MMIO adapter checks and actual EXTI preemption inside row touch."""
import json,sys,binascii,shutil
from pathlib import Path
import guard_nes_irq284 as old
from probe_nes_live287 import ARM
from probe_nes_decode280 import records,chunks
from nes_delta231 import BASE,ROOT,sha

def main():
    old.ARM=ARM;old.main()
    d=Path(sys.argv[sys.argv.index('--out')+1]);ep=old.Endpoint()
    class Interrupt(ARM):
        inject=False
        def hook(self,uc,address,size,user):
            if self.inject and address==(self.symbols['nes_resident287_touch']&~1):
                self.inject=False;self.gpio(0);self.gpio(1)
            super().hook(uc,address,size,user)
    arm=Interrupt(d/'output.elf',ep);ep.arm=arm
    for name in ('reset285','reset280','irq_init284'):arm.call(name,[])
    arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
    def word(name):return int.from_bytes(arm.uc.mem_read(arm.symbols[name],4),'little')
    for f in range(905,908):
        for b in chunks(records(BASE/f'probes/nes-joint284/test04/frame{f}.records')):
            arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
        for name in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286'):assert arm.call(name,[])
        if f==907:arm.call('irq_begin284',[]);arm.inject=True
        for _ in range(34):
            ok=arm.call('next_step286',[]);assert ok
            if ok==2:break
        else:raise AssertionError('group limit')
        out=bytes(arm.uc.mem_read(arm.symbols['output285'],word('output_size285')))
        assert out==(BASE/f'probes/nes-joint284/test04/plans{f-904}.bin').read_bytes()
        if f==907:
            assert not arm.inject and len(arm.exti)==1 and arm.exti[0]['frame'][6]==(arm.symbols['nes_resident287_touch']&~1)
            assert word('rows_reused287')==29
        assert arm.call('commit285',[])
    r=json.loads((d/'result.json').read_text());r['row_preemption287']=arm.exti;r['row_plan_exact']=True
    r['adapter_sha256']=sha(ROOT/'tools/probe_nes_live287.py');r['guard287_sha256']=sha(Path(__file__))
    shutil.copyfile(__file__,d/Path(__file__).name);(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS actual row touch IRQ exact plans')

if __name__=='__main__':main()
