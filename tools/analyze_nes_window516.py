# SPDX-License-Identifier: MIT
"""Compare actual 509 and 516 ACKs. Attribute section 5, SEAL and final VBlank waits on one clock."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean
from analyze_nes_transfer512 import CLOCKS_PER_MS, equivalent_packets, fpga, logical_packets, read
from nes_raw506 import sha

def profile(folder):
    with (folder/'window.csv').open() as f:
        rows=[{k:(v if k=='event' else int(v)) for k,v in r.items()} for r in csv.DictReader(f)]
    frames=[]
    for g in range(905,917):
        seq=[r for r in rows if r['g']==g]
        def find(ev):return [r for r in seq if r['event']==ev]
        loads={r['index']:r for r in find('load')}
        service={}
        for ack in find('ack'):
            if ack['section']!=5:continue
            group=str(ack['op'])
            service[group]=service.get(group,0)+ack['clock']-loads[ack['index']]['clock']
        last5=max(r['clock'] for r in find('ack') if r['section']==5)
        seal=find('seal')[0];ready=find('upload165_entry')[0];final=find('final212')[0]
        begin=next(r for r in find('load') if r['op']==3)
        ack=next(r for r in find('ack') if r['op']==3)
        assert ack['value']==1 and last5<=begin['clock']<=seal['clock']<=ready['clock']<=final['clock']<=ack['clock']
        first_dma=find('ppu_dma')[0];reveal=find('reveal')[0]
        waits=[]
        for w in find('wait169'):
            is_final=w['clock']>final['clock']
            ret=next(r for r in seq if r['clock']>w['clock'] and
                     (r['event']=='final_upload212_same_blank212' if is_final else r['event'].startswith('wait_return_')))
            # The instrumented candidate calls wait169 by tail jump. In that case
            # RTS goes to the caller of wait_final516, not the former JSR site.
            waits.append(dict(clock=w['clock'],line=w['line'],stage='final' if is_final else 'upload',
                              wait_clocks=ret['clock']-w['clock'],post_wait_to_ACK_clocks=ack['clock']-ret['clock'],
                              remaining_lower_clocks=max(0,(261-w['line'])*1360) if w['line']>=225 else 0))
        borrows=find('borrow516')
        if borrows:
            assert len(borrows)==1 and borrows[0]['frame']==ack['frame'] and borrows[0]['clock']<reveal['clock']<ack['clock']
        frames.append(dict(generation=g,section5_service_clocks=service,last_section5_ACK=last5,seal_load=begin['clock'],
                           seal_start=seal['clock'],validated_ready=ready['clock'],validated_line=ready['line'],
                           first_PPU_DMA=first_dma['clock'],first_DMA_line=first_dma['line'],final_ready=final['clock'],
                           final_ready_line=final['line'],final_waits=waits,borrow_clocks=[r['clock'] for r in borrows],
                           reveal=reveal['clock'],ACK=ack['clock'],ACK_line=ack['line']))
    return frames

def edge_cases(path):
    edges=read(path/'edges.json');assert len(edges)==8
    cases={}
    for name,r in edges.items():
        events=r['masterclock_events']
        entry=next((e for e in events if e['event']=='released'),None)
        branch=next((e for e in events if e['event'] in ('fresh','borrow')),None)
        ack=next(e for e in events if e['event']=='ACK')
        cases[name]=dict(commits=r['commits'],status=r['status'],release_line=None if entry is None else int(entry['line']),
                         decision=branch['event'] if branch else None,decision_line=int(branch['line']) if branch else None,
                         ack_line=int(ack['line']),decision_to_ACK_clocks=int(ack['clock'])-int(branch['clock']) if branch else None)
    return cases

def check(a):
    t=a.temp;ref=t/'nes-transfer512-original04'
    oracle=equivalent_packets(logical_packets(ref))
    runs={}
    for suffix,start,old in [('01',3000000,ref),('02',3178684,t/'nes-history515-phase-original01')]:
        reference=read(old/'joint.json')
        for variant in ('base','final','fill','both'):
            tag=variant+suffix
            folder=t/f'nes-window516-{tag}'
            j=read(folder/'joint.json');frames=profile(folder)
            assert j['passed'] and j['commits']==12 and j['last_status']==1 and j['future_ACK_filtered'] and j['map_WRAM_VRAM_verified']==12
            assert j['parameters']==reference['parameters'] and j['parameters']['start']==start and j['firmware_SHA256']==reference['firmware_SHA256']
            assert j['ROM_read_allocations']==3280 and j['max_bulk_banks']<=2 and j['vram_DMA_B']==36144
            packets=logical_packets(folder)
            assert equivalent_packets(packets)==oracle
            records=[bytes.fromhex(json.loads(l)[2]) for l in (folder/'packets.jsonl').read_text().splitlines()]
            dma_by_index={}
            with (folder/'window.csv').open() as f:
                for r in csv.DictReader(f):
                    if r['event']=='zero_dma':
                        dma_by_index.setdefault(int(r['index']),[]).append(int(r['value']))
            expected={}
            if variant in ('fill','both'):
                for i,b in enumerate(records,1):
                    if b[:2]==bytes([5,5]) and b[16:]==bytes(2):
                        n=int.from_bytes(b[14:16],'little')
                        expected[i]=[64]*(n//64)+([n%64] if n%64 else [])
            assert dma_by_index==expected
            events=read(folder/'events.json')
            assert sum(e.get('opcode')=='0xea' for e in events)==12
            clocks=[f['ACK'] for f in frames]
            assert clocks==[f['ACK_masterclock'] for f in j['frames']]
            for g in range(905,917):assert sha(folder/f'frame-{g}.rgb')==sha(old/f'frame-{g}.rgb')
            if variant=='base':
                assert clocks==[f['ACK_masterclock'] for f in reference['frames']] and j['wire_B']==reference['wire_B']
            gaps=[(b-a)/CLOCKS_PER_MS for a,b in zip(clocks[1:],clocks[2:])]
            warm=frames[2:]
            runs[tag]=dict(first_display_ms=(clocks[0]-start)/CLOCKS_PER_MS,later_mean_ms=mean(gaps),
                           later_intervals_ms=gaps,later_min_ms=min(gaps),later_max_ms=max(gaps),
                           warm_section5_service_ms=mean(sum(f['section5_service_clocks'].values()) for f in warm)/CLOCKS_PER_MS,
                           warm_last5_to_validated_ms=mean(f['validated_ready']-f['last_section5_ACK'] for f in warm)/CLOCKS_PER_MS,
                           warm_section5_by_op_ms={str(op):sum(f['section5_service_clocks'].get(str(op),0) for f in warm)/(10*CLOCKS_PER_MS) for op in (2,4,5)},
                           warm_zero_DMA_B=sum(sum(v) for i,v in expected.items() if int.from_bytes(records[i-1][8:10],'little')>=907),
                           warm_final_waits=sum(w['stage']=='final' for f in warm for w in f['final_waits']),
                           warm_borrows=sum(len(f['borrow_clocks']) for f in warm),
                           wire_B=sum(j['wire_B'].values()),wire_by_op=j['wire_B'],IRQ=j['SysTick_calls'],ARM_instructions=j['ARM_instructions'],
                           SNES_stack_B=j['observed_stack_B'],ARM_stack_gap_B=int(j['observed_stack_low'],16)-int(j['workspace_end'],16),
                           firmware_SHA256=j['firmware_SHA256'],client_SHA256=j['client_SHA256'],frames=frames,
                           joint_SHA256=sha(folder/'joint.json'),trace_SHA256=sha(folder/'window.csv'))
    cases=edge_cases(a.edges)
    combined_edge=edge_cases(t/'nes-window516-edgesboth03')
    board=t/'nes-window516-fit01';src=t/'nes-fault507-board01'
    pins=read(src/'source-pins.json')['board_inputs']
    assert [n for n,v in pins.items() if sha(board/n)!=v]==['sink-program.hex']
    assert sha(a.client/'sink-program.hex')==sha(board/'sink-program.hex')
    areas={'final':fpga(board)}
    for kind in ('fill','both'):
        variant_board=t/f'nes-window516-fit-{kind}01'
        assert [n for n,v in pins.items() if sha(variant_board/n)!=v]==['sink-program.hex']
        assert sha(a.client.parent.parent/f'{kind}02/client/sink-program.hex')==sha(variant_board/'sink-program.hex')
        areas[kind]=fpga(variant_board)
    for name,area in areas.items():
        selected=board if name=='final' else t/f'nes-window516-fit-{name}01'
        area['SOF_SHA256']=sha(selected/'output_files/board.sof')
    fill=read(t/'nes-window516-fillguards02/fill.json')
    assert len(fill)==8
    cleanup={}
    for fault in ('none','program','done','busy','token'):
        r=read(a.client.parent.parent/f'recovery-{fault}/result.json')
        assert r['passed'] and r['firmware_sha256']==runs['base01']['firmware_SHA256']
        cleanup[fault]=[r['safe_return'],r['base_restored']]
    return dict(scope='Actual Cortex-M4 and actual 65816 with modeled IRQ/SPI/ROM calendar; two identical starts per pair. No new physical test.',
                last_allowed_sample_line=246,boards=areas,baseline_device=fpga(src),SNES_body_B={k:read((a.client if k=='final' else a.client.parent.parent/f'{k}02/client')/'build.json')['body_bytes'] for k in ('final','fill','both')},
                new_WRAM_B=0,runs=runs,edges=cases,combined_edges=combined_edge,fill_guards=fill,ARM_base_recovery=cleanup)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','client','edges','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(check(a),indent=2)+'\n',encoding='utf8',newline='\n')
