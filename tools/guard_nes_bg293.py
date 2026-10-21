# SPDX-License-Identifier: MIT
"""BG boundary STOP/commit and real compiled ISR preemption; intercepted sink."""
import argparse,binascii,json,struct
from pathlib import Path
from probe_nes_native289 import Producer
from probe_nes_decode280 import records,chunks
from guard_nes_irq284 import Endpoint
from nes_delta231 import BASE,sha

class Interrupted(Producer):
    inject=False
    def hook(self,uc,address,size,user):
        if self.inject and address==(self.symbols['flush285']&~1):
            self.inject=False;self.gpio(1)
        super().hook(uc,address,size,user)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);ep=Endpoint();arm=Interrupted(a.source/'output.elf',ep);ep.arm=arm;checks=[]
    for n in ('irq_init284','reset259','reset285','reset280'):arm.call(n,[])
    arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
    word=lambda n:int.from_bytes(arm.uc.mem_read(arm.symbols[n],4),'little')
    def save():return bytes(arm.uc.mem_read(0x20000000,0x40000)),arm.uc.context_save()
    def restore(s):
        arm.uc.mem_write(0x20000000,s[0]);arm.uc.context_restore(s[1]);arm.pending=False;arm.pr=0;arm.gpio(0);arm.packets=[]
    def stop_check(label):
        snap=save();n=word('output_size285');prefix=bytes(arm.uc.mem_read(arm.symbols['output285'],n))
        assert not arm.call('commit285',[])
        arm.call('stop286',[])
        assert not arm.call('next_step286',[]) and not arm.call('prepare289',[]) and not arm.call('commit285',[])
        assert word('output_size285')==n and bytes(arm.uc.mem_read(arm.symbols['output285'],n))==prefix
        checks.append(label+': STOP rejects further plan/producer/commit; published prefix unchanged');restore(snap)
    for f in (905,906,907):
        for b in chunks(records(BASE/f'probes/nes-joint284/test04/frame{f}.records')):
            arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
        for n in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286'):assert arm.call(n,[])
        for step in range(30):
            if f==907 and step==28:
                stop_check('before BG publication');assert not arm.call('prepare289',[])
                arm.call('irq_begin284',[]);snap=save();assert arm.call('next_step286',[])==1
                n=word('output_size285');expected=bytes(arm.uc.mem_read(arm.symbols['output285'],n));reserve=(word('reserve_bytes293'),word('reserve_plans293'))
                restore(snap);before=len(arm.exti);arm.inject=True
                assert arm.call('next_step286',[])==1 and not arm.inject and len(arm.exti)==before+1
                assert word('output_size285')==n and bytes(arm.uc.mem_read(arm.symbols['output285'],n))==expected
                assert (word('reserve_bytes293'),word('reserve_plans293'))==reserve
                assert arm.exti[-1]['frame'][6]==(arm.symbols['flush285']&~1)
                checks.append('IRQ at BG flush: real handler and eight-word return preserve batch and reservation')
                stop_check('after BG publication');assert not arm.call('prepare289',[])
                continue
            result=arm.call('next_step286',[]);assert result==(2 if step==29 else 1)
        if f==907:stop_check('after final planning')
        assert arm.call('prepare289',[]) and arm.call('produce289',[]) and arm.call('commit285',[])
    result=dict(passed=True,checks=checks,EXTI=arm.exti,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),actual_ACK=False,scope=__doc__)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
