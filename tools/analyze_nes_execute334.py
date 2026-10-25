# SPDX-License-Identifier: MIT
"""Bind ARM arithmetic/scan and shared-sequencer experiments to whole costs."""
import argparse,csv,json,re
from collections import defaultdict
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile


def wire(transfers):
    out=defaultdict(list)
    for t in transfers:
        b=bytes.fromhex(t['tx'])
        if not b:continue
        if b[0]==0xe1:
            payload=(b[:3]+b[5:-2]).hex();out[b[1]].append(payload)
            if b[1] in (2,4,5,7,8,12,14):out['ordered_DMA'].append(payload)
        if b[0]==0xe9:out[0xe9].append(b.hex())
    return dict(out)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');a=ap.parse_args()
    pins={};d=BASE/'probes/nes-execute334'
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    old=js(ROOT/'analysis/execute332-verification.json');assert old['passed']
    runs={};results={}
    for tag,ref in [('window02','window03'),('fixed01','fixed02'),('normal01','normal01'),('arm-fixed01','fixed02'),('arm-window01','window03'),('arm-normal01','normal01')]:
        q=d/tag
        if not (q/'result.json').exists():assert a.partial,(tag,'missing');continue
        result=js(q/'result.json');assert result['passed'];results[tag]=result
        previous=BASE/'probes/nes-execute332'/ref;pr=js(previous/'result.json')
        changed={k for k,v in result['rtl_hashes'].items() if v!=pr['rtl_hashes'][k]}
        assert changed==(set() if tag.startswith('arm-') else {'nes_mux260.sv','nes_core257.sv','nes_transport257.sv','nes_plan_batch206.sv','nes_joint257.sv','nes_joint266.sv','nes_plan_rom267.sv'}),(tag,changed)
        for n,h in result['rtl_hashes'].items():read(q/n);assert sha(q/n)==h
        tb=read(q/'joint266_tb.sv');assert sha(q/'joint266_tb.sv')==result['tb_sha256']
        assert '#22.727 clk=~clk' in tb and 'romcycle267%357368>=330088&&romcycle267%357368<354640&&romcycle267%12==3' in tb
        assert 'core_ready267&&romcycle267%120==3' in tb
        if not tag.startswith('arm-'):
            assert 'encoded payload reread334' in tb and 'plan phase before source drain334' in tb
        for n in ('nes_native289.c','nes_output264.c','nes_refill267.c','nes_execute334.py','probe_nes_execute334.py'):read(q/n)
        for n in ('ordinary.sfc','bus.csv','timing.csv','capture.lua','packets.hex'):
            p=q/('CPU-'+n);assert sha(p)==sha(previous/('CPU-'+n));pins[str(p)]=sha(p)
        pins[str(q/'output.elf')]=sha(q/'output.elf');assert pins[str(q/'output.elf')]==result['ELF_sha256']
        events=list(csv.reader(read(q/'joint-events.csv').splitlines()))
        meta=js(q/'metadata317.json')
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(q/'cycles.csv').splitlines())}
        rows=[]
        for prior in old['runs'][ref]['rows']:
            f=prior['frame'];e=[x for x in events if len(x)>1 and x[1]==str(f)]
            def first(n,k=None):return next(x for x in e if x[0]==n and (k is None or x[2]==str(k)))
            start=first('start319');end=first('frame_done');finish=int(end[2])/1e9;total=source[f]+int(end[3])/1e9
            if 'fixed' in tag:assert int(start[2])/1e9==prior['start_ms'] and int(start[3])==prior['start_ROM_cycle']
            tr=js(q/f'arm{f}.json')['transfers'];assert wire(tr)==wire(js(previous/f'arm{f}.json')['transfers']),(tag,f,'wire')
            arm=next(x for x in result['ARM']['frames'] if x['frame']==f)
            tx=[x for x in e if x[0]=='arm267'];assert sum(int(x[3]) for x in tx)==arm['SPI_bytes']
            max_credit=max(int(x[2]) for x in e if x[0]=='credits');assert max_credit<=2
            accept=int(first('rom_accept327',0)[-1])/1e9
            req=first('firstreq305',0);cycle=int(req[3]);close=(cycle//357368-1)*357368+354640
            last=int([x for x in e if x[0]=='consume293'][-1][-1])/1e9
            tile=[int(x[-1])/1e9 for x in e if x[0]=='consume293' and x[2]=='1']
            maps=[int(x[-1])/1e9 for x in e if x[0]=='consume293' and x[2]=='2' and int(x[3])>=128] if f==907 else []
            calls=[x for x in meta if x['start']['generation']==f-904]
            prep=next(x for x in calls if x['name']=='prepare289');final=next(x for x in calls if x['name']=='tiles290' and x['arg']==1)
            h2_ins=final['start']['instruction']-prep['end']['instruction']
            first_ordinary=next(x for x in tr if bytes.fromhex(x['tx'])[:3]==bytes((0xe1,2,4)))
            obs={n:[x[2:-1]+[int(x[-1])/1e9] for x in e if x[0]==n] for n in ('tile_last334','stage_ready334','DMA_ready334')}
            rows.append(dict(frame=f,start_ms=int(start[2])/1e9,start_ROM_cycle=int(start[3]),finish_ms=finish,total_ms=total,gap_ms=total-1000/60,
                duration_delta_ms=total-prior['total_ms'],finish_delta_ms=finish-prior['finish_ms'],start_delta_ms=int(start[2])/1e9-prior['start_ms'],
                first_ROM_accept_ms=accept,post_ROM_ms=finish-accept,source_ms=source[f],tail_ms=finish-last,
                request_ms=int(req[-1])/1e9,request_wait_ms=accept-int(req[-1])/1e9,
                previous_window_closed_before_start_ms=(int(start[3])-close)*45.454/1e6 if 'normal' not in tag else None,
                previous_window_closed_before_source_complete_ms=source[f]+(int(start[3])-close)*45.454/1e6 if 'normal' not in tag else None,
                ROM_accept_delta_ms=accept-prior['first_ROM_accept_ms'],post_ROM_delta_ms=(finish-accept)-prior['post_ROM_ms'],
                partition_ms=dict(ROM_to_last_tile=tile[-1]-accept,tile_to_first_map=maps[0]-tile[-1],map_span=maps[-1]-maps[0],last_map_to_last_ordinary=last-maps[-1],final_tail=finish-last) if maps else None,
                ARM_instructions=arm['instructions'],ARM_delta=arm['instructions']-prior['ARM_instructions'],SPI_bytes=arm['SPI_bytes'],SPI_delta=arm['SPI_bytes']-prior['SPI_bytes'],max_credit=max_credit,
                command_counts={hex(op):sum(int(x[2])==op for x in tx) for op in (0xe0,0xe1,0xe2,0xe9,0xea)},
                H2_callsite_envelope_instructions=h2_ins,H2_callsite_envelope_CPI1_ms=h2_ins/84000,
                first_OAM_pretransfer_instructions=first_ordinary['instructions'],observation_ms=obs,wire_and_E9_identical=True))
        with (q/'output.elf').open('rb') as f:
            elf=ELFFile(f);sections={n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.bss','.data')}
        runs[tag]=dict(rows=rows,SysTick=len(result['ARM']['IRQ_cases']),EXTI=len(result['ARM']['EXTI284']),stack=result['ARM']['stack_observed'],sections=sections)
    if a.partial:
        print(json.dumps(dict(status='partial',runs=runs),indent=2));return
    b=js(d/'board02/result.json');assert b['passed']
    for n,h in b['actual_inputs'].items():pins[str(d/'board02'/n)]=sha(d/'board02'/n);assert sha(d/'board02'/n)==h
    whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',b['summary'])[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    report=read(d/'board02/output_files/board.map.rpt');log=read(d/'board02/map.log')
    assert 'Warning (10034)' not in log
    assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
    assert all(x+'|state' in report for x in ('nes_core257:encoder','nes_output260:flow','nes_validator278:validator'))
    assert 'State Machine - |fxpak_nes_screen137_top|nes_live_joint:core|nes_plan_path267:retained_plan267|nes_plan_batch206:transport|state' not in report
    nodes={}
    for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
        c=[v.strip() for v in line.split(';')]
        if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
    assert sum(nodes.values())==whole['comb']
    def own(suffix):
        found=[v for k,v in nodes.items() if k.endswith(suffix)];assert len(found)==1;return found[0]
    def tree(suffix):
        paths=[k for k in nodes if k.endswith(suffix)];assert len(paths)==1
        return sum(v for k,v in nodes.items() if k==paths[0] or k.startswith(paths[0]+'|'))
    groups=dict(host_validator=own('nes_output260:flow')+own('nes_validator278:validator'),
        queue_SPI=own('nes_queue260:queue')+own('nes_spi270:spi_front270'),
        source=own('nes_core257:encoder')+tree('nes_transport257:transport'),
        plan=own('nes_plan_path267:retained_plan267')+tree('nes_plan_batch206:transport')+own('nes_plan_spi200:endpoint'))
    groups['outside']=whole['comb']-sum(groups.values())
    def lines(s):return [x for x in s.splitlines() if x.strip()]
    for n in ('nes_mux260.sv','nes_core257.sv','nes_transport257.sv','nes_plan_batch206.sv','nes_joint257.sv','nes_validator278.sv'):
        s=read(d/'board02'/n);t=read(d/'window02'/n)
        if n=='nes_mux260.sv':s=s.replace(' output wire tile_closed267,\n','').replace('assign tile_closed267=tiles_closed;','')
        assert lines(s)==lines(t),n
    # The whole-board wrapper already takes the external board lease instead
    # of instantiating the functional slice's lease. Bind its ONLY334 change
    # to the two new plan-state ports/connections, retaining that332 boundary.
    s=read(d/'board02/nes_joint266.sv')
    for fragment in ('output wire [2:0] plan_state334,input wire [2:0] plan_next334,',
                     '.plan_state334(plan_state334),.plan_next334(plan_next334),'):
        assert s.count(fragment)==1;s=s.replace(fragment,'')
    assert lines(s)==lines(read(BASE/'probes/nes-execute332/board03/nes_joint266.sv'))
    def load(p):
        with p.open('rb') as f:return [(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD']
    for tag in runs:assert load(d/tag/'output.elf')==load(d/'window02/output.elf'),tag
    # Unit tests used the initial build path. Debug sections differ; actual
    # load addresses, memory sizes and every execution byte must be identical.
    unit_elf=d/'window01/output.elf';pins[str(unit_elf)]=sha(unit_elf)
    assert load(unit_elf)==load(d/'window02/output.elf')
    units={}
    for tag,script in [('kernels01','check_nes_kernels334.py'),('producer01','check_nes_resume330.py'),('pause01','check_nes_pause330.py'),('status01','check_nes_status331.py'),('publish01','check_nes_publish332.py')]:
        r=js(d/tag/'result.json');assert r['passed'] and r['ELF_sha256']==sha(unit_elf) and r['script_sha256']==sha(ROOT/'tools'/script);read(ROOT/'tools'/script);units[tag]=r
    assert len(units['producer01']['frames'])==71 and len(units['pause01']['frames'])==71
    guards={}
    # The first ten fault cases passed before an assertion whose source_empty
    # predicate includes source_live fired during intentional cancellation.
    # Bind those original passes, retain case11 failure, then bind11..16 to
    # the corrected live-only invariant. No DUT change or repeated MAP.
    q=d/'guards01'
    for n,h in results['window02']['rtl_hashes'].items():read(q/n);assert sha(q/n)==h
    assert sha(q/'output.elf')==sha(d/'window02/output.elf');pins[str(q/'output.elf')]=sha(q/'output.elf')
    read(q/'joint266_tb.sv');guards['guards01_partial']=[]
    for c in range(1,11):
        p=q/f'case{c}'/'vsim.log';raw=read(p);assert f'PASS OWNER319 GUARD={c} ' in raw and '# Errors: 0' in raw
        guards['guards01_partial'].append(dict(case=c,passed=True,log_sha256=sha(p)))
    raw=read(q/'case11/vsim.log');assert 'Fatal: plan phase before source drain334' in raw and 'PASS OWNER319 GUARD=11 ' not in raw
    for gt,rt in [('guards02','window02'),('guards-arm01','arm-window01')]:
        g=js(d/gt/'result.json');assert g['passed'] and g['rtl_hashes']==results[rt]['rtl_hashes'] and g['ELF_sha256']==sha(d/rt/'output.elf')
        assert [c['case'] for c in g['cases']]==(list(range(11,17)) if gt=='guards02' else [3,5,6,7,9,10])
        read(d/gt/'joint266_tb.sv');assert sha(d/gt/'joint266_tb.sv')==g['tb_sha256']
        if gt=='guards02':assert 'transport.source_live&&!dut.core.transport_empty' in (d/gt/'joint266_tb.sv').read_text()
        for c in g['cases']:
            p=d/gt/f"case{c['case']}"/'vsim.log';raw=read(p);assert sha(p)==c['log_sha256'] and f"PASS OWNER319 GUARD={c['case']}" in raw
        for folder,script in [('aperture',None),('final-raw0','check_nes_final332.py')]:
            r=js(d/gt/folder/'result.json');assert r['passed']
            assert r['log_sha256']==sha(d/gt/folder/'vsim.log')
            assert r['tb_sha256'] in [sha(p) for p in (d/gt/folder).glob('*.sv')]
            if script:
                assert r['script_sha256']==sha(ROOT/'tools'/script) and r['cases']==7
                assert r['RTL_sha256']==results[rt]['rtl_hashes']['nes_validator278.sv']
            else:assert r['RTL_sha256']==results[rt]['rtl_hashes']['nes_bulk_aperture188.sv']
            for p in (d/gt/folder).iterdir():
                if p.is_file() and p.suffix in ('.sv','.log','.hex'):read(p)
        guards[gt]=g['cases']
    for n in ('nes_execute334.py','probe_nes_execute334.py','map_nes_execute334.py','guard_nes_execute334.py','check_nes_kernels334.py','analyze_nes_execute334.py'):read(ROOT/'tools'/n)
    assert 'Fatal: original body reread' in read(d/'window01/vsim.log')
    assert 'module nes_joint266 #(parameter SHARED=1)' in read(d/'board01-run.log')
    split={k:[dict(frame=x['frame'],ARM_only_delta_ms=x['duration_delta_ms'],joint_extra_delta_ms=y['total_ms']-x['total_ms'],joint_extra_finish_delta_ms=y['finish_ms']-x['finish_ms']) for x,y in zip(runs['arm-'+k]['rows'],runs[j]['rows'])] for k,j in [('fixed01','fixed01'),('window01','window02'),('normal01','normal01')]}
    out=dict(stage=334,passed=True,runs=runs,split=split,whole=whole,whole_delta={k:whole[k]-old['whole'][k] for k in whole},comb_deficit=whole['comb']-15408,
        ARM_only_whole=old['whole'],ARM_only_comb_deficit=old['comb_deficit'],own_entity_comb=nodes,groups=groups,
        own_entity_delta={k:v-old['own_entity_comb'].get(k,0) for k,v in nodes.items() if v!=old['own_entity_comb'].get(k,0)},
        units=units,guards=guards,selected_RTL=332,selected_ARM=334,unit_execution_image_identical=True,joint_RTL_rejected_for_area=True,
        preserved_failures=['window01 old-state monitor','board01 wrapper-name generation','guards01 case11 live-qualified empty monitor'],
        scope='Actual M4 instructions/CPI1/84MHz with SPI/IRQ/2slots/ROM; unchanged32565816 bus trace; wholeLite MAP, no FIT/STA/physical60fps.',pins=pins)
    (ROOT/'analysis/execute334-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,whole=whole,delta=out['whole_delta'],split=split,warm={k:v['rows'][-1] for k,v in runs.items()}),indent=2))


if __name__=='__main__':main()
