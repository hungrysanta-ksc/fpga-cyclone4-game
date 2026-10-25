# SPDX-License-Identifier: MIT
"""Replay real M4 pre-commit snapshots against the full-material fallback."""
import argparse,json,random
from pathlib import Path
from probe_nes_arm264 import ARM,ELFFile
from probe_nes_decode280 import golden
from nes_delta231 import sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--last',type=int,default=3);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);elf=a.source/'output.elf'
    with elf.open('rb') as f:
        syms=ELFFile(f).get_section_by_name('.symtab')
        sizes={n:syms.get_symbol_by_name(n)[0]['st_size'] for n in ('dirty285','resident285','video285','input285')}
    rows=[];pins={str(elf):sha(elf)}
    for serial in range(1,a.last+1):
        p=a.source/f'precommit352-{serial}.bin';snapshot=p.read_bytes();pins[str(p)]=sha(p)
        def fresh():
            arm=ARM(elf,None);arm.uc.mem_write(0x20000000,snapshot);return arm
        def word(arm,n,v=None):
            at=arm.symbols[n]
            if v is not None:arm.uc.mem_write(at,v.to_bytes(4,'little'))
            return int.from_bytes(arm.uc.mem_read(at,4),'little')
        def run(arm):
            before=arm.instructions;assert arm.call('input_commit286',[])==1
            mask=word(arm,'raw_groups352');assert arm.call('begin_step286',[])==1
            return mask,arm.instructions-before,{n:bytes(arm.uc.mem_read(arm.symbols[n],size)) for n,size in sizes.items()}
        opt=fresh();mask,cost,state=run(opt)
        full=fresh();word(full,'display_epoch352',0);fm,fc,fs=run(full)
        assert fm==0xffffffff and state==fs,(serial,'full comparison mismatch')
        assert mask==(0xffffffff if serial==1 else 2),(serial,hex(mask))
        rows.append(dict(serial=serial,case='actual snapshot',mask=mask,instructions=cost,full_instructions=fc,exact=True))
        for offset,label in ((22,'cold'),(23,'raw cold')):
            arm=fresh();arm.uc.mem_write(arm.symbols['receiver280']+offset,b'\x01')
            m,_,st=run(arm);assert m==0xffffffff and st==fs
            rows.append(dict(serial=serial,case=label+' full fallback'))
        for name in ('display_epoch352','display_serial352','display_count352'):
            arm=fresh();word(arm,name,word(arm,name)^128);m,_,st=run(arm)
            assert m==0xffffffff and st==fs
            rows.append(dict(serial=serial,case=name+' mismatch full fallback'))
        arm=fresh();arm.call('stop286',[])
        assert word(arm,'display_epoch352')==0 and word(arm,'raw_groups352')==0xffffffff
        assert arm.call('input_commit286',[])==0 and arm.call('begin_step286',[])==0 and arm.call('commit285',[])==0
        rows.append(dict(serial=serial,case='STOP invalidates and rejects commit/execution'))
        arm=fresh();arm.uc.mem_write(0x20028000,b'bad');assert arm.call('block286',[0x20028000,3,0])==0
        assert arm.call('input_commit286',[])==0
        rows.append(dict(serial=serial,case='bad block CRC cannot commit'))
        arm=fresh();assert arm.call('input_commit286',[])==1 and arm.call('input_commit286',[])==0
        assert arm.call('begin_step286',[])==0
        rows.append(dict(serial=serial,case='repeated input commit fails closed'))
        arm=fresh();assert arm.call('commit285',[])==0
        assert word(arm,'display_serial352')==int.from_bytes(snapshot[arm.symbols['display_serial352']-0x20000000:arm.symbols['display_serial352']-0x20000000+4],'little')
        rows.append(dict(serial=serial,case='unpublished output cannot advance display history'))
        if serial!=3:continue
        # Synthetic checked-material perturbations isolate group arithmetic.
        # They are NOT claimed as new source CRC admission tests.
        rng=random.Random(352)
        for case in range(34):
            arm=fresh();full=fresh()
            for obj in (arm,full):
                old=golden(906)[1]
                obj.uc.mem_write(obj.symbols['history286']+4398,old)
            positions=[] if case==0 else [((case-1)%32)*8,256+((case-1)%32)*8] if case<=32 else rng.sample(range(512),40)
            for pos in positions:
                for obj in (arm,full):
                    at=obj.symbols['history286']+4398+pos;v=obj.uc.mem_read(at,1)[0];obj.uc.mem_write(at,bytes([(v+1)%64]))
            expected=0
            for pos in positions:expected|=1<<((pos%256)//8)
            word(arm,'source_groups352',expected)
            word(full,'display_epoch352',0)
            m,_,st=run(arm);_,_,ref=run(full)
            expected=0
            for pos in positions:expected|=1<<((pos%256)//8)
            assert m==expected and st==ref,(case,hex(m),hex(expected))
            rows.append(dict(serial=serial,case='synthetic group '+str(case),mask=m,exact=True))
        arm=fresh();word(arm,'source_groups352',0);m,_,st=run(arm)
        assert m==0 and st!=fs
        rows.append(dict(serial=serial,case='oracle detects deliberately missing changed group'))
    result=dict(passed=True,cases=rows,pins=pins,scope='Actual M4 snapshot replay, full material equivalence including both-bank stale bits; synthetic edits are arithmetic tests, not CRC admission evidence.')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(dict(passed=True,cases=len(rows))))
if __name__=='__main__':main()
