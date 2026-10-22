# SPDX-License-Identifier: MIT
"""Paired canonical/planner/H2, live output IRQ/ROM and whole Lite evidence."""
import argparse,csv,difflib,json,re,struct
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();b=a.base.resolve();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    def csvrows(p):return list(csv.DictReader(pin(p).open()))
    prior=js(ROOT/'analysis/joint285-verification.json');old284=js(ROOT/'analysis/joint284-verification.json')
    tags=['arm03','arm04','armguards02','guards01','guards02','test01','window01','board01'];checks={t:js(b/t/'result.json') for t in tags};assert all(r['passed'] for r in checks.values())
    arm=checks['arm03'];split=checks['arm04'];assert len(arm['frames'])==len(split['frames'])==71 and not arm['geometry_boundary'] and split['geometry_boundary']
    def allocated_elf(p):
        data=pin(p).read_bytes();assert data[:6]==b'\x7fELF\x01\x01'
        offset=struct.unpack_from('<I',data,32)[0];size,count=struct.unpack_from('<HH',data,46);sections=[]
        for i in range(count):
            h=struct.unpack_from('<10I',data,offset+i*size)
            if h[2]&2:sections.append((h[1:4],h[5],b'' if h[1]==8 else data[h[4]:h[4]+h[5]]))
        return sections
    assert allocated_elf(b/'arm03/planner.elf')==allocated_elf(b/'arm04/planner.elf')
    assert arm['metadata_bytes_per_frame']==split['metadata_bytes_per_frame']==8570
    ar={r['frame']:r for r in arm['frames']};oldarm={r['frame']:r for r in prior['planner']};planner=[]
    for tag in ('arm03','arm04'):
        r=checks[tag];assert r['script_sha256']==sha(pin(ROOT/'tools/probe_nes_planner286.py'))
        for n,h in r['input_hashes'].items():assert sha(pin(Path(n)))==h,n
        for n,h in r['generated_hashes'].items():assert sha(pin(b/tag/n))==h,n
    for row in split['frames']:
        f=row['frame'];now=ar[f]
        for key in ('steps','commit_instructions','plan_bytes','callbacks'):assert row[key]==now[key],(f,key)
        # geometry_ready286 short-circuits phase==2 before reading valid.
        # Original final-block expansion takes the three-instruction longer
        # completed/valid path; only the forced-boundary candidate differs.
        boundary_delta=-3 if now['tail_payload']==0 else 0
        for key in now['components']:
            assert row['components'][key]-now['components'][key]==(boundary_delta if key=='expand286' else 0),(f,key)
        assert row['postdecode_instructions']-now['postdecode_instructions']==boundary_delta
        original=oldarm[f]['begin_instructions']+oldarm[f]['plan_instructions'];cost=now['postdecode_instructions']
        # This is a wire/CS allocation only: no newly executed FPGA packetizer
        # or total-latency bound is implied by forcing the Python block split.
        extra=row['extra_block_count'];tail=row['tail_payload'];extra_wire=extra*15
        planner.append(dict(frame=f,old285_planner_instructions=original,new286_postdecode_instructions=cost,new286_components=now['components'],
            new286_steps=now['steps'],old285_ms=original/84000,new286_ms=cost/84000,delta_ms=(cost-original)/84000,
            expansion_ms=now['components']['expand286']/84000,early_H2_ms=now['components']['h2early286']/84000,
            group_steps_ms=sum(now['steps'][:-1])/84000,final_step_ms=now['steps'][-1]/84000,
            max_group_ms=now['max_group_instructions']/84000,extra_geometry_blocks=extra,extra_SPI_bytes=extra_wire,
            extra_wire_and_CS_allocation_ms=extra_wire*8/2625+extra*.008,tail_payload_bytes=tail,
            tail_wire_and_CS_allocation_ms=(tail+15)*8/2625+.008,
            prefix_prepare_ms=sum(now['components'][n] for n in ('expand286','begin285','geometry_plan286','h2early286'))/84000,
            forced_boundary_postdecode_delta_instructions=boundary_delta,
            forced_boundary_postdecode_ms=row['postdecode_instructions']/84000,
            decoder_boundary_delta_instructions=row['decoder_instructions']-now['decoder_instructions'],
            geometry_first_latency_gain_ms=None))
    assert checks['armguards02']['ELF_sha256']==arm['generated_hashes']['planner.elf']
    assert checks['armguards02']['script_sha256']==sha(pin(ROOT/'tools/guard_nes_planner286.py')) and len(checks['armguards02']['checks'])==15
    assert checks['guards01']['guards']==[3,23,24]+list(range(39,53))
    assert checks['guards02']['guards']==list(range(56,62))
    assert checks['guards02']['entry_hashes']['guard_nes_joint286.py']==sha(pin(ROOT/'tools/guard_nes_joint286.py'))
    for tag in ('guards01','guards02'):
        assert checks[tag]['TB_sha256']==sha(pin(b/tag/'joint266_tb.sv'))
    schedules={}
    for tag,count,oldrows in [('test01',71,prior['normal']),('window01',3,prior['restricted_ROM'])]:
        q=b/tag;r=checks[tag];assert r['frames']==count
        assert r['input_hashes']['probe_nes_schedule286.py']==sha(pin(ROOT/'tools/probe_nes_schedule286.py'))
        assert r['input_hashes']['nes_joint286.py']==sha(pin(ROOT/'tools/nes_joint286.py'))
        assert r['tb_sha256']==sha(pin(q/'joint266_tb.sv'))
        for n in ('result.json','planner.elf','nes_planner211.c','nes_planner285.c','nes_input286.inc'):
            assert r['input_hashes']['planner-'+n]==sha(pin(q/('planner-'+n)))==sha(pin(b/'arm03'/n)),n
        for n,h in r['rtl_hashes'].items():
            assert sha(pin(q/n))==h==sha(pin(b/'test01'/n)),n
            if n not in ('nes_mux260.sv','nes_validator278.sv'):assert h==sha(pin(BASE/'probes/nes-joint285/test01'/n)),n
        for guard in ('guards01','guards02'):
            for n,h in checks[guard]['rtl_hashes'].items():
                assert h==sha(pin(b/guard/n))
                if n in r['rtl_hashes']:assert h==r['rtl_hashes'][n],(guard,n)
        source={int(x['frame']):x for x in csvrows(q/'cycles.csv')};events=list(csv.reader(pin(q/'joint-events.csv').open()));old={x['frame']:x for x in oldrows};rows=[];prev=[0,0,0]
        assert 'identity owner changed' in pin(q/'joint266_tb.sv').read_text()
        for event in (e for e in events if e[0]=='frame_done'):
            f=int(event[1]);es=[e for e in events if int(e[1])==f];spi=[e for e in es if e[0]=='arm267'];wait=[e for e in es if e[0]=='wait284'];end=next(e for e in es if e[0]=='armdone284')
            pc=next(e for e in es if e[0]=='planner286');cc=next(e for e in es if e[0]=='commit286')
            assert int(pc[2])==ar[f]['postdecode_instructions'] and int(cc[2])==ar[f]['commit_instructions']
            counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,prev)];prev=counters
            src=int(source[f]['total'])*45.454/1e6;out=int(event[3])/1e9;total=src+out;before=old[f]['diagnostic_serial_ms']
            cost_delta=(ar[f]['postdecode_instructions']-oldarm[f]['begin_instructions']-oldarm[f]['plan_instructions'])/84000
            rows.append(dict(frame=f,source_ms=src,output_including_planner_ms=out,diagnostic_serial_ms=total,prior285_ms=before,
                delta285_ms=total-before,postdecode_CPI1_ms=ar[f]['postdecode_CPI1_ms'],planner_cost_delta_ms=cost_delta,
                frozen_additive_ms=before+cost_delta,retimed_minus_frozen_ms=total-before-cost_delta,margin_ms=1000/60-total,
                absolute_end_ms=int(event[2])/1e9,E2=sum(int(e[2])==226 for e in spi),E8=sum(int(e[2])==232 for e in spi),E9=sum(int(e[2])==233 for e in spi),
                SPI_bytes=sum(int(e[3]) for e in spi),ARM_output_all_boundary_instructions=sum(int(e[5]) for e in spi)+sum(int(e[4]) for e in wait)+int(end[3]),
                exception_cycles=sum(int(e[6]) for e in spi)+sum(int(e[5]) for e in wait)+int(end[4]),IRQ_waits=len(wait),timer_fallbacks=sum(int(e[2])==0 for e in wait),tile_wait_cycles=inc[0],slot_wait_cycles=inc[1],core_priority_blocks=inc[2]))
            now=js(q/f'arm{f}.json');then=js(BASE/'probes/nes-joint285'/tag/f'arm{f}.json')
            for op in (225,233):
                select=lambda v:[t['tx'] for t in v['transfers'] if t['tx'] and bytes.fromhex(t['tx'])[0]==op]
                assert select(now)==select(then),(tag,f,op)
        assert len(rows)==count;schedules[tag]=rows
    def mapping(folder):
        summary=pin(folder/'output_files/board.map.summary').read_text();m={}
        for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:m[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',summary).group(1).replace(',',''))
        own={}
        for line in pin(folder/'output_files/board.map.rpt').read_text().splitlines():
            f=[x.strip() for x in line.split(';')]
            if len(f)==14 and re.fullmatch(r'\d+ \(\d+\)',f[2]):own[f[10]]={k:int(re.search(r'\((\d+)\)',f[i]).group(1)) for k,i in [('comb',2),('FF',3)]}
        assert sum(v['comb'] for v in own.values())==m['comb'];return m,own
    board=b/'board01';whole,own=mapping(board);oldwhole,oldown=mapping(BASE/'probes/nes-joint284/board02')
    for n,h in checks['board01']['actual_inputs'].items():assert sha(pin(board/n))==h,n
    for n in ('nes_mux260.sv','nes_validator278.sv','nes_plan_batch206.sv','nes_plan_spi200.sv','nes_spi270.sv'):
        actual=pin(board/n).read_bytes();sim=pin(b/'test01'/n).read_bytes()
        if n=='nes_mux260.sv':
            anchor=b' output wire tile_closed267,\n';assignment=b' reg tiles_closed;assign tile_closed267=tiles_closed;';assert actual.count(anchor)==actual.count(assignment)==1
            actual=actual.replace(anchor,b'').replace(assignment,b' reg tiles_closed;')
        assert actual==sim,n
    region=lambda key:sum(v['comb'] for k,v in own.items() if key in k)
    regions=dict(host=sum(v['comb'] for k,v in own.items() if k.endswith('nes_output260:flow')),validator=region('nes_validator278:validator'),queue=region('nes_queue260:queue'),plan=region('nes_plan_batch206:transport')+region('nes_plan_spi200:endpoint'),SPI=region('nes_spi270:spi_front270'))
    selected=sum(regions.values());outside=whole['comb']-selected;budget=15408-outside
    changes=[dict(path=k,before=oldown.get(k,dict(comb=0,FF=0)),after=own.get(k,dict(comb=0,FF=0))) for k in sorted(own.keys()|oldown.keys()) if own.get(k)!=oldown.get(k)]
    assert sum(x['after']['comb']-x['before']['comb'] for x in changes)==whole['comb']-oldwhole['comb']
    area=dict(whole_MAP=whole,prior_MAP=oldwhole,delta={k:whole[k]-oldwhole[k] for k in whole},regions=regions,selected=selected,outside=outside,budget=budget,target_with_128_reserve=budget-128,
              selected_delta=selected-prior['area']['boundary'],outside_delta=outside-(oldwhole['comb']-prior['area']['boundary']),deficit=whole['comb']-15408,instance_changes=changes)
    warnings=js(b/'warning-audit.json');assert warnings['added']==warnings['removed']==[]
    for n,h in warnings['input_hashes'].items():assert sha(pin(Path(n)))==h,n
    area['warning_audit']=warnings
    warm=schedules['test01'][2:];warmmax=max(warm,key=lambda x:x['diagnostic_serial_ms'])
    result=dict(passed=True,stage=286,selected=tags,planner=planner,ARM=dict(context_bytes=arm['context_bytes'],certificate_bytes=32,size=arm['size'],observed_stack=arm['observed_stack'],guards=checks['armguards02']['checks']),
                forced_geometry_extra_blocks=sum(x['extra_geometry_blocks'] for x in planner),forced_geometry_extra_SPI_bytes=sum(x['extra_SPI_bytes'] for x in planner),forced_geometry_new_RTL=False,
                early_H2_exact_frames=71,metadata_bytes_per_frame=8570,normal=schedules['test01'],warm_max=warmmax,warm_over=[x['frame'] for x in warm if x['margin_ms']<0],restricted_ROM=schedules['window01'],area=area,
                new_RTL=True,new_MAP=True,full_path_ms=None,P2_selected=False,FIT=False,STA=False,physical=False,
                limits=['Actual M4 canonical expansion, speculative local H2 and group-step planner; local byte-loop memory helpers explicitly charged. Instruction costs at CPI1/84MHz, not hardware WCET.',
                        'Retimed serial candidate charges all postdecode work after input COMMITTED. Source decoder/control remains prior280 cost replay; live output ARM/IRQ and actual ROM arbitration retained.',
                        'No source/planner IRQ preemption or full firmware integration. Group callbacks retain original batch packing into diagnostic storage, not a streaming E9 consumer.',
                        'Forced geometry boundary is ARM/packing-only. No new FPGA packetizer or early ROM lease; extra SPI/CS values are allocations, not end-to-end latency bounds.',
                        'Early H2 is byte-exact but not substituted for the live output ARM H2 producer; both costs are conservatively charged. CPU279 bus trace reused; no live65816/activeVBlank/fullprogramROM/physical60fps.',
                        'Shared admission context removes duplication but host executor and independent validator remain. Whole MAP delta includes mapping changes outside the selected boundary.'],
                input_hashes=pins,script_sha256=sha(Path(__file__)))
    for name,rows in [('costs.csv',schedules['test01']),('restricted.csv',schedules['window01'])]:
        with (d/name).open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=rows[0],lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('passed','warm_max','restricted_ROM','area')},ensure_ascii=False))


if __name__=='__main__':main()
