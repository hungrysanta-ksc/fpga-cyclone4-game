# SPDX-License-Identifier: MIT
"""Isolate ARM296 on hash-identical RTL295; reuse matching whole Lite evidence."""
import argparse,csv,json,re
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
    oldlive=js(oldbase/'test03/result.json');board=js(oldbase/'board01/result.json')
    schedules={};services=[];critical=[]
    for tag,mode in [('test01','normal'),('window01','restricted')]:
        q=b/tag;r=js(q/'result.json');assert r['passed'] and r['frames']==3
        assert r['rtl_hashes']==oldlive['rtl_hashes']
        for name,h in r['rtl_hashes'].items():assert sha(pin(q/name))==h==sha(pin(oldbase/'test03'/name))
        assert loaded(q/'output.elf')==loaded(armbase/'test02/output.elf')
        assert r['tb_sha256']==sha(pin(q/'joint266_tb.sv'))
        for name in ('nes_bg293.py','nes_bg294.py','nes_bg295.py','nes_stage290.py','nes_close295.py','probe_nes_live295.py','nes_wait296.py','probe_nes_live297.py'):
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
            e1=lambda z:[t['tx'] for t in z['transfers'] if t['tx'].startswith('e1')]
            assert e1(transfers)==e1(oracle)
            credits=[int(e[2]) for e in es if e[0]=='credits'];assert credits and max(credits)<=4
            assert len([e for e in es if e[0]=='checkpoint287'])==31
            src=int(source[f]['total'])*45.454/1e6;out=int(event[3])/1e9;total=src+out
            counters=list(map(int,next(e for e in es if e[0]=='romwait267')[2:]));inc=[x-y for x,y in zip(counters,last)];last=counters
            completed=[e for e in nr['service296'] if e['after_done']!=e['before_done']];assert len(completed)==1
            services.extend(dict(mode=mode,frame=f,**e) for e in completed)
            rows.append(dict(frame=f,source_ms=src,output_ms=out,total_ms=total,margin_ms=1000/60-total,
                before295_ms=before[295]['total_ms'],delta_vs295_ms=total-before[295]['total_ms'],before296_ms=before[296]['total_ms'],delta_vs296_ms=total-before[296]['total_ms'],
                ARM_instructions=nr['instructions'],SPI_bytes=nr['SPI_bytes'],E2=sum(int(e[2])==226 for e in spi),E9=sum(int(e[2])==233 for e in spi),
                timer_fallbacks=sum(int(e[2])==0 for e in wait),IRQ_waits=len(wait),max_credit=max(credits),
                parser_windows_ms=sum(int(e[3]) for e in es if e[0]=='parser')/1e9,map_receipt_windows_ms=sum(int(e[3]) for e in es if e[0]=='receipt')/1e9,
                service_instructions=completed[0]['end_instruction']-completed[0]['instruction'],tile_wait_cycles=inc[0],slot_wait_cycles=inc[1],core_priority_blocks=inc[2]))
            if f==907:critical.append(dict(mode=mode,OBJ_plan_ms=[int(e[-1])/1e9 for e in es if e[0]=='plan293' and e[2]=='1'],OBJ_start_ms=[int(e[-1])/1e9 for e in es if e[0]=='tile293' and e[2]=='1'],tile_receipt_ms=[int(e[-1])/1e9 for e in es if e[0]=='consume293' and e[2]=='1']))
        assert len(rows)==3;schedules[mode]=rows
    # Exact loaded code identity binds the old directed ARM tests, not new executions.
    reused={}
    for tag in ('native01','armguard01','h2guard01','irqguard01'):
        r=js(armbase/tag/'result.json');assert r['passed'] and r['ELF_sha256']==sha(pin(armbase/'window01/output.elf'))
        assert loaded(armbase/'window01/output.elf')==loaded(b/'test01/output.elf')
        reused[tag]=dict(result_sha256=sha(armbase/tag/'result.json'),fresh=False)
    for tag in ('guards01','close02'):
        r=js(oldbase/tag/'result.json');assert r['passed']
        for name,h in r['rtl_hashes'].items():
            assert sha(pin(oldbase/tag/name))==h
            if (b/'test01'/name).exists():assert sha(pin(b/'test01'/name))==h
        reused[tag]=dict(result_sha256=sha(oldbase/tag/'result.json'),fresh=False)
    # Verify the retained whole-board inputs and the bus-observation port normalization.
    for name,h in board['actual_inputs'].items():assert sha(pin(oldbase/'board01'/name))==h
    for name in ('nes_plan_batch206.sv','nes_tile_producer260.sv','nes_validator278.sv'):
        assert sha(pin(oldbase/'board01'/name))==sha(pin(b/'test01'/name))
    host=pin(oldbase/'board01/nes_mux260.sv').read_bytes().replace(b' output wire tile_closed267,\n',b'').replace(b' reg tiles_closed;assign tile_closed267=tiles_closed;',b' reg tiles_closed;')
    assert host==pin(b/'test01/nes_mux260.sv').read_bytes()
    raw=pin(oldbase/'board01/output_files/board.map.summary').read_text();whole={}
    for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]:whole[k]=int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',raw).group(1).replace(',',''))
    assert whole==prior[295]['whole_MAP']
    own={}
    for line in pin(oldbase/'board01/output_files/board.map.rpt').read_text().splitlines():
        f=[x.strip() for x in line.split(';')]
        if len(f)==14 and re.fullmatch(r'\d+ \(\d+\)',f[2]):own[f[10]]=int(re.search(r'\((\d+)\)',f[2]).group(1))
    assert sum(own.values())==whole['comb']
    def region(s,tree=False):return sum(v for k,v in own.items() if (s in k if tree else k.endswith(s)))
    regions=dict(host=region('nes_output260:flow'),validator=region('nes_validator278:validator'),queue=region('nes_queue260:queue',True),plan=region('nes_plan_batch206:transport',True)+region('nes_plan_spi200:endpoint',True),SPI=region('nes_spi270:spi_front270',True),glue=region('nes_joint267_board:native_joint267')+region('nes_joint257:core'))
    deficit=whole['comb']-15408;fixed=sum(regions.values());outside=whole['comb']-fixed
    budget=[]
    for name,cost in [('host_validator',regions['host']+regions['validator']),('fixed_boundary',fixed)]:
        budget.append(dict(candidate=name,current_comb=cost,replacement_budget=cost-deficit,reserve128_budget=cost-deficit-128,required_reduction=deficit,required_percent=100*deficit/cost,measured_replacement_comb=None))
    # Reviewed removal contract: exact unique anchors, no invented per-state LUT savings.
    review=[]
    def boundary(name,file,anchor,remove,retain,ports,risk):
        lines=pin(b/'test01'/file).read_text().splitlines();hits=[i+1 for i,s in enumerate(lines) if anchor in s];assert len(hits)==1,(name,hits)
        review.append(dict(candidate=name,file=file,line=hits[0],anchor=anchor,remove=remove,retain=retain,port_owner=ports,added_cost_or_risk=risk,measured_comb_saving=None))
    boundary('receipt continuation','nes_mux260.sv','OTILE,OSELECT:if(range_ready)state<=ORET;',
        'host OTILE/OSELECT/ORET and SEND/WAIT_RECEIPT handoff; validator return-to-V_ACTIVE then host re-dispatch',
        'ordinary exact reads + ordered ACK + tap drained; map exact reads + full token; duplicate/domain/CRC mask; batch last-only credit',
        'one host-clock executor owns phase RAM B; queue head remains held',
        'operation continuation selector and direct fault routing replace handshake; no predicted LUT saving')
    boundary('manifest continuation','nes_mux260.sv','OCHECKNEXT:state<=opos==oend?ORET:OREAD;',
        'host OCHECKNEXT/ORLE ready polling and validator per-byte V_ACTIVE dispatch; use direct RAM comparison return to decoder',
        'encoded cursor/RLE remaining and expanded 422-byte cursor simultaneously live; checked_byte required for second RAM comparison',
        'queue RAM registered reader and phase RAM B remain distinct ports',
        'central queue address selection and operation/decode mux charged; expanded cursor cannot alias packet cursor')
    boundary('descriptor admission','nes_mux260.sv','wire [16:0] descriptor_end287=',
        'cross-module receipt_first/count valid conversion and secondary execution dispatch',
        'independent widened end/domain/alignment checks before use; original descriptor immutable until consume and receipt',
        'executor latches one receipt operation; SNES view retains active descriptor',
        'share arithmetic only for proven non-overlapping admission; retaining checks may retain arithmetic')
    boundary('concurrent CRC observer','nes_mux260.sv','reg tap_seen278,tap_fault278,tap_repeat278;',
        'none of bus strobe latch/pattern/CRC observation',
        'actual payload observation, compressed-pattern expansion, provisional hash and raw coverage independent of ARM',
        'observer runs while ordinary bus consumer owns queue read; validator hashes on phase RAM B',
        'merging main FSM must leave observer able to progress while bus wait active')
    boundary('final display ownership','nes_mux260.sv',"if(ap==24'h006058)begin",
        'only internal display request/response continuation may fuse; no final ACK guard removed',
        'seal/certificate/12 exact reads/full token/no queue/no owner and lease mailbox',
        'phase RAM B supplies display; existing host-to-NES final mailbox retained',
        'early packet retire cannot imply final frame retirement')
    boundary('STOP write gate','nes_validator278.sv','if(reset||abort_source||fault||(state!=V_CLEARALL&&!lease_ok))v_we=0;',
        'duplicate internal fault relay only after same-edge abort proof',
        'RAM write inhibit, persistent invalidation, burned token/serial history, no resume by stale ACK',
        'single executor B write gate; source A lease and reset/CDC remain separate',
        'moving fault decoding must not introduce a one-cycle post-STOP write')
    result=dict(passed=True,stage=297,normal=schedules['normal'],restricted=schedules['restricted'],service_events=services,critical907=critical,
        ARM_loaded_identical296=True,RTL_hash_identical295=True,whole_MAP=whole,comb_deficit=deficit,area=dict(regions=regions,fixed_boundary=fixed,outside=outside,budget=15408-outside,delta_vs296={k:whole[k]-prior[296]['whole_MAP'][k] for k in whole}),
        reuse=reused,new_MAP=False,new_RTL=False,new_live_frames=6,joint_replacement_implemented=False,budgets=budget,joint_review=review,
        scope='Fresh live ARM296+RTL295 A/B with IRQ, SPI and ROM arbitration. Source timing replay, CPI1/84MHz, IRQ overhead allocation and modeled map/tile/display bus remain. Unit guards and whole Quartus Lite MAP reused by matching hashes; broad executor is reviewed, not synthesized.',
        full_schedule71=False,full_RUN=False,physical=False,FIT=False,STA=False,input_hashes=pins,script_sha256=sha(Path(__file__)))
    for name,rows in [*schedules.items(),('control',review),('budget',budget)]:
        with (d/f'{name}.csv').open('w',newline='',encoding='utf-8') as fp:w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('passed','normal','restricted','area','comb_deficit')}))

if __name__=='__main__':main()
