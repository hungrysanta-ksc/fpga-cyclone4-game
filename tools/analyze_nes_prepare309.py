# SPDX-License-Identifier: MIT
"""Same-RTL ARM preparation timing, byte equality, guards and unchanged area."""
import csv,json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile

def main():
    pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    prior=js(ROOT/'analysis/ingress307-verification.json')
    for p,h in prior['input_hashes'].items():assert sha(Path(p))==h
    def loaded(p):
        with pin(p).open('rb') as f:return [(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD']
    d=BASE/'probes/nes-prepare309';runs={};readiness=[];rtl=None
    for tag,mode in [('reference01','reference'),('window02','restricted'),('normal01','normal')]:
        q=d/tag;r=js(q/'result.json');assert r['passed']
        if rtl is None:rtl=r['rtl_hashes']
        assert r['rtl_hashes']==rtl
        for n,h in r['rtl_hashes'].items():assert sha(pin(q/n))==h
        assert sha(pin(q/'output.elf'))==r['ELF_sha256']
        for p in q.iterdir():
            if p.suffix in ('.c','.h','.inc','.s','.ld','.dll') or p.name=='size287.log':pin(p)
        events=list(csv.reader(pin(q/'joint-events.csv').open()))
        src={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(pin(q/'cycles.csv').open())}
        obs=js(q/'prepare309.json');rows=[]
        for f in (905,906,907):
            es=[x for x in events if x[1]==str(f)];end=next(x for x in es if x[0]=='frame_done')
            oldtag='test01' if mode=='normal' else 'window03'
            tx=js(q/f'arm{f}.json')['transfers'];old=js(BASE/'probes/nes-ingress307'/oldtag/f'arm{f}.json')['transfers']
            wire=lambda xs:[x['tx'] for x in xs if x['tx'].startswith(('e1','e9'))]
            assert wire(tx)==wire(old),('E1/E9 exact bytes',tag,f)
            total=src[f]+int(end[3])/1e9
            base=next(x for x in prior['normal' if mode=='normal' else 'restricted'] if x['frame']==f)
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            row=dict(frame=f,total_ms=total,delta307_ms=total-base['total_ms'],gap_ms=total-1000/60,
                absolute_finish_ms=int(end[2])/1e9,frame_start_ms=int(end[2])/1e9-total,
                instructions=arm['instructions'],SPI_bytes=arm['SPI_bytes'],max_credit=max(int(x[2]) for x in es if x[0]=='credits'))
            assert row['max_credit']<=4
            if mode=='reference':assert total==base['total_ms'] and arm['instructions']==base['ARM_instructions']
            os=[x for x in obs if x['generation']==f-904]
            ready=next(x for x in os if x['name']=='next_step286' and x['result']==2)
            prep=[x for x in os if x['name']=='prepare289'];slices=[x for x in os if x['name']=='prepare_slice309']
            grant=next(x for x in es if x[:3]==['firstmiss305',str(f),'0'])
            first=next(x for x in es if x[:3]==['romplan305',str(f),'0'])
            rec=dict(mode=mode,frame=f,ready_ms=ready['end']['modeled_ns']/1e6,first_BG_plan_ms=int(first[-1])/1e9,first_BG_grant_ms=int(grant[-1])/1e9,
                ready_before_grant_ms=int(grant[-1])/1e9-ready['end']['modeled_ns']/1e6,
                final_prepare_instructions=sum(x['end']['instruction']-x['start']['instruction'] for x in prep),
                slices=len(slices),max_slice_instructions=max([x['end']['instruction']-x['start']['instruction'] for x in slices] or [0]),
                pregrant_slices=sum(x['end']['modeled_ns']<int(grant[-1])/1000 for x in slices),
                completed_ms=next((x['end']['modeled_ns']/1e6 for x in slices if x['prepared']==207),None))
            readiness.append(rec);rows.append(row)
        runs[mode]=dict(rows=rows,stack=r['ARM']['stack_observed'])
    assert loaded(d/'reference01/output.elf')==loaded(BASE/'probes/nes-ingress307/window03/output.elf')
    assert loaded(d/'window02/output.elf')==loaded(d/'normal01/output.elf')
    reference_rtl=js(BASE/'probes/nes-ingress307/window03/result.json')['rtl_hashes'];assert rtl==reference_rtl
    checks={}
    for tag in ('prepguard01','native01','supply01','wait01','armguard01','credit01','h2guard01','irqguard01'):
        x=js(d/tag/'result.json');assert x['passed'] and x['ELF_sha256']==sha(d/'window02/output.elf');checks[tag]=x
    for n in ('nes_prepare309.py','probe_nes_live309.py','guard_nes_prepare309.py'):pin(ROOT/'tools'/n)
    assert len(checks['prepguard01']['checks'])==24 and len(checks['native01']['frames'])==71
    size=(d/'window02/size287.log').read_text().splitlines()[-1].split()
    assert sha(d/'window02/nes_prepare309.py')==sha(ROOT/'tools/nes_prepare309.py')
    result=dict(stage=309,passed=True,selected=False,status='ARM_preparation_hidden_but_restricted_frame_regressed',runs=runs,readiness=readiness,checks=checks,whole_MAP_reused=prior['whole_MAP'],comb_deficit=2175,
        ARM_memory=dict(text=int(size[0]),bss=int(size[2]),observed_stack=runs['restricted']['stack']),
        new_MAP=False,RTL_identical307=True,metadata_bytes_identical=True,scope='CPI1/84MHz actual M4 plus same live RTL/IRQ/ROM and ordinary65816 trace; readiness interpolated from existing callbacks, not hardware timestamps',
        limitations=['Full ARM RUN, full live65816, whole71 live, FIT/STA and physical60fps remain unverified','ARM preparation only; queue/host/validator replacement is not implemented'],input_hashes=pins)
    pin(Path(__file__))
    (ROOT/'analysis/prepare309-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(runs=runs,readiness=readiness),indent=2))
if __name__=='__main__':main()
