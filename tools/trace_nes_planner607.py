"""Profile exactly the linked instructions charged between confirmed input and the first E9."""
import argparse
from bisect import bisect_right
from collections import Counter
import json
from pathlib import Path
import re
import struct

from check_nes_game478 import ELFFile, UC_ARM_REG_LR
from check_nes_rows604 import check_geometry, fixture, simulate
from check_nes_wire600 import ROOT, pin, read, sha
from trace_nes_overlap606 import Transfers


def locations(elf):
    with elf.open('rb') as f:
        e=ELFFile(f)
        funcs=sorted((s['st_value']&~1,s['st_size'],s.name) for s in
                     e.get_section_by_name('.symtab').iter_symbols() if s['st_info']['type']=='STT_FUNC' and s['st_value'])
        lines={}
        for unit in e.get_dwarf_info().iter_CUs():
            lp=e.get_dwarf_info().line_program_for_CU(unit)
            if not lp:continue
            for entry in lp.get_entries():
                st=entry.state
                if st is None:continue
                lines[st.address]=None if st.end_sequence else (
                    Path(lp['file_entry'][st.file-1].name.decode()).name,st.line)
    starts=[s for s,n,k in funcs];indices=sorted(lines)
    def locate(pc):
        i=bisect_right(starts,pc)-1
        assert i>=0 and (not funcs[i][1] or pc<funcs[i][0]+funcs[i][1]),hex(pc)
        ix=bisect_right(indices,pc)-1
        line=lines[indices[ix]] if ix>=0 else None
        return funcs[i][2],line
    return locate


class Profile(Transfers):
    def hook(self,u,at,size,user):
        if (at==getattr(self,'poll_return',None) and len(self.prefix)==14 and
                'confirmed_ms' not in self.prefix[-1]):
            self.record=True
        track=getattr(self,'record',False) and self.first_bg is None
        before=self.instructions if track else 0
        if track:caller=(u.reg_read(UC_ARM_REG_LR)&~1)-2
        super().hook(u,at,size,user)
        if track and self.instructions!=before:
            assert self.instructions==before+1
            self.pcs[at,caller]+=1


def collect(d,src,a,link,candidate):
    g=954
    ref=read(ROOT/'analysis/overlap606-trace.json')
    pin(src/'obj-nes-100/firmware.stm',ref['firmware_SHA256'])
    geom,raw=fixture(a.data,d,g)
    m=Profile(src,False,400)
    lut=re.search(r'\{(.+?)\}',(src/'nes_palette165.inc').read_text())[1]
    m.u.mem_write(m.lut,struct.pack('<64H',*map(int,lut.split(','))))
    p=read(ROOT/'analysis/whole580-verification.json')['phases'][0]['parameters']
    assert link.request('reset')=='OK'
    m.start(link,g,a.warm,p['driver_extra_us'],'normal')
    m.io=[];m.emits=[];m.prefix=[];m.pcs=Counter()
    for _ in range(512):
        assert m.call('nes_runtime165_step',[m.rt])
        if m.saw_ea:break
    check_geometry(m,geom,raw)
    assert m.saw_ea and m.saw_seal and m.state_value()==0 and m.io==ref['frames'][0]['io']
    elf=src/'obj-nes-100/sd2snes.elf'
    locate=locations(elf)
    funcs=Counter();lines=Counter();callers=Counter()
    for (pc,lr),n in m.pcs.items():
        func,line=locate(pc);funcs[func]+=n
        label='%s:%s'%line if line else 'no_line'
        lines[func+' '+label]+=n
        if func in ('memset','memcpy','memcmp','fine','tile','find221','ordinary','patched','epoch','map_word185'):
            try:par,pos=locate(lr)
            except AssertionError:par,pos='external',None
            callers[f'{func} from {par} {pos}']+=n
    elapsed=sum(funcs.values())*2/84000
    old=read(ROOT/'analysis/overlap606-verification.json')['phases'][0]
    assert abs(elapsed-old['commit_to_E9_nontransfer_ms'])<1e-8,(elapsed,old)
    return [dict(generation=g,ELF=sha(elf),instructions=sum(funcs.values()),execution_ms=elapsed,
                 functions=dict(funcs.most_common()),lines=dict(lines.most_common()),callers=dict(callers.most_common()),
                 first_E9=m.first_bg,final_ACK_and_EA=True)]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('board','probe','arm','warm','data','out','report'):
        p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    r=simulate(a,'trace',a.arm/'src',True,collect)
    a.report.write_bytes((json.dumps(r,indent=2)+'\n').encode())
