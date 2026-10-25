"""Bind actual ARM/IRQ/ROM schedules, independent guards and whole Lite300."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from probe_nes_arm264 import ELFFile

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);a=ap.parse_args();b=a.base.resolve();pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    def loaded(p):
        with pin(p).open('rb') as fp:return [(x['p_vaddr'],x['p_memsz'],x.data()) for x in ELFFile(fp).iter_segments() if x['p_type']=='PT_LOAD']
    old=js(ROOT/'analysis/joint298-verification.json');base300=js(ROOT/'analysis/arch300-verification.json');base302=js(ROOT/'analysis/slice302-verification.json');baseline=BASE/'probes/nes-joint298/test04'
    schedules={};services=[];all_results={}
    for tag,mode,ref in [('test03','normal','normal'),('window01','restricted','restricted')]:
        q=b/tag;r=js(q/'result.json');assert r['passed'];all_results[tag]=r
        for name,h in r['rtl_hashes'].items():assert sha(pin(q/name))==h
        assert sha(pin(q/'joint266_tb.sv'))==r['tb_sha256']
        for p in q.iterdir():
            if p.suffix in ('.c','.h','.inc','.s','.ld'):pin(p)
        if tag=='isolated01':assert loaded(q/'output.elf')==loaded(baseline/'output.elf')
        elif tag=='window01':assert loaded(q/'output.elf')==loaded(b/'test03/output.elf')
        else:assert loaded(q/'output.elf')!=loaded(baseline/'output.elf')
        source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(pin(q/'cycles.csv').open())}
        events=list(csv.reader(pin(q/'joint-events.csv').open()));rows=[];last=[0,0,0]
        for event in (e for e in events if e[0]=='frame_done'):
            f=int(event[1]);es=[e for e in events if int(e[1])==f];nr=next(x for x in r['ARM']['frames'] if x['frame']==f)
            t=js(q/f'arm{f}.json');prior=js(BASE/'probes/nes-joint298'/('test04' if ref=='normal' else 'window04')/f'arm{f}.json')
            e1=lambda x:[v['tx'] for v in x['transfers'] if v['tx'].startswith('e1')]
            assert e1(t)==e1(prior),('original payload order',f)
            assert [v['tx'] for v in t['transfers'] if v['tx'].startswith('e9')]==[v['tx'] for v in prior['transfers'] if v['tx'].startswith('e9')],('original plan wire',f)
            credit=[int(e[2]) for e in es if e[0]=='credits'];assert credit and max(credit)<=4
            assert sum(e[0]=='checkpoint287' for e in es)==sum(e.get('checkpoint287',False) for e in t['transfers'])
            receipt=sum(e[0]=='receipt' for e in es);assert receipt==sum(e[0]=='consume293' and e[2]=='2' for e in es)
            counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,last)];last=counters
            before=next(x for x in old[ref] if x['frame']==f);total=source[f]+int(event[3])/1e9
            rows.append(dict(frame=f,source_ms=source[f],output_ms=int(event[3])/1e9,total_ms=total,prior298_ms=before['total_ms'],delta_ms=total-before['total_ms'],margin_ms=1000/60-total,ARM_instructions=nr['instructions'],SPI_bytes=nr['SPI_bytes'],max_credit=max(credit),E2=sum(e[0]=='arm267' and int(e[2])==226 for e in es),E9=sum(e[0]=='arm267' and int(e[2])==233 for e in es),timer_fallbacks=sum(e[0]=='wait284' and int(e[2])==0 for e in es),slot_wait_cycles=inc[1],core_priority_blocks=inc[2],map_receipts=receipt))
            rows[-1]['prior302_ms']=next(x['total_ms'] for x in base302[ref] if x['frame']==f)
            services.extend(dict(mode=mode,frame=f,published_prefix_remaining=e['before_size']-e['plan_at'],**e) for e in nr['service296'])
        assert len(rows)==3;schedules[mode]=rows
    for tag in ('window01',):assert all_results[tag]['rtl_hashes']==all_results['test03']['rtl_hashes']
    guard=js(b/'guards01/result.json');assert guard['passed'] and len(guard['guards'])==44
    for n,h in guard['rtl_hashes'].items():
        assert sha(pin(b/'guards01'/n))==h
        if n in all_results['test03']['rtl_hashes']:assert h==all_results['test03']['rtl_hashes'][n]
    assert sha(pin(b/'guards01/joint266_tb.sv'))==guard['TB_sha256']
    for n in guard['guards']:assert f'PASS HOST278 GNEG={n}' in pin(b/'guards01'/f'guard{n}.log').read_text()
    armguards={}
    for tag in ('native01','armguard01','credit01','supply01','wait01','h2guard01','irqguard01'):
        z=js(b/tag/'result.json');assert z['passed'] and z['ELF_sha256']==sha(b/'test03/output.elf');armguards[tag]=dict(fresh=True,checks=z.get('checks',z.get('cases',z.get('guards'))),frames=len(z.get('frames',[])))
    for tag,name in {'native01':'probe_nes_native302.py','armguard01':'guard_nes_slice302.py','credit01':'guard_nes_credit302c.py','supply01':'guard_nes_supply303.py','wait01':'guard_nes_wait303.py','h2guard01':'guard_nes_h2302.py','irqguard01':'guard_nes_irq284.py'}.items():
        assert js(b/tag/'result.json')['script_sha256']==sha(pin(ROOT/'tools'/name))
    native=js(b/'native01/result.json')
    assert len(native['frames'])==71 and sum(x['packets'] for x in native['frames'])==1039
    assert sum(x['bytes'] for x in native['frames'])==73260 and native['fixture_reads']==0
    board=js(b/'board02/result.json');assert board['passed'] and not board['undriven']
    for n,h in board['actual_inputs'].items():assert sha(pin(b/'board02'/n))==h
    priorboard=js(BASE/'probes/nes-arch300/board01/result.json')
    changed={n for n,h in board['actual_inputs'].items() if h!=priorboard['actual_inputs'][n]}
    assert changed=={'nes_mux260.sv','nes_validator278.sv'}
    assert sha(b/'board02/nes_validator278.sv')==sha(b/'test03/nes_validator278.sv')
    host=(b/'board02/nes_mux260.sv').read_bytes().replace(b' output wire tile_closed267,\n',b'').replace(b' reg tiles_closed;assign tile_closed267=tiles_closed;',b' reg tiles_closed;')
    assert host==(b/'test03/nes_mux260.sv').read_bytes()
    for n in ('nes_record305.py',):
        assert sha(pin(ROOT/'tools'/n))==sha(pin(b/'board02'/n))==sha(pin(b/'test03'/n))
    report=pin(b/'board02/output_files/board.map.rpt').read_text();summary=pin(b/'board02/output_files/board.map.summary').read_text();whole={};own={}
    assert 'Lite Edition' in summary
    assert 'nes_validator278:validator|state' in report and 'nes_output260:flow|state' in report
    for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:whole[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',summary).group(1).replace(',',''))
    for line in report.splitlines():
        f=[x.strip() for x in line.split(';')]
        if len(f)==14 and re.fullmatch(r'\d+ \(\d+\)',f[2]):own[f[10]]=int(re.search(r'\((\d+)\)',f[2]).group(1))
    assert sum(own.values())==whole['comb']
    def region(s,tree=False):return sum(v for k,v in own.items() if (s in k if tree else k.endswith(s)))
    regions=dict(host=region('nes_output260:flow'),validator=region('nes_validator278:validator'),queue=region('nes_queue260:queue',True),plan=region('nes_plan_batch206:transport',True)+region('nes_plan_spi200:endpoint',True),SPI=region('nes_spi270:spi_front270',True),glue=region('nes_joint267_board:native_joint267')+region('nes_joint257:core'))
    flow=(b/'test03/nes_mux260.sv').read_text();oldflow=(baseline/'nes_mux260.sv').read_text()
    def section(s,a,z):return s[s.index(a):s.index(z,s.index(a))]
    assert section(flow,' // Capture only',' // Original descriptor').replace('wire [12:0] tap_end278=descriptor_end287[12:0];',"wire [12:0] tap_end278={1'b0,startpos[11:0]}+{1'b0,outlen[11:0]};")==section(oldflow,' // Capture only',' // Original descriptor')
    v=(b/'test03/nes_validator278.sv').read_text()
    for anchor in ('range_end283>domain_end283','V_RWRITE:if(!crc_covered287)fault<=7;else if(v_q&v_mask)fault<=2;','V_PCHECKTEST:if(checked_byte!=v_value||ram_q!=255)fault<=3;','if((!map_phase305||cursor!=256)||!v_all_consumed||!certificate_ok)','if(h_count!=12)fault<=7;','if(reset||abort_source||fault||(state!=V_CLEARALL&&!lease_ok))v_we=0;'):assert anchor in v
    result=dict(passed=True,stage=305,**schedules,service_events=services,whole_MAP=whole,delta_MAP={k:whole[k]-base300['whole_MAP'][k] for k in whole},regions=regions,fixed_boundary=sum(regions.values()),outside=whole['comb']-sum(regions.values()),fixed_budget=15408-whole['comb']+sum(regions.values()),comb_deficit=whole['comb']-15408,fresh_RTL_guards=44,ARM_checks=armguards,new_live_frames=6,new_MAP=True,full_schedule71=False,full_RUN=False,actual_SNES_live=False,FIT=False,STA=False,physical=False,scope='Actual active-record replacement and page-local validator addresses; unchanged ARM303 supply priority. Source replay, CPI1/84MHz, IRQ allocation, ordinary65816 trace and map/tile/display bus model retained.',input_hashes=pins,script_sha256=sha(Path(__file__)))
    size=(b/'test03/size287.log').read_text().splitlines()[-1].split()
    result['ARM_memory']=dict(text=int(size[0]),data=int(size[1]),bss=int(size[2]),observed_stack=all_results['test03']['ARM'].get('stack_observed'))
    result['ARM_continuation']=js(b/'armguard01/result.json')
    result['selected']=False
    result['FSM_extracted']=['host state','validator state']
    result['changed_whole_inputs']=sorted(changed)
    result['scope_limitations']=['Source replay; actual M4 instructions with CPI1/84MHz and IRQ24 allocation','ordinary65816 trace plus map/tile/display bus model; no full live65816','Combined ARM/RTL effect only; no isolated causal speedup','Header raw storage and typed copies replaced; queue/SPI/plan ingress remains','One fresh whole Lite MAP; no FIT/STA/physical60fps']
    for name in ('nes_record305.py','probe_nes_live305.py','guard_nes_record305.py','guard_nes_supply303.py','guard_nes_wait303.py','guard_nes_irq293.py','map_nes_record305.py'):
        pin(ROOT/'tools'/name)
    previous303=js(ROOT/'analysis/joint303-verification.json')
    assert loaded(b/'test03/output.elf')==loaded(BASE/'probes/nes-joint303/test01/output.elf')
    result['unchanged_ARM303_load_segments']=True
    rom=[]
    for tag,mode in [('test03','normal'),('window01','restricted')]:
        events=list(csv.reader(pin(b/tag/'joint-events.csv').open()))
        for f in (905,906,907):
            es=[e for e in events if int(e[1])==f]
            for kind in ('0','1'):
                plans=[e for e in es if e[0]=='romplan305' and e[2]==kind]
                tiles=[e for e in es if e[0]=='romtile305' and e[2]==kind]
                if not plans or not tiles:continue
                first=plans[0];tile=tiles[0];cycle=int(first[3]);phase=cycle%357368
                until_open=330088-phase if phase<330088 else 0 if phase<354640 else 357368-phase+330088
                rom.append(dict(mode=mode,frame=f,kind=int(kind),first_plan_cycle=cycle,phase=phase,first_tile_cycle=int(tile[4]),first_plan_ms=int(first[-1])/1e9,first_tile_ms=int(tile[-1])/1e9,plan_to_tile_ms=(int(tile[-1])-int(first[-1]))/1e9,window_open_wait_ms=until_open*45.454/1e6 if mode=='restricted' else 0,plan_count=len(plans),tile_count=len(tiles),last_tile_ms=int(tiles[-1][-1])/1e9,first_tile_cumulative_slot=int(tile[5]),first_tile_cumulative_core=int(tile[6]),first_tile_cumulative_other=int(tile[7]),first_tile_cumulative_rom_reads=int(tile[8])))
    for mode,rows in schedules.items():
        for row in rows:
            row['prior303_ms']=next(x['total_ms'] for x in previous303[mode] if x['frame']==row['frame'])
            row['delta303_ms']=row['total_ms']-row['prior303_ms']
    diagnostic=js(b/'window02/result.json');assert diagnostic['passed']
    assert diagnostic['rtl_hashes']==all_results['window01']['rtl_hashes']
    for n,h in diagnostic['rtl_hashes'].items():assert sha(pin(b/'window02'/n))==h
    assert sha(pin(b/'window02/joint266_tb.sv'))==diagnostic['tb_sha256']
    assert loaded(b/'window02/output.elf')==loaded(b/'test03/output.elf')
    de=list(csv.reader(pin(b/'window02/joint-events.csv').open()))
    before=list(csv.reader(pin(b/'window01/joint-events.csv').open()))
    assert [e for e in de if e[0]=='frame_done']==[e for e in before if e[0]=='frame_done']
    trace=[]
    for f in (905,906,907):
        for kind in ('0','1'):
            request=next(e for e in de if e[:3]==['firstreq305',str(f),kind])
            miss=next(e for e in de if e[:3]==['firstmiss305',str(f),kind])
            tile=next(e for e in de if e[:3]==['romtile305',str(f),kind])
            assert int(miss[4])==1 and int(miss[5])==0
            trace.append(dict(frame=f,kind=int(kind),request_cycle=int(request[3]),request_qualified=int(request[4]),request_hit=int(request[5]),request_pending=int(request[6]),request_ready=int(request[7]),request_ms=int(request[-1])/1e9,first_miss_grant_cycle=int(miss[3]),first_miss_grant_ms=int(miss[-1])/1e9,first_tile_ms=int(tile[-1])/1e9))
    for row in trace:
        row['request_to_grant_ms']=row['first_miss_grant_ms']-row['request_ms']
        row['grant_to_first_tile_ms']=row['first_tile_ms']-row['first_miss_grant_ms']
    result['ROM_first_request_and_grant']=trace
    result['diagnostic_replay_frames']=3
    result['diagnostic_replay_same_completion']=True
    result['ROM_diagnostics']=rom
    assert 'reg [7:0] header[0:20]' not in flow
    assert 'reg [11:0] length,first,count' not in flow
    assert 'wire [7:0] header[0:20]' in flow and 'active_t305 active305;' in flow
    assert 'wire [16:0] descriptor_end287=active305.endpos;' in flow
    assert "v_addr={1'b1,v_mapmode,v_bit_at[10:3]};" in v
    assert "v_addr={1'b0,v_bank,v_bit_at[10:3]};" in v
    result['active_record_bits']=145
    result['active_record_plus_packet_cursor_bits']=154
    assert 154<=160
    result['removed_logical_storage_upper_bits']=189-154
    # Exhaustive address identity over admitted domains; actual cold bank0/1
    # RTL runs and negative bounds remain separate evidence.
    equalities=0
    def address(old,new):
        nonlocal equalities
        assert old==new and 0<=new<1024;equalities+=1
    for bit in range(1328):
        address(512+(bit>>3),512|((bit>>3)&255))
        for bank in (0,1):address(bank*256+(bit>>3),(bank<<8)|((bit>>3)&255))
    for bit in range(2048):address(768+(bit>>3),768|((bit>>3)&255))
    for bank in (0,1):
        for c in range(422):
            oldaddr=bank*256+c if c<144 else 512+c if c<166 else 768+c-166
            phase,local=(0,c) if c<166 else (1,c-166)
            address(oldaddr,((3 if phase else bank if local<144 else 2)<<8)|(local&255))
        for idx in range(32):address(448+bank*32+idx,(7<<6)|(bank<<5)|idx)
    for a in (683,699,700,694,695,696,697,698,712,713,714,715):address(a,512|(a-512))
    assert equalities==6952
    result['address_model_equalities']=equalities
    result['remaining_required_comb']=result['comb_deficit']
    result['input_hashes']=pins
    (ROOT/'analysis/record305-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    for name,rows in schedules.items():
        with (ROOT/f'analysis/record305-{name}.csv').open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print(json.dumps({k:result[k] for k in ('normal','restricted','whole_MAP','delta_MAP','regions','comb_deficit')},indent=2))

if __name__=='__main__':main()
