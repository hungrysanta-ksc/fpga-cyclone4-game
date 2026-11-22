"""Align checked 909 tile returns, VRAM writes and 910 capture at a common phase."""
import argparse
import json
from pathlib import Path

from analyze_nes_deadline922 import measure
from analyze_nes_palette921 import coverage, directory, read, read_csv, sha
from analyze_nes_obj923 import recovery, tiles
from nes_window924 import BASE, MODES, WORK, run_tag
from nes_deadline922 import image
from test_nes_raw506_joint import MASTER, PERIOD

# Keep the original, the two interventions, the Flash/receipt controls, and
# the final links on the same pinned trace. Other diagnostics are opt-in.
REVIEW = ('control','queue','receipt','both','fill','fragment','final','headerfit',
          'checked','object','safeheader','objheader')


def sample(folder, arm):
    m, check = measure(folder, arm)
    f = m['frames']
    clocks = f[909]['clocks']
    e0 = clocks['E0_response']
    spi = read(folder/'events.json')
    ea = next(round(e['clock']) for e in spi if e.get('opcode')=='0xea' and e['clock']>e0)
    assert clocks['ACK'] <= e0 < ea < f[910]['commit'] < f[910]['commit_D2']
    oam = [{k:int(r[k]) for k in ('clock','line','frame')} | {'event':r['event']}
           for r in read_csv(folder,'window.csv') if r['g']=='909' and r['op']=='8'
           and r['event'] in ('load','ack')]
    return dict(flash=(arm/'link/src/obj-nes-100/firmware.stm').stat().st_size,
                display908=m['display908'], gaps=m['gaps'], intervals=m['intervals'],
                pre909=f[909]['preDMA'], residual909=f[909]['residual_DMA'], oam909=oam,
                ack909=clocks['ACK'], valid_E0=e0, retire_EA=ea, commit_D3=f[910]['commit'],
                commit_D2=f[910]['commit_D2'], capture_offset=f[910]['D2_minus_nearest_capture'],
                ready911=f[911]['capture_ready'],
                pre912=f[912]['preDMA'], ack912=m['final_ACK']),check


def accepted_dma(folder, pre):
    jobs=tiles(folder)
    available={j['offset']+i+0x4000*j['section']:j['clocks'][-1]
               for j in jobs for i in range(j['bytes'])}
    dma=[r for r in read_csv(folder,'tile532.csv') if r['g']=='909' and r['event']=='tile']
    events=[r for r in read_csv(folder,'window.csv') if r['g']=='909']
    starts=[r for r in events if r['event']=='ppu_dma' and r['op']!='3']
    shown=int(next(r['frame'] for r in events if r['event']=='reveal'))
    early=[(address,n) for kind,address,n,_ in pre if kind=='tile']
    assert [(int(r['dst']),int(r['n'])) for r in dma]==early
    evidence=[]
    for row,(address,n) in zip(dma,early,strict=True):
        ready=max(available[i] for i in range(address,address+n))
        selected=int(row['clock'])
        bus=next(r for r in starts if int(r['clock'])>=selected)
        start=int(bus['clock'])
        assert ready<selected<=start and int(bus['value'])==n
        assert not evidence or evidence[-1]['DMA']<start
        evidence.append(dict(address=address,bytes=n,last_bank_return=ready,selected=selected,
                             DMA=start,line=int(bus['line']),VBlank=int(bus['frame']),shown=shown))
    return evidence


def analyze(temp, modes, partial=False):
    out={}
    for phase in (1,2):
        for cache in ('warm','cold'):
            key=f'{phase}-{cache}'
            ref,quality=sample(directory(temp,phase,'923warm',cache),BASE)
            old,old_quality=sample(directory(temp,phase,'920reference',cache),image('baseline'))
            for field in ('tiles','RGB','map','colors','sections'):
                assert old_quality[field]==quality[field],(key,field)
            for mode in ('915','923',*modes):
                if mode in ('915','923'):
                    row=dict(old if mode=='915' else ref)
                else:
                    folder=directory(temp,phase,run_tag(mode),cache)
                    if partial and not (folder/'records.bin').exists():
                        continue
                    row,actual=sample(folder, BASE if mode=='control' else WORK/mode)
                    costs=quality['params']['driver_extra_us']
                    current=actual['params']['driver_extra_us']
                    assert current.keys()==costs.keys()
                    assert all(abs(current[op]-us)<1e-12 for op,us in costs.items())
                    actual['params']['driver_extra_us']=costs
                    assert actual==quality,(mode,key)
                    if mode=='control':
                        assert row==ref,(mode,key)
                    row['accepted_DMA']=accepted_dma(folder,row['pre909'])
                row['same912']=coverage(row['pre912']).keys()==coverage(ref['pre912']).keys()
                row['pre912_B']=len(coverage(row['pre912']))
                row['capture_offset_from_923']=row['commit_D2']-(ref['commit_D2']-ref['capture_offset'])
                row['early909_B']=len(coverage(row['pre909']))
                row['e0_to_commit_D2']=row['commit_D2']-row['valid_E0']
                row['capture911_gain']=ref['ready911']-row['ready911']
                row['interval_gain']=old['intervals']-row['intervals']
                row['ack_gain']=old['ack912']-row['ack912']
                out.setdefault(mode,{})[key]=row
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--modes',nargs='+',choices=MODES,default=REVIEW)
    p.add_argument('--partial',action='store_true')
    p.add_argument('--recovery',choices=MODES,nargs='*',default=[])
    p.add_argument('--select',choices=MODES,help='require complete timing, Flash and recovery evidence')
    a=p.parse_args()
    cases=analyze(a.temp,a.modes,a.partial)
    evidence={}
    for mode in a.recovery:
        assert mode in cases and len(cases[mode])==4
        evidence[mode]=dict(recovery=recovery(mode,WORK),reports=read(WORK/(mode+'-report.json')))
    wire=a.temp/'nes-header924-wire'
    raw=(wire/'wire.log').read_text()
    assert 'PASS905 first' in raw and 'Errors: 0' in raw
    assert 'short header lane' in (wire/'tb_supply905.sv').read_text()
    gates={}
    for mode,rows in cases.items():
        if len(rows)!=4:
            continue
        warm=[rows[f'{p}-warm'] for p in (1,2)]
        cold=[rows[f'{p}-cold'] for p in (1,2)]
        gates[mode]=dict(flash=all(r['flash']<=212992 for r in rows.values()),
            OBJ_in_previous_blank=all(any(d['address']>=0x4000 and d['VBlank']==d['shown']-1
                                          for d in r.get('accepted_DMA',[])) for r in warm),
            capture_and_display=all(r['capture_offset_from_923']<0 and r['capture911_gain']==PERIOD and
                                    r['display908']==cases['923'][f'{p}-warm']['display908'] and
                                    r['display908']+1==cases['915'][f'{p}-warm']['display908']
                                    for p,r in zip((1,2),warm)),
            warm_interval_and_ack=all(r['interval_gain']>0 and r['ack_gain']>0 for r in warm),
            cold_dma_and_intervals=all(r['pre912_B']==496 and r['same912'] and r['intervals']<=16 for r in cold),
            cold_ack_faster=all(r['ack_gain']>0 for r in cold))
    if a.select:
        assert not a.partial and a.select in evidence
        assert all(gates[a.select].values()),(a.select,gates[a.select])
    out=dict(selected=a.select,master_Hz=MASTER,frame_clocks=PERIOD,cases=cases,gates=gates,proof=evidence,wire=dict(bench=sha(wire/'tb_supply905.sv'),
             monitor=sha(wire/'nes_screen_status151.sv'),observer=sha(wire/'nes_supply905.sv')))
    a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8')
