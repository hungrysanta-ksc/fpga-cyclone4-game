# SPDX-License-Identifier: MIT
"""Bind new ARM schedules to unchanged, previously mapped and guarded RTL300."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from probe_nes_arm264 import ELFFile


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);a=ap.parse_args();b=a.base.resolve();pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    def loaded(p):
        with pin(p).open('rb') as fp:return [(x['p_vaddr'],x['p_memsz'],x.data()) for x in ELFFile(fp).iter_segments() if x['p_type']=='PT_LOAD']
    old=js(ROOT/'analysis/arch300-verification.json');prior=js(ROOT/'analysis/joint298-verification.json')
    reference=js(BASE/'probes/nes-arch300/test03/result.json');out={};services=[]
    for tag,mode,oldtag in [('test05','normal','test04'),('window03','restricted','window04')]:
        q=b/tag;r=js(q/'result.json');assert r['passed']
        assert r['rtl_hashes']==reference['rtl_hashes']
        for n,h in r['rtl_hashes'].items():assert sha(pin(q/n))==h
        assert sha(pin(q/'joint266_tb.sv'))==r['tb_sha256']
        for p in q.iterdir():
            if p.suffix in ('.c','.h','.inc','.s','.ld','.py'):pin(p)
        assert loaded(q/'output.elf')==loaded(b/'test05/output.elf')
        events=list(csv.reader(pin(q/'joint-events.csv').open()));source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(pin(q/'cycles.csv').open())};rows=[];last=[0,0,0]
        for e in (x for x in events if x[0]=='frame_done'):
            f=int(e[1]);es=[x for x in events if int(x[1])==f];arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            t=js(q/f'arm{f}.json');p=js(BASE/f'probes/nes-joint298/{oldtag}/arm{f}.json')
            for cmd in ('e1','e9'):
                assert [x['tx'] for x in t['transfers'] if x['tx'].startswith(cmd)]==[x['tx'] for x in p['transfers'] if x['tx'].startswith(cmd)],(f,cmd)
            credit=[int(x[2]) for x in es if x[0]=='credits'];assert credit and max(credit)<=4
            assert sum(x[0]=='checkpoint287' for x in es)==sum(x.get('checkpoint287',False) for x in t['transfers'])
            receipts=sum(x[0]=='receipt' for x in es);assert receipts==sum(x[0]=='consume293' and x[2]=='2' for x in es)
            counters=list(map(int,next(x for x in es if x[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,last)];last=counters
            total=source[f]+int(e[3])/1e9
            v298=next(x['total_ms'] for x in prior[mode] if x['frame']==f);v300=next(x['total_ms'] for x in old[mode] if x['frame']==f)
            rows.append(dict(frame=f,total_ms=total,source_ms=source[f],output_ms=int(e[3])/1e9,prior298_ms=v298,prior300_ms=v300,delta298_ms=total-v298,delta300_ms=total-v300,margin_ms=1000/60-total,ARM_instructions=arm['instructions'],SPI_bytes=arm['SPI_bytes'],max_credit=max(credit),map_receipts=receipts,E2=sum(x[0]=='arm267' and int(x[2])==226 for x in es),timer_fallbacks=sum(x[0]=='wait284' and int(x[2])==0 for x in es),slot_wait_cycles=inc[1],core_priority_blocks=inc[2]))
            changed=[x for x in arm['service296'] if x.get('end_instruction') is not None]
            useful=[x for x in changed if x['end_instruction']-x['instruction']>100]
            rows[-1].update(checkpoints=sum(x[0]=='checkpoint287' for x in es),service_calls=len(changed),BG_prefix_before_first_slice=(useful[0]['plan_at']>=useful[0]['before_size']) if useful else None,max_service_instructions=max((x['end_instruction']-x['instruction'] for x in changed),default=0))
            for x in changed:
                services.append(dict(mode=mode,frame=f,**x))
        assert len(rows)==3;out[mode]=rows
    checks={}
    for tag in ('native04','guards04','credit03','h2guard03','irqguard03'):
        z=js(b/tag/'result.json');assert z['passed'] and z['ELF_sha256']==sha(b/'test05/output.elf');checks[tag]=dict(frames=len(z.get('frames',[])),checks=z.get('checks',z.get('cases',z.get('guards'))),STOP_checks=z.get('STOP_checks'),IRQ_checks=z.get('IRQ_checks'))
    assert js(b/'guards04/result.json')['script_sha256']==sha(pin(ROOT/'tools/guard_nes_slice302.py'))
    assert js(b/'credit03/result.json')['script_sha256']==sha(pin(ROOT/'tools/guard_nes_credit302c.py'))
    # No new RTL or synthesis. Revalidate archived whole-MAP input hashes.
    board=js(BASE/'probes/nes-arch300/board01/result.json');assert board['passed'] and not board['undriven']
    for n,h in board['actual_inputs'].items():assert sha(pin(BASE/'probes/nes-arch300/board01'/n))==h
    guards=js(BASE/'probes/nes-arch300/guards01/result.json');assert guards['passed'] and len(guards['guards'])==44
    for n in guards['guards']:assert f'PASS HOST278 GNEG={n}' in pin(BASE/'probes/nes-arch300/guards01'/f'guard{n}.log').read_text()
    for n,h in guards['rtl_hashes'].items():
        assert sha(pin(BASE/'probes/nes-arch300/guards01'/n))==h
        if n in reference['rtl_hashes']:assert h==reference['rtl_hashes'][n]
    for n in ('nes_slice302.py','probe_nes_live302.py','nes_slice302b.py','probe_nes_live302b.py','nes_slice302c.py','probe_nes_live302c.py'):
        assert sha(pin(ROOT/'tools'/n))==sha(pin(b/'test05'/n))==sha(pin(b/'window03'/n))
    size=pin(b/'test05/size287.log').read_text().splitlines()[-1].split();memory=dict(text=int(size[0]),data=int(size[1]),bss=int(size[2]))
    result=dict(passed=True,stage=302,**out,service_events=services,ARM_memory=memory,ARM_checks=checks,whole_MAP=old['whole_MAP'],regions=old['regions'],comb_deficit=old['comb_deficit'],fixed_boundary=old['fixed_boundary'],outside=old['outside'],fixed_budget=old['fixed_budget'],new_MAP=False,MAP_provenance='unchanged RTL300; existing whole Quartus Lite MAP, hashes verified',fresh_live_frames=6,reused_RTL_guards=44,new_RTL=False,FIT=False,STA=False,full_RUN=False,physical=False,input_hashes=pins,script_sha256=sha(Path(__file__)))
    intermediate=js(b/'initial-slice302-verification.json')
    postwait=js(b/'postwait-slice302-verification.json')
    result.update(intermediate_postwait={k:postwait[k] for k in ('normal','restricted')},variant='302c checked phase / pre-WFI IRQ-bounded wait fill',intermediate_single_slice={k:intermediate[k] for k in ('normal','restricted')},slice_guards=js(b/'guards04/result.json'))
    (ROOT/'analysis/slice302-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    for mode,rows in out.items():
        with (ROOT/f'analysis/slice302-{mode}.csv').open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print(json.dumps({k:result[k] for k in ('normal','restricted','ARM_memory','comb_deficit','new_MAP')},indent=2))


if __name__=='__main__':main()
