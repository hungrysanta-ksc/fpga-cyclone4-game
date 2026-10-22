# SPDX-License-Identifier: MIT
"""Measure common descriptor/manifest/receipt execution with unchanged ARM296."""
import argparse,ast,csv,json,re
from pathlib import Path
from probe_nes_arm264 import ELFFile
from nes_delta231 import BASE,ROOT,sha

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    b=a.base.resolve();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    def loaded(p):
        with pin(p).open('rb') as fp:return [(s['p_vaddr'],s['p_memsz'],s['p_flags'],s.data()) for s in ELFFile(fp).iter_segments() if s['p_type']=='PT_LOAD']
    prior={n:js(ROOT/f'analysis/joint{n}-verification.json') for n in (295,296)}
    oldbase=BASE/'probes/nes-joint295';armbase=BASE/'probes/nes-joint296'
    oldlive=js(oldbase/'test03/result.json');board=js(b/'board01/result.json')
    schedules={};services=[];critical=[]
    for tag,mode in [('test04','normal'),('window04','restricted')]:
        q=b/tag;r=js(q/'result.json');assert r['passed'] and r['frames']==3
        changed={'nes_mux260.sv','nes_validator278.sv','nes_joint257.sv','nes_joint266.sv'}
        assert {n for n,h in r['rtl_hashes'].items() if h!=oldlive['rtl_hashes'][n]}==changed
        for name,h in r['rtl_hashes'].items():assert sha(pin(q/name))==h
        assert loaded(q/'output.elf')==loaded(armbase/'test02/output.elf')
        assert r['tb_sha256']==sha(pin(q/'joint266_tb.sv'))
        for name in ('nes_bg293.py','nes_bg294.py','nes_bg295.py','nes_stage290.py','nes_close295.py','probe_nes_live295.py','nes_wait296.py','nes_joint298.py','probe_nes_live298.py'):
            assert r['input_hashes'][name]==sha(pin(ROOT/'tools'/name))==sha(pin(q/name))
        for p in q.iterdir():
            if p.suffix in ('.c','.h','.inc','.s','.ld'):pin(p)
        events=list(csv.reader(pin(q/'joint-events.csv').open()))
        source={int(x['frame']):x for x in csv.DictReader(pin(q/'cycles.csv').open())}
        rows=[];last=[0,0,0]
        for event in (e for e in events if e[0]=='frame_done'):
            f=int(event[1]);es=[e for e in events if int(e[1])==f];spi=[e for e in es if e[0]=='arm267'];wait=[e for e in es if e[0]=='wait284']
            nr=next(x for x in r['ARM']['frames'] if x['frame']==f)
            before={n:next(x for x in prior[n][mode] if x['frame']==f) for n in prior}
            transfers=js(q/f'arm{f}.json');oracle=js(armbase/('test02' if mode=='normal' else 'window02')/f'arm{f}.json')
            isolated=js(BASE/'probes/nes-joint297'/('test01' if mode=='normal' else 'window01')/f'arm{f}.json')
            e1=lambda z:[t['tx'] for t in z['transfers'] if t['tx'].startswith('e1')]
            assert e1(transfers)==e1(oracle)
            credits=[int(e[2]) for e in es if e[0]=='credits'];assert credits and max(credits)<=4
            assert len([e for e in es if e[0]=='checkpoint287'])==31
            src=int(source[f]['total'])*45.454/1e6;out=int(event[3])/1e9;total=src+out
            counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,last)];last=counters
            completed=[e for e in nr['service296'] if e['after_done']!=e['before_done']];assert len(completed)==1
            receipt_events=sum(e[0]=='receipt' for e in es)
            assert receipt_events==sum(e[0]=='consume293' and e[2]=='2' for e in es) and receipt_events>0
            services.extend(dict(mode=mode,frame=f,**e) for e in completed)
            rows.append(dict(frame=f,source_ms=src,output_ms=out,total_ms=total,margin_ms=1000/60-total,
                before295_ms=before[295]['total_ms'],delta_vs295_ms=total-before[295]['total_ms'],before296_ms=before[296]['total_ms'],delta_vs296_ms=total-before[296]['total_ms'],
                ARM_instructions=nr['instructions'],SPI_bytes=nr['SPI_bytes'],E2=sum(int(e[2])==226 for e in spi),E9=sum(int(e[2])==233 for e in spi),
                timer_fallbacks=sum(int(e[2])==0 for e in wait),IRQ_waits=len(wait),max_credit=max(credits),
                parser_windows_ms=sum(int(e[3]) for e in es if e[0]=='parser')/1e9,map_receipt_windows_ms=sum(int(e[3]) for e in es if e[0]=='receipt')/1e9,
                service_instructions=completed[0]['end_instruction']-completed[0]['instruction'],tile_wait_cycles=inc[0],slot_wait_cycles=inc[1],core_priority_blocks=inc[2],
                receipt_events=receipt_events,ARM_transfer_records_identical297=transfers['transfers']==isolated['transfers']))
            if f==907:critical.append(dict(mode=mode,OBJ_plan_ms=[int(e[-1])/1e9 for e in es if e[0]=='plan293' and e[2]=='1'],OBJ_start_ms=[int(e[-1])/1e9 for e in es if e[0]=='tile293' and e[2]=='1'],tile_receipt_ms=[int(e[-1])/1e9 for e in es if e[0]=='consume293' and e[2]=='1']))
        assert len(rows)==3;schedules[mode]=rows
    # Exact loaded code identity binds the old directed ARM tests, not new executions.
    reused={}
    for tag in ('native01','armguard01','h2guard01','irqguard01'):
        r=js(armbase/tag/'result.json');assert r['passed'] and r['ELF_sha256']==sha(pin(armbase/'window01/output.elf'))
        assert loaded(armbase/'window01/output.elf')==loaded(b/'test04/output.elf')
        reused[tag]=dict(result_sha256=sha(armbase/tag/'result.json'),fresh=False)
    guard=js(b/'guards02/result.json');assert guard['passed'] and len(guard['guards'])==42
    for name,h in guard['rtl_hashes'].items():
        assert sha(pin(b/'guards02'/name))==h
        if (b/'test04'/name).exists():assert sha(pin(b/'test04'/name))==h
    for case in guard['guards']:assert f'PASS HOST278 GNEG={case}' in pin(b/'guards02'/f'guard{case}.log').read_text()
    for name in ('nes_joint298.py','guard_nes_joint298.py'):
        assert guard['entry_hashes'][name]==sha(pin(ROOT/'tools'/name))==sha(pin(b/'guards02'/name))
    close=js(oldbase/'close02/result.json');assert close['passed']
    assert close['rtl_hashes']['nes_plan_batch206.sv']==sha(pin(b/'test04/nes_plan_batch206.sv'))
    reused['close02']=dict(result_sha256=sha(oldbase/'close02/result.json'),fresh=False)
    # Verify the retained whole-board inputs and the bus-observation port normalization.
    for name,h in board['actual_inputs'].items():assert sha(pin(b/'board01'/name))==h
    for name in ('nes_plan_batch206.sv','nes_tile_producer260.sv','nes_validator278.sv'):
        assert sha(pin(b/'board01'/name))==sha(pin(b/'test04'/name))
    host=pin(b/'board01/nes_mux260.sv').read_bytes().replace(b' output wire tile_closed267,\n',b'').replace(b' reg tiles_closed;assign tile_closed267=tiles_closed;',b' reg tiles_closed;')
    assert host==pin(b/'test04/nes_mux260.sv').read_bytes()
    raw=pin(b/'board01/output_files/board.map.summary').read_text();whole={}
    assert 'Lite Edition' in raw
    pin(ROOT/'tools/map_nes_joint298.py');pin(b/'board01/map_nes_joint298.py')
    for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:whole[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',raw).group(1).replace(',',''))
    assert board['passed'] and not board['undriven']
    # Only passive observation was added after MAP. Bind the full RTL transform
    # (including shared port constants), not merely its final function name.
    def transform_ast(p):
        t=ast.parse(pin(p).read_text())
        t.body=[x for x in t.body if not(isinstance(x,ast.FunctionDef) and x.name=='observe')]
        return ast.dump(t,include_attributes=False)
    assert transform_ast(b/'board01/nes_joint298.py')==transform_ast(ROOT/'tools/nes_joint298.py')
    baseline=js(oldbase/'board01/result.json')
    for name,h in board['actual_inputs'].items():
        if name not in changed:assert h==baseline['actual_inputs'][name],name
    own={}
    for line in pin(b/'board01/output_files/board.map.rpt').read_text().splitlines():
        f=[x.strip() for x in line.split(';')]
        if len(f)==14 and re.fullmatch(r'\d+ \(\d+\)',f[2]):own[f[10]]=int(re.search(r'\((\d+)\)',f[2]).group(1))
    assert sum(own.values())==whole['comb']
    report=(b/'board01/output_files/board.map.rpt').read_text()
    fsms=[x.strip() for x in report.splitlines() if 'State Machine -' in x and
          any(y in x for y in ('nes_validator278:validator|state','nes_output260:flow|state'))]
    assert any('nes_validator278:validator|state' in x for x in fsms)
    assert any('nes_output260:flow|state' in x for x in fsms)
    def region(s,tree=False):return sum(v for k,v in own.items() if (s in k if tree else k.endswith(s)))
    regions=dict(host=region('nes_output260:flow'),validator=region('nes_validator278:validator'),queue=region('nes_queue260:queue',True),plan=region('nes_plan_batch206:transport',True)+region('nes_plan_spi200:endpoint',True),SPI=region('nes_spi270:spi_front270',True),glue=region('nes_joint267_board:native_joint267')+region('nes_joint257:core'))
    deficit=whole['comb']-15408;fixed=sum(regions.values());outside=whole['comb']-fixed
    budget=[]
    for name,cost in [('host_validator',regions['host']+regions['validator']),('fixed_boundary',fixed)]:
        budget.append(dict(candidate=name,current_comb=cost,replacement_budget=cost-deficit,reserve128_budget=cost-deficit-128,required_reduction=deficit,required_percent=100*deficit/cost,measured_replacement_comb=cost,reference297_comb=3440 if name=='host_validator' else 4847))
    # Bind actual replacement and unchanged independent datapaths, not state-count estimates.
    flow=pin(b/'test04/nes_mux260.sv').read_text();validator=pin(b/'test04/nes_validator278.sv').read_text()
    previous_flow=pin(oldbase/'test03/nes_mux260.sv').read_text();previous_validator=pin(oldbase/'test03/nes_validator278.sv').read_text()
    def section(s,start,end):return s[s.index(start):s.index(end,s.index(start))]
    assert section(flow,' // Capture only',' // Original descriptor')==section(previous_flow,' // Capture only',' // Original descriptor')
    assert section(flow,' // Original descriptor',' // One command handshake')==section(previous_flow,' // Original descriptor',' wire manifest_byte282=')
    assert section(validator,' always @*begin\n  v_addr=context_addr',' task advance_range')==section(previous_validator,' always @*begin\n  v_addr=context_addr',' task advance_range')
    assert all(x not in flow for x in ('ordinary_mode','opos','oend','rle_left','rle_zero','WAIT_RECEIPT:','OCHECKNEXT:','ORLE:','ORET:','OISSUE:','OCERT:','OFINISH:'))
    for x in ('if(rec_i!=0||cursor!=0||!v_count||range_end283>domain_end283',
              'V_RWRITE:if(!crc_covered287)fault<=7;else if(v_q&v_mask)fault<=2;',
              'V_PCHECKTEST:if(checked_byte!=v_value||ram_q!=255)fault<=3;',
              'if(cursor!=422||!v_all_consumed||!certificate_ok)',
              'if(h_count!=12)fault<=7;',
              'if(reset||abort_source||fault||(state!=V_CLEARALL&&!lease_ok))v_we=0;'):assert x in validator,x
    review=[dict(part='descriptor/receipt',removed='host WAIT_RECEIPT/ORET relay; common completion owns return',retained='original descriptor and exact-read/token/ordered ACK; independent widened domain and CRC/duplicate/persistent RAM checks'),
            dict(part='manifest',removed='host ordinary_mode/opos/oend/rle state and OCHECKNEXT/ORLE byte return',retained='one engine encoded cursor plus separate 422-byte expanded cursor and checked_byte; registered queue and phase RAM latency'),
            dict(part='certificate/seal',removed='host OISSUE/OCERT/OFINISH relay',retained='digest/certificate CRC and all-consumed seal, 12 exact display reads and final ACK'),
            dict(part='concurrent observer',removed='none',retained='byte-identical SNES strobe/pattern CRC tap and RAM mux/write gate')]
    result=dict(passed=True,stage=298,normal=schedules['normal'],restricted=schedules['restricted'],service_events=services,critical907=critical,
        ARM_loaded_identical296=True,RTL_hash_identical295=False,whole_MAP=whole,comb_deficit=deficit,area=dict(regions=regions,fixed_boundary=fixed,outside=outside,budget=15408-outside,delta_vs297={k:whole[k]-prior[295]['whole_MAP'][k] for k in whole}),
        reuse=reused,new_MAP=True,new_RTL=True,new_live_frames=6,joint_replacement_implemented=True,RTL_guards=guard['guards'],FSM_extracted=True,budgets=budget,joint_review=review,
        scope='Actual shared descriptor/manifest/receipt/certificate engine and unchanged ARM296; fresh live IRQ/SPI/ROM and 42 RTL guards, whole Lite MAP. ARM unit/71 and close decoder evidence reused by hashes. Source replay/CPI1/IRQ overhead allocation and modeled map/tile/display bus remain.',
        full_schedule71=False,full_RUN=False,physical=False,FIT=False,STA=False,input_hashes=pins,script_sha256=sha(Path(__file__)))
    for name,rows in [*schedules.items(),('control',review),('budget',budget)]:
        with (d/f'{name}.csv').open('w',newline='',encoding='utf-8') as fp:w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:result[k] for k in ('passed','normal','restricted','area','comb_deficit')}))

if __name__=='__main__':main()
