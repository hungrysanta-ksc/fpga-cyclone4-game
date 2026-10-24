# SPDX-License-Identifier: MIT
"""Bind fixed-phase A/B, continuous ARM/IRQ schedules and whole Lite cost."""
import csv,json,re
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile

def main():
    d=BASE/'probes/nes-owner319';pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    previous=js(ROOT/'analysis/metadata317-verification.json');runs={}
    for tag in ('fixed02','reference01','window01','normalref01','normal01'):
        q=d/tag;r=js(q/'result.json');assert r['passed']
        for n,h in r['rtl_hashes'].items():assert sha(q/n)==h;read(q/n)
        assert sha(q/'output.elf')==r['ELF_sha256']
        pins[str(q/'output.elf')]=sha(q/'output.elf')
        pins[str(q/'producer263.dll')]=sha(q/'producer263.dll')
        for name in ('ordinary.sfc','bus.csv','timing.csv','capture.lua','packets.hex'):
            actual=q/('CPU-'+name);expected=BASE/'probes/nes-executor313/cpu03'/name
            assert sha(actual)==sha(expected);pins[str(actual)]=sha(actual);pins[str(expected)]=sha(expected)
        assert sha(q/'joint266_tb.sv')==r['tb_sha256'];read(q/'joint266_tb.sv')
        ev=list(csv.reader(read(q/'joint-events.csv').splitlines()))
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(q/'cycles.csv').splitlines())}
        rows=[]
        for f in (905,906,907):
            e=[x for x in ev if len(x)>1 and x[1]==str(f)]
            end=next(x for x in e if x[0]=='frame_done');start=next(x for x in e if x[0]=='start319')
            bg=next(x for x in e if x[:3]==['romtile305',str(f),'0'])
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            finish=int(end[2])/1e9;total=source[f]+int(end[3])/1e9
            assert sum(int(x[3]) for x in e if x[0]=='arm267')==arm['SPI_bytes']
            rows.append(dict(frame=f,start_ms=int(start[2])/1e9,start_ROM_cycle=int(start[3]),finish_ms=finish,
                total_ms=total,gap_ms=total-1000/60,actual_start_to_finish_ms=finish-int(start[2])/1e9,
                first_BG_ms=int(bg[-1])/1e9,tail_ms=finish-int(bg[-1])/1e9,
                ARM_instructions=arm['instructions'],SPI_bytes=arm['SPI_bytes'],
                max_credit=max(int(x[2]) for x in e if x[0]=='credits')))
            assert rows[-1]['max_credit']<=2
        runs[tag]=dict(rows=rows,ELF=r['ELF_sha256'],SysTick=len(r['ARM']['IRQ_cases']),EXTI=len(r['ARM']['EXTI284']),stack=r['ARM']['stack_observed'])
    # ELF container metadata can differ across build paths; compare every
    # loadable byte, virtual address and zero-fill extent, as in stage317.
    images=[]
    for q in [d/tag for tag in runs]+[BASE/'probes/nes-metadata317/arm01']:
        pins[str(q/'output.elf')]=sha(q/'output.elf')
        with (q/'output.elf').open('rb') as f:
            images.append([(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD'])
    assert all(v==images[0] for v in images)
    comparisons={}
    for label,ref,candidate in [('fixed','reference01','fixed02'),('normal','normalref01','normal01')]:
        pairs=[]
        for b,a in zip(runs[ref]['rows'],runs[candidate]['rows']):
            if label=='fixed':assert a['start_ms']==b['start_ms'] and a['start_ROM_cycle']==b['start_ROM_cycle']
            pairs.append(dict(frame=a['frame'],delta_ms=a['total_ms']-b['total_ms'],finish_delta_ms=a['finish_ms']-b['finish_ms'],
                BG_delta_ms=a['first_BG_ms']-b['first_BG_ms'],ARM_delta=a['ARM_instructions']-b['ARM_instructions'],SPI_delta=a['SPI_bytes']-b['SPI_bytes']))
        comparisons[label]=pairs
    comparisons['continuous']=[dict(frame=a['frame'],delta_ms=a['total_ms']-b['total_ms'],
        finish_delta_ms=a['finish_ms']-b['finish_ms']) for b,a in zip(previous['runs']['arm01']['rows'],runs['window01']['rows'])]
    board=js(d/'board01/result.json');assert board['passed']
    for n,h in board['actual_inputs'].items():assert sha(d/'board01'/n)==h;pins[str(d/'board01'/n)]=h
    summary=board['summary'];whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',summary)[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    baseline=js(ROOT/'analysis/response315-verification.json')['whole_MAP']
    report=read(d/'board01/output_files/board.map.rpt');maplog=read(d/'board01/map.log')
    for entity in ('nes_core257:encoder','nes_output260:flow','nes_validator278:validator','nes_plan_batch206:transport'):
        assert entity+'|state' in report
    latches=re.findall(r'Warning \(10240\):[^\r\n]+',maplog)
    assert all('cache_index141' in x for x in latches) and 'Warning (10034)' not in maplog
    def own(report):
        nodes={}
        for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
            c=[v.strip() for v in line.split(';')]
            if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):
                nodes[c[10]]=dict(comb=int(re.search(r'\((\d+)\)',c[2])[1]),FF=int(re.search(r'\((\d+)\)',c[3])[1]))
        return nodes
    own_new=own(report);own_old=own(read(BASE/'probes/nes-response315/board01/output_files/board.map.rpt'))
    assert sum(v['comb'] for v in own_new.values())==whole['comb']
    own_delta={k:{metric:own_new.get(k,{}).get(metric,0)-own_old.get(k,{}).get(metric,0) for metric in ('comb','FF')}
               for k in set(own_new)|set(own_old)}
    own_delta={k:v for k,v in sorted(own_delta.items()) if any(v.values())}
    assert sum(v['comb'] for v in own_delta.values())==whole['comb']-baseline['comb']
    def region(nodes):
        suffixes=('nes_output260:flow','nes_validator278:validator','nes_queue260:queue','nes_spi270:spi_front270',
                  'nes_core257:encoder','nes_transport257:transport','nes_plan_path267:retained_plan267',
                  'nes_plan_batch206:transport','nes_plan_spi200:endpoint')
        roots={s:next(k for k in nodes if k.endswith(s)) for s in suffixes}
        return sum(v['comb'] for k,v in nodes.items() if k in roots.values() or
                   any(k.startswith(roots[s]+'|') for s in ('nes_transport257:transport','nes_plan_batch206:transport')))
    old_region=region(own_old);new_region=region(own_new);assert old_region==6717
    for n in ('nes_queue260.sv','nes_plan_batch206.sv','nes_plan_spi200.sv','nes_core257.sv','nes_transport257.sv','nes_spi270.sv','nes_validator278.sv'):
        assert (d/'board01'/n).read_text().split()==(d/'fixed02'/n).read_text().split(),n
        for tag in ('window01','normal01'):assert sha(d/tag/n)==sha(d/'fixed02'/n)
    guards=js(d/'guards04/result.json');assert guards['passed'] and [x['case'] for x in guards['cases']]==[5,6,7]
    for n,h in guards['rtl_hashes'].items():
        assert h==sha(d/'fixed02'/n)==sha(d/'guards03'/n)==sha(d/'guards04'/n)
        read(d/'guards03'/n);read(d/'guards04'/n)
    assert guards['tb_sha256']==sha(d/'guards04/joint266_tb.sv');read(d/'guards04/joint266_tb.sv');read(d/'guards03/joint266_tb.sv')
    for case in guards['cases']:
        p=d/'guards04'/f"case{case['case']}"/'vsim.log'
        assert sha(p)==case['log_sha256'];read(p)
        case['run']='guards04'
    passed_prior=[]
    for case in range(1,5):
        p=d/'guards03'/f'case{case}'/'vsim.log';raw=read(p)
        assert f'PASS OWNER319 GUARD={case} fault=4' in raw and 'Errors: 0' in raw and '** Fatal:' not in raw
        passed_prior.append(dict(case=case,passed=True,run='guards03',log_sha256=sha(p)))
    guards['cases']=passed_prior+guards['cases'];guards['scope']='guards03 cases1..4 plus guards04 cases5..7; guards03 case5 harness early-exit preserved'
    for n in ('nes_owner319.py','probe_nes_owner319.py','map_nes_owner319.py','guard_nes_owner319.py','analyze_nes_owner319.py'):read(ROOT/'tools'/n)
    out=dict(stage=319,passed=True,selected=False,identical_ARM_PT_LOAD=True,runs=runs,comparisons=comparisons,whole_MAP=whole,
        delta315={k:whole[k]-baseline[k] for k in whole},own_resource_delta=own_delta,comb_deficit=whole['comb']-15408,
        remaining_ms=runs['window01']['rows'][-1]['gap_ms'],guards=guards,
        regional_comb=dict(baseline=old_region,candidate=new_region,delta=new_region-old_region,
            outside_delta=whole['comb']-baseline['comb']-(new_region-old_region)),latch_warnings=latches,
        scope='Implemented host admission, source record termination and source/plan cursor ownership; not a replacement of all host/validator/source/plan FSMs.',
        limitations=['Actual M4 instructions CPI1/84MHz and IRQ model, not hardware cycles.',
         'Fixed absolute capture/source start and ROM phase paired separately from continuous frames.',
         'RAM banks/ports and independent validator unchanged; source/plan decode FSMs still separate.',
         'Ordinary 65816 bus trace replayed; tile/map/VBlank partly modeled; no whole71/fullRUN/FITSTA/physical60fps.'],input_hashes=pins)
    (ROOT/'analysis/owner319-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
    print(json.dumps({k:out[k] for k in ('comparisons','whole_MAP','delta315','comb_deficit','remaining_ms')},indent=2))
if __name__=='__main__':main()
