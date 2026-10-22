# SPDX-License-Identifier: MIT
"""Paired ARM workset costs; only actually retimed frames get full schedule rows."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    b=a.base.resolve();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    old=js(ROOT/'analysis/joint287-verification.json')
    selected=['arm03','armguard01','rowguard01','workset01','irqguard01','h2guard01','test01','window01']
    r={t:js(b/t/'result.json') for t in selected};assert all(q['passed'] for q in r.values())
    assert len(r['arm03']['frames'])==71
    for n,h in r['arm03']['input_hashes'].items():assert sha(pin(Path(n)))==h,n
    for n,h in r['arm03']['generated_hashes'].items():assert sha(pin(b/'arm03'/n))==h,n
    for tag,count in [('armguard01',15),('rowguard01',5),('workset01',9),('h2guard01',8)]:assert len(r[tag]['checks'])==count
    for tag in ('armguard01','rowguard01','workset01'):assert r[tag]['ELF_sha256']==r['arm03']['generated_hashes']['planner.elf']
    for tag,script in [('armguard01','guard_nes_planner286.py'),('rowguard01','guard_nes_rows287.py'),('workset01','guard_nes_workset288.py'),('h2guard01','guard_nes_h2287.py')]:assert r[tag]['script_sha256']==sha(pin(ROOT/'tools'/script))
    assert r['irqguard01']['row_plan_exact'] and len(r['irqguard01']['row_preemption287'])==1
    assert r['h2guard01']['ELF_sha256']==r['test01']['ELF_sha256']
    assert sha(pin(b/'irqguard01/output.elf'))==r['test01']['ELF_sha256']
    prior={x['frame']:x for x in old['planner']};planner=[]
    for x in r['arm03']['frames']:
        f=x['frame'];new=x['postdecode_CPI1_ms'];before=prior[f]['new287_ms']
        planner.append(dict(frame=f,before_ms=before,after_ms=new,delta_ms=new-before,rows_reused=x['rows_reused287'],rows_full=x['rows_full287']))
    reference=js(BASE/'probes/nes-joint287/test06/result.json');schedules={}
    for tag,oldrows in [('test01',old['normal']),('window01',old['restricted_ROM'])]:
        q=b/tag;v=r[tag];assert v['frames']==3 and not v['full_RUN'] and not v['physical']
        assert v['rtl_hashes']==reference['rtl_hashes']
        for n,h in v['rtl_hashes'].items():assert sha(pin(q/n))==h
        for n in ('nes_planner288.py','probe_nes_planner288.py','probe_nes_live288.py'):assert v['input_hashes'][n]==sha(pin(ROOT/'tools'/n))==sha(pin(q/n))
        assert v['ELF_sha256']==sha(pin(q/'output.elf'))
        assert v['tb_sha256']==sha(pin(q/'joint266_tb.sv'))
        for p in q.iterdir():
            if p.suffix in ('.c','.h','.inc','.s','.ld'):pin(p)
        source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())}
        events=list(csv.reader(pin(q/'joint-events.csv').open()));previous={x['frame']:x for x in oldrows};rows=[];last=[0,0,0]
        for event in (e for e in events if e[0]=='frame_done'):
            f=int(event[1]);es=[e for e in events if int(e[1])==f];spi=[e for e in es if e[0]=='arm267'];wait=[e for e in es if e[0]=='wait284']
            counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,last)];last=counters
            now=js(q/f'arm{f}.json');then=js(BASE/'probes/nes-joint287'/('test06' if tag=='test01' else 'window01')/f'arm{f}.json')
            for op in (225,233):
                select=lambda z:[t['tx'] for t in z['transfers'] if t['tx'] and bytes.fromhex(t['tx'])[0]==op]
                assert select(now)==select(then),(tag,f,op)
            src=int(source[f]['total'])*45.454/1e6;out=int(event[3])/1e9;total=src+out
            rows.append(dict(frame=f,source_ms=src,output_ms=out,total_ms=total,before_ms=previous[f]['diagnostic_serial_ms'],delta_ms=total-previous[f]['diagnostic_serial_ms'],margin_ms=1000/60-total,
                E2=sum(int(e[2])==226 for e in spi),E9=sum(int(e[2])==233 for e in spi),IRQ_waits=len(wait),timer_fallbacks=sum(int(e[2])==0 for e in wait),tile_wait_cycles=inc[0],slot_wait_cycles=inc[1],core_priority_blocks=inc[2]))
        assert len(rows)==3;schedules[tag]=rows
    size=lambda p:list(map(int,re.search(r'\n\s*(\d+)\s+(\d+)\s+(\d+)',pin(p).read_text()).groups()))
    newsize=size(b/'test01/size287.log');oldsize=size(BASE/'probes/nes-joint287/test06/size287.log');assert newsize[2]-oldsize[2]==2048
    # RTL byte identity binds the existing whole MAP, not a fresh synthesis.
    area=old['area'];pin(BASE/'probes/nes-joint287/board01/output_files/board.map.summary')
    result=dict(passed=True,stage=288,selected=selected,planner=planner,normal=schedules['test01'],restricted=schedules['window01'],
        planner_improved=sum(x['delta_ms']<0 for x in planner),planner_regressed=sum(x['delta_ms']>0 for x in planner),
        ARM_size=dict(before=oldsize,after=newsize,delta=[x-y for x,y in zip(newsize,oldsize)],observed_stack=r['test01']['ARM']['stack_observed']),
        unchanged_RTL=True,new_MAP=False,area_reference='NES287 board01',whole_MAP=area['whole_MAP'],comb_deficit=area['deficit'],expanded_boundary_comb=area['expanded_boundary'],expanded_budget=area['expanded_budget'],
        adopted=False,normal71_retimed=False,full_RUN=False,physical=False,FIT=False,STA=False,
        input_hashes=pins,script_sha256=sha(Path(__file__)))
    for name,rows in [('planner',planner),('normal',result['normal']),('restricted',result['restricted'])]:
        with (d/f'{name}.csv').open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('passed','planner_improved','planner_regressed','normal','restricted','ARM_size','comb_deficit')}))


if __name__=='__main__':main()
