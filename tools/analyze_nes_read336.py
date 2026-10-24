# SPDX-License-Identifier: MIT
"""Bind actual read-owned RTL, ARM E9 CRC, same-phase schedules and whole Lite."""
import argparse,csv,json,re
from collections import Counter
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from analyze_nes_execute334 import wire
from analyze_nes_receipt335 import completed_unit,load_image
from probe_nes_arm264 import ELFFile


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');a=ap.parse_args()
    root=BASE/'probes/nes-read336';pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    old=js(ROOT/'analysis/execute334-verification.json');area=js(ROOT/'analysis/execute332-verification.json')
    runs={};final_rtl=None
    for tag,ref in [('window01','arm-window01'),('fixed01','arm-fixed01'),('normal01','arm-normal01'),('rtl-fixed01','arm-fixed01'),('arm-fixed01','arm-fixed01')]:
        d=root/tag;prior=BASE/'probes/nes-execute334'/ref
        if not (d/'result.json').exists():assert a.partial,tag;continue
        r=js(d/'result.json');pr=js(prior/'result.json');assert r['passed']
        changed={n for n,h in r['rtl_hashes'].items() if h!=pr['rtl_hashes'][n]}
        assert changed==(set() if tag.startswith('arm-') else {'nes_mux260.sv','nes_validator278.sv','nes_joint266.sv'}),(tag,changed)
        for n,h in r['rtl_hashes'].items():read(d/n);assert sha(d/n)==h
        if not tag.startswith('arm-'):
            if final_rtl is None:final_rtl=r['rtl_hashes']
            else:assert final_rtl==r['rtl_hashes']
        for n in ('CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc'):
            pins[str(d/n)]=sha(d/n);assert sha(d/n)==sha(prior/n)
        for fixture in d.iterdir():
            if fixture.is_file() and fixture.suffix in ('.hex','.expected','.palette','.lens','.desc'):
                pins[str(fixture)]=sha(fixture)
                assert (prior/fixture.name).exists() and sha(fixture)==sha(prior/fixture.name),(tag,fixture.name,'fixture changed')
        pins[str(d/'output.elf')]=sha(d/'output.elf');assert sha(d/'output.elf')==r['ELF_sha256']
        if tag.startswith('rtl-'):assert load_image(d/'output.elf')==load_image(prior/'output.elf')
        read(d/'joint266_tb.sv');assert sha(d/'joint266_tb.sv')==r['tb_sha256']
        assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log')
        ev=list(csv.reader(read(d/'joint-events.csv').splitlines()))
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(d/'cycles.csv').splitlines())}
        rows=[]
        for prev in old['runs'][ref]['rows']:
            f=prev['frame'];events=[x for x in ev if len(x)>1 and x[1]==str(f)]
            first=lambda n:next(x for x in events if x[0]==n)
            start=first('start319');finish=first('frame_done');request=next(x for x in events if x[0]=='firstreq305' and x[2]=='0');accept=next(x for x in events if x[0]=='rom_accept327' and x[2]=='0')
            total=source[f]+int(finish[3])/1e9;start_ms=int(start[2])/1e9;finish_ms=int(finish[2])/1e9;accept_ms=int(accept[-1])/1e9;request_ms=int(request[-1])/1e9
            if 'fixed' in tag:assert start_ms==prev['start_ms'] and int(start[3])==prev['start_ROM_cycle']
            tr=js(d/f'arm{f}.json')['transfers'];assert wire(tr)==wire(js(prior/f'arm{f}.json')['transfers']),(tag,f,'wire')
            arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
            credit=max(int(x[2]) for x in events if x[0]=='credits');assert credit<=2
            assert sum(int(x[3]) for x in events if x[0]=='arm267')==arm['SPI_bytes']
            counts=Counter();max_job_ps=0;read_job=None;read_offset=0;units=[];observed=[];write_times=[];last_unit=None;receipt={};published=0;chunk_token=None
            for x in events:
                if x[0]=='read336':
                    token,op,section,pos,offset,data,t=map(int,x[2:]);assert offset==read_offset,(tag,f,x)
                    if not read_offset:chunk_token=token
                    assert token==chunk_token
                    read_offset+=1;counts['read_bytes']+=1;read_job=t
                    # All current replay frames have raw tables; raw0 is a
                    # separate public-port test, not inferred from this corpus.
                    u=completed_unit(op,section,pos,2)
                    if u:units.append((token,int(u[0]),u[1]));last_unit=None
                elif x[0]=='unit336':
                    token,ismap,unit,t=map(int,x[2:]);observed.append((token,ismap,unit));last_unit=(ismap,unit);counts['units']+=1
                elif x[0]=='private336':
                    token,addr,value,t=map(int,x[2:]);assert last_unit is not None
                    assert token==chunk_token
                    ismap,u=last_unit;bit=1<<(u%8)
                    if addr>=512:
                        assert addr==(768 if ismap else 512)+u//8
                        assert not receipt.get(addr,0)&bit;receipt[addr]=receipt.get(addr,0)|bit;assert value==receipt[addr]
                    else:assert not ismap and addr%256==u//8 and value&bit
                    assert read_job is not None and t>read_job;max_job_ps=max(max_job_ps,t-read_job);write_times.append(t);counts['private_writes']+=1
                elif x[0]=='publish336':
                    token,n,t=map(int,x[2:]);assert token==chunk_token and n==read_offset and n>0 and all(z<t for z in write_times)
                    read_offset=0;write_times=[];published+=1;chunk_token=None
            if not tag.startswith('arm-'):
                assert units==observed and read_offset==0,(tag,f,'actual coverage/ACK')
                counts['published_chunks']=published
            rows.append(dict(frame=f,total_ms=total,delta_ms=total-prev['total_ms'],start_ms=start_ms,start_delta_ms=start_ms-prev['start_ms'],finish_ms=finish_ms,finish_delta_ms=finish_ms-prev['finish_ms'],start_ROM_cycle=int(start[3]),
                source_ms=source[f],first_request_ms=request_ms,request_delta_ms=request_ms-prev['request_ms'],first_accept_ms=accept_ms,accept_delta_ms=accept_ms-prev['first_ROM_accept_ms'],post_ROM_ms=finish_ms-accept_ms,post_ROM_delta_ms=finish_ms-accept_ms-prev['post_ROM_ms'],
                gap_ms=total-1000/60,post_ROM_cap_gap_ms=finish_ms-accept_ms-3.18,ARM_instructions=arm['instructions'],instruction_delta=arm['instructions']-prev['ARM_instructions'],SPI_bytes=arm['SPI_bytes'],SPI_delta=arm['SPI_bytes']-prev['SPI_bytes'],max_credit=credit,
                read_jobs=dict(counts),receipt_RAM_cycles_derived=2*counts['private_writes'],receipt_RAM_us_derived=2*counts['private_writes']*11.904/1000,max_read_to_private_write_ns=max_job_ps/1000,wire_identical=True))
        with (d/'output.elf').open('rb') as stream:
            elf=ELFFile(stream);sections={n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.bss','.data')}
        runs[tag]=dict(rows=rows,sections=sections,stack=r['ARM']['stack_observed'],IRQ_cases=len(r['ARM']['IRQ_cases']),EXTI=len(r['ARM']['EXTI284']),IRQ_model={k:r['ARM'][k] for k in ('hardware_cycles','full_RUN','IRQ_body_service_boundary','IRQ_entry_exit_cycles','IRQ_preemption_modeled')})
    if a.partial:print(json.dumps(runs,indent=2));return
    br=js(root/'board01/result.json');assert br['passed']
    old_board=js(BASE/'probes/nes-execute332/board03/result.json')
    assert {n for n,h in br['actual_inputs'].items() if h!=old_board['actual_inputs'].get(n)}=={'nes_joint266.sv','nes_mux260.sv','nes_validator278.sv'}
    for n,h in br['actual_inputs'].items():read(root/'board01'/n);assert sha(root/'board01'/n)==h
    assert sha(root/'board01/nes_validator278.sv')==final_rtl['nes_validator278.sv']
    # The production board exports the unchanged tiles_closed status, while
    # the replay wrapper reads it hierarchically. Normalize only those two
    # known lines, and require every other byte of the actual host to match.
    board_host=read(root/'board01/nes_mux260.sv')
    assert board_host.count(' output wire tile_closed267,\n')==1
    assert board_host.count('reg tiles_closed;assign tile_closed267=tiles_closed;')==1
    board_host=board_host.replace(' output wire tile_closed267,\n','').replace('reg tiles_closed;assign tile_closed267=tiles_closed;','reg tiles_closed;')
    assert board_host==read(root/'window01/nes_mux260.sv')
    wrapper=read(BASE/'probes/nes-execute332/board03/nes_joint266.sv').replace('assign v_all_consumed=1;','').replace(' flow(',' flow(.jobs_committed336(v_all_consumed),')
    assert wrapper==read(root/'board01/nes_joint266.sv')
    # Board wrapper has additional production ports; compare the actual change
    # against its pinned332 wrapper instead of equating different module names.
    report=read(root/'board01/output_files/board.map.rpt');log=read(root/'board01/map.log')
    assert 'Warning (10034)' not in log
    assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
    whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',br['summary'])[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
    nodes={}
    for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
        c=[x.strip() for x in line.split(';')]
        if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
    assert sum(nodes.values())==whole['comb']
    def own(suffix):
        found=[v for k,v in nodes.items() if k.endswith(suffix)];assert len(found)==1;return found[0]
    def tree(suffix):
        paths=[k for k in nodes if k.endswith(suffix)];assert len(paths)==1
        return sum(v for k,v in nodes.items() if k==paths[0] or k.startswith(paths[0]+'|'))
    groups=dict(host_validator_aperture=own('nes_output260:flow')+own('nes_validator278:validator')+own('nes_bulk_aperture188:shared_ram.aperture'),
        queue_SPI=own('nes_queue260:queue')+own('nes_spi270:spi_front270'),source=own('nes_core257:encoder')+tree('nes_transport257:transport'),
        plan=own('nes_plan_path267:retained_plan267')+tree('nes_plan_batch206:transport')+own('nes_plan_spi200:endpoint'))
    outside=whole['comb']-sum(groups.values())
    guards=js(root/'guards01/partial-result.json');assert guards['passed'] and guards['rtl_hashes']==final_rtl
    assert guards['ELF_sha256']==sha(root/'window01/output.elf')
    read(root/'guards01/joint266_tb.sv');assert sha(root/'guards01/joint266_tb.sv')==guards['tb_sha256']
    read(root/'guards01/case19/vsim.log');assert sha(root/'guards01/case19/vsim.log')==guards['failed_case19_log_sha256']
    for row in guards['cases']:assert sha(root/f"guards01/case{row['case']}/vsim.log")==row['log_sha256'];read(root/f"guards01/case{row['case']}/vsim.log")
    extra={}
    middle=js(root/'guards02/partial-result.json');assert middle['passed'] and middle['rtl_hashes']==final_rtl and middle['ELF_sha256']==guards['ELF_sha256']
    read(root/'guards02/joint266_tb.sv');assert sha(root/'guards02/joint266_tb.sv')==middle['tb_sha256']
    for row in middle['cases']:read(root/f"guards02/case{row['case']}/vsim.log");assert sha(root/f"guards02/case{row['case']}/vsim.log")==row['log_sha256']
    read(root/'guards02/case21/vsim.log');assert sha(root/'guards02/case21/vsim.log')==middle['failed_case21_log_sha256']
    more=js(root/'guards04/result.json');assert more['passed'] and more['rtl_hashes']==final_rtl and more['ELF_sha256']==guards['ELF_sha256']
    assert sorted(x['case'] for x in guards['cases']+middle['cases']+more['cases'])==[3,5,6,7,9,10,17,18,19,20,21,22,23]
    read(root/'guards04/joint266_tb.sv');assert sha(root/'guards04/joint266_tb.sv')==more['tb_sha256']
    for row in more['cases']:read(root/f"guards04/case{row['case']}/vsim.log");assert sha(root/f"guards04/case{row['case']}/vsim.log")==row['log_sha256']
    extra['completed_guards02']=middle
    extra['additional_guards']=more
    for label,sub in [('CRC','crc01'),('raw0_STOP_reset','guards04/final-raw0'),('aperture','guards04/aperture')]:
        z=js(root/sub/'result.json');assert z['passed'];extra[label]=z
        if label=='CRC':
            assert z['ELF_sha256']==sha(root/'window01/output.elf')
            assert z['script_sha256']==sha(ROOT/'tools/check_nes_crc336.py')
        else:
            rtl='nes_validator278.sv' if label=='raw0_STOP_reset' else 'nes_bulk_aperture188.sv'
            tb='final332_tb.sv' if label=='raw0_STOP_reset' else 'aperture325_tb.sv'
            assert z['RTL_sha256']==final_rtl[rtl]
            for n,key in [(rtl,'RTL_sha256'),(tb,'tb_sha256'),('vsim.log','log_sha256')]:read(root/sub/n);assert sha(root/sub/n)==z[key]
            if label=='raw0_STOP_reset':assert z['script_sha256']==sha(ROOT/'tools/check_nes_final336.py')
    read(root/'guards03/case21/vsim.log')
    for n in ('nes_read336.py','probe_nes_read336.py','guard_nes_read336.py','check_nes_crc336.py','check_nes_final336.py','map_nes_read336.py','analyze_nes_read336.py'):read(ROOT/'tools'/n)
    result=dict(stage=336,passed=True,runs=runs,whole=whole,whole_delta={k:whole[k]-area['whole'][k] for k in whole},comb_deficit=whole['comb']-15408,own_entity_comb=nodes,own_entity_delta={k:v-area['own_entity_comb'].get(k,0) for k,v in nodes.items() if v!=area['own_entity_comb'].get(k,0)},groups=groups,outside_comb=outside,scope_capacity=15408-outside,scope_with_132_margin=15276-outside,guards=guards,extra=extra,
        scope='actual M4 instruction/CPI1 model and unchanged325 bus trace; whole Lite MAP, not FIT/STA/physical60fps',pins=pins)
    (ROOT/'analysis/read336-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,whole=whole,comb_deficit=result['comb_deficit'],warm={k:v['rows'][-1] for k,v in runs.items()},pins=len(pins)),indent=2))


if __name__=='__main__':main()
