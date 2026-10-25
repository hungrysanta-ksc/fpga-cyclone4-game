# SPDX-License-Identifier: MIT
"""Reconcile passive port traces with unchanged full338/336 schedules."""
import argparse,csv,json,re
from collections import Counter
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_receipt335 import load_image

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=BASE/'probes/nes-port350');ap.add_argument('--partial',action='store_true');a=ap.parse_args()
    pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    prior=js(ROOT/'analysis/owner349-verification.json')
    for n,h in prior['pins'].items():assert sha(Path(n))==h,n;pins[n]=h
    baseline=js(ROOT/'analysis/ingress338-verification.json');runs={}
    for tag,ref in [('window01','window03'),('fixed01','fixed01'),('normal01','normal01')]:
        d=a.root/tag;b=BASE/'probes/nes-ingress338'/ref
        if not (d/'result.json').exists():assert a.partial,tag;continue
        result=js(d/'result.json');old=js(b/'result.json');assert result['passed']
        assert result['rtl_hashes']==old['rtl_hashes'] and result['ARM']==old['ARM'],tag
        for n,h in result['rtl_hashes'].items():assert sha(d/n)==h;read(d/n)
        for n in ('cycles.csv','blocks.txt','joint-events.csv','CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc'):
            assert sha(d/n)==sha(b/n),(tag,n);pins[str(d/n)]=sha(d/n)
        assert load_image(d/'output.elf')==load_image(b/'output.elf');pins[str(d/'output.elf')]=sha(d/'output.elf')
        assert 'PASS REFILL267 frames=3' in read(d/'vsim.log')
        assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log')
        assert sha(d/'joint266_tb.sv')==result['tb_sha256'];read(d/'joint266_tb.sv')
        header_cases=0
        field_order=[0,1,2,3,10,11,14,15,12,13,16,17,18,19,20]
        for f in (905,906,907):
            arm=js(d/f'arm{f}.json');assert arm==js(b/f'arm{f}.json')
            for t in arm['transfers']:
                tx=bytes.fromhex(t['tx'])
                if not tx or tx[0]!=0xe1:continue
                packet=tx[1:-2];n=15 if packet[0]==14 else 14 if packet[0]==12 else 10
                skip_order=list(range(4))+list(range(10,10+n-4))
                assert dict((x,packet[x]) for x in field_order[:n])==dict((x,packet[x]) for x in skip_order)
                assert len(skip_order)==n
                header_cases+=1
        rows=list(csv.DictReader(read(d/'ports350.csv').splitlines()))
        events=list(csv.reader(read(d/'joint-events.csv').splitlines()))
        frame_rows=[]
        for f in (905,906,907):
            rr=[x for x in rows if x['frame']==str(f)];count=Counter();states=Counter();writes=[];captured=[]
            for row in rr:
                v={k:int(x) if re.fullmatch(r'\d+',x) else None for k,x in row.items()}
                assert not v['reset'] and not v['fault'],(tag,f,'unexpected fault')
                occupancy=(v['accepted']-v['retired'])&65535
                assert occupancy<=2,(tag,f,'credit')
                if v['ingress_write']:
                    count['ingress_bytes']+=1
                    assert v['ingress_addr']>=512
                    if v['state'] not in (0,16):count['ingress_while_active']+=1
                if v['request']:count['observed_read_request_clocks']+=1
                if v['capture']:
                    assert v['read_data'] is not None
                    count['host_captures']+=1
                    if v['state']==55:
                        count['header_captures']+=1
                        mapping=[0,1,2,3,10,11,14,15,12,13,16,17,18,19,20]
                        assert v['previous_addr']==512+256*(v['retired']&1)+mapping[v['at']-1]
                    else:
                        count['descriptor_captures' if v['state']==18 else 'metadata_captures' if v['state']==43 else 'payload_captures']+=1
                        assert v['previous_addr']==512+256*(v['retired']&1)+(v['parser']&255)
                if v['expected_write']:
                    count['expected_write_clocks']+=1;assert 0<=v['read_addr']<472
                    writes.append((v['time'],v['read_addr'],v['write_data']))
                    if not v['range_ready']:count['expected_writes_without_range_ready']+=1
                if v['op']==3 and v['validator_state']==32:
                    count['independent_expected_captures']+=1
                    assert v['previous_addr']<472
                    captured.append((v['time'],v['previous_addr'],v['read_data']))
                if v['ingress_write'] and (v['request'] or v['capture'] or v['expected_write']):
                    count['simultaneous_useful_A_B_clocks']+=1
                    assert v['ingress_addr']!=v['read_addr']
                states[v['state']]+=1
            # A request is logged at every selected cycle, but state-change rows are
            # not state dwell time. Count only read/write/capture events as work.
            e=[x for x in events if len(x)>1 and x[1]==str(f)]
            first=lambda n:next(x for x in e if x[0]==n)
            start=int(first('start319')[2]);done=int(first('input_done337')[-1])
            req=int(next(x for x in e if x[0]=='firstreq305' and x[2]=='0')[-1])
            e9=next(x for x in e if x[0]=='ARM_wire_start334' and x[2]=='233');e9start=int(e9[-1])
            e1=next(x for x in e if x[0]=='ARM_wire_start334' and x[2]=='225')
            completed=[x for x in e if x[0]=='arm267' and int(x[4])<req]
            checkpoints=[x for x in e if x[0]=='checkpoint287' and int(x[2])<req]
            waits=[x for x in e if x[0]=='wait284' and int(x[3])<req]
            inst=sum(int(x[5]) for x in completed)+sum(int(x[3]) for x in checkpoints)+sum(int(x[4]) for x in waits)
            exceptions=sum(int(x[6]) for x in completed)+sum(int(x[5]) for x in waits)
            wireps=0
            for x in completed:
                ws=next(y for y in e if y[0]=='ARM_wire_start334' and y[2]==x[2] and int(y[-1])<int(x[4]) and int(y[-1])==max(int(z[-1]) for z in e if z[0]=='ARM_wire_start334' and int(z[-1])<int(x[4])))
                wireps+=int(x[4])-int(ws[-1])
            total=(req-done)/1e9;armms=(inst+exceptions)/84000;wirems=wireps/1e9
            final_begin=next(int(x['time']) for x in rr if x['op']=='3' and x['state']=='42')
            final_end=next(int(x['time']) for x in rr if x['op']=='3' and x['state']=='47')
            top=next(x for x in result['ARM']['frames'] if x['frame']==f)['components']
            preparation={k:top[k] for k in ('expand286','begin285','geometry_plan286','h2early286','input_commit286','begin_step286')}
            frame_rows.append(dict(frame=f,counts=dict(count),logged_state_rows=dict(states),
                prior_timing=next(x for x in baseline['runs'][ref]['rows'] if x['frame']==f),
                source_done_to_request_ms=total,source_done_to_first_E1_ms=(int(e1[-1])-done)/1e9,
                first_E9_to_request_ms=(req-e9start)/1e9,
                before_first_request=dict(instructions=inst,exception_cycles=exceptions,checkpoints=len(checkpoints),waits=len(waits),
                    ARM_CPI1_ms=armms,SPI_transaction_ms=wirems,residual_including_activation_and_pipeline_ms=total-armms-wirems),
                expected_write_events=len(writes),expected_capture_events=len(captured),
                final_scan_interval_us=(final_end-final_begin)/1e6,
                top_level_prepare_instructions=preparation,
                top_level_prepare_CPI1_ms=sum(preparation.values())/84000))
        runs[tag]=dict(rows=frame_rows,rtl_unchanged=True,ARM_unchanged=True,timeline_byte_exact=True,
                      skip_identity_header_model_cases=header_cases,
                      skip_identity_model_scope='Original and ascending-address read orders produce the same final fields; no new RTL or STOP proof for candidate.')
    guards=None
    if (a.root/'guards01/result.json').exists():
        g=a.root/'guards01';guards=js(g/'result.json');assert guards['passed']
        assert guards['rtl_hashes']==js(a.root/'window01/result.json')['rtl_hashes']
        for x in guards['cases']:
            cd=g/f"case{x['case']}";assert sha(cd/'vsim.log')==x['log_sha256'];log=read(cd/'vsim.log');read(cd/'ports350.csv')
            m=re.search(r'INJECT350 case=(\d+) state=(\d+) addr=(\d+) previous=(\d+) time=(\d+)',log)
            assert m and int(m[1])==x['case'];x['injection']=dict(zip(('case','state','address','previous_address','time_ps'),map(int,m.groups())))
            if x['case']==30:assert int(m[2])==55
            if x['case']==31:assert int(m[2])==18
        read(g/'joint266_tb.sv')
        for name in ('aperture','final-raw0'):
            extra=js(g/name/'result.json');assert extra['passed'];guards[name]=extra
            for p in (g/name).iterdir():
                if p.is_file() and p.suffix in ('.sv','.log'):read(p)
    else:assert a.partial,'guards'
    for n in ('probe_nes_port350.py','guard_nes_port350.py','analyze_nes_port350.py'):read(ROOT/'tools'/n)
    out=dict(stage=350,passed=True,complete=not a.partial,selected_RTL=338,selected_ARM=336,
             prior_pins_rehashed=len(prior['pins']),runs=runs,guards=guards,
             whole_Lite_reused_identical_RTL=baseline['whole'],new_MAP=False,
             scope='Passive RTL port traces and unchanged M4 instruction/IRQ/CPI1 schedule. Not physical WCET, fullRUN, FIT, STA or new synthesized savings.',pins=pins)
    if not a.partial:(ROOT/'analysis/port350-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
    print(json.dumps({k:v for k,v in out.items() if k!='pins'},indent=2))

if __name__=='__main__':main()
