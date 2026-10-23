# SPDX-License-Identifier: MIT
"""Bind passive M4 observations, split candidate schedules and whole Lite MAP."""
import json,csv,re
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile

def main():
    d=BASE/'probes/nes-metadata317';pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    base=js(ROOT/'analysis/response315-verification.json');runs={}
    for tag,mode in [('observe02','restricted'),('arm01','restricted'),('window01','restricted'),('normal01','normal')]:
        q=d/tag;r=js(q/'result.json');assert r['passed']
        for n,h in r['rtl_hashes'].items():assert sha(pin(q/n))==h
        assert sha(pin(q/'output.elf'))==r['ELF_sha256']
        assert sha(pin(q/'joint266_tb.sv'))==r['tb_sha256']
        assert all(x['pending']<2 for x in js(q/'issue307.json'))
        for n in ('ordinary.sfc','bus.csv','timing.csv','capture.lua','packets.hex'):
            assert sha(pin(q/('CPU-'+n)))==sha(pin(BASE/'probes/nes-executor313/cpu03'/n))
        events=list(csv.reader(pin(q/'joint-events.csv').open()))
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(pin(q/'cycles.csv').open())}
        marks=js(q/'metadata317.json');rows=[]
        for f in (905,906,907):
            prior=next(x for x in base['runs'][mode]['rows'] if x['frame']==f)
            es=[x for x in events if len(x)>1 and x[1]==str(f)]
            end=next(x for x in es if x[0]=='frame_done');finish=int(end[2])/1e9
            total=source[f]+int(end[3])/1e9;start=finish-total
            bg=int(next(x for x in es if x[:3]==['romtile305',str(f),'0'])[-1])/1e9
            consume=max(int(x[-1])/1e9 for x in es if x[0]=='consume293')
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            tx=[x for x in es if x[0]=='arm267'];assert sum(int(x[3]) for x in tx)==arm['SPI_bytes']
            local=[x for x in marks if x['end']['generation']==f-904]
            ready=min(x['end']['modeled_ns']/1e6 for x in local if x['name']=='next_step286' and x['result']==2)
            preparation=[dict(name=x['name'],start_ms=x['start']['modeled_ns']/1e6,end_ms=x['end']['modeled_ns']/1e6,
                instructions=x['end']['instruction']-x['start']['instruction'],result=x['result'],pending=x['start']['pending'],
                IRQ_level=x['start']['IRQ_level'],plan_at=x['start']['plan_at'],plan_bytes=x['start']['plan_bytes'])
                for x in local if x['name'] in ('prepare289','prepare_slice309','issue_metadata317')]
            a=js(q/f'arm{f}.json');req=[x for x in a['transfers'] if x['tx'].startswith('e10f')];assert len(req)==1
            rows.append(dict(frame=f,total_ms=total,gap_ms=total-1000/60,delta315_ms=total-prior['total_ms'],
                start_ms=start,finish_ms=finish,finish_delta315_ms=finish-prior['finish_ms'],
                BG_ms=bg,tail_ms=finish-bg,tail_delta315_ms=finish-bg-prior['after_BG_ms'],
                last_consume_ms=consume,planner_ready_ms=ready,ready_before_BG_ms=bg-ready,
                requirements_tx_end_ms=req[0]['RTL_ns']/1e6,requirements_before_BG_ms=bg-req[0]['RTL_ns']/1e6,
                preparation=preparation,ARM_instructions=arm['instructions'],ARM_delta315=arm['instructions']-prior['ARM_instructions'],
                SPI_bytes=arm['SPI_bytes'],SPI_delta315=arm['SPI_bytes']-prior['SPI_bytes'],
                responses={hex(c):dict(count=sum(int(x[2])==c for x in tx),wire_bytes=sum(int(x[3]) for x in tx if int(x[2])==c)) for c in (0xe0,0xe2,0xe9)},
                max_credit=max(int(x[2]) for x in es if x[0]=='credits')))
            assert rows[-1]['max_credit']<=2
            if tag in ('arm01','window01') and f==907:assert ready<=req[0]['RTL_ns']/1e6<bg
            if tag=='observe02':assert abs(rows[-1]['delta315_ms'])<1e-9 and rows[-1]['ARM_delta315']==0 and rows[-1]['SPI_delta315']==0
        size=list(map(int,pin(q/'size287.log').read_text().splitlines()[1].split()[:3]))
        runs[tag]=dict(mode=mode,rows=rows,aggregate_delta315_ms=sum(x['delta315_ms'] for x in rows),
            ARM_size=dict(text=size[0],data=size[1],bss=size[2]),stack=r['ARM']['stack_observed'],
            SysTick_bodies=len(r['ARM']['IRQ_cases']),SysTick_instructions=sum(x['instructions'] for x in r['ARM']['IRQ_cases']),
            EXTI_entries=len(r['ARM']['EXTI284']),EXTI_entry_exit_cycles=r['ARM']['IRQ_entry_exit_cycles'])
    board=js(d/'board01/result.json');assert board['passed']
    for n,h in board['actual_inputs'].items():assert sha(pin(d/'board01'/n))==h
    def metric(label):return int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',board['summary'])[1].replace(',',''))
    whole={k:metric(v) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    def norm(s):return s.replace(' output wire tile_closed267,\n','').replace('reg tiles_closed;assign tile_closed267=tiles_closed;','reg tiles_closed;')
    for n in ('nes_mux260.sv','nes_validator278.sv','nes_queue260.sv','nes_spi270.sv'):
        baseline=pin(BASE/'probes/nes-response315/window01'/n).read_text()
        for tag in ('observe02','arm01'):assert pin(d/tag/n).read_text()==baseline,(tag,n)
        final=pin(d/'window01'/n).read_text()
        assert norm(pin(d/'board01'/n).read_text())==final
        for tag in ('normal01','guards01','terminal01'):assert pin(d/tag/n).read_text()==final,(tag,n)
    for n in ('nes_queue260.sv','nes_spi270.sv','nes_plan_spi200.sv','nes_plan_batch206.sv'):
        ref=sha(pin(BASE/'probes/nes-response315/board01'/n))
        for tag in ('board01','arm01','window01','normal01'):assert sha(pin(d/tag/n))==ref,(tag,n)
    for tag in ('guards01','terminal01'):
        guard=js(d/tag/'result.json');assert guard['passed'] and guard['positive_control317']
    armguards=js(d/'armguards01/result.json');assert armguards['passed']
    segments=[]
    for q in (BASE/'probes/nes-response315/window01',d/'observe02'):
        with pin(q/'output.elf').open('rb') as f:segments.append([(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD'])
    assert segments[0]==segments[1]
    candidates=[]
    for tag in ('arm01','window01','normal01'):
        with (d/tag/'output.elf').open('rb') as f:candidates.append([(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD'])
    assert candidates[0]==candidates[1]==candidates[2]
    report=pin(d/'board01/output_files/board.map.rpt').read_text()
    assert '|nes_output260:flow|state ' in report
    assert '|nes_validator278:validator|state ' in report
    result=dict(stage=317,passed=True,selected=False,runs=runs,whole_MAP=whole,
        delta315={k:whole[k]-base['whole_MAP'][k] for k in whole},comb_deficit=whole['comb']-15408,
        unchanged_baseline_PT_LOAD=True,ARM_guards=armguards,
        limitations=base['limits']+['Passive modeled event time equals RTL checkpoint plus pending CPI1/84MHz instructions; not hardware cycle measurement.',
            'Joint terminal controller has a measured area regression; no adoption/FIT/STA.'],input_hashes=pins)
    for n in ('nes_metadata317.py','nes_joint317.py','probe_nes_live317.py','probe_nes_candidate317.py','guard_nes_joint317.py','guard_nes_metadata317.py','map_nes_joint317.py','analyze_nes_metadata317.py'):pin(ROOT/'tools'/n)
    (ROOT/'analysis/metadata317-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({k:result[k] for k in ('whole_MAP','delta315','comb_deficit')},indent=2))
    for tag,x in runs.items():print(tag,x['aggregate_delta315_ms'],x['ARM_size'],x['rows'][-1])
if __name__=='__main__':main()
