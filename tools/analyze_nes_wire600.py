"""Match pin payloads, linked receiver calls, and credit floors on the two MMC577 timelines."""
import argparse
from bisect import bisect_right
import csv
import math
import struct
from collections import Counter
from pathlib import Path
import json

from check_nes_game478 import Machine, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
from check_nes_wire600 import GENERATIONS, ROOT, pin, pin_packets, read, sha
from check_nes_ack593 import Display
from check_nes_transport584 import Probe
from test_nes_service509_schedule import Calendar

WIRE = 2625000
BUDGET = WIRE / (8*60)
INPUT = ('0xd0','0xd1','0xd2','0xd3')

class Receiver(Machine):
    def hook(self,u,at,size,user):
        injecting=False
        if at==self.spi:
            op=u.mem_read(u.reg_read(UC_ARM_REG_R1),1)[0]
            n=u.reg_read(UC_ARM_REG_R3)
            self.ops.append((hex(op),n))
            injecting=self.bad_crc and op==0xd1
            reply=u.reg_read(UC_ARM_REG_R2)
        super().hook(u,at,size,user)
        if injecting:
            u.mem_write(reply+n-1,bytes([u.mem_read(reply+n-1,1)[0]^1]))

    def start(self,packets):
        self.call('nes_native165_reset',[self.state])
        self.packets=packets
        self.ops=[]
        self.index=self.spi_calls=0
        self.start_token=0xfffc
        self.prepared=self.bad_crc=False

    def pump(self):
        if self.state_value()==2:
            return self.call('nes_native165_prepare',[self.state,1,self.spi|1,0])
        return self.call('nes_native165_poll',[self.state,self.spi|1,0])

    def receive(self,packets,geometry,raw,g):
        self.start(packets)
        before=self.instructions
        while self.index<len(packets):
            assert self.pump()==1 and self.spi_calls<128
        assert self.prepared and self.state_value()==4
        layout=self.layout['nes_native165']
        assert int.from_bytes(self.u.mem_read(self.state+layout['generation'],2),'little')==g
        offset=0
        counts=struct.unpack_from('<6H',geometry,5728)
        for name,count,width,capacity in zip(('maps','rows','objects','exceptions','raster','palette'),
                counts,(2,1,8,4,8,1),(1056,224,128,128,224,64),strict=True):
            size=count*width
            assert bytes(self.u.mem_read(self.state+layout[name],size))==geometry[offset:offset+size]
            offset+=capacity*width
        assert bytes(self.u.mem_read(self.state+layout['raw_pixels'],len(raw)))==raw
        ops=Counter();calls=Counter()
        for op,n in self.ops:ops[op]+=n;calls[op]+=1
        return dict(wire=dict(ops),calls=dict(calls),receive_instructions=self.instructions-before)

    def guards(self,packets):
        self.start(packets); self.bad_crc=True
        assert not self.pump() and self.index==0 and self.state_value()==5
        self.start(packets)
        assert self.pump() and self.index==1
        def direct(block,token):
            ptr=0x20013000
            self.u.mem_write(ptr,block)
            return self.call('nes_native165_packet',[self.state,token,ptr,len(block)])
        next_token=self.start_token+1
        abort=packets[0][:3]+bytes.fromhex('e002'+'00'*8)
        assert direct(abort,next_token) and self.state_value()==0
        assert not direct(packets[-1],next_token+1) and self.state_value()!=4
        self.start(packets)
        assert self.pump()
        assert not direct(packets[1][:1]+b'\xff\xff'+packets[1][3:],next_token)
        self.start(packets)
        assert self.pump() and not direct(packets[1],next_token+1)
        return ['corrupt_D1_no_POP','abort_then_late_COMMIT','wrong_generation','future_token']

class DisplayGate(Display):
    input_exchange=Probe.input_exchange

    def produce(self):
        end=len(self.packets) if self.prepared else len(self.packets)-1
        self.produced=min(end,self.index+1)
        self.max_ring=max(self.max_ring,self.produced-self.index)

def display_guards(src,g,packets):
    rows=[]
    for mode in ('normal','wrong_final_ACK','STOP_at_EA'):
        m=DisplayGate(src,False,400)
        m.generation=m.ep.generation=g
        m.index=m.produced=m.max_ring=0
        m.start_token=65520
        m.packets=packets
        m.prepared=m.saw_ea=m.saw_seal=False
        m.guard_mode=mode
        for _ in range(512):
            ok=m.call('nes_runtime165_step',[m.rt])
            if m.saw_ea or not ok:break
        else:raise AssertionError('no terminal outcome')
        count=m.get(m.rt,'nes_native_runtime165','frames',4)
        assert m.saw_seal and bool(ok)==(mode=='normal') and m.max_ring==1
        assert m.saw_ea==(mode!='wrong_final_ACK') and count==int(mode!='wrong_final_ACK')
        assert m.state_value()==(0 if ok else 4)
        rows.append(dict(mode=mode,displayed=count,EA=m.saw_ea,receiver_state=m.state_value()))
    return rows

def ms(n):return n*8000/WIRE

def compare(phase,g,receivers,body,map_reference,traces):
    i=phase['phase']
    source=phase['frames'][str(g)]
    ops=source['operation_wire_B']
    events=[e for e in traces if e['generation']==g and e['event']=='SPI']
    assert sum(e['opcode']=='0xea' for e in events)==1
    for op in INPUT:
        assert ops[op]==receivers['legacy']['wire'][op]
    totals=body['frames'][str(g)]['phases'][str(i)]
    oldmap=totals['output']['map'];newmap=map_reference[g-905]['map']
    output_B=sum(ops[op] for op in ('0xe1','0xe9','0xea'))-oldmap['wire_B']+newmap['wire_B']
    old_partial=sum(ops[k] for k in INPUT)+output_B
    new_partial=sum(receivers['shared']['wire'].values())+output_B
    target=math.ceil(old_partial-BUDGET)
    assert target=={952:429,954:518}[g] and old_partial-new_partial>=target

    # MMC577 starts after a drained preceding SEAL and must confirm the new
    # final identity. Only E0 can advance the host's retired cursor, max 4.
    n_e1=sum(e['opcode']=='0xe1' for e in events)-oldmap['packets']+newmap['packets']
    e0_min=(n_e1+3)//4
    assert n_e1>0 and events[-1]['opcode']=='0xea' and events[-2]['opcode']=='0xe8'
    # Charge only one pre-EA plan status. Drop rearm, all plan service polls,
    # observer and barriers from the optimistic screen to avoid double counting.
    floor=new_partial+20*e0_min+20
    assert floor>BUDGET
    aux=sum(n for k,n in ops.items() if k not in INPUT+('0xe1','0xe9','0xea','0xe0','0xe8'))
    observed=new_partial+ops['0xe0']+ops['0xe8']+aux
    calls=Counter(e['opcode'] for e in events)
    counts=dict(receivers['shared']['calls'],**{'0xe1':n_e1,'0xe9':calls['0xe9'],'0xea':1,
                                                '0xe0':calls['0xe0'],'0xe8':calls['0xe8']})
    extra=phase['parameters']['driver_extra_us']
    t=source['terms']
    assert abs(sum(t.values())-source['ACK_interval_ms'])<1e-8
    return dict(phase=i,generation=g,old_partial_B=old_partial,new_partial_B=new_partial,
                extra_saved_B=old_partial-new_partial,target_B=target,E1_packets=n_e1,
                credit_E0_min=e0_min,pre_EA_E8_min=1,wire_floor_B=floor,
                wire_floor_ms=ms(floor),floor_shortfall_B=math.ceil(floor-BUDGET),
                E0_observed=calls['0xe0'],E8_observed=calls['0xe8'],observer_B=aux,
                old_poll_count_scenario_B=observed,old_poll_count_wire_ms=ms(observed),
                old_poll_count_wire_plus_mean_driver_ms=ms(observed)+sum(n*extra[k] for k,n in counts.items())/1000,
                baseline_SPI_B=sum(ops.values()),baseline_ACK_interval_ms=source['ACK_interval_ms'],
                baseline_display_interval_ms=source['reveal_interval_ms'],
                baseline_ROM_reads=source['nested_resource']['ROM_reads'],
                baseline_ROM_request_wait_union_ms=source['nested_resource']['ROM_request_to_grant_union_ms'],
                baseline_SEAL_VBlank_service_ms=t['SEAL_VBlank_service_ms'],
                baseline_post_SEAL_DMA_ms=t['SEAL_DMA_ms'],baseline_final_waits=source['final_wait_count'])

MASTER = 21477272
LINE = 1364
FRAME = 262*LINE
PAIR = 2*FRAME-4

def ppu_position(t):
    pos=t%PAIR
    if pos>=FRAME:
        pos-=FRAME
        if pos>=241*LINE-4: pos+=4
    return divmod(pos,LINE)

def first_visible_switch(t):
    # Optimistic permission anywhere inside VBlank. No 246-line cutoff,
    # validation, palette/OAM DMA setup or scanline guard charged here.
    t=math.ceil(t)
    line,h=ppu_position(t)
    return t if line>=225 else t+(225-line)*LINE-h

def retime(row,phase,receiver,events,window,reads,cal):
    g=row['generation']
    def stamp(gen,event):
        tick,=[int(x['clock']) for x in window if x['g']==str(gen) and x['op']=='3' and x['event']==event]
        return tick
    start=next(e['clock'] for e in events if e['generation']==g and e['event']=='source_begin')
    prev_reveal=stamp(g-1,'reveal')
    prev_ack=stamp(g-1,'ack')
    assert prev_reveal<prev_ack<=start and ppu_position(prev_reveal)[0]>=225
    p=phase['parameters']
    assert p['ROM_calendar']==cal.summary and p['CPI']==2
    shift=p['ROM_phase']
    assert all(cal.select(req-shift)==(grant-shift,rsp-shift) for _,req,grant,rsp in reads)
    rx_b=sum(receiver['wire'].values())
    # The M4 checker uses callbacks for synchronous SPI; its instruction count
    # excludes the driver implementation. Charge these bytes, caller, driver once.
    input_ms=ms(rx_b)+receiver['receive_instructions']*p['CPI']/84000
    extra=p['driver_extra_us']
    input_ms+=sum(n*extra[k] for k,n in receiver['calls'].items())/1000
    ready=start+input_ms*MASTER/1000
    first_e9=next(e for e in events if e['generation']==g and e.get('opcode')=='0xe9')
    # Regrant all real reads serially at the earliest possible time after
    # that first plan packet, allowing even late OBJ reads to start at once.
    release=ready+(ms(first_e9['bytes'])+extra['0xe9']/1000)*MASTER/1000
    rsp=release;wait=0
    for _ in reads:
        grant,r=cal.select(rsp-shift)
        wait+=grant+shift-rsp
        rsp=r+shift
    # Drop the final E0 after retirement and E8/EA from the pre-display bound.
    # Their bytes still belong to the steady-state wire floor.
    wire_before=row['wire_floor_B']-20-20-7-rx_b
    before=ready+ms(wire_before)*MASTER/1000
    reveal=first_visible_switch(max(rsp,before))
    assert ppu_position(reveal)[0]>=225
    # Last grant from which all reads could finish by one 60 Hz period after
    # the previous reveal, even with every remaining tile request ready.
    deadline=math.floor(prev_reveal+MASTER/60)
    turn,off=divmod(deadline-shift,cal.period)
    until=bisect_right([response for _,response in cal.pairs],off)
    q,k=divmod(turn*len(cal.pairs)+until-len(reads),len(cal.pairs))
    latest=q*cal.period+cal.pairs[k][0]+shift
    def finish(t):
        for _ in reads: t=cal.select(t-shift)[1]+shift
        return t
    assert finish(latest)<=deadline<finish(latest+1)
    count=0
    t=start
    while t<=deadline:
        _,r=cal.select(t-shift)
        t=r+shift
        if t<=deadline: count+=1
    return dict(ROM_grants_from_source_before_deadline=count,ROM_reads_due=len(reads),
                latest_ROM_release_for_one_period=latest,release_advance_needed_ms=(release-latest)*1000/MASTER,
                start_masterclock=p['start'],source_begin=start,previous_reveal=prev_reveal,
                previous_ACK=prev_ack,receiver_ready_ms=(ready-start)*1000/MASTER,
                ROM_release=release,ROM_last_response=rsp,ROM_wait_ms=wait*1000/MASTER,
                pre_display_bus_end=before,VBlank_wait_ms=(reveal-max(rsp,before))*1000/MASTER,
                earliest_reveal_scenario=reveal,interval_ms=(reveal-prev_reveal)*1000/MASTER)

def main(a):
    base=a.arm/'src'
    whole=read(ROOT/'analysis/whole580-verification.json')
    manifest=read(ROOT/'analysis/whole580-manifest.json')
    body=read(ROOT/'analysis/body581-verification.json')
    maps=read(ROOT/'analysis/abi582-verification.json')['frames']
    sources={'legacy':base,'shared':a.probe/'ARM/src'}
    machines={k:Receiver(src,bytes(128)) for k,src in sources.items()}
    # Verify the producers/consumers used in the four-credit proof.
    for n in ('nes_sink_window184.c','nes_plan_service200.c','nes_native165.c'):
        pin(base/n,manifest['ARM_project_files']['src/'+n]['sha256'])
        if n!='nes_native165.c':pin(sources['shared']/n,sha(base/n))
    assert 's->retired)<4' in (base/'nes_sink_window184.c').read_text()
    assert 'if(!read509(p,rx,phase))' in (base/'nes_plan_service200.c').read_text()
    receiver={};guard={};displays={};phase_rows=[]
    for g in GENERATIONS:
        data=[a.data/f'frame{g}.{ext}' for ext in ('geometry','raw')]
        for p in data:pin(p,body['inputs'][p.name])
        receiver[g]={}
        for name,m in machines.items():
            d=a.probe/name
            row=next(r for r in read(d/'result.json')['frames'] if r['generation']==g)
            pin(d/f'transactions-{g}.txt',row['wire_SHA256'])
            pkts=pin_packets(d,g)
            assert len(pkts)==row['packets']
            if name=='shared':
                guard[g]=m.guards(pkts)
                displays[g]=display_guards(sources[name],g,pkts)
            receiver[g][name]=m.receive(pkts,*(p.read_bytes() for p in data),g)
            receiver[g][name]['pins_sha256']=row['wire_SHA256']
    cal=Calendar(a.calendar)
    for phase in whole['phases']:
        d=a.traces/f"nes-close561-run{phase['phase']}"
        for n in ('events.json','window.csv','seal528.csv','obj-phases.json'):
            pin(d/n,phase['evidence'][n])
        trace=read(d/'events.json')
        reads=read(d/'obj-phases.json')
        with (d/'window.csv').open() as f: window=list(csv.DictReader(f))
        with (d/'seal528.csv').open() as f:
            for r in csv.DictReader(f):
                assert ppu_position(int(r['clock']))==(int(r['line']),int(r['h']))
        for g in GENERATIONS:
            row=compare(phase,g,receiver[g],body,maps,trace)
            row['relaxed_calendar']=retime(row,phase,receiver[g]['shared'],trace,window,
                                           reads[str(g)]['rom_service'],cal)
            phase_rows.append(row)
    products={name:dict(firmware_B=(src/'obj-nes-100/firmware.stm').stat().st_size,
                        firmware_sha256=sha(src/'obj-nes-100/firmware.stm'),
                        free_Flash_B=212992-(src/'obj-nes-100/firmware.stm').stat().st_size)
              for name,src in sources.items()}
    assert products['legacy']['firmware_sha256']==read(ROOT/'analysis/trial577-package.json')['firmware_SHA256']
    result=dict(stage=600,wire_capacity_B=BUDGET,ARM=products,receiver=receiver,guards=guard,
                modeled_peripheral_display_guards=displays,phases=phase_rows,
                new_display_interval_ms=None,whole_board_FIT=None,physical=False,
                scope='D1 and destructive protocol pin tests, linked receivers on ready source, 582/599 map packet sizes. Fixed MMC577 E0-only retirement and pre-EA E8. Retimed optimistic ROM and VBlank calendar, no coupled new display or hardware timing.')
    result['evidence']={str(path.relative_to(ROOT).as_posix()):sha(path) for path in (
        ROOT/'analysis/whole580-manifest.json',ROOT/'analysis/whole580-verification.json',
        ROOT/'analysis/abi582-verification.json',ROOT/'analysis/body581-verification.json',
        ROOT/'tools/check_nes_wire600.py',ROOT/'tools/analyze_nes_wire600.py',
        ROOT/'tools/test_nes_transfer512_spi.py',ROOT/'tools/nes_transfer512.py')}
    result['RTL']={k:sha(a.probe/k/'nes_native_spi165.sv') for k in sources}
    a.out.write_bytes((json.dumps(result,indent=2)+'\n').encode('utf8'))
    print([(r['phase'],r['generation'],r['extra_saved_B'],r['wire_floor_B']) for r in phase_rows])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('arm','data','traces','calendar','probe','out'):p.add_argument('--'+n,type=Path,required=True)
    main(p.parse_args())
