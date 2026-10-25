# SPDX-License-Identifier: MIT
"""Bind actual321 execution, paired319 schedules, guards and whole Lite MAP."""
import csv,json,re
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile

def main():
    d=BASE/'probes/nes-execute321';pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    baseline=js(ROOT/'analysis/owner319-verification.json');runs={};images=[]
    for tag in ('fixed05','window01','normal01'):
        q=d/tag;r=js(q/'result.json');assert r['passed']
        for n,h in r['rtl_hashes'].items():assert sha(q/n)==h;read(q/n)
        assert sha(q/'joint266_tb.sv')==r['tb_sha256'];read(q/'joint266_tb.sv')
        assert sha(q/'output.elf')==r['ELF_sha256'];pins[str(q/'output.elf')]=sha(q/'output.elf')
        with (q/'output.elf').open('rb') as f:images.append([(x['p_vaddr'],x['p_memsz'],x.data()) for x in ELFFile(f).iter_segments() if x['p_type']=='PT_LOAD'])
        for n in ('ordinary.sfc','bus.csv','timing.csv','capture.lua','packets.hex'):
            p=q/('CPU-'+n);ref=BASE/'probes/nes-executor313/cpu03'/n
            assert sha(p)==sha(ref);pins[str(p)]=sha(p);pins[str(ref)]=sha(ref)
        ev=list(csv.reader(read(q/'joint-events.csv').splitlines()))
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(q/'cycles.csv').splitlines())}
        rows=[];previous_counts=[0]*7
        for f in (905,906,907):
            e=[x for x in ev if len(x)>1 and x[1]==str(f)]
            end=next(x for x in e if x[0]=='frame_done');start=next(x for x in e if x[0]=='start319')
            bg=next(x for x in e if x[:3]==['romtile305',str(f),'0'])
            counters=next(x for x in e if x[0]=='execute321')
            cumulative=list(map(int,counters[2:]));counts=[a-b for a,b in zip(cumulative,previous_counts)]
            assert all(x>=0 for x in counts);previous_counts=cumulative
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            assert sum(int(x[3]) for x in e if x[0]=='arm267')==arm['SPI_bytes']
            finish=int(end[2])/1e9;total=source[f]+int(end[3])/1e9
            rows.append(dict(frame=f,start_ms=int(start[2])/1e9,start_ROM_cycle=int(start[3]),finish_ms=finish,total_ms=total,
                gap_ms=total-1000/60,first_BG_ms=int(bg[-1])/1e9,tail_ms=finish-int(bg[-1])/1e9,
                metadata_release_ms=int(next(x for x in e if x[:3]==['release312',str(f),'15'])[-1])/1e9,
                last_consume_ms=max(int(x[-1]) for x in e if x[0]=='consume293')/1e9,
                ARM_instructions=arm['instructions'],SPI_bytes=arm['SPI_bytes'],max_credit=max(int(x[2]) for x in e if x[0]=='credits'),
                execution_counts=dict(zip(('phase_cycles','RAM_reads','RAM_commits','queue_reads','OPEN_wait','PUT_wait','receipt_wait'),counts)),cumulative_counts=cumulative))
            assert rows[-1]['max_credit']<=2
        runs[tag]=dict(rows=rows,SysTick=len(r['ARM']['IRQ_cases']),EXTI=len(r['ARM']['EXTI284']),stack=r['ARM']['stack_observed'])
    warm=runs['window01']['rows'][-1]
    assert warm['metadata_release_ms']<warm['first_BG_ms']
    q=BASE/'probes/nes-metadata317/arm01/output.elf';pins[str(q)]=sha(q)
    with q.open('rb') as f:images.append([(x['p_vaddr'],x['p_memsz'],x.data()) for x in ELFFile(f).iter_segments() if x['p_type']=='PT_LOAD'])
    assert all(x==images[0] for x in images)
    comparisons={}
    for tag,ref in [('fixed05','fixed02'),('window01','window01'),('normal01','normal01')]:
        rows=[]
        for a,b in zip(runs[tag]['rows'],baseline['runs'][ref]['rows']):
            if tag=='fixed05':assert a['start_ms']==b['start_ms'] and a['start_ROM_cycle']==b['start_ROM_cycle']
            rows.append(dict(frame=a['frame'],delta_ms=a['total_ms']-b['total_ms'],finish_delta_ms=a['finish_ms']-b['finish_ms'],
                BG_delta_ms=a['first_BG_ms']-b['first_BG_ms'],ARM_delta=a['ARM_instructions']-b['ARM_instructions'],SPI_delta=a['SPI_bytes']-b['SPI_bytes']))
        comparisons[tag]=rows
    board=js(d/'board02/result.json');assert board['passed']
    for n,h in board['actual_inputs'].items():assert sha(d/'board02'/n)==h;pins[str(d/'board02'/n)]=h
    whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',board['summary'])[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    report=read(d/'board02/output_files/board.map.rpt');log=read(d/'board02/map.log')
    for fsm in ('nes_output260:flow|state','nes_core257:encoder|state','nes_validator278:validator|control_state321'):
        assert fsm in report
    assert 'nes_plan_batch206:transport|state' not in report
    latches=re.findall(r'Warning \(10240\):[^\r\n]+',log)
    assert all('cache_index141' in x for x in latches) and 'Warning (10034)' not in log
    def own(raw):
        nodes={}
        for line in raw.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
            c=[v.strip() for v in line.split(';')]
            if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):
                nodes[c[10]]=dict(comb=int(re.search(r'\((\d+)\)',c[2])[1]),FF=int(re.search(r'\((\d+)\)',c[3])[1]))
        return nodes
    nodes=own(report);old=own(read(BASE/'probes/nes-owner319/board01/output_files/board.map.rpt'))
    assert sum(x['comb'] for x in nodes.values())==whole['comb']
    suffixes=('nes_output260:flow','nes_validator278:validator','nes_queue260:queue','nes_spi270:spi_front270','nes_core257:encoder','nes_transport257:transport','nes_plan_path267:retained_plan267','nes_plan_batch206:transport','nes_plan_spi200:endpoint')
    regional={}
    for suffix in suffixes:
        root=next(n for n in nodes if n.endswith(suffix));children=suffix in ('nes_transport257:transport','nes_plan_batch206:transport')
        def total(ns):return {m:sum(v[m] for n,v in ns.items() if n==root or (children and n.startswith(root+'|'))) for m in ('comb','FF')}
        regional[suffix]=dict(before=total(old),after=total(nodes))
    for n in ('nes_core257.sv','nes_validator278.sv','nes_mux260.sv','nes_plan_batch206.sv'):
        actual=(d/'board02'/n).read_text()
        if n=='nes_mux260.sv':
            # Existing board-only export; the TB observes the same register
            # hierarchically. No logic or control difference is normalized.
            for alias in (' output wire tile_closed267,','assign tile_closed267=tiles_closed;'):
                assert actual.count(alias)==1
                assert alias in (BASE/'probes/nes-owner319/board01'/n).read_text()
                actual=actual.replace(alias,'')
        assert actual.split()==(d/'fixed05'/n).read_text().split(),n
        for tag in ('window01','normal01'):assert sha(d/tag/n)==sha(d/'fixed05'/n)
    plan=read(d/'board02/nes_plan_batch206.sv');checker=read(d/'board02/nes_validator278.sv');host=read(d/'board02/nes_mux260.sv')
    assert not re.search(r'\bstate<=',plan) and 'wire [2:0] state=plan_state321' in plan
    for name in ('V_RREAD','V_RWRITE','V_PREAD','V_PWRITE','V_CHECKREAD','V_CHECKTEST','V_PCHECKREAD','V_PCHECKTEST','D_READ','D_CHECK'):assert 'control_state321<='+name+';' not in checker
    for name in ('DREAD','DCAP','PREAD','PCAP','MREAD313','MCAP313','XWAIT298','MWAIT313'):assert not re.search(r'\b'+name+r':',host)
    guards=js(d/'guards02/result.json');assert guards['passed'] and [x['case'] for x in guards['cases']]==list(range(1,12))
    for n,h in guards['rtl_hashes'].items():assert h==sha(d/'fixed05'/n)==sha(d/'guards02'/n);read(d/'guards02'/n)
    assert sha(d/'guards02/joint266_tb.sv')==guards['tb_sha256'];read(d/'guards02/joint266_tb.sv')
    for case in guards['cases']:
        p=d/'guards02'/f"case{case['case']}"/'vsim.log';assert sha(p)==case['log_sha256'];raw=read(p)
        expected=3 if case['case']==6 else 4
        assert f"PASS EXECUTE321 GUARD={case['case']} fault={expected}" in raw and '** Fatal:' not in raw and 'Failed to open readmem file' not in raw
    for n in ('nes_execute321.py','probe_nes_execute321.py','map_nes_execute321.py','guard_nes_execute321.py','analyze_nes_execute321.py'):read(ROOT/'tools'/n)
    out=dict(stage=321,passed=True,selected=False,runs=runs,comparisons=comparisons,whole_MAP=whole,
        delta319={k:whole[k]-baseline['whole_MAP'][k] for k in whole},comb_deficit=whole['comb']-15408,
        remaining_ms=runs['window01']['rows'][-1]['gap_ms'],regional=regional,
        regional_comb=sum(x['after']['comb'] for x in regional.values()),guards=guards,
        FSMs=[x.strip() for x in report.splitlines() if re.match(r'\s*\d+\. State Machine - ',x)],
        latches=latches,identical_ARM_PT_LOAD=True,input_hashes=pins,
        limitations=['CPI1/84MHz actual ARM instructions and IRQ model; not hardware WCET.',
        'Ordinary65816 prior CPU trace replay, tile/map/VBlank partly modeled.',
        'Whole Lite MAP only; no FIT/STA/full71/fullRUN/physical60fps.',
        'Retains checker initialization/hash/certificate/display state, independent cursors and transport CDC.'])
    out['regional_delta']=out['regional_comb']-6700
    out['outside_delta']=out['delta319']['comb']-out['regional_delta']
    counts=runs['window01']['rows'][-1]['execution_counts']
    out['warm_execution_occupancy_us']={
        'checker_RAM_phases':counts['phase_cycles']*11.904/1000,
        'queue_read_capture':counts['queue_reads']*2*11.904/1000,
        'scope':'Adjacent cumulative snapshots; occupancy, not a measured removable critical path. Excludes header, PUT, transport and other state costs.'}
    (ROOT/'analysis/execute321-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:out[k] for k in ('comparisons','whole_MAP','delta319','comb_deficit','remaining_ms','regional_comb')},indent=2))
if __name__=='__main__':main()
