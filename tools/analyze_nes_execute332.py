# SPDX-License-Identifier: MIT
"""Same-phase/continuous ARM map publication and final RAM job, whole Lite."""
import argparse,csv,json,re
from collections import defaultdict
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');a=ap.parse_args()
    d=BASE/'probes/nes-execute332';pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    old=js(ROOT/'analysis/completion331-verification.json');assert old['passed']
    def wire(transfers):
        g=defaultdict(list)
        for t in transfers:
            b=bytes.fromhex(t['tx'])
            if not b:continue
            if b[0]==0xe1:g[b[1]].append((b[:3]+b[5:-2]).hex())
            if b[0]==0xe1 and b[1] in (2,4,5,7,8,12,14):g['ordered_DMA'].append((b[:3]+b[5:-2]).hex())
            if b[0]==0xe9:g[0xe9].append(b.hex())
        return dict(g)
    runs={};results={}
    cases=[('window01','window04'),('window02','window04'),('window03','window04'),('fixed02','fixed02'),('normal01','normal01'),('arm-fixed01','fixed02'),('arm-window01','window04')]
    for tag,ref in cases:
        q=d/tag
        if not (q/'result.json').exists():assert a.partial,(tag,'missing');continue
        r=js(q/'result.json');assert r['passed'];results[tag]=r
        prev=BASE/'probes/nes-completion331'/ref;pr=js(prev/'result.json')
        changed={n for n,h in r['rtl_hashes'].items() if pr['rtl_hashes'][n]!=h}
        expected=set() if tag.startswith('arm-') else {'nes_mux260.sv','nes_validator278.sv','nes_joint257.sv','nes_joint266.sv'}|({'nes_queue260.sv'} if tag!='window01' else set())
        assert changed==expected,(tag,changed)
        for n,h in r['rtl_hashes'].items():read(q/n);assert sha(q/n)==h
        tb=read(q/'joint266_tb.sv');assert sha(q/'joint266_tb.sv')==r['tb_sha256']
        assert '#22.727 clk=~clk' in tb and 'romcycle267%357368>=330088&&romcycle267%357368<354640&&romcycle267%12==3' in tb
        assert 'core_ready267&&romcycle267%120==3' in tb
        assert sha(q/'output.elf')==r['ELF_sha256'];pins[str(q/'output.elf')]=r['ELF_sha256']
        for n in ('nes_native289.c','nes_output264.c','nes_refill267.c','nes_execute332.py'):read(q/n)
        for n in ('ordinary.sfc','bus.csv','timing.csv','capture.lua','packets.hex'):
            p=q/('CPU-'+n);assert sha(p)==sha(prev/('CPU-'+n));pins[str(p)]=sha(p)
        events=list(csv.reader(read(q/'joint-events.csv').splitlines()))
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(q/'cycles.csv').splitlines())}
        metadata=js(q/'metadata317.json');rows=[]
        for prior in old['runs'][ref]['rows']:
            f=prior['frame'];e=[x for x in events if len(x)>1 and x[1]==str(f)]
            def event(name,kind=None):return next(x for x in e if x[0]==name and (kind is None or x[2]==str(kind)))
            start=event('start319');end=event('frame_done');finish=int(end[2])/1e9;total=source[f]+int(end[3])/1e9
            if 'fixed' in tag:assert int(start[2])/1e9==prior['start_ms'] and int(start[3])==prior['start_ROM_cycle']
            transfers=js(q/f'arm{f}.json')['transfers'];assert wire(transfers)==wire(js(prev/f'arm{f}.json')['transfers']),('wire',tag,f)
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            tx=[x for x in e if x[0]=='arm267'];assert sum(int(x[3]) for x in tx)==arm['SPI_bytes']
            credit=max(int(x[2]) for x in e if x[0]=='credits');assert credit<=2
            accept=int(event('rom_accept327',0)[-1])/1e9
            calls=[x for x in metadata if x['start']['generation']==f-904]
            publication=[x for x in calls if x['name']=='publish_map332'];assert len(publication)==1 and publication[0]['result']==1
            ordinary=[x for x in calls if x['name'] in ('oam227','dirty_span231','span')]
            assert ordinary and min(x['start']['instruction'] for x in ordinary)>=publication[0]['end']['instruction']
            tile=[int(x[-1])/1e9 for x in e if x[0]=='consume293' and x[2]=='1']
            maps=[int(x[-1])/1e9 for x in e if x[0]=='consume293' and x[2]=='2' and int(x[3])>=128] if f==907 else []
            last=int([x for x in e if x[0]=='consume293'][-1][-1])/1e9
            first_map=next(x for x in transfers if x['tx'].startswith('e10e'))
            first_map_tx=next(x for x in tx if int(x[4])==first_map['RTL_ns']*1000 and int(x[2])==0xe1)
            rows.append(dict(frame=f,start_ms=int(start[2])/1e9,start_ROM_cycle=int(start[3]),finish_ms=finish,total_ms=total,gap_ms=total-1000/60,
                duration_delta_ms=total-prior['total_ms'],finish_delta_ms=finish-prior['finish_ms'],start_delta_ms=int(start[2])/1e9-prior['start_ms'],
                first_ROM_accept_ms=accept,first_BG_ms=int(event('romtile305',0)[-1])/1e9,last_tile_consume_ms=tile[-1],first_map_consume_ms=maps[0] if maps else None,
                last_consume_ms=last,tail_ms=finish-last,post_ROM_ms=finish-accept,ARM_instructions=arm['instructions'],ARM_delta=arm['instructions']-prior['ARM_instructions'],
                partition_ms=dict(ROM_to_last_tile=tile[-1]-accept,tile_to_first_map=maps[0]-tile[-1],map_span=maps[-1]-maps[0],last_map_to_last_ordinary=last-maps[-1],final_tail=finish-last) if maps else None,
                SPI_bytes=arm['SPI_bytes'],SPI_delta=arm['SPI_bytes']-prior['SPI_bytes'],max_credit=credit,publication=publication[0],
                ordinary_prepare=[dict(name=x['name'],start_ms=x['start']['modeled_ns']/1e6,end_ms=x['end']['modeled_ns']/1e6,inclusive_instructions=x['end']['instruction']-x['start']['instruction']) for x in ordinary],
                first_map_E1_bytes=len(bytes.fromhex(first_map['tx'])),first_map_E1_end_ms=int(first_map_tx[4])/1e9,pre_first_map_E1_ARM_instructions=first_map['instructions'],
                command_counts={hex(op):sum(int(x[2])==op for x in tx) for op in (0xe0,0xe1,0xe2,0xe9,0xea)},opcode_payloads_and_E9_identical=True))
            if maps:assert abs(sum(rows[-1]['partition_ms'].values())-rows[-1]['post_ROM_ms'])<1e-9
        with (q/'output.elf').open('rb') as f:
            elf=ELFFile(f);sections={n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.bss','.data')}
        runs[tag]=dict(rows=rows,SysTick=len(r['ARM']['IRQ_cases']),EXTI=len(r['ARM']['EXTI284']),stack=r['ARM']['stack_observed'],sections=sections)
    if a.partial:print(json.dumps(dict(status='partial_not_final',runs=runs),indent=2));return
    boards={}
    for tag in ('board01','board02','board03'):
        b=js(d/tag/'result.json');assert b['passed']
        for n,h in b['actual_inputs'].items():pins[str(d/tag/n)]=sha(d/tag/n);assert sha(d/tag/n)==h
        whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',b['summary'])[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
        log=read(d/tag/'map.log');assert 'Warning (10034)' not in log
        assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
        for n in ('nes_mux260.sv','nes_spi270.sv','nes_queue260.sv','nes_validator278.sv','nes_joint257.sv','nes_bulk_aperture188.sv'):
            content=read(d/tag/n);s=read(d/('window'+tag[-2:])/n)
            if n=='nes_mux260.sv':content=content.replace(' output wire tile_closed267,\n','').replace('assign tile_closed267=tiles_closed;','')
            assert content==s,(tag,n)
        report=read(d/tag/'output_files/board.map.rpt');nodes={}
        assert 'nes_validator278:validator|state' in report and 'nes_output260:flow|state' in report
        for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
            c=[v.strip() for v in line.split(';')]
            if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
        assert sum(nodes.values())==whole['comb']
        boards[tag]=dict(whole=whole,delta={k:whole[k]-old['whole'][k] for k in whole},own_entity_comb=nodes,own_entity_delta={n:nodes.get(n,0)-old['own_entity_comb'].get(n,0) for n in sorted(set(nodes)|set(old['own_entity_comb'])) if nodes.get(n,0)!=old['own_entity_comb'].get(n,0)})
    def load(p):
        with p.open('rb') as f:return [(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD']
    for tag in ('window03','fixed02','normal01','arm-fixed01','arm-window01'):assert load(d/tag/'output.elf')==load(d/'window03/output.elf'),tag
    unit={}
    for tag,name in [('producer02','check_nes_resume330.py'),('pause02','check_nes_pause330.py'),('status02','check_nes_status331.py')]:
        r=js(d/tag/'result.json');assert r['passed'] and r['ELF_sha256']==sha(d/'window03/output.elf') and r['script_sha256']==sha(ROOT/'tools'/name);read(ROOT/'tools'/name);unit[tag]=r
    assert len(unit['producer02']['frames'])==71 and len(unit['pause02']['frames'])==3 and len(unit['status02']['tests'])==205
    publication=js(d/'publish01/result.json');assert publication['passed'] and len(publication['cases'])==8
    assert publication['ELF_sha256']==sha(d/'window03/output.elf') and publication['script_sha256']==sha(ROOT/'tools/check_nes_publish332.py')
    g=js(d/'guards02/result.json');assert g['passed'] and g['rtl_hashes']==results['window03']['rtl_hashes'] and g['ELF_sha256']==sha(d/'window03/output.elf')
    read(d/'guards02/joint266_tb.sv');assert sha(d/'guards02/joint266_tb.sv')==g['tb_sha256']
    assert sorted(x['case'] for x in g['cases'])==[3,5,6,7,10,11,12,13,14,15,16]
    for c in g['cases']:
        p=d/'guards02'/f"case{c['case']}"/'vsim.log';raw=read(p);assert sha(p)==c['log_sha256']
        fault=7 if c['case'] in (10,14) else 3 if c['case']==6 else 4;assert f"PASS OWNER319 GUARD={c['case']} fault={fault}" in raw
    aperture=js(d/'guards02/aperture/result.json');assert aperture['passed']
    for n,key in [('nes_bulk_aperture188.sv','RTL_sha256'),('aperture325_tb.sv','tb_sha256'),('vsim.log','log_sha256')]:read(d/'guards02/aperture'/n);assert sha(d/'guards02/aperture'/n)==aperture[key]
    raw0=js(d/'guards02/final-raw0/result.json');assert raw0['passed'] and raw0['cases']==7 and raw0['RTL_sha256']==results['window03']['rtl_hashes']['nes_validator278.sv']
    assert raw0['script_sha256']==sha(ROOT/'tools/check_nes_final332.py')
    for n,key in [('nes_validator278.sv','RTL_sha256'),('final332_tb.sv','tb_sha256'),('vsim.log','log_sha256')]:read(d/'guards02/final-raw0'/n);assert sha(d/'guards02/final-raw0'/n)==raw0[key]
    for n in ('context.hex','display.hex'):read(d/'guards02/final-raw0'/n)
    for name in ('nes_execute332.py','probe_nes_execute332.py','map_nes_execute332.py','guard_nes_execute332.py','analyze_nes_execute332.py','check_nes_publish332.py','check_nes_final332.py'):read(ROOT/'tools'/name)
    split={k:[dict(frame=x['frame'],ARM_only_delta_ms=x['duration_delta_ms'],joint_extra_delta_ms=y['total_ms']-x['total_ms'],joint_extra_finish_delta_ms=y['finish_ms']-x['finish_ms']) for x,y in zip(runs['arm-'+k]['rows'],runs[j]['rows'])] for k,j in [('fixed01','fixed02'),('window01','window03')]}
    whole=boards['board03']['whole']
    nodes=boards['board03']['own_entity_comb']
    def own(suffix):
        found=[v for k,v in nodes.items() if k.endswith(suffix)];assert len(found)==1;return found[0]
    def tree(suffix):
        paths=[k for k in nodes if k.endswith(suffix)];assert len(paths)==1
        return sum(v for k,v in nodes.items() if k==paths[0] or k.startswith(paths[0]+'|'))
    groups=dict(host_validator=own('nes_output260:flow')+own('nes_validator278:validator'),
        queue_SPI=own('nes_queue260:queue')+own('nes_spi270:spi_front270'),
        source=own('nes_core257:encoder')+tree('nes_transport257:transport'),
        plan=own('nes_plan_path267:retained_plan267')+tree('nes_plan_batch206:transport')+own('nes_plan_spi200:endpoint'))
    outside=whole['comb']-sum(groups.values())
    caps=dict(host_validator=2100,queue_SPI=600,source=1100,plan=310)
    out=dict(stage=332,passed=True,baseline='331 common completion response + cold preparation',runs=runs,split=split,boards=boards,whole=whole,whole_delta=boards['board03']['delta'],comb_deficit=whole['comb']-15408,
        own_entity_comb=boards['board03']['own_entity_comb'],producer_frames=71,producer_guards=unit['producer02']['guards'],pause_guards=unit['pause02']['guards'],status_guards=205,publication_guards=publication['cases'],RTL_guards=g['cases'],
        groups=groups,budget329_rebased=dict(caps=caps,outside=outside,whole_if_caps_met=outside+sum(caps.values()),scope='Design caps only, not predicted/measured savings.'),
        raw0_final_job=raw0,
        scope='Actual M4 instructions with CPI1/84MHz model, SPI/IRQ/2slot/ROM and unchanged32565816 bus trace; wholeLite MAP, no FIT/STA/physical60fps.',pins=pins)
    (ROOT/'analysis/execute332-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,whole=whole,whole_delta=out['whole_delta'],split=split,warm={k:v['rows'][-1] for k,v in runs.items()}),indent=2))


if __name__=='__main__':main()
