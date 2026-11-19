"""Hardware bin 7 and matched replay: producer/consumer timestamps and first valid ARM reply."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import numpy as np

from analyze_nes_input848 import CLOCK_MS
from analyze_nes_map830 import load, packets, window
from analyze_nes_output856 import ROOT, overlap, physical
from analyze_nes_transition850 import RGB555, STRIDE
from check_nes_game478 import crc
from prepare_nes_ack861 import SOURCE


def real(logs, ed):
    path=logs/f'nes-budget-mmc{ed}.txt'
    hw=physical(path)
    fields=dict(l.split('=',1) for l in path.read_text().splitlines() if '=' in l)
    row=dict(zip(fields['columns'].split(','), (int(x,16) for x in fields['b07'].split(',')),strict=True))
    n=row['frames']
    out=hw['bins'][35]
    for op in ('e0','e8','e1','out'):
        out[op+'_B_per_frame']=round(row[op]/n,5)
    out['E0_per_frame']=out['e0_B_per_frame']/20
    # Short format covers slots 0..255. Full frames contribute at most 1024 to BG.
    out['min_frames_using_high_BG_slot']=max(0,(row['bg']-256*n+767)//768)
    calls,_,hi,lo,_=map(int,fields['cost_op_04'].split(','))
    out['estimated_E0_SPI_ms_per_frame']=round(out['E0_per_frame']*((hi<<32)+lo)/int(fields['cost_clock_hz'])*1000/calls,5)
    poll=list(map(int,fields['cost_poll_2'].split(',')))
    assert poll[0]==poll[1]+poll[2]
    return dict(bin=out,sha=hw['sha256'],whole_run_final_quiet=poll[2])


def observe(temp, ed, phase, quiet, pin=None, high=False, consumer=None, tail864=False):
    base=temp/'nes-ack861'
    suffix='' if pin is None else f'-g{pin}-bounded'
    slot='-high' if high else ''
    d=temp/f'nes-tile821-demo-jointmirror-p{phase}-861-{ed}-{quiet}{slot}{suffix}'
    if consumer is not None:
        d=d.with_name(d.name+f'-cpu{consumer}-864')
    if tail864:
        d=d.with_name(d.name+'-tail864')
        if tail864=='control':d=d.with_name(d.name+'-control')
    r=load(d/'joint.json')
    expected=load(ROOT/f'analysis/trial{ed}-package.json')
    client=load(ROOT/f'analysis/trial{consumer}-package.json')['client'] if consumer else expected['client']
    sources=SOURCE if pin is None else SOURCE[:pin+2-905]
    arm=expected['ARM']
    if tail864:
        from prepare_nes_trial802 import PROBES
        from nes_raw506 import sha
        arm=sha(PROBES/'nes-tail864'/('control' if tail864=='control' else 'link')/'src/obj-nes-100/firmware.stm')
    assert r['passed'] and r['commits']==len(sources) and r['firmware_SHA256']==arm and r['client_SHA256']==client
    obs=load(d/'ack861.json')
    spi=[e for e in load(d/'events.json') if e['event']=='SPI']
    transactions=defaultdict(list)
    for e in spi:
        transactions[e['generation']].append(e)
    d1=Counter()
    for e in spi:
        if e['opcode']=='0xd1':
            d1[e['input_generation']]+=e['bytes']
    for f in load(base/'sender-demo/verified.json')['frames'][:len(sources)]:
        assert d1[f['generation']]==f['board_D1_B']
    e1=[e for e in spi if e['opcode']=='0xe1']
    payload=packets(d)
    assert len(payload)==len(e1)
    ppu=defaultdict(list)
    for e in window(d):
        ppu[e['g']].append(e)
    rows=[]
    previous=None
    for i,(source,(begin,end),work) in enumerate(zip(sources,obs['output'],obs['loads'],strict=True)):
        g=905+i
        assert (d/f'frame-{g}.rgb').read_bytes()[7*STRIDE:231*STRIDE]==(
            base/'split'/str(source)/f'frame-{source:04d}.rgb').read_bytes()[8*STRIDE:232*STRIDE].translate(RGB555)
        p=ppu[g]
        head,=(e for e in p if e['event']=='load' and e['op']==3)
        show,=(e for e in p if e['event']=='reveal')
        ack,=(e for e in p if e['event']=='ack' and e['op']==3)
        if i<2:  # Cold DMA tracing records starts only for the first bank.
            previous=show['frame']
            continue
        idx=head['index']
        seal=payload[idx-1]
        send=e1[idx-1]
        assert seal[0]==3 and send['generation']==g
        inside=[e for e in p if head['clock']<=e['clock']<=show['clock']]
        dma=[e for e in inside if e['event']=='ppu_dma']
        ends=[e for e in inside if e['event']=='ppu_last']
        assert len(dma)==len(ends)>0
        status=[e for e in transactions[g] if e['opcode']=='0xe0' and e['start']>=send['clock']-1]
        receipt=bytes([1,3])+seal[2:10]+bytes.fromhex('659a')
        valid=[]
        for e in status:
            b=bytes.fromhex(e['reply'])
            assert b[1]==0xf7 and crc(b[1:19],8,7,0)==b[-1]
            if b[7:19]==receipt and b[2]&7==2 and int.from_bytes(b[3:5],'big')==int.from_bytes(b[5:7],'big')==idx:
                valid.append(e)
        first=valid[0]
        assert first['start']>=ack['clock']-1 and r['frames'][i]['ACK_masterclock']==ack['clock']
        marks=[begin,send['clock'],head['clock'],dma[0]['clock'],ends[-1]['clock'],show['clock'],ack['clock'],first['clock'],end]
        assert marks==sorted(marks),(source,marks)
        parts=['issue','queue','until_DMA','DMA_span','until_show','publish_ACK','until_E0','after_E0']
        ms={k:round((b-a)/CLOCK_MS,6) for k,a,b in zip(parts,marks,marks[1:])}
        calls=[e for e in status if e['start']<first['start']]
        def input_wire(start,stop):
            return round(sum(overlap(start,stop,e['start'],e['clock']) for e in transactions[g]
                             if e['opcode'] in ('0xd0','0xd1','0xd2','0xd3'))/CLOCK_MS,6)
        quiet_wait=[clock for gen,clock,reason,progress in obs['waits'] if gen==g and reason==2 and not progress]
        ranges=[]; tiles=[]
        for b in payload:
            if int.from_bytes(b[8:10],'little')!=g:continue
            at,n,span=[int.from_bytes(b[j:j+2],'little') for j in (10,12,14)]
            if b[1]==2 and b[0] in (2,4,9):
                ranges.append((at,1472 if b[0]==9 else n if b[0]==2 else span))
            elif b[0]==7:
                tiles.append((b[1],at,span))
        rows.append(dict(
            source=source, g=g, work=work, ms=ms, total_ms=round((end-begin)/CLOCK_MS,6),
            marks=[round(x,2) for x in marks], frames=[head['frame'],dma[0]['frame'],show['frame']],
            crosses_VBlank=dma[0]['frame']!=ends[-1]['frame'],
            map=ranges, tile=tiles, DMA_B=sum(e['value'] for e in dma),
            DMA_active_ms=round(sum(b['clock']-a['clock'] for a,b in zip(dma,ends))/CLOCK_MS,6),
            SEAL_payload_B=len(seal)-16, gap=show['frame']-previous, quiet=len(quiet_wait), pending_E0=len(calls),
            E0_calls=sum(e['opcode']=='0xe0' for e in transactions[g]),
            E8_calls=sum(e['opcode']=='0xe8' for e in transactions[g]),
            E1_bytes=sum(e['bytes'] for e in transactions[g] if e['opcode']=='0xe1'),
            input_SPI_after_ACK_ms=input_wire(ack['clock'],first['clock']),
            input_SPI_after_E0_ms=input_wire(first['clock'],end),
            pending_before_show=sum(e['start']<show['clock'] for e in calls),
            pending_before_ACK=sum(e['start']<ack['clock'] for e in calls),
            first_query_after_ACK_ms=round((first['start']-ack['clock'])/CLOCK_MS,6)))
        previous=show['frame']
    return rows


def summarize(rows):
    return dict(mean_ms={k:round(mean(r['ms'][k] for r in rows),5) for k in rows[0]['ms']},
                total_ms=round(mean(r['total_ms'] for r in rows),5),work=[round(mean(r['work'][k] for r in rows),4) for k in range(3)],
                DMA_active_ms=round(mean(r['DMA_active_ms'] for r in rows),5),
                spi_per_generation={k:round(mean(r[k] for r in rows),4) for k in ('E0_calls','E8_calls','E1_bytes')},
                input_SPI_after_ACK_ms=round(mean(r['input_SPI_after_ACK_ms'] for r in rows),5),
                input_SPI_after_E0_ms=round(mean(r['input_SPI_after_E0_ms'] for r in rows),5),
                quiet=sum(r['quiet'] for r in rows),pending_E0=sum(r['pending_E0'] for r in rows),
                pending_before_show=sum(r['pending_before_show'] for r in rows),
                pending_before_ACK=sum(r['pending_before_ACK'] for r in rows),
                SEAL_payload_counts=dict(Counter(r['SEAL_payload_B'] for r in rows)),
                gaps=sum(r['gap'] for r in rows),last_ACK=rows[-1]['marks'][6])


def standardize(sets, hw):
    """One common set of weights, selected by workload only, for paired stage times."""
    target=np.array([mean(hw[e]['bin'][k] for e in (855,860)) for k in ('bg','obj','mapdirty')])
    work=np.asarray([r['work'] for r in sets['855']],dtype=float)
    x=(work-target)/np.maximum(1,work.std(axis=0))
    theta=np.zeros(3)
    def moments(t):
        s=x@t
        w=np.exp(s-s.max())
        return w/w.sum(), s.max()+np.log(w.sum())
    bounds=dict(target=target.tolist(),sample_min=work.min(axis=0).tolist(),sample_max=work.max(axis=0).tolist())
    if np.any(target<work.min(axis=0)) or np.any(target>work.max(axis=0)):
        return dict(**bounds,matched=False)
    for _ in range(100):
        w,loss=moments(theta)
        err=w@x
        if max(abs(err))<1e-8:
            assert max(abs(w@work-target))<1e-5
            return dict(**bounds,matched=True,effective_frames=round(1/(w@w),2),
                        DMA_active_ms={tag:round(float(w@[r['DMA_active_ms'] for r in rows]),5)
                                       for tag,rows in sets.items()},
                        fraction_DMA_crosses_VBlank={tag:round(float(w@[r['crosses_VBlank'] for r in rows]),5)
                                                     for tag,rows in sets.items()},
                        mean_ms={tag:{k:round(float(w@[r['ms'][k] for r in rows]),5)
                                      for k in rows[0]['ms']} for tag,rows in sets.items()})
        centered=x-err
        direction=np.linalg.lstsq((centered*w[:,None]).T@centered,err,rcond=1e-12)[0]
        for power in range(25):
            trial=theta-direction*0.5**power
            if moments(trial)[1]<loss:
                theta=trial
                break
        else:
            break
    return dict(**bounds,matched=False)


def compare(temp,hw,phase,high):
    sets={tag:observe(temp,ed,phase,q,high=high) for tag,ed,q in [('855',855,128),('860',860,128),('860_slow',860,256)]}
    workload={}
    for a,b,c in zip(*sets.values(),strict=True):
        for key in ('source','work','map','tile'):
            assert a[key]==b[key]==c[key],(a['source'],key)
        workload[a['source']]=dict(map=a['map'],tile=a['tile'])
        for row in (a,b,c):
            del row['map'],row['tile']
    result=dict(summary={k:summarize(rows) for k,rows in sets.items()},
                common_workload=standardize(sets,hw),geometry=workload,frames=sets)
    gen=911 if high else 907
    pinned=next(row for row in observe(temp,860,phase,256,pin=gen,high=high) if row['g']==gen)
    ref=next(row for row in sets['860'] if row['g']==gen)
    assert pinned['source']==ref['source'] and pinned['work']==ref['work']
    # Reconstructed phase entry uses integer DWT ticks; wire completion is observed directly.
    assert abs(pinned['marks'][0]-ref['marks'][0])<1 and pinned['marks'][1]==ref['marks'][1]
    result['single_frame_control']=pinned
    return result


def analyze(temp,logs):
    hw={ed:real(logs,ed) for ed in (855,860)}
    phases={phase:compare(temp,hw,phase,False) for phase in (1,2)}
    high={phase:compare(temp,hw,phase,True) for phase in (1,2)}
    for p in (1,2):
        assert high[p]['summary']['860']['SEAL_payload_counts']=={168:60}
        assert phases[p]['summary']['860']['SEAL_payload_counts']=={72:60}
        for a,b in zip(phases[p]['frames']['860'],high[p]['frames']['860'],strict=True):
            assert [a['work'][0]+439,*a['work'][1:]]==b['work']
    return dict(hardware=hw,phase=phases,high_slot=high,
                marks='SNES master clocks. ARM output start, SEAL wire end, consumer load, first post-SEAL DMA, last pre-reveal DMA byte, reveal, SNES ACK, first E0 transfer end with full matching receipt, ARM output end. DMA_span includes setup/gaps. Two bank warmups excluded.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','logs','out'): parser.add_argument(k,type=Path)
    a=parser.parse_args()
    a.out.write_text(json.dumps(analyze(a.temp,a.logs),separators=(',',':'))+'\n')
