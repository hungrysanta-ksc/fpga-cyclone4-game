# SPDX-License-Identifier: MIT
"""Replay immutable preparation from352 snapshots; disjoint M4 PC accounting."""
import argparse,bisect,collections,json
from pathlib import Path
from probe_nes_arm264 import ARM,ELFFile
from nes_delta231 import BASE,sha

class Profile(ARM):
    def __init__(self,elf):
        with elf.open('rb') as f:
            e=ELFFile(f);self.funcs=sorted((s['st_value']&~1,s['st_size'],s.name) for s in e.get_section_by_name('.symtab').iter_symbols() if s['st_info']['type']=='STT_FUNC' and s['st_size'])
        self.starts=[x[0] for x in self.funcs];self.counts=collections.Counter();self.pcs=collections.Counter()
        super().__init__(elf,None)
    def hook(self,uc,address,size,user):
        i=bisect.bisect_right(self.starts,address)-1
        n=self.funcs[i][2] if i>=0 and address<self.funcs[i][0]+self.funcs[i][1] else 'return_or_stub'
        self.counts[n]+=1;self.pcs[address]+=1;super().hook(uc,address,size,user)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    d=BASE/'probes/nes-raw352/fixed02';elf=d/'output.elf';r=json.loads((d/'result.json').read_text());rows=[];pins={str(elf):sha(elf)}
    for serial in (1,2,3):
        p=d/f'precommit352-{serial}.bin';snapshot=p.read_bytes();pins[str(p)]=sha(p)
        frame=next(x for x in r['ARM']['frames'] if x['frame']==serial+904)
        for name in ('expand286','geometry_plan286','h2early286'):
            arm=Profile(elf);arm.uc.mem_write(0x20000000,snapshot)
            if name=='expand286' and serial==1:
                # Live expansion follows geometry seal (phase2), before final
                # raw seal. Warm seals share one block and already have phase0.
                # Geometry bytes are identical; raw is not read here.
                arm.uc.mem_write(arm.symbols['receiver280']+20,b'\0\x02')
            if name=='geometry_plan286':
                # sizeof(context286)=124; phase at119 after five32bit pointers,
                # first/end/bank[32], groups/g/palettes. Validate before replay.
                at=arm.symbols['ctx286']+119;assert arm.uc.mem_read(at,1)==b'\x01';arm.uc.mem_write(at,b'\0')
            assert arm.call(name,[])==1
            assert arm.instructions==frame['components'][name],(serial,name,arm.instructions,frame['components'][name])
            assert sum(arm.counts.values())==arm.instructions
            rows.append(dict(frame=serial+904,call=name,instructions=arm.instructions,exclusive_function_instructions=dict(arm.counts),top_instruction_addresses=[dict(address=hex(k),executions=v) for k,v in arm.pcs.most_common(20)]))
    result=dict(passed=True,rows=rows,pins=pins,scope='Replayed prepared352 snapshots; exact same recorded M4 instruction counts. Exclusive PC buckets do not double-count nested calls. No new planner implementation or timing gain.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(rows[-3:],indent=2))
if __name__=='__main__':main()
