# SPDX-License-Identifier: MIT
"""ROM phase attribution and joint source/poll/OAM/whole-area review.

CPU service is newly measured. Transfer alternatives are frozen-count cost
sensitivities, NOT retimed schedules or synthesized replacements.
"""
from pathlib import Path
import argparse,binascii,collections,csv,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent

def pack6(data):
    assert len(data)%4==0 and all(x<64 for x in data)
    return b''.join(sum(v<<(6*i) for i,v in enumerate(data[a:a+4])).to_bytes(3,'little')
                    for a in range(0,len(data),4))

def unpack6(data,count):
    assert count%4==0 and len(data)==count*3//4
    return bytes((int.from_bytes(data[a:a+3],'little')>>(6*i))&63
                 for a in range(0,len(data),3) for i in range(4))

def chunk_lengths(lengths):
    out=[];used=0
    for n in lengths:
        assert 0<n<=243
        if used+n>248:out.append(used);used=0
        used+=n
    if used:out.append(used)
    return out

def raw_delta(data,previous):
    """Reuse the source MASK shape: block id, 64-bit bitmap, changed bytes."""
    assert len(data)%256==0 and len(data)<=512 and all(x<64 for x in data)
    if previous is not None:assert len(previous)==len(data)
    records=[]
    for at in range(0,len(data),64):
        mask=sum(1<<i for i in range(64) if previous is None or data[at+i]!=previous[at+i])
        if mask:
            records.append(bytes([68+at//64])+mask.to_bytes(8,'little')+
                           bytes(data[at+i] for i in range(64) if mask>>i&1))
    return records

def raw_decode(records,previous,count):
    assert count in (0,256,512)
    assert previous is None or len(previous)==count
    data=bytearray(count) if previous is None else bytearray(previous)
    covered=set();last=67
    for r in records:
        assert len(r)>=9 and last<r[0]<68+count//64
        last=r[0];mask=int.from_bytes(r[1:9],'little')
        assert mask and len(r)==9+mask.bit_count() and all(x<64 for x in r[9:])
        if previous is None:assert mask==(1<<64)-1
        at=(r[0]-68)*64;values=iter(r[9:])
        for i in range(64):
            if mask>>i&1:data[at+i]=next(values)
        covered.add(r[0])
    if previous is None:assert covered==set(range(68,68+count//64))
    return bytes(data)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--retimed',action='store_true')
    a=ap.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    b=a.base.resolve();p=BASE/'probes/nes-joint278';old=BASE/'probes/nes-joint276'
    pins={}
    def read(p):
        data=p.read_bytes();pins[str(p)]=hashlib.sha256(data).hexdigest()
        return data.decode('utf-8-sig')
    def js(p):return json.loads(read(p))
    def csvs(p):return list(csv.DictReader(read(p).splitlines()))
    def events(p):return list(csv.reader(read(p/'joint-events.csv').splitlines()))
    baseline=js(p/'analysis01/result.json');assert baseline['passed']
    measured=js(b/'cpu02/result.json');guards=js(b/'guards01/result.json')
    assert measured['passed'] and guards['passed'] and measured['CPU']['commands']==544
    assert guards['ROM_sha256']==measured['ROM_sha256']
    assert read(b/'cpu02/packets.hex')==read(p/'test07/CPU-packets.hex')
    oldcpu=csvs(p/'test07/CPU-timing.csv');newcpu=csvs(b/'cpu02/timing.csv')
    assert len(oldcpu)==len(newcpu)==544
    cpudelta=collections.Counter();oamdelta=collections.Counter()
    for before,after in zip(oldcpu,newcpu):
        for key in ['case','serial','sequence','op','section','length','output_bytes','dma_bytes']:
            assert before[key]==after[key],key
        f=int(before['serial'])+904
        delta=int(before['total_clocks'])-int(after['total_clocks'])
        cpudelta[f]+=delta
        if before['op']=='8' and before['section']=='4':oamdelta[f]+=delta
    assert measured['template']['fills']==71
    assert measured['template']['bytes']==sum(int(x['output_bytes']) for x in newcpu
                                               if x['op']=='8' and x['section']=='4')
    assert measured['ROM_used_bytes']==1296 # body783 + zero1 + template512
    assert js(p/'test07/CPU-result.json')['rom_body_bytes']==653
    assert 'program_rom[0:4095]' in read(p/'board01/nes_sink_bus165.sv')
    for name in ['ordinary.sfc','bus.csv','capture.lua']:
        readpath=b/'cpu02'/name
        pins[str(readpath)]=hashlib.sha256(readpath.read_bytes()).hexdigest()

    # Compare absolute boundaries, not just each frame's elapsed duration.
    rom=[]
    series={}
    for label,folder in [('276',old/'window01'),('278',p/'window01')]:
        ev=events(folder);previous=[0,0,0];series[label]=[]
        for f in [905,906,907]:
            finish=next(x for x in ev if x[0]=='frame_done' and int(x[1])==f)
            tx=[x for x in ev if x[0]=='arm267' and int(x[1])==f]
            counts=collections.Counter(int(x[2]) for x in tx)
            rw=next(x for x in ev if x[0]=='romwait267' and int(x[1])==f)
            waits=list(map(int,rw[2:]));increments=[x-y for x,y in zip(waits,previous)];previous=waits
            rc=next(x for x in ev if x[0]=='rom267' and int(x[1])==f)
            # ROM markers have no timestamp: bracket with neighboring timed
            # ARM events. Do not invent an exact ROM ready instant.
            ri=ev.index(rc)
            left=[int(x[4]) for x in ev[:ri] if x[0]=='arm267']
            right=[int(x[4]) for x in ev[ri+1:] if x[0]=='arm267']
            row=dict(frame=f,output_start_ms=(int(finish[2])-int(finish[3]))/1e9,
                     end_ms=int(finish[2])/1e9,output_duration_ms=int(finish[3])/1e9,
                     E2=counts[226],SPI_bytes=sum(int(x[3]) for x in tx),
                     instructions=sum(int(x[5]) for x in tx),transactions=len(tx),
                     commands=dict(counts),tile_bytes=int(rc[2]),ROM_reads_cumulative=int(rc[4]),
                     core_reads_cumulative=int(rc[3]),
                     tile_wait_cycles=increments[0],slot_wait_cycles=increments[1],
                     core_priority_blocks=increments[2],
                     ROM_done_bracket_ms=[max(left)/1e9,min(right)/1e9],
                     last_E9_ms=max(int(x[4]) for x in tx if int(x[2])==233)/1e9)
            series[label].append(row)
    for before,after in zip(series['276'],series['278']):
        assert before['tile_bytes']==after['tile_bytes']
        assert before['ROM_reads_cumulative']==after['ROM_reads_cumulative']
        assert before['core_reads_cumulative']==after['core_reads_cumulative']
        delta={k:after[k]-before[k] for k in [
            'output_start_ms','end_ms','output_duration_ms','E2','SPI_bytes',
            'instructions','transactions','slot_wait_cycles','tile_wait_cycles','core_priority_blocks']}
        charged=delta['SPI_bytes']*8/2625+delta['instructions']/84000+delta['transactions']*.008
        delta.update(charged_transaction_delta_ms=charged,
                     remaining_schedule_delta_ms=delta['output_duration_ms']-charged)
        assert abs(delta['end_ms']-delta['output_start_ms']-delta['output_duration_ms'])<1e-10
        rom.append(dict(frame=before['frame'],before=before,after=after,delta=delta))
    assert rom[-1]['delta']['E2']==4 and rom[-1]['delta']['SPI_bytes']==36
    assert rom[-1]['delta']['output_start_ms']<0 and rom[-1]['delta']['end_ms']<0
    tb=read(p/'test07/joint266_tb.sv')
    assert 'romcycle267%357368>=330088' in tb and 'romcycle267%357368<354640' in tb
    assert 'romcycle267%12==3' in tb and 'romcycle267%120==3' in tb

    # Pin source packetizer and count every existing byte/transaction. The
    # prepare/blocked/WAITACK counters overlap SPI service and are not gains.
    read(p/'test07/nes_transport257.sv');read(p/'test07/nes_core257.sv')
    costs={int(x['frame']):x for x in csvs(p/'analysis01/costs.csv')}
    cyc=csvs(p/'test07/cycles.csv');blocks=collections.defaultdict(list)
    for line in read(p/'test07/blocks.txt').splitlines():
        f,token,n,hexdata=line.split();data=bytes.fromhex(hexdata)
        assert len(data)==int(n);blocks[int(f)].append(data)
    rows=[];priorwire=0;rawtotal=0;packedtotal=0;previous_raw=None
    for c in cyc:
        f=int(c['frame']);records=[]
        for line in read(p/'test07'/f'frame{f}.records').splitlines():
            n,h=line.split();r=bytes.fromhex(h);assert len(r)==int(n);records.append(r)
        assert b''.join(records)==b''.join(blocks[f])
        assert chunk_lengths([len(x) for x in records])==list(map(len,blocks[f]))
        packed_lengths=[];raw=False;pixels=0;crc=65535;raw_image=bytearray();prefix=[]
        for r in records:
            trailer=r[:4] in [bytes([255,255,0,3]),bytes([255,255,0,4])]
            if trailer:
                crc=binascii.crc_hqx(r[:-2],crc)
                assert crc==int.from_bytes(r[-2:],'little')
            else:crc=binascii.crc_hqx(r,crc)
            if raw and not trailer:
                offset=int.from_bytes(r[:2],'little');count=r[2];data=r[3:]
                assert offset==pixels and count==len(data)
                packed=pack6(data);assert unpack6(packed,count)==data
                packed_lengths.append(len(packed)+3)
                raw_image.extend(data)
                pixels+=count;rawtotal+=count;packedtotal+=len(packed)
            else:
                packed_lengths.append(len(r))
                if not raw or r[:4]==bytes([255,255,0,3]):prefix.append(r)
            if r[:4]==bytes([255,255,0,3]):raw=True
        assert pixels==512
        delta_records=raw_delta(raw_image,previous_raw)
        assert raw_decode(delta_records,previous_raw,512)==raw_image
        changed_raw=512 if previous_raw is None else sum(x!=y for x,y in zip(raw_image,previous_raw))
        previous_raw=bytes(raw_image)
        delta_lengths=list(map(len,prefix+delta_records+[records[-1]]))
        delta_payload=sum(delta_lengths);delta_blocks=len(chunk_lengths(delta_lengths))
        payload=sum(map(len,records));n=len(blocks[f]);packed_payload=sum(packed_lengths)
        packed_blocks=len(chunk_lengths(packed_lengths))
        current=int(c['wirebytes_cumulative'])
        wire_sample=current-priorwire-(int(costs[f-1]['SPI_bytes']) if f>905 else 0)
        priorwire=current
        # Stats sample precedes the final D3's 2us SS tail; first sample also
        # omits its byte counter increment. Later samples include prior D3.
        sourcewire=wire_sample+(8 if f==905 else 0)
        empty=(sourcewire-payload-19*n-8)//8
        assert sourcewire==payload+19*n+8+8*empty and empty>=0
        transactions=3*n+empty+1
        wire_ms=sourcewire*8/2625+transactions*.008
        actual=float(costs[f]['source_ms'])
        assert .0015<wire_ms-actual<.0021,(f,wire_ms,actual)
        cpu_gain=cpudelta[f]/21477.272727
        # Zero-cost removal is an optimistic screening calculation only.
        free_status_pop=(2*n+empty)*(8*8/2625+.008)
        # Proposed exchange:8B authenticated request,5B frozen reply header
        # (flags,length,token16,CRC8), payload,2B payload CRC16. Empty=13B.
        # Final POP+input COMMIT remains one8B command. Full frame semantic
        # CRC, epoch/generation/STOP/final display remain independent.
        def exchange_cost(data,count):
            wire=data+15*count+13*empty+8
            tx=count+empty+1
            return wire,tx,wire*8/2625+tx*.008
        exwire,extx,exms=exchange_cost(payload,n)
        pkwire,pktx,pkms=exchange_cost(packed_payload,packed_blocks)
        dtwire,dttx,dtms=exchange_cost(delta_payload,delta_blocks)
        total=float(costs[f]['diagnostic_serial_ms'])
        rows.append(dict(frame=f,baseline_ms=total,source_ms=actual,source_payload=payload,
            source_blocks=n,source_empty_status=empty,source_SPI_bytes=sourcewire,
            source_transactions=transactions,source_wire_and_setup_ms=wire_ms,
            source_counter_tail_difference_ms=wire_ms-actual,
            CPU_gain_ms=cpu_gain,OAM_only_gain_ms=oamdelta[f]/21477.272727,
            frozen_CPU_only_ms=total-cpu_gain,
            frozen_free_source_status_POP_ms=total-cpu_gain-free_status_pop,
            source_zero_cost_status_POP_credit_ms=free_status_pop,
            packed_payload=packed_payload,packed_blocks=packed_blocks,
            exchange_SPI_bytes=exwire,exchange_transactions=extx,
            exchange_wire_credit_ms=wire_ms-exms,
            packed_exchange_SPI_bytes=pkwire,packed_exchange_transactions=pktx,
            packed_exchange_wire_credit_ms=wire_ms-pkms,
            frozen_exchange_CPU_ms=total-cpu_gain-(wire_ms-exms),
            frozen_packed_exchange_CPU_ms=total-cpu_gain-(wire_ms-pkms),
            packed_joint_gap_ms=total-cpu_gain-(wire_ms-pkms)-1000/60,
            raw_changed=changed_raw,raw_delta_records=len(delta_records),
            raw_delta_payload=sum(map(len,delta_records)),delta_payload=delta_payload,
            delta_blocks=delta_blocks,delta_exchange_SPI_bytes=dtwire,
            delta_exchange_transactions=dttx,delta_exchange_wire_credit_ms=wire_ms-dtms,
            frozen_delta_exchange_CPU_ms=total-cpu_gain-(wire_ms-dtms),
            delta_joint_headroom_ms=1000/60-(total-cpu_gain-(wire_ms-dtms)),
            observed_output_E2=int(costs[f]['E2_short'])))
    assert rawtotal==71*512 and packedtotal==71*384
    rejects=0
    for bad in [bytes([64,0,0,0]),b'\0',b'\0\0\0']:
        try:pack6(bad)
        except AssertionError:rejects+=1
    try:unpack6(b'\0\0',4)
    except AssertionError:rejects+=1
    assert rejects==4
    # Abstract cold/STOP/count-change reconstruction, not new RTL evidence.
    zeros=bytes(512);changed=bytes([1])+zeros[1:]
    cold=raw_delta(zeros,None);warm_delta=raw_delta(changed,zeros)
    assert raw_decode(cold,None,512)==zeros
    assert raw_decode(raw_delta(changed,None),None,512)==changed
    assert raw_decode([],None,0)==b''
    assert raw_decode(raw_delta(zeros[:256],None),None,256)==zeros[:256]
    negatives=[
        (warm_delta,None,512), # stale delta after STOP or raw0->2
        (cold+[cold[0]],None,512),
        ([bytes([67])+cold[0][1:]],zeros,512),
        ([cold[0][:-1]],zeros,512),
        ([cold[0][:9]+bytes([64])+cold[0][10:]],zeros,512),
        (cold,None,0),
        (warm_delta,zeros[:256],512),
        (cold[:-1],None,512)]
    rejected=0
    for records,previous,count in negatives:
        try:raw_decode(records,previous,count)
        except AssertionError:rejected+=1
    assert rejected==8

    # Only disjoint own counts; no summed inclusive parents.
    own={}
    for line in read(p/'board01/output_files/board.map.rpt').splitlines():
        fields=[v.strip() for v in line.split(';')]
        if len(fields)==14 and re.fullmatch(r'\d+ \(\d+\)',fields[2]):
            own[fields[10]]=int(re.search(r'\((\d+)\)',fields[2])[1])
    assert sum(own.values())==17815
    def region(part):return sum(v for k,v in own.items() if part in k)
    source=region('nes_core257:encoder')
    transport=region('nes_transport257:transport')
    front=region('nes_spi270:spi_front270')
    plan=region('nes_plan_batch206:transport')+region('nes_plan_spi200:endpoint')
    host=sum(v for k,v in own.items() if k.endswith('nes_output260:flow'))
    queue=region('nes_queue260:queue')
    validator=region('nes_validator278:validator')
    assert (source,transport,front,plan,host,queue,validator)==(1399,334,512,711,2486,174,1063)
    endpoint_region=transport+front+plan+host+queue
    expanded=endpoint_region+source+validator
    area=dict(whole_comb=17815,device_comb=15408,deficit=2407,
        source=source,source_transport=transport,common_SPI=front,plan_control=plan,
        host=host,queue=queue,validator=validator,
        source_transport_SPI_even_free_whole=17815-source-transport-front,
        source_transport_SPI_even_free_gap=2407-source-transport-front,
        endpoint_region=endpoint_region,endpoint_region_budget=endpoint_region-2407,
        expanded_region=expanded,expanded_region_budget=expanded-2407,
        retained_outside_expanded=17815-expanded,proved_FPGA_reclaim=0,new_MAP=False)
    retimed=[]
    if a.retimed:
        for name,ref in [('test01',p/'test07'),('window01',p/'window01')]:
            folder=b/name;r=js(folder/'result.json');prior=js(ref/'result.json')
            assert r['passed'] and r['frames']==3 and r['rtl_hashes']==prior['rtl_hashes']
            assert r['CPI']==1 and r['actual_tile_ROM'] and r['actual_SNES_bus_trace_replayed']
            assert read(folder/'nes_output264.c')==read(ref/'nes_output264.c')
            assert read(folder/'CPU-timing.csv')==read(b/'cpu02/timing.csv')
            assert read(folder/'CPU-packets.hex')==read(ref/'CPU-packets.hex')
            assert read(folder/'blocks.txt').splitlines()==[
                x for x in read(ref/'blocks.txt').splitlines() if int(x.split()[0])<=907]
            ev=events(folder);be=events(ref)
            timings={int(x['frame']):x for x in csvs(folder/'cycles.csv')}
            previous={int(x['frame']):x for x in csvs(ref/'cycles.csv')}
            for f in [905,906,907]:
                end=next(x for x in ev if x[0]=='frame_done' and int(x[1])==f)
                priorend=next(x for x in be if x[0]=='frame_done' and int(x[1])==f)
                source_ms=int(timings[f]['total'])*45.454/1e6
                total=source_ms+int(end[3])/1e9
                prevtotal=int(previous[f]['total'])*45.454/1e6+int(priorend[3])/1e9
                polls=sum(x[0]=='arm267' and int(x[1])==f and int(x[2])==226 for x in ev)
                oldpolls=sum(x[0]=='arm267' and int(x[1])==f and int(x[2])==226 for x in be)
                tx=js(folder/f'arm{f}.json')['transfers'];oldtx=js(ref/f'arm{f}.json')['transfers']
                assert [x['tx'] for x in tx if x['tx'].startswith('e1')]==[
                    x['tx'] for x in oldtx if x['tx'].startswith('e1')]
                retimed.append(dict(run=name,frame=f,prior278_ms=prevtotal,diagnostic_ms=total,
                    delta278_ms=total-prevtotal,E2=polls,prior_E2=oldpolls,
                    absolute_end_ms=int(end[2])/1e9,prior_absolute_end_ms=int(priorend[2])/1e9,
                    isolated_CPU_gain_ms=cpudelta[f]/21477.272727))
    warm=rows[2:]
    result=dict(passed=True,stage=279,scope=__doc__,frames=71,ROM_comparison=rom,
        ROM_window=dict(period_cycles=357368,open_first=330088,open_end=354640,qualified_stride=12,
                        core_stride=120,clock_period_ns=45.454,
                        scope='Global-phase deterministic stress fixture, not live NES CPU/physical ROM timing'),
        measured_CPU=measured,CPU_STOP=guards,raw6_roundtrip_bytes=rawtotal,
        raw6_packed_bytes=packedtotal,raw6_rejects=rejects,
        raw_delta=dict(frames=71,decoded_bytes=rawtotal,model_rejects=rejected,
            warm_changed_min=min(x['raw_changed'] for x in rows[2:]),
            warm_changed_max=max(x['raw_changed'] for x in rows[2:]),
            FPGA_base_bytes_before=4608,FPGA_base_bytes_candidate=5120,
            FPGA_canonical_used_before=4398,FPGA_canonical_used_candidate=4910,
            logical_RAM_bits_added=4096,
            M9K_count_delta_inferred=0,physical_RAM_delta_proven=False,
            ARM_additional_history_bytes_upper=512,
            note='Grow existing single-port base_hi512x8 to1024x8; source-side input history, not display-bank reuse. Count change/STOP/epoch mismatch force cold. New RTL, ARM decoder, control/port timing and MAP unimplemented.'),
        frame954=next(x for x in rows if x['frame']==954),
        screens={k:dict(max=max(warm,key=lambda x:x[k])[k],
                        frame=max(warm,key=lambda x:x[k])['frame'],
                        over=sum(x[k]>1000/60 for x in warm))
                 for k in ['baseline_ms','frozen_CPU_only_ms','frozen_free_source_status_POP_ms',
                           'frozen_exchange_CPU_ms','frozen_packed_exchange_CPU_ms','frozen_delta_exchange_CPU_ms']},
        area=area,retimed_OAM_only=retimed,new_CPU=True,new_RTL=False,new_ARM=False,
        new_MAP=False,new_schedule=bool(retimed),new_schedule_frames=len(retimed),
        assumptions=['CPU gains are isolated service measurements; frozen credits are not retimed schedule gains.',
            'Source polling is a TB consumer, not actual ARM source decode. Output ARM CPI1/84MHz remains diagnostic.',
            'Exchange empty-poll count frozen; changed ROM phase, ARM decode/CRC, CDC, refill, port arbitration and final commit costs unknown.',
            'Raw6 roundtrip is representation evidence, not implemented N5-v2 encoder/decoder/CRC protocol.',
            'Raw MASK delta roundtrip uses exact bytes, not CRC equality; source-base serial/epoch and cold coverage remain mandatory.',
            'Plan and output overlap. One common executor requires bounded arbitration and separate live contexts.',
            'No credit for removing source prepare/WAITACK counters or all output E2 wire: these overlap useful work/wait.'],
        full_path_ms=None,P2_selected=False,input_hashes=pins,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with (d/'costs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    (d/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['passed','frame954','screens','area','retimed_OAM_only']},indent=2))

if __name__=='__main__':main()
