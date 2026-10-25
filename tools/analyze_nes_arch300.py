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
    old=js(ROOT/'analysis/joint298-verification.json');baseline=BASE/'probes/nes-joint298/test04'
    schedules={};services=[];all_results={}
    for tag,mode,ref in [('test03','normal','normal'),('window01','restricted','restricted'),('isolated01','RTL_only_restricted','restricted')]:
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
            assert sum(e[0]=='checkpoint287' for e in es)==31
            receipt=sum(e[0]=='receipt' for e in es);assert receipt==sum(e[0]=='consume293' and e[2]=='2' for e in es)
            counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,last)];last=counters
            before=next(x for x in old[ref] if x['frame']==f);total=source[f]+int(event[3])/1e9
            rows.append(dict(frame=f,source_ms=source[f],output_ms=int(event[3])/1e9,total_ms=total,prior298_ms=before['total_ms'],delta_ms=total-before['total_ms'],margin_ms=1000/60-total,ARM_instructions=nr['instructions'],SPI_bytes=nr['SPI_bytes'],max_credit=max(credit),E2=sum(e[0]=='arm267' and int(e[2])==226 for e in es),E9=sum(e[0]=='arm267' and int(e[2])==233 for e in es),timer_fallbacks=sum(e[0]=='wait284' and int(e[2])==0 for e in es),slot_wait_cycles=inc[1],core_priority_blocks=inc[2],map_receipts=receipt))
            services.extend(dict(mode=mode,frame=f,published_prefix_remaining=e['before_size']-e['plan_at'],**e) for e in nr['service296'] if e.get('after_done')!=e['before_done'])
        assert len(rows)==3;schedules[mode]=rows
    for tag in ('window01','isolated01'):assert all_results[tag]['rtl_hashes']==all_results['test03']['rtl_hashes']
    guard=js(b/'guards01/result.json');assert guard['passed'] and len(guard['guards'])==44
    for n,h in guard['rtl_hashes'].items():
        assert sha(pin(b/'guards01'/n))==h
        if n in all_results['test03']['rtl_hashes']:assert h==all_results['test03']['rtl_hashes'][n]
    for n in guard['guards']:assert f'PASS HOST278 GNEG={n}' in pin(b/'guards01'/f'guard{n}.log').read_text()
    armguards={}
    for tag in ('native01','armguard01','h2guard01','irqguard01'):
        z=js(b/tag/'result.json');assert z['passed'] and z['ELF_sha256']==sha(b/'test03/output.elf');armguards[tag]=dict(fresh=True,checks=z.get('checks',z.get('cases',z.get('guards'))),frames=len(z.get('frames',[])))
    board=js(b/'board01/result.json');assert board['passed'] and not board['undriven']
    for n,h in board['actual_inputs'].items():assert sha(pin(b/'board01'/n))==h
    priorboard=js(BASE/'probes/nes-joint298/board01/result.json')
    changed={n for n,h in board['actual_inputs'].items() if h!=priorboard['actual_inputs'][n]}
    assert changed=={'nes_mux260.sv','nes_validator278.sv','nes_joint266.sv'}
    assert sha(b/'board01/nes_validator278.sv')==sha(b/'test03/nes_validator278.sv')
    host=(b/'board01/nes_mux260.sv').read_bytes().replace(b' output wire tile_closed267,\n',b'').replace(b' reg tiles_closed;assign tile_closed267=tiles_closed;',b' reg tiles_closed;')
    assert host==(b/'test03/nes_mux260.sv').read_bytes()
    for n in ('nes_arch300.py',):
        assert sha(pin(ROOT/'tools'/n))==sha(pin(b/'board01'/n))==sha(pin(b/'test03'/n))
    report=pin(b/'board01/output_files/board.map.rpt').read_text();summary=pin(b/'board01/output_files/board.map.summary').read_text();whole={};own={}
    assert 'Lite Edition' in summary
    for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:whole[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',summary).group(1).replace(',',''))
    for line in report.splitlines():
        f=[x.strip() for x in line.split(';')]
        if len(f)==14 and re.fullmatch(r'\d+ \(\d+\)',f[2]):own[f[10]]=int(re.search(r'\((\d+)\)',f[2]).group(1))
    assert sum(own.values())==whole['comb']
    def region(s,tree=False):return sum(v for k,v in own.items() if (s in k if tree else k.endswith(s)))
    regions=dict(host=region('nes_output260:flow'),validator=region('nes_validator278:validator'),queue=region('nes_queue260:queue',True),plan=region('nes_plan_batch206:transport',True)+region('nes_plan_spi200:endpoint',True),SPI=region('nes_spi270:spi_front270',True),glue=region('nes_joint267_board:native_joint267')+region('nes_joint257:core'))
    flow=(b/'test03/nes_mux260.sv').read_text();oldflow=(baseline/'nes_mux260.sv').read_text()
    def section(s,a,z):return s[s.index(a):s.index(z,s.index(a))]
    assert section(flow,' // Capture only',' // Original descriptor')==section(oldflow,' // Capture only',' // Original descriptor')
    v=(b/'test03/nes_validator278.sv').read_text()
    for anchor in ('range_end283>domain_end283','V_RWRITE:if(!crc_covered287)fault<=7;else if(v_q&v_mask)fault<=2;','V_PCHECKTEST:if(checked_byte!=v_value||ram_q!=255)fault<=3;','if(cursor!=422||!v_all_consumed||!certificate_ok)','if(h_count!=12)fault<=7;','if(reset||abort_source||fault||(state!=V_CLEARALL&&!lease_ok))v_we=0;'):assert anchor in v
    result=dict(passed=True,stage=300,**schedules,service_events=services,whole_MAP=whole,delta_MAP={k:whole[k]-old['whole_MAP'][k] for k in whole},regions=regions,fixed_boundary=sum(regions.values()),outside=whole['comb']-sum(regions.values()),fixed_budget=15408-whole['comb']+sum(regions.values()),comb_deficit=whole['comb']-15408,fresh_RTL_guards=44,ARM_checks=armguards,new_live_frames=9,new_MAP=True,full_schedule71=False,full_RUN=False,actual_SNES_live=False,FIT=False,STA=False,physical=False,scope='Actual shared descriptor end / aligned metadata RAM / early OBJ supply. Source replay, CPI1/84MHz, IRQ allocation, ordinary65816 trace and map/tile/display bus model retained.',input_hashes=pins,script_sha256=sha(Path(__file__)))
    (ROOT/'analysis/arch300-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    for name,rows in schedules.items():
        with (ROOT/f'analysis/arch300-{name}.csv').open('w',newline='') as fp:w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print(json.dumps({k:result[k] for k in ('normal','restricted','RTL_only_restricted','whole_MAP','delta_MAP','regions','comb_deficit')},indent=2))

if __name__=='__main__':main()
