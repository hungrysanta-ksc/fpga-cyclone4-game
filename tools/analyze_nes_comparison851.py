"""Reconcile board D1 lengths, independent NES pixels and final ARM/65816 display timing."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from analyze_nes_input848 import CLOCK_MS,stats
from analyze_nes_map830 import load,packets,window
from analyze_nes_transition850 import RGB555,STRIDE
from check_nes_game478 import sha
from corpus_nes_848 import CLIPS


def spi_occupancy(events, start, end):
    ticks = Counter()
    for event in events:
        if event['event'] == 'SPI':
            begin = event['start']
        elif event['event'] == 'observer':
            begin = event['clock'] - 8*8*1000*CLOCK_MS/2625000
        else:
            continue
        overlap = min(end,event['clock']) - max(start,begin)
        if overlap > 0:
            ticks[event['opcode']] += overlap
    return {op:round(t/CLOCK_MS,3) for op,t in sorted(ticks.items())}


def trace(temp,clip,phase,variant,work,wire):
    run=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-851-{variant}'
    cpu=load(run/'joint.json')
    assert cpu['passed'] and cpu['commits']==62 and cpu['last_status']==1
    gs=[w['g'] for w in work]
    assert [w['source_frame'] for w in work]==list(range(CLIPS[clip]-2,CLIPS[clip]+60))
    assert [w['generation'] for w in cpu['frames']]==gs
    reveals=[r for r in window(run) if r['event']=='reveal']
    assert [r['g'] for r in reveals]==gs
    events=load(run/'events.json')
    spi=[e for e in events if e['event']=='SPI']
    ea=[e for e in spi if e['opcode']=='0xea']
    d3=[e for e in spi if e['opcode']=='0xd3']
    ack=[v['ACK_masterclock'] for v in cpu['frames']]
    assert [e['generation'] for e in ea]==[e['input_generation'] for e in d3]==gs
    assert all(a<=e['start'] for a,e in zip(ack,ea))
    assert all(e['clock']<=d['start'] for e,d in zip(ea,d3[1:]))
    identity={e['generation']:bytes.fromhex(e['reply']) for e in spi if e['opcode']=='0xe0'}
    d1=Counter()
    for e in spi:
        if e['opcode']=='0xd1':
            d1[e['input_generation']]+=e['bytes']
    screen=run/'first-screen'
    verified=load(screen/'verified.json')
    assert verified['display_ACKs']==62
    mismatch={}
    late=[]
    for serial,(row,v) in enumerate(zip(work,wire),1):
        g,f=row['g'],row['source_frame']
        r=identity[g]
        assert r[7:9]==b'\x01\x03' and int.from_bytes(r[11:15],'little')==serial
        assert int.from_bytes(r[15:17],'little')==g and d1[g]==v['board_D1_B'] and v['source']==f
        src=temp/f'nes-contiguous848-split02/{f}/frame-{f:04d}.rgb'
        expected=src.read_bytes()[8*STRIDE:232*STRIDE].translate(RGB555)
        received=(screen/f'frame-{g}.rgb').read_bytes()[7*STRIDE:231*STRIDE]
        if (run/f'frame-{g}.rgb').read_bytes()[7*STRIDE:231*STRIDE]!=expected:
            late.append(f)
        assert len(received)==len(expected)==224*STRIDE
        if expected!=received:
            mismatch[f]=sum(expected[i:i+3]!=received[i:i+3] for i in range(0,len(expected),3))
    gaps=[b['frame']-a['frame'] for a,b in zip(reveals[1:],reveals[2:])]
    dt=[(b['clock']-a['clock'])/CLOCK_MS for a,b in zip(reveals[1:],reveals[2:])]
    delay=[(e['clock']-a)/CLOCK_MS for e,a in zip(ea[2:],ack[2:])]
    return dict(firmware=cpu['firmware_SHA256'],snes=cpu['client_SHA256'],gaps_VBlank=gaps,
                total_VBlank=sum(gaps),elapsed_ms=round(sum(dt),3),interval_ms=stats(dt),
                final_ACK=ack[-1],final_EA=round(ea[-1]['clock']),ACK_to_EA_ms=stats(delay),
                SPI_D1_B=sum(d1[g] for g in gs[2:]),ARM_instructions=cpu['ARM_instructions'],
                occupied_ms=spi_occupancy(events,reveals[1]['clock'],reveals[-1]['clock']),
                verified_display_ACKs=verified['display_ACKs'],verified_window_rows=verified['exact_window_rows'],
                source_pixel_mismatches=mismatch,late_sample_mismatch_IDs=late),run


def inputs(temp,base,clip):
    data=base/clip/clip
    work=load(data/'work.json')
    standard,candidate=(load(base/f'{s}-{clip}/verified.json')['frames'] for s in ('sender','reuse'))
    old=temp/'nes-work848'/clip/clip
    delta_raw=Counter()
    for w in work:
        name='frame%d.raw'%w['g']
        delta_raw[(data/name).stat().st_size-(old/name).stat().st_size]+=1
    wire=load(base/f'reuse-{clip}/sender.json')
    old_wire=load(base/f'sender-{clip}/sender.json')
    refs=0
    for w,x,y in zip(work[2:],standard[2:],candidate[2:]):
        assert (x['generation'],x['transactions'])==(y['generation'],y['transactions'])
        for i,r in enumerate(wire[str(w['g'])]):
            b=bytes.fromhex(r['wire'])
            prefix=12 if i==0 else 0
            refs+=int(b[prefix:prefix+2]==b'\xff\xfe')
    def cycles(records):
        return sum(r['ready_cycles'] for w in work[2:] for r in records[str(w['g'])])
    return work,standard,candidate,dict(raw_size_delta_B_to_frame_count=dict(delta_raw),
                reused_blocks=refs,transactions=sum(w['transactions'] for w in standard[2:]),
                summed_sender_ready_cycles=[cycles(records) for records in (old_wire,wire)],
                receiver_instructions_826_and_reuse=[sum(v['receive_instructions'] for v in frames[2:])
                                                      for frames in (standard,candidate)],
                saved_D1_B=sum(x['board_D1_B']-y['board_D1_B'] for x,y in zip(standard[2:],candidate[2:])))


def compare(temp,probe):
    root=temp/'nes-comparison851'
    result={}
    for clip in ('opening','demo'):
        work,original,reused,summary=inputs(temp,root,clip)
        control_rx=load(probe/f'plain-{clip}.json')
        assert [g for g,_ in control_rx['frames']]==[w['g'] for w in work]
        summary['receiver_instructions_common']=sum(n for _,n in control_rx['frames'][2:])
        phases={}
        for phase in (1,2):
            runs={}
            expected=None
            for v in ('826','849','common','reuse'):
                r,path=trace(temp,clip,phase,v,work,reused if v=='reuse' else original)
                sequence=packets(path)
                if expected is None:
                    expected=sequence
                    control=path
                r['same_output_packet_order_as_MMC826']=sequence==expected
                r['different_screen_buffers_from_MMC826']=[
                    w['source_frame'] for w in work
                    if sha(path/'first-screen'/('frame-%d.rgb'%w['g']))!=sha(control/'first-screen'/('frame-%d.rgb'%w['g']))]
                assert not r['source_pixel_mismatches'], (clip,phase,v,r['source_pixel_mismatches'])
                assert not r['different_screen_buffers_from_MMC826'], (clip,phase,v,r['different_screen_buffers_from_MMC826'])
                runs[v]=r
            assert runs['common']['firmware']==runs['reuse']['firmware']
            assert control_rx['firmware']==runs['common']['firmware']
            assert len({v['snes'] for v in runs.values()})==1
            delta={}
            for a,b in (('826','849'),('849','common'),('common','reuse'),('849','reuse')):
                delta[f'{a}_to_{b}']=dict(VBlank=runs[b]['total_VBlank']-runs[a]['total_VBlank'],
                        final_ACK_ms=round((runs[b]['final_ACK']-runs[a]['final_ACK'])/CLOCK_MS,3))
            phases[phase]=dict(runs=runs,delta=delta)
        result[clip]=dict(inputs=summary,phases=phases)
    fit=temp/'nes-board851/output_files/board.fit.rpt'
    report=fit.read_text(errors='replace')
    m=re.search(r'Selected device has (\d+) memory locations of type M9K.*?requires (\d+) memory locations',report)
    assert m and 'Error (170040)' in report
    fw=probe/'link/src/obj-nes-100/firmware.stm'
    assert sha(fw)==runs['reuse']['firmware']
    result['resources']=dict(flash=fw.stat().st_size,flash_limit=212992,history_bits=1056*15,
                             M9K_available=int(m[1]),M9K_required=int(m[2]),fit=False,sta=None)
    result['guards']=load(probe/'guards.json')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('temp','probe','out'):
        p.add_argument(arg,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(compare(a.temp,a.probe),indent=2)+'\n')
