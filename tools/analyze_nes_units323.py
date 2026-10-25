# SPDX-License-Identifier: MIT
"""Bind actual M4/SPI, new65816 split trace, same-phase runs and whole Lite."""
import csv,json,re
from collections import Counter,defaultdict
from nes_delta231 import BASE,ROOT,sha

def main():
    d=BASE/'probes/nes-units323';pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    baseline=js(ROOT/'analysis/owner319-verification.json');runs={};comparisons={};aggregates={}
    for tag,old in [('fixed04','fixed02'),('window01','window01'),('normal01','normal01')]:
        q=d/tag;r=js(q/'result.json');assert r['passed'];rows=[]
        for n,h in r['rtl_hashes'].items():assert sha(q/n)==h;read(q/n)
        assert sha(q/'output.elf')==r['ELF_sha256'];pins[str(q/'output.elf')]=sha(q/'output.elf')
        assert sha(q/'joint266_tb.sv')==r['tb_sha256'];read(q/'joint266_tb.sv')
        for name in ('ordinary.sfc','bus.csv','timing.csv','capture.lua','packets.hex'):
            assert sha(q/('CPU-'+name))==sha(d/'cpu01'/name);read(d/'cpu01'/name) if name!='ordinary.sfc' else pins.update({str(d/'cpu01'/name):sha(d/'cpu01'/name)})
        events=list(csv.reader(read(q/'joint-events.csv').splitlines()))
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(q/'cycles.csv').splitlines())}
        for f in (905,906,907):
            e=[x for x in events if len(x)>1 and x[1]==str(f)]
            end=next(x for x in e if x[0]=='frame_done');start=next(x for x in e if x[0]=='start319')
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            bg=int(next(x for x in e if x[:3]==['romtile305',str(f),'0'])[-1])/1e9
            meta=int(next(x for x in e if x[:3]==['release312',str(f),'15'])[-1])/1e9
            finish=int(end[2])/1e9;total=source[f]+int(end[3])/1e9
            assert sum(int(x[3]) for x in e if x[0]=='arm267')==arm['SPI_bytes']
            row=dict(frame=f,start_ms=int(start[2])/1e9,start_ROM_cycle=int(start[3]),finish_ms=finish,total_ms=total,
                gap_ms=total-1000/60,first_BG_ms=bg,tail_ms=finish-bg,metadata_release_ms=meta,
                ARM_instructions=arm['instructions'],SPI_bytes=arm['SPI_bytes'],max_credit=max(int(x[2]) for x in e if x[0]=='credits'))
            assert row['max_credit']<=2;rows.append(row)
            transfers=js(q/f'arm{f}.json')['transfers'];ops=Counter();domains=Counter();commands=Counter();wire=Counter()
            for t in transfers:
                tx=bytes.fromhex(t['tx'])
                if tx:commands[tx[0]]+=1;wire[tx[0]]+=len(tx)
                if tx and tx[0]==0xe1:
                    assert len(tx)==int.from_bytes(tx[13:15],'little')+19
                    ops[tx[1]]+=1
                    if tx[1] in (2,4,5,7,8):
                        domain=tx[2];first=int.from_bytes(tx[11:13],'little');count=int.from_bytes(tx[15:17],'little')
                        assert count and first+count<={0:1024,1:128,3:32,4:544,5:1121,6:128,7:16}[domain]
                        domains[domain]+=1
            row['E1_ops']=dict(ops);row['unit_domains']=dict(domains)
            row['SPI_command_counts']=dict(commands);row['SPI_command_bytes']=dict(wire)
        runs[tag]=dict(rows=rows,SysTick=len(r['ARM']['IRQ_cases']),EXTI=len(r['ARM']['EXTI284']),stack=r['ARM']['stack_observed'])
        comparisons[tag]=[]
        for a,b in zip(rows,baseline['runs'][old]['rows']):
            if tag=='fixed04':assert a['start_ms']==b['start_ms'] and a['start_ROM_cycle']==b['start_ROM_cycle']
            comparisons[tag].append(dict(frame=a['frame'],start_delta_ms=a['start_ms']-b['start_ms'],total_delta_ms=a['total_ms']-b['total_ms'],finish_delta_ms=a['finish_ms']-b['finish_ms'],BG_delta_ms=a['first_BG_ms']-b['first_BG_ms'],ARM_delta=a['ARM_instructions']-b['ARM_instructions'],SPI_delta=a['SPI_bytes']-b['SPI_bytes']))
        aggregates[tag]=dict(sum_frame_duration_delta_ms=sum(x['total_delta_ms'] for x in comparisons[tag]),last_finish_delta_ms=comparisons[tag][-1]['finish_delta_ms'])
    board=js(d/'board02/result.json');assert board['passed']
    for n,h in board['actual_inputs'].items():assert sha(d/'board02'/n)==h;pins[str(d/'board02'/n)]=h
    whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',board['summary'])[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    log=read(d/'board02/map.log');latches=re.findall(r'Warning \(10240\):[^\r\n]+',log)
    assert all('cache_index141' in x for x in latches) and 'Warning (10034)' not in log
    def nodes(report):
        out={}
        for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
            c=[v.strip() for v in line.split(';')]
            if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):out[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
        return out
    new=nodes(read(d/'board02/output_files/board.map.rpt'));old=nodes(read(BASE/'probes/nes-owner319/board01/output_files/board.map.rpt'))
    assert sum(new.values())==whole['comb']
    deltas={k:new.get(k,0)-old.get(k,0) for k in set(new)|set(old)};deltas={k:v for k,v in sorted(deltas.items()) if v}
    # The wholeboard wrapper exports tile_closed267; this preexisting port-only difference is explicit.
    a=read(d/'board02/nes_mux260.sv');b=read(d/'fixed04/nes_mux260.sv')
    a=a.replace('output wire tile_closed267,','').replace('assign tile_closed267=tiles_closed;','')
    b=b.replace('output wire tile_closed267,','').replace('assign tile_closed267=tiles_closed;','')
    assert a.split()==b.split()
    for tag in ('window01','normal01'):
        for n in js(d/'fixed04/result.json')['rtl_hashes']:assert sha(d/tag/n)==sha(d/'fixed04'/n)
    guards=js(d/'guards01/result.json');assert guards['passed'] and len(guards['cases'])==11
    assert guards['ELF_sha256']==sha(d/'fixed04/output.elf')
    assert guards['tb_sha256']==sha(d/'guards01/joint266_tb.sv');read(d/'guards01/joint266_tb.sv')
    for c in guards['cases']:
        p=d/'guards01'/f"case{c['case']}"/'vsim.log';assert sha(p)==c['log_sha256'];read(p)
    for n,h in guards['rtl_hashes'].items():assert sha(d/'fixed04'/n)==h
    cpu=js(d/'cpu01/result.json');assert cpu['CPU']['commands']==546 and cpu['CPU']['output_bytes']==128041
    totals=[]
    for q in (BASE/'probes/nes-executor313/cpu03',d/'cpu01'):
        t=defaultdict(lambda:[0,0,0])
        for r in csv.DictReader(read(q/'timing.csv').splitlines()):
            x=t[int(r['serial'])];x[0]+=1;x[1]+=int(r['total_clocks']);x[2]+=int(r['output_bytes'])
        totals.append(t)
    cpu_delta={s:[totals[1][s][i]-totals[0][s][i] for i in range(3)] for s in (1,2,3)}
    for n in ('nes_units323.py','probe_nes_units323.py','map_nes_units323.py','guard_nes_units323.py','probe_nes_cpu323.py'):read(ROOT/'tools'/n)
    sizes={}
    for label,q in [('319',BASE/'probes/nes-owner319/fixed02'),('323',d/'fixed04')]:
        words=read(q/'size287.log').splitlines()[1].split();sizes[label]=dict(text=int(words[0]),data=int(words[1]),bss=int(words[2]))
    out=dict(stage=323,passed=True,selected=False,runs=runs,comparisons=comparisons,aggregates=aggregates,whole_MAP=whole,ARM_sizes=sizes,
        delta319={k:whole[k]-baseline['whole_MAP'][k] for k in whole},own_comb_delta=deltas,
        comb_deficit=whole['comb']-15408,remaining_ms=runs['window01']['rows'][-1]['gap_ms'],
        baseline_retained_gap_ms=baseline['remaining_ms'],baseline_retained_comb_deficit=2416,
        continuous_duration_is_not_phase_matched_gain=True,
        CPU_delta_command_clock_bytes=cpu_delta,CPU=cpu['CPU'],guards=guards,latch_warnings=latches,
        physical_60fps_proven=False,FIT=False,STA=False,input_hashes=pins)
    out['input_hashes'][str(ROOT/'tools/analyze_nes_units323.py')]=sha(ROOT/'tools/analyze_nes_units323.py')
    (ROOT/'analysis/units323-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:out[k] for k in ('comparisons','whole_MAP','delta319','comb_deficit','remaining_ms','CPU_delta_command_clock_bytes')},indent=2))
if __name__=='__main__':main()
