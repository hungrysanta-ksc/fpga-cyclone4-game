# SPDX-License-Identifier: MIT
"""Bind passive335 traces to334 schedules; model candidate costs, not new RTL."""
import argparse,binascii,csv,json,re
from collections import Counter,defaultdict
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile

HOST_PS=11904


def completed_unit(op,section,pos,raw):
    # Independent byte-to-coverage definition, not host first/end decoder code.
    if op in (12,14):return (True,pos//2) if pos%2==1 else None
    if op==7:
        size,base=(16,0) if section==0 else (32,1024)
        return (False,base+pos//size) if pos%size==size-1 else None
    if section==3:return (False,1152+pos//16) if pos%16==15 else None
    if section!=5:return None
    if 1121<=pos<3169:
        return (False,1184+(pos-1121)//16) if (pos-1121)%16==15 else None
    if raw and 3169<=pos<3418:
        return (False,1312+(pos-3169)//16) if (pos-3169)%16==15 or pos==3417 else None
    return None


def load_image(p):
    with p.open('rb') as f:return [(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD']


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');args=ap.parse_args()
    pins={};base=BASE/'probes/nes-receipt335'
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    old=js(ROOT/'analysis/execute334-verification.json');area=js(ROOT/'analysis/execute332-verification.json')
    assert old['passed'] and area['passed'] and old['selected_RTL']==332
    runs={};all_chunks=[]
    for tag,ref in [('window02','arm-window01'),('fixed01','arm-fixed01'),('normal01','arm-normal01')]:
        q=base/tag
        if not (q/'result.json').exists():assert args.partial,(tag,'pending');continue
        r=js(q/'result.json');assert r['passed']
        prev=BASE/'probes/nes-execute334'/ref;pr=js(prev/'result.json')
        assert r['rtl_hashes']==pr['rtl_hashes'] and r['ARM']['frames']==pr['ARM']['frames']
        for key in ('IRQ_cases','EXTI284','stack_observed'):
            assert r['ARM'][key]==pr['ARM'][key],(tag,key)
        for name,h in r['rtl_hashes'].items():read(q/name);assert sha(q/name)==h
        read(q/'joint266_tb.sv');assert sha(q/'joint266_tb.sv')==r['tb_sha256']
        assert 'Errors: 0, Warnings: 0' in read(q/'vlog.log')
        for name in ('output.elf','CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc','probe_nes_receipt335.py'):
            pins[str(q/name)]=sha(q/name)
        assert load_image(q/'output.elf')==load_image(prev/'output.elf')
        assert sha(q/'CPU-bus.csv')==sha(prev/'CPU-bus.csv')
        for name in ('CPU-timing.csv','CPU-ordinary.sfc'):
            assert sha(q/name)==sha(prev/name),(tag,name)
        events=list(csv.reader(read(q/'joint-events.csv').splitlines()))
        old_events=list(csv.reader(read(prev/'joint-events.csv').splitlines()))
        assert [x for x in events if not x[0].endswith('335')]==old_events,(tag,'passive timeline changed')
        states=re.search(r'typedef enum logic\[5:0\] \{([^}]+)\}',read(q/'nes_validator278.sv'))[1].split(',')
        hashes=bytes(int(x,16) for x in read(q/'hashes.hex').split())
        rows=[]
        for prior in old['runs'][ref]['rows']:
            f=prior['frame'];ev=[x for x in events if len(x)>1 and x[1]==str(f)]
            arm=js(q/f'arm{f}.json')
            cert=next(bytes.fromhex(t['tx'])[17:49] for t in arm['transfers'] if bytes.fromhex(t['tx'])[:2]==b'\xe1\x0d')
            raw,scroll=cert[20],int.from_bytes(cert[14:16],'little')
            chunks=[];current=None;expected={};occupancy={}
            for x in ev:
                if x[0]=='desc335':
                    assert len(x)==13,x
                    token,op,section,start,span,length,bank,first,end,zero,t=map(int,x[2:])
                    current=dict(frame=f,token=token,op=op,section=section,start=start,span=span,length=length,bank=bank,
                        first=first,end=end,zero=zero,start_ps=t,bytes=[],reads=[],ports=[],ranges=[],acks=[])
                    chunks.append(current)
                elif x[0]=='expected335':expected[int(x[2])]=(int(x[3]),int(x[4]))
                elif x[0]=='state335':occupancy[states[int(x[2])]]=int(x[3])
                elif current and ((x[0]=='consume293' and x[2]=='2' and int(x[3])==current['token']) or
                                  (x[0]=='receipt312' and current['op']==7 and x[2]=='7')):
                    current['release_ps']=int(x[-1])
                elif x[0] in ('byte335','read335','ack335','range335','port335'):
                    assert current is not None,x
                    dest={'byte335':'bytes','read335':'reads','ack335':'acks','range335':'ranges','port335':'ports'}[x[0]]
                    current[dest].append(list(map(int,x[2:])))
            received={};summary=[];raw_crc_checks=0
            for c in chunks:
                n=c['length'];token=c['token']
                assert [x[1] for x in c['bytes']]==list(range(n)),(tag,f,token,'served bytes')
                assert [x[1] for x in c['reads']]==list(range(n)),(tag,f,token,'counted bytes')
                assert all(x[0]==token for x in c['bytes']+c['reads'])
                assert all(x[1]==x[2] and x[3]==n for x in c['reads'])
                assert len(c['acks'])==1 and c['acks'][0][0]==token,(tag,f,token,'ACK')
                ack=c['acks'][0][-1];assert ack>c['reads'][-1][-1]
                assert c['release_ps']>=ack,(f,token,'release before ACK')
                masks={};unit_times=[];jobs=[];crc_data=defaultdict(bytearray)
                for b,rd in zip(c['bytes'],c['reads']):
                    pos=c['start']+b[1];t=rd[-1]
                    unit=completed_unit(c['op'],c['section'],pos,raw)
                    if c['section']==5 and c['op'] in (2,4,5,8) and (pos<scroll or raw and pos>=3169) and not c['zero']:
                        # Eight-cycle reservation per CRC byte includes
                        # length/hash RAM overhead and arbitration allowance;
                        # new arbitration is an allocation, not measured RTL.
                        jobs.append((t,8,'CRC'))
                        if pos>=3169:crc_data[(pos-3169)//16].append(b[2])
                    if unit:
                        ismap,u=unit;addr=(768 if ismap else 512)+u//8;bit=1<<(u%8)
                        if addr not in masks:masks[addr]=[0,t]
                        assert not masks[addr][0]&bit;masks[addr][0]|=bit;masks[addr][1]=t
                        unit_times.append((u,t))
                for index,data in crc_data.items():
                    assert len(data)==(9 if index==15 else 16),(f,token,index,len(data))
                    at=(f-905)*64+c['bank']*32+index*2
                    assert binascii.crc_hqx(bytes(data),65535)==int.from_bytes(hashes[at:at+2],'little')
                    raw_crc_checks+=1
                units=[u for u,t in unit_times]
                if units:
                    assert len(c['ranges'])==1 and c['ranges'][0][2:4]==[units[0],units[-1]+1],(f,token,c['ranges'],units)
                else:assert not c['ranges'],(f,token,'unexpected coverage')
                writes=[p for p in c['ports'] if p[3]]
                actual_receipt=[p for p in writes if 512<=p[2]<=677 or 768<=p[2]<=1023]
                assert [p[2] for p in actual_receipt]==list(masks),(f,token,'mask address walk')
                for p in actual_receipt:
                    addr=p[2];mask=masks[addr][0]
                    assert p[-1]>ack and not received.get(addr,0)&mask
                    received[addr]=received.get(addr,0)|mask;assert p[4]==received[addr],(f,token,addr,'receipt mask')
                persistent=[p for p in writes if p[2]<422]
                assert len(persistent)==(0 if c['op'] in (12,14) else len(masks))
                for p,(addr,(mask,t)) in zip(persistent,masks.items()):
                    assert p[2]==c['bank']*256+addr-512 and p[4]&mask==mask
                ismap=c['op'] in (12,14)
                for addr,(mask,t) in masks.items():jobs.append((t,4 if ismap else 6,'receipt'))
                free=0;backlog=0;completions=[];delays=[]
                for t,cycles,kind in sorted(jobs):
                    completions=[z for z in completions if z>t]
                    backlog=max(backlog,len(completions)+1)
                    begin=max(t,free);delays.append(begin-t);free=begin+cycles*HOST_PS;completions.append(free)
                assert not jobs or free<=ack,(tag,f,token,'allocated port service spills past ACK')
                gaps=[b[-1]-a[-1] for a,b in zip(c['reads'],c['reads'][1:])]
                last_port=max([p[-1] for p in c['ports']],default=ack)
                late_expected=sum(expected[(u//8) if ismap else 256+u//8][1]>t for u,t in unit_times)
                out=dict(token=token,op=c['op'],section=c['section'],bytes=n,units=len(units),mask_bytes=len(masks),
                    min_read_gap_ps=min(gaps) if gaps else None,actual_RAM_cycles=len(c['ports']),actual_RAM_writes=len(writes),
                    actual_ACK_to_last_RAM_ps=max(0,last_port+HOST_PS-ack) if c['ports'] else 0,
                    actual_ACK_to_release_ps=c['release_ps']-ack,
                    allocated_jobs=len(jobs),allocated_port_cycles=sum(x[1] for x in jobs),allocated_max_backlog=backlog,
                    allocated_max_delay_ps=max(delays,default=0),allocated_finish_before_ACK_ps=ack-free if jobs else None,
                    units_before_expected_available=late_expected)
                summary.append(out);all_chunks.append(dict(run=tag,frame=f,**out))
            warm=prior.copy();warm.pop('observation_ms',None)
            receipt_ps=sum(x['actual_ACK_to_last_RAM_ps'] for x in summary)
            rows.append(dict(frame=f,baseline=warm,unchanged_timeline=True,chunks=len(chunks),DMA_bytes=sum(x['bytes'] for x in summary),
                coverage_units=sum(x['units'] for x in summary),bitmap_bytes=sum(x['mask_bytes'] for x in summary),raw_CRC_checks=raw_crc_checks,
                max_mask_bytes=max(x['mask_bytes'] for x in summary),min_read_gap_ps=min(x['min_read_gap_ps'] for x in summary if x['min_read_gap_ps'] is not None),
                receipt_RAM_cycles=sum(x['actual_RAM_cycles'] for x in summary),receipt_RAM_ms=sum(x['actual_RAM_cycles'] for x in summary)*HOST_PS/1e9,
                ACK_to_last_RAM_sum_ms=receipt_ps/1e9,optimistic_total_remove_ACK_RAM_ms=prior['total_ms']-receipt_ps/1e9,
                ACK_to_release_sum_ms=sum(x['actual_ACK_to_release_ps'] for x in summary)/1e9,
                deferred_extra_mask_read_allocation_ms=sum(x['mask_bytes'] for x in summary)*2*HOST_PS/1e9,
                optimistic_zero_post_ROM_gap_ms=prior['total_ms']-prior['post_ROM_ms']-1000/60,
                post_ROM_cap_only_total_ms=prior['total_ms']-prior['post_ROM_ms']+3.18,
                expected_late_units=sum(x['units_before_expected_available'] for x in summary),
                max_allocated_backlog=max(x['allocated_max_backlog'] for x in summary),
                max_allocated_delay_ps=max(x['allocated_max_delay_ps'] for x in summary),
                min_allocated_finish_before_ACK_ps=min(x['allocated_finish_before_ACK_ps'] for x in summary if x['allocated_finish_before_ACK_ps'] is not None),
                validator_state_ticks=occupancy))
        runs[tag]=rows
    if args.partial:print(json.dumps(dict(runs=runs),indent=2));return
    nodes=area['own_entity_comb']
    def own(s):
        v=[v for k,v in nodes.items() if k.endswith(s)];assert len(v)==1;return v[0]
    aperture=own('nes_bulk_aperture188:shared_ram.aperture');validator=own('nes_validator278:validator')
    board=BASE/'probes/nes-execute332/board03'
    br=js(board/'result.json');assert br['passed']
    for n,h in br['actual_inputs'].items():
        read(board/n);assert sha(board/n)==h
    report=board/'output_files/board.map.rpt';read(report);assert sha(report)==area['pins'][str(report)]
    for n in ('probe_nes_receipt335.py','analyze_nes_receipt335.py'):read(ROOT/'tools'/n)
    out=dict(stage=335,passed=True,scope='unchanged332RTL/334ARM passive measurements plus Python cost model; no candidate RTL/MAP/FIT/STA',
        runs=runs,chunks=all_chunks,whole=area['whole'],comb_deficit=2241,groups=area['groups'],aperture_comb=aperture,
        host_validator_aperture_comb=area['groups']['host_validator']+aperture,
        impossible_free_validator_aperture_remaining_deficit=2241-validator-aperture,
        design_scope_comb=sum(area['groups'].values())+aperture,design_scope_cap=4110+aperture,
        deferred_mask_RAM_candidate=dict(base=716,length=18,unvalidated_remaining_window=[734,767]),
        allocated_cycles=dict(CRC_byte=8,map_bitmap_byte=4,other_bitmap_byte=6,host_period_ps=HOST_PS),
        new_measured_gain_ms=None,new_candidate_comb=None,candidate_port_cost_is_allocation=True,pins=pins)
    (ROOT/'analysis/receipt335-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,pins=len(pins),warm={k:v[-1] for k,v in runs.items()},area_scope=out['host_validator_aperture_comb']),indent=2))


if __name__=='__main__':main()
