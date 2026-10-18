# SPDX-License-Identifier: MIT
"""Packet-order schedule and physical-port audit of the proposed typed split.

Uses recorded C packet order and measured non-map mark intervals; new typed
DMA/setup and parser remain sensitivities, not executed hardware timings.
"""
from pathlib import Path
import argparse,csv,json,struct,shutil
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_spantrade247 import spans,encode,decode
from analyze_nes_mapjoint247 import bitmap
from analyze_nes_validation247 import manifest_wire,manifest_decode
from analyze_nes_batchorder247 import join

BYTE_MS=8/2625
MASTER_MS=21477.270


def append_chunks(ranges,data):
    """Append-only policy prototype. Trailer binding fields are placeholders.

    No buffer backfill: each descriptor's source is the current append pointer
    plus six. Final 32B trailer carries only the count in this policy test;
    production epoch/serial/token/CRC binding is NOT implemented here.
    """
    result=[];body=bytearray();count=0
    def seal():
        return bytes(body)+struct.pack('<H',count)+bytes(30)
    for at,n in ranges:
        if len(body)+6+n+32>2048:
            result.append(seal());body=bytearray();count=0
        src=len(body)+6
        body+=struct.pack('<HHH',at,src,n)+data[at:at+n];count+=1
    if count:result.append(seal())
    return result


def read_chunks(items,base,receipt,initialized):
    out=bytearray(base);seen=set();end=0
    for b in items:
        if not 40<=len(b)<=2048:raise ValueError('chunk bounds')
        count=struct.unpack_from('<H',b,len(b)-32)[0];at=0
        if not count:raise ValueError('empty chunk')
        for _ in range(count):
            if at+6>len(b)-32:raise ValueError('descriptor truncated')
            dst,src,n=struct.unpack_from('<HHH',b,at);at+=6
            if dst%2 or n%2 or not 0<n<=64 or dst<end or dst+n>4096:raise ValueError('destination')
            if src!=at or src+n>len(b)-32:raise ValueError('source')
            out[dst:dst+n]=b[src:src+n];seen.update(range(dst//2,(dst+n)//2));end=dst+n;at+=n
        if at!=len(b)-32:raise ValueError('trailing bytes')
    if bitmap(seen)!=receipt:raise ValueError('receipt')
    if not initialized and len(seen)!=2048:raise ValueError('cold')
    return bytes(out)


def trailer_guards():
    data=bytes((i*31+7)&255 for i in range(4096));cc=append_chunks([(0,2),(16,4),(4094,2)],data)
    bm=bitmap({0,8,9,2047});b=cc[0];cases=[]
    for at,value in [(0,1),(0,4096),(2,0),(4,0),(4,66),(4,3),(8,0),(10,2047),(len(b)-32,0),(len(b)-32,4)]:
        x=bytearray(b);struct.pack_into('<H',x,at,value);cases.append(([bytes(x)],bm,True))
    cases += [(cc+cc,bm,True),([b[:-1]],bm,True),([],bm,True),(cc,bytes(256),True),(cc,bm,False)]
    for item,receipt,init in cases:
        try:read_chunks(item,bytes(4096),receipt,init)
        except ValueError:pass
        else:raise AssertionError('bad append-only policy accepted')
    return len(cases)


def replace_map_packets(pp,wire,mf,compressed):
    result=[];seen=set()
    for b in pp:
        kind='map' if b[0]==9 else 'manifest' if b[0] in (10,11) else None
        if kind is None:result.append(b);continue
        if kind in seen:continue
        seen.add(kind)
        for offset,payload in (wire if kind=='map' else mf):
            h=bytearray(b[:16]);h[0]=9 if kind=='map' else 11 if compressed else 10
            struct.pack_into('<HH',h,10,offset,len(payload));result.append(bytes(h)+payload)
    assert seen=={'map','manifest'}
    return result


def simulate(frame,pp,marks,placement,setup,barrier):
    """One-frame event model. Queued jobs serialize on the single SNES CPU.

    Input must finish before BEGIN. Existing op7 drains before/after. Map
    publication occurs after its LAST packet, never at output-phase start.
    Four outstanding jobs constrain ordinary output credits. Unknown source,
    planner, FPGA parse, tile generation, dispatch and waits are zero here.
    """
    source=placement['source_spi_bytes'];total=placement['ready4_bytes']
    ordinary=[b for b in pp if b[0] not in (1,3,7)]
    bulk=sum(b[0]==7 for b in pp)
    allocated=sum(len(b)-16+19 for b in pp if b[0]!=7)+83*bulk
    allocated+=20*((len(ordinary)+3)//4)+99+32
    # Keep the existing final-control67 after display, not hidden under work.
    prefix=total-source-allocated-67
    assert prefix>=0,(frame,prefix)
    t=source*BYTE_MS;cpu=t;pending=[];events=[];wire=source;mi=0;seq=0
    map_remaining=sum(b[0]==9 for b in pp);map_retire_pending=False
    map_ready=map_end=None;credit_wait=0
    def event(label,start,end,bytes_=0):
        events.append(dict(frame=frame,policy='barrier' if barrier else 'queued',setup_clocks=setup,
                           event=label,start_ms=start,end_ms=end,spi_bytes=bytes_))
    def spi(label,n):
        nonlocal t,wire
        start=t;t+=n*BYTE_MS;wire+=n;event(label,start,t,n)
    def drain():
        nonlocal t
        t=max(t,cpu);pending.clear()
    def job(label,ms,queued=True):
        nonlocal t,cpu,credit_wait
        pending[:]=[x for x in pending if x>t]
        if queued and len(pending)>=4:
            old=t;t=max(t,pending.pop(0));credit_wait+=t-old
        start=max(t,cpu);cpu=start+ms;event(label,start,cpu)
        if queued:pending.append(cpu)
        assert len(pending)<=4
    event('source_input',0,t,source)
    for index,b in enumerate(pp):
        op=b[0];n=len(b)-16
        if op==1:
            spi('BEGIN',n+19);spi('plan_and_initial_controls',prefix)
        elif op==7:
            drain();spi('tile_descriptor_command',43)
            expanded=int.from_bytes(b[14:16],'little')
            job('tile_mark_and_payload_normalization',marks[mi]+8*expanded/MASTER_MS,False);mi+=1
            drain();spi('tile_ack_polls',40)
        elif op==3:
            drain()
            if map_retire_pending:spi('typed_ack_polls',40)
            spi('SEAL_certificate',n+19+32)
            job('coverage_tail',placement['seal_coverage_tail_ms'],False);drain()
            job('display_sample',placement['display_sensitivity_maximum_ms'],False);drain()
            spi('final_retire_controls',67)
        else:
            # Source SPI and destination SPI share one serial timeline.
            pending[:]=[x for x in pending if x>t]
            if len(pending)>=4:
                old=t;t=max(t,pending.pop(0));credit_wait+=t-old
            spi('map_packet' if op==9 else 'manifest_packet' if op in (10,11) else 'metadata_packet',n+19)
            if op==9:
                map_remaining-=1
                if map_remaining==0:
                    map_ready=t
                    spi('typed_descriptor_command',59)
                    ms=placement['staging_payload_normalization_ms']+placement['runs']*setup/MASTER_MS
                    job('typed_map_dma',ms);map_end=cpu
                    if barrier:drain();spi('typed_ack_polls',40)
                    else:map_retire_pending=True
            elif op in (10,11):
                # One ordered FIFO read head: FPGA cannot inspect manifest
                # past an earlier SNES-owned packet that has not retired.
                drain()
            else:
                # Only measured mark is charged. Other packet copy/dispatch,
                # MVN/RLE and ordinary payload DMA remain explicitly unknown.
                job('metadata_mark',marks[mi]);mi+=1
            seq+=1
            if seq%4==0 or seq==len(ordinary):spi('ordinary_ready_poll',20)
    assert mi==len(marks) and wire==total and map_ready is not None
    serial=[e for e in events if e['spi_bytes']]
    assert sum(e['spi_bytes'] for e in serial)==total
    assert all(a['end_ms']<=b['start_ms'] for a,b in zip(serial,serial[1:]))
    return dict(frame=frame,policy='barrier' if barrier else 'queued',setup_clocks=setup,
                total_ms=t,headroom_ms=1000/60-t,spi_bytes=wire,prefix_plan_control_bytes=prefix,
                map_ready_ms=map_ready,map_end_ms=map_end,queue_credit_wait_ms=credit_wait,
                total_display_low_ms=t-placement['display_sensitivity_maximum_ms']+placement['display_sensitivity_minimum_ms']),events


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);pins={};probe=BASE/'probes/nes-wholepath247'
    def pin(f,expected=None):
        h=sha(f)
        if expected is not None:assert h==expected,f
        pins[f.relative_to(BASE).as_posix()]=h;return f
    def read(f):return json.loads(pin(f).read_text(encoding='utf-8'))
    prior=read(probe/'placement05/result.json');old=read(probe/'validation-analysis02/result.json')
    joint=read(probe/'jointdecode-analysis03/result.json');assert all(x['passed'] for x in (prior,old,joint))
    placements={r['frame']:r for r in prior['rows'] if r['placement']=='FPGA_typed_ext16'}
    packetsets=[]
    for stage,proof in [('validation-test02',old),('jointdecode-test02',joint)]:
        groups={g:[] for g in range(1,72)}
        for f in sorted((probe/stage/'run').glob('req-*.bin')):
            b=pin(f,proof['input_hashes'][f.relative_to(BASE).as_posix()]).read_bytes()
            groups[int.from_bytes(b[8:10],'little')].append(b)
        packetsets.append(groups)
    timing=probe/'validation-test02/run/mask-phase247.csv'
    mark={g:[] for g in range(1,72)};start={}
    for r in csv.DictReader(pin(timing,old['input_hashes'][timing.relative_to(BASE).as_posix()]).open()):
        g=int(r['generation']);t=int(r['master_clock'])
        if r['event']=='mark212':start[g]=t
        elif r['event']=='mark_return247':mark[g].append((t-start.pop(g))/MASTER_MS)
    jointrows={(int(r['frame']),r['mode']):r for r in csv.DictReader(pin(probe/'validation-analysis02/joint-frames.csv').open())}
    for name in ('nes_delta231.py','analyze_nes_spantrade247.py','analyze_nes_mapjoint247.py',
                 'analyze_nes_validation247.py','analyze_nes_maskrun247.py','analyze_nes_batchorder247.py','analyze_nes_geometry230.py'):
        pin(ROOT/'tools'/name)
    rows=[];events=[];chunkrows=[];last=bytes(4096);stale=[set(range(2048)),set(range(2048))]
    banks={gap:[bytes(4096),bytes(4096)] for gap in (0,16)};checked=0
    for g in range(1,72):
        f=g+904;pp=packetsets[1][g]
        nonmap=lambda items:[b[:2]+b[10:16]+(b[16:] if b[0]!=7 else b'') for b in items if b[0] in (2,4,5,7,8)]
        assert nonmap(packetsets[0][g])==nonmap(pp)
        assert abs(sum(mark[g])-old['rows'][g-1]['mark_ms'])<1e-9
        assert max(i for i,b in enumerate(pp) if b[0]==7)<min(i for i,b in enumerate(pp) if b[0]==9)
        path=probe/f'jointdecode-test02/run/expected-{g}.bin'
        current=pin(path,joint['input_hashes'][path.relative_to(BASE).as_posix()]).read_bytes()[:4096]
        bank=(g-1)%2;changed={w for w in range(2048) if current[2*w:2*w+2]!=last[2*w:2*w+2]}
        for st in stale:st.update(changed)
        words=set(stale[bank])
        for gap in (0,16):
            fmt='exact64' if gap==0 else 'gap16_64';rr=spans(words,gap,64);wire=encode(rr,current,True)
            assert join([(2,at,n) for at,n in rr])==join([(2,w*2,2) for w in sorted(words)])
            covered={w for at,n in rr for w in range(at//2,(at+n)//2)};bm=bitmap(covered)
            got,seen=decode(wire,True,banks[gap][bank],g>2,[(0,bm[:240]),(240,bm[240:])])
            cc=append_chunks(rr,current)
            assert got==current and seen==covered and words<=covered
            assert read_chunks(cc,banks[gap][bank],bm,g>2)==current
            checked+=8192;banks[gap][bank]=current
            mf=manifest_wire(bm);compressed=sum(len(b)+19 for at,b in mf)<294
            if compressed:assert manifest_decode(mf)==bm
            else:mf=[(0,bm[:240]),(240,bm[240:])]
            replaced=replace_map_packets(pp,wire,mf,compressed)
            if gap==0:
                assert [b[16:] for b in replaced]==[b[16:] for b in pp]
            model=jointrows[f,'packed_'+fmt];placement=dict(placements[f])
            placement.update(ready4_bytes=int(model['ready4'])+99*len(cc)+32,
                             runs=len(rr),chunks=len(cc),staging_payload_normalization_ms=sum(n for at,n in rr)*8/MASTER_MS)
            if gap==0:assert placement==placements[f]
            chunkrows.append(dict(frame=f,format=fmt,runs=len(rr),values_bytes=sum(n for at,n in rr),
                chunks=len(cc),maximum_chunk=max(map(len,cc)),spi_bytes=placement['ready4_bytes']))
            if f<907:continue # cold needs multiple typed chunks, not this warm schedule
            assert len(cc)==1
            for barrier in (True,False):
                for setup in (0,500,1000,1500):
                    row,ev=simulate(f,replaced,mark[g],placement,setup,barrier)
                    row['format']=fmt;rows.append(row)
                    if f in (952,954,955,970):
                        for e in ev:e['format']=fmt
                        events+=ev
        stale[bank].clear();last=current
    for f in range(907,976):
        assert len({r['prefix_plan_control_bytes'] for r in rows if r['frame']==f})==1
    board=BASE/'probes/nes-source240/board01'
    for f in ('nes_bulk_aperture188.sv','nes_tile_bulk206.sv','nes_sink_spi165.sv',
              'nes_source_encoder240.sv','nes_source240.sv','nes_direct206.sv','nes_live_joint.sv',
              'output_files/board.map.rpt','output_files/board.fit.rpt','output_files/board.fit.summary'):
        pin(board/f)
    for f in ('nes_native_runtime165.c','nes_sink_window184.c','nes_plan_service200.c'):
        pin(BASE/'probes/nes-runtime233/arm01/src'/f)
    report=(board/'output_files/board.map.rpt').read_text(errors='replace')
    # Preserve exact table rows for selected boundaries, no additive FIT claim.
    entities={}
    for name in ('nes_source240:native_source240','nes_source_encoder240:encoder',
                 'nes_sink_spi165:endpoint','nes_bulk_aperture188:aperture','nes_tile_bulk206:bulk'):
        lines=[x for x in report.splitlines() if x.startswith(';') and '|'+name+'|' in x and ' ; ' in x]
        # The utilization table starts its entity cell with the short hierarchy.
        rows_for_entity=[x for x in lines if x.split(';')[1].strip().strip('|')==name]
        assert rows_for_entity,name
        entities[name]=rows_for_entity[0]
    aperture=(board/'nes_bulk_aperture188.sv').read_text()
    endpoint=(board/'nes_sink_spi165.sv').read_text()
    assert 'storage[{writer,count[10:0]}]<=byte_data;' in aperture
    assert 'retired<=retired+1\'b1' in endpoint and 'if(checking&&enable&&!fault)' in endpoint
    summary={}
    for fmt in ('exact64','gap16_64'):
      for policy in ('barrier','queued'):
        for setup in (0,500,1000,1500):
            rr=[r for r in rows if r['format']==fmt and r['policy']==policy and r['setup_clocks']==setup]
            summary[f'{fmt}_{policy}_{setup}']=dict(max_ms=max(r['total_ms'] for r in rr),
                max_with_display_low_ms=max(r['total_display_low_ms'] for r in rr),
                over=[r['frame'] for r in rr if r['headroom_ms']<0],minimum_headroom_ms=min(r['headroom_ms'] for r in rr),
                frame954=next(r for r in rr if r['frame']==954))
    result=dict(passed=True,stage=248,scope=__doc__,frames=71,scheduled_warm_frames=69,cold_schedule_excluded=True,schedules=len(rows),summary=summary,
        rows=rows,events=events,chunkrows=chunkrows,source_entities=entities,input_hashes=pins,script_sha256=sha(Path(__file__)),
        reconstructions=284,reconstructed_bytes=checked,python_trailer_negatives=trailer_guards(),
        same_final_map_dma_all=True,
        merged_base='64640645e3e37adb697d0293a509d0329e4eae4e',
        area=dict(required_le=15898,device_le=15408,required_labs=1003,device_labs=963,
                  base_m9k=54,typed_prior_m9k_arithmetic=56,receipt_bytes=256,
                  descriptor_prefix_requires_backfill_or_count_pass=True,aperture_random_write_supported=False,
                  packet_release_current_owner='SNES ACK checker only',new_area_measured=False),
        physical=False,fit=False,new_cpu_execution=False,new_rtl=False,
        limitations=['ActualC packet order and prior measured marks;new event times are conditional,not device execution.',
          'Known wire is conserved exactly. Plan/control residual is grouped before tile barriers;unknown tile generation and ARM time are zero.',
          'Gap16 replaces only map/manifest packets in Python;not an executed C sender. Trailer is a policy model with binding placeholders,not a certificate.',
          'New FPGA parser and SNES chunk fixed overhead are zero;setup0 is diagnostic only,500..1500 sensitivity not measured.',
          'Nonmap copy/dispatch/RLE/MVN/ordinary DMA time,extra polls and source prepare remain unknown.',
          'Aperture map notification is after last map packet. Queued variant REQUIRES new asynchronous typed ownership;existingop7 is barrier.',
          'Existing4slot FIFO,FPGA shared read port and head ownership need redesigned routing;the model does not implement it.',
          'Coverage and display remain after drain/certificate;display samples exclude VBlank waits and are not WCET.',
          'MAP entity counts cannot be subtracted from FIT totals or added as reclaimed area. No candidate has joint area/time approval.'])
    raw=a.out/'result.json';raw.write_text(json.dumps(result,indent=2)+'\n')
    public={k:v for k,v in result.items() if k not in ('rows','events','chunkrows','input_hashes')}
    public.update(input_count=len(pins),private_result_sha256=sha(raw))
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n')
    for name,data in [('frames.csv',rows),('events.csv',events),('chunks.csv',chunkrows)]:
        with (a.out/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
    shutil.copyfile(__file__,a.out/'analyzer.py');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
