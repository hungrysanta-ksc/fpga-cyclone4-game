# SPDX-License-Identifier: MIT
"""Bind cold-preparation controls, common response ABI and whole Lite costs."""
import argparse,csv,json,re
from collections import defaultdict
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');a=ap.parse_args()
    d=BASE/'probes/nes-completion331';pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    old=js(ROOT/'analysis/resume330-verification.json');assert old['passed']
    selected=js(ROOT/'analysis/joint328-verification.json');assert selected['passed']
    def wire(transfers):
        g=defaultdict(list)
        for x in transfers:
            b=bytes.fromhex(x['tx'])
            if not b:continue
            if b[0]==0xe1:g[b[1]].append((b[:3]+b[5:-2]).hex())
            if b[0]==0xe9:g[0xe9].append(b.hex())
        return dict(g)
    runs={};results={}
    for tag,ref in [('window04','window01'),('fixed02','fixed01'),('normal01','normal01'),('arm-window01','window01'),('arm-normal01','normal01')]:
        q=d/tag
        if not (q/'result.json').exists():assert a.partial,(tag,'missing');continue
        r=js(q/'result.json');assert r['passed'];results[tag]=r
        prev=BASE/'probes/nes-resume330'/ref;pr=js(prev/'result.json')
        changed={n for n,h in r['rtl_hashes'].items() if pr['rtl_hashes'][n]!=h}
        assert changed==(set() if tag.startswith('arm-') else {'nes_spi270.sv','nes_mux260.sv','nes_queue260.sv'}),changed
        for n,h in r['rtl_hashes'].items():read(q/n);assert sha(q/n)==h
        assert sha(q/'joint266_tb.sv')==r['tb_sha256'];tb=read(q/'joint266_tb.sv')
        assert '#22.727 clk=~clk' in tb and 'romcycle267%357368>=330088&&romcycle267%357368<354640&&romcycle267%12==3' in tb
        assert 'core_ready267&&romcycle267%120==3' in tb
        assert sha(q/'output.elf')==r['ELF_sha256'];pins[str(q/'output.elf')]=r['ELF_sha256']
        for n in ('nes_native289.c','nes_output264.c','nes_refill267.c','nes_completion331.py'):read(q/n)
        for n in ('ordinary.sfc','bus.csv','timing.csv','capture.lua','packets.hex'):
            p=q/('CPU-'+n);assert sha(p)==sha(prev/('CPU-'+n));pins[str(p)]=sha(p)
        events=list(csv.reader(read(q/'joint-events.csv').splitlines()))
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(q/'cycles.csv').splitlines())}
        metadata=js(q/'metadata317.json');rows=[]
        for prior in old['runs'][ref]['rows']:
            f=prior['frame'];e=[x for x in events if len(x)>1 and x[1]==str(f)]
            def event(name,kind=None):return next(x for x in e if x[0]==name and (kind is None or x[2]==str(kind)))
            start=event('start319');end=event('frame_done');finish=int(end[2])/1e9;total=source[f]+int(end[3])/1e9
            if tag=='fixed02':assert int(start[2])/1e9==prior['start_ms'] and int(start[3])==prior['start_ROM_cycle']
            transfers=js(q/f'arm{f}.json')['transfers']
            assert wire(transfers)==wire(js(prev/f'arm{f}.json')['transfers']),('wire',tag,f)
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            tx=[x for x in e if x[0]=='arm267'];assert sum(int(x[3]) for x in tx)==arm['SPI_bytes']
            credit=max(int(x[2]) for x in e if x[0]=='credits');assert credit<=2
            accept=int(event('rom_accept327',0)[-1])/1e9
            calls=[x for x in metadata if x['name']=='prepare_map330' and x['start']['generation']==f-904]
            tile=[int(x[-1])/1e9 for x in e if x[0]=='consume293' and x[2]=='1']
            maps=[int(x[-1])/1e9 for x in e if x[0]=='consume293' and x[2]=='2' and int(x[3])>=128] if f==907 else []
            last=int([x for x in e if x[0]=='consume293'][-1][-1])/1e9
            ref328=next(x for x in selected['runs']['arm-'+ref]['rows'] if x['frame']==f)
            first_map=next(x for x in transfers if x['tx'].startswith('e10e'))
            rows.append(dict(frame=f,start_ms=int(start[2])/1e9,start_ROM_cycle=int(start[3]),finish_ms=finish,total_ms=total,gap_ms=total-1000/60,
                duration_delta_ms=total-prior['total_ms'],finish_delta_ms=finish-prior['finish_ms'],start_delta_ms=int(start[2])/1e9-prior['start_ms'],
                versus328_duration_delta_ms=total-ref328['total_ms'],first_ROM_accept_ms=accept,first_BG_ms=int(event('romtile305',0)[-1])/1e9,
                last_tile_consume_ms=tile[-1],first_map_consume_ms=maps[0] if maps else None,last_consume_ms=last,tail_ms=finish-last,post_ROM_ms=finish-accept,
                ARM_instructions=arm['instructions'],ARM_delta=arm['instructions']-prior['ARM_instructions'],SPI_bytes=arm['SPI_bytes'],SPI_delta=arm['SPI_bytes']-prior['SPI_bytes'],max_credit=credit,
                map_prepare_calls=len(calls),map_prepare_inclusive_instructions=sum(x['end']['instruction']-x['start']['instruction'] for x in calls),
                map_calls_completed_before_ROM=sum(x['end']['modeled_ns']/1e6<accept for x in calls),
                first_map_E1_bytes=len(bytes.fromhex(first_map['tx'])),pre_first_map_E1_ARM_instructions=first_map['instructions'],
                command_counts={hex(op):sum(int(x[2])==op for x in tx) for op in (0xe0,0xe1,0xe2,0xe9,0xea)},opcode_payloads_and_E9_identical=True))
        with (q/'output.elf').open('rb') as f:
            elf=ELFFile(f);sections={n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.bss','.data')}
        runs[tag]=dict(rows=rows,SysTick=len(r['ARM']['IRQ_cases']),EXTI=len(r['ARM']['EXTI284']),stack=r['ARM']['stack_observed'],sections=sections)
    if a.partial:print(json.dumps(dict(status='partial_not_final',runs=runs),indent=2));return
    board=js(d/'board04/result.json');assert board['passed']
    for n,h in board['actual_inputs'].items():pins[str(d/'board04'/n)]=sha(d/'board04'/n);assert sha(d/'board04'/n)==h
    whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',board['summary'])[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    log=read(d/'board04/map.log');assert 'Warning (10034)' not in log
    assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
    for n in ('nes_mux260.sv','nes_spi270.sv','nes_queue260.sv','nes_validator278.sv','nes_joint257.sv','nes_bulk_aperture188.sv'):
        b=read(d/'board04'/n);s=read(d/'window04'/n)
        if n=='nes_mux260.sv':b=b.replace(' output wire tile_closed267,\n','').replace('assign tile_closed267=tiles_closed;','')
        assert b==s,n
    report=read(d/'board04/output_files/board.map.rpt');nodes={}
    for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
        c=[v.strip() for v in line.split(';')]
        if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
    assert sum(nodes.values())==whole['comb']
    baseline_area=js(ROOT/'analysis/budget326-verification.json')['own_entity_comb']
    area_delta={n:nodes.get(n,0)-baseline_area.get(n,0) for n in sorted(set(nodes)|set(baseline_area)) if nodes.get(n,0)!=baseline_area.get(n,0)}
    def load(p):
        with p.open('rb') as f:return [(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD']
    assert load(d/'window04/output.elf')==load(d/'fixed02/output.elf')==load(d/'normal01/output.elf')
    assert load(d/'arm-window01/output.elf')==load(d/'arm-normal01/output.elf')
    producer=js(d/'producer01/result.json');pause=js(d/'pause01/result.json');status=js(d/'status01/result.json')
    # The queue length repair changed RTL only; producer01 used the earlier
    # directory's ELF. Bind its executable load image, not debug-path bytes.
    assert producer['passed'] and producer['ELF_sha256']==sha(d/'window02/output.elf')
    pins[str(d/'window02/output.elf')]=sha(d/'window02/output.elf')
    assert load(d/'window02/output.elf')==load(d/'window03/output.elf')
    for r in (pause,status):assert r['passed'] and r['ELF_sha256']==sha(d/'window03/output.elf')
    pins[str(d/'window03/output.elf')]=sha(d/'window03/output.elf')
    assert load(d/'window03/output.elf')==load(d/'window04/output.elf')
    assert len(producer['frames'])==71 and len(pause['frames'])==3 and len(status['tests'])==205
    identity=js(d/'identity02/result.json');assert identity['passed'] and len(identity['cases'])==11 and identity['ELF_sha256']==sha(d/'window04/output.elf')
    for r,name in [(producer,'check_nes_resume330.py'),(pause,'check_nes_pause330.py'),(status,'check_nes_status331.py'),(identity,'check_nes_identity331.py')]:
        assert r['script_sha256']==sha(ROOT/'tools'/name)
    guards=js(d/'guards01/result.json');assert guards['passed'] and guards['rtl_hashes']==results['window04']['rtl_hashes'] and guards['ELF_sha256']==sha(d/'window04/output.elf')
    read(d/'guards01/joint266_tb.sv');assert guards['tb_sha256']==sha(d/'guards01/joint266_tb.sv')
    assert sorted(x['case'] for x in guards['cases'])==[3,5,6,7,10,11]
    for c in guards['cases']:
        p=d/'guards01'/f"case{c['case']}"/'vsim.log';raw=read(p);assert sha(p)==c['log_sha256']
        fault=7 if c['case']==10 else 3 if c['case']==6 else 4;assert f"PASS OWNER319 GUARD={c['case']} fault={fault}" in raw
    spi=js(d/'spi02/result.json');assert spi['passed'] and spi['RTL_sha256']==sha(d/'window04/nes_spi270.sv')
    for n,key in [('nes_spi270.sv','RTL_sha256'),('spi331_tb.sv','tb_sha256'),('vsim.log','log_sha256')]:read(d/'spi02'/n);assert sha(d/'spi02'/n)==spi[key]
    aperture=js(d/'guards01/aperture/result.json');assert aperture['passed']
    for n,key in [('nes_bulk_aperture188.sv','RTL_sha256'),('aperture325_tb.sv','tb_sha256'),('vsim.log','log_sha256')]:read(d/'guards01/aperture'/n);assert sha(d/'guards01/aperture'/n)==aperture[key]
    for name in ('nes_completion331.py','probe_nes_completion331.py','map_nes_completion331.py','guard_nes_completion331.py','check_nes_status331.py','check_nes_identity331.py','check_nes_spi331.py','analyze_nes_completion331.py','check_nes_resume330.py','check_nes_pause330.py'):read(ROOT/'tools'/name)
    split={k:[dict(frame=x['frame'],ARM_only_delta_ms=x['duration_delta_ms'],joint_extra_delta_ms=y['total_ms']-x['total_ms'],joint_extra_finish_delta_ms=y['finish_ms']-x['finish_ms']) for x,y in zip(runs['arm-'+k]['rows'],runs[j]['rows'])] for k,j in [('window01','window04'),('normal01','normal01')]}
    out=dict(stage=331,passed=True,baseline='330 ARM +325 RTL; retained328 also compared',runs=runs,split=split,whole=whole,whole_delta={k:whole[k]-old['whole'][k] for k in whole},comb_deficit=whole['comb']-15408,own_entity_comb=nodes,own_entity_delta=area_delta,
        producer_frames=71,producer_guards=producer['guards'],pause_guards=pause['guards'],status_guards=205,identity_guards=identity['cases'],RTL_guards=guards['cases'],SPI=spi,
        scope='Actual M4 instructions with CPI1/84MHz model, SPI/IRQ/2slot/ROM and unchanged32565816 bus trace; new wholeLite MAP, no FIT/STA/physical60fps.',pins=pins)
    (ROOT/'analysis/completion331-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,whole=whole,whole_delta=out['whole_delta'],split=split,warm={k:v['rows'][-1] for k,v in runs.items()}),indent=2))


if __name__=='__main__':main()
