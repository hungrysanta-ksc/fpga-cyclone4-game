# SPDX-License-Identifier: MIT
"""Actual ARM continuation, every OBJ yield STOP, and real IRQ return guards."""
import argparse,binascii,json
from pathlib import Path
from probe_nes_native289 import Producer
from probe_nes_decode280 import records,chunks
from guard_nes_irq284 import Endpoint
from nes_delta231 import BASE,sha


class Interrupted(Producer):
    inject=False
    def hook(self,uc,address,size,user):
        if self.inject and address==(self.symbols['step286']&~1):
            self.inject=False;self.gpio(1)
        super().hook(uc,address,size,user)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    ep=Endpoint();arm=Interrupted(a.source/'output.elf',ep);ep.arm=arm
    for n in ('irq_init284','reset259','reset285','reset280'):arm.call(n,[])
    arm.uc.mem_write(arm.symbols['palette285'],(BASE/'probes/nes-delta231/test07/palette.bin').read_bytes())
    word=lambda n:int.from_bytes(arm.uc.mem_read(arm.symbols[n],4),'little')
    def save():return bytes(arm.uc.mem_read(0x20000000,0x40000)),arm.uc.context_save()
    def restore(s):
        arm.uc.mem_write(0x20000000,s[0]);arm.uc.context_restore(s[1]);arm.pending=False;arm.pr=0;arm.gpio(0)
    def signature():
        n=word('output_size285');v=arm.symbols['video285'];size=arm.call('layout285',[4])
        return bytes(arm.uc.mem_read(v,size)),bytes(arm.uc.mem_read(arm.symbols['output285'],n)),tuple(word(x) for x in ('obj_init302','obj_rank302','obj_at302','batch_size285','batch_count285'))
    rows=[];stop_checks=irq_checks=0
    for f in (905,906,907):
        for b in chunks(records(BASE/f'probes/nes-joint284/test04/frame{f}.records')):
            arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])
        for n in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286','begin_native290'):assert arm.call(n,[])
        arm.call('irq_begin284',[]);costs=[]
        for i in range(2048):
            snap=save();before=arm.instructions;ok=arm.call('next_step286',[]);assert ok;cost=arm.instructions-before
            if ok==3:
                costs.append(cost);expected=signature();after=save()
                assert not arm.call('commit285',[])
                arm.call('stop286',[])
                assert not arm.call('service296',[]) and not arm.call('next_step286',[]) and not arm.call('tiles290',[0]) and not arm.call('commit285',[])
                assert tuple(word(n) for n in ('obj_init302','obj_rank302','obj_at302'))==(0,0,0)
                assert signature()[1]==expected[1];stop_checks+=1;restore(after)
                if f==907:
                    restore(snap);prior=len(arm.exti);arm.inject=True;assert arm.call('next_step286',[])==3 and not arm.inject and len(arm.exti)==prior+1
                    assert signature()==expected;irq_checks+=1
            assert arm.call('tiles290',[0])
            if ok==2:break
        else:raise AssertionError('unbounded planner')
        assert arm.call('prepare289',[]) and arm.call('tiles290',[1]) and arm.call('commit285',[])
        rows.append(dict(frame=f,yields=len(costs),max_slice_instructions=max(costs),slice_instructions=costs,final_tail_instructions=cost))
    r=dict(passed=True,frames=rows,STOP_checks=stop_checks,IRQ_checks=irq_checks,ELF_sha256=sha(a.source/'output.elf'),script_sha256=sha(Path(__file__)),actual_ACK=False,scope=__doc__)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))


if __name__=='__main__':main()
