"""Align the physical tile destinations and both edges of DMA to the prior display."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import analyze_nes_banks933 as banks
import analyze_nes_obj923 as obj
from analyze_nes_palette921 import coverage, directory, read_csv, sha
from analyze_nes_rows931 import job_times
from analyze_nes_window924 import sample
from nes_chain935 import ORIGINAL, QueuedPages, fit_arm, output


def markers():
    from check_nes_frame862_arm import TimedProbe
    machine=TimedProbe(fit_arm()/'link/src')
    modes={'MMC3':384,'START':385,'BOOT':386,'EARLY':410,'LATE':411,'CONTROL':412}
    address=0x20012000
    cases={f'/sd2snes/NES {k} 925.nh1':v for k,v in modes.items()}
    cases.update({f'NES {k} 925.nh1.tmp':0 for k in modes})
    cases.update({r'\sd2snes\NES EARLY 925.nh1':410,'NES  925.nh1':0,'NES MMC 925.nh1':0,
                  'NES MMC3 935.nh1':0,'NES control 925.nh1':0,'':0})
    assert machine.call('marker_geometry',[0])==0
    for path,expected in cases.items():
        machine.u.mem_write(address,path.encode()+b'\0')
        assert machine.call('marker_geometry',[address])==expected
    return len(cases)+1


def measure(temp,variant,phase,cache,control=False,*,tag=None,trial=None):
    tag=tag or '935'+variant+('base' if control else 'final')
    path=directory(temp,phase,tag,cache)
    old=directory(temp,phase,'933fair',cache)
    base,checks=sample(directory(temp,phase,'925final',cache),ORIGINAL)
    prior,prior_checks=sample(old,ORIGINAL)
    assert checks==prior_checks
    previous=directory(temp,phase,'934windowfair',cache)
    previous_times=job_times(previous)
    current_times=job_times(path)
    assert current_times.keys()==previous_times.keys()
    other934=[(t-previous_times[j],j) for j,t in current_times.items() if j[:2] not in ((912,32),(912,35))]
    rom=output(variant)
    with patch.object(banks,'client',lambda _:rom):
        result=banks.measure(path,trial or (ORIGINAL if control else fit_arm()),base,prior,job_times(old),checks)
    early=result['preDMA']
    rows=[r for r in read_csv(path,'window.csv') if r['g']=='912' and
          int(r['clock'])<result['SEAL'] and r['event'] in ('ppu_dma','ppu_last')]
    writes=[]
    target=result['target_VBlank']
    for entry,start,end in zip(early,rows[::2],rows[1::2],strict=True):
        kind,addr,size,frame=entry
        assert start['event']=='ppu_dma' and end['event']=='ppu_last'
        assert int(start['value'])==size and int(start['frame'])==int(end['frame'])==frame
        writes.append(dict(address=addr,size=size,VBlank=frame,first_line=int(start['line']),
                           last_line=int(end['line']),first=int(start['clock']),last=int(end['clock'])))
    expected=set(coverage(base['pre912']))
    actual=set(coverage([r for r in early if r[3]==target]))
    beam=[]
    for raw in (path/'beam934.csv').read_text().splitlines():
        event,*rest=raw.split(',')
        tick,frame,line,addr,size,latched,a=map(int,rest)
        if frame==target and addr==0x8440 and size==32:
            beam.append(dict(event=event,tick=tick,line=line,latch=latched,A8=a))
    same=result['next_capture_ready']==prior['ready911']
    success=[e for e in beam if e['event'] in ('grant','grant935') and 225<=e['latch']<=252]
    large=next((w for w in writes if w['address']==0x8ca0 and w['size']==288 and w['VBlank']==target),None)
    tail=next((w for w in writes if w['address']==0x8440 and w['size']==32 and w['VBlank']==target),None)
    granted=next((e for e in success if large and tail and large['last']<e['tick']<=tail['first']),None)
    cold_pass=(actual==expected and len(expected)==496 and granted is not None and
               result['total']==15 and result['gain_vs925']>0 and same and result['other_later_vs932']==0)
    return dict(target=target,DMA=writes,beam=beam,bytes_in_target=len(actual & expected),tail_grant=granted,
                cold_pass=cold_pass if cache=='cold' else None,
                capture910=same,capture_D2=result['capture_D2'],capture_offset=result['capture_offset'],
                D2_minus_reference_capture=result['capture_D2']-(prior['ready911']-240*341*4),
                other_count=len(other934),other_later=result['other_later_vs932'],max_other_delay=result['max_other_delta_vs932'],
                later_vs934=sum(delay>0 for delay,_ in other934),latest_vs934=max(other934),
                gaps=result['gaps'],intervals=result['total'],ACK=result['ACK'],ACK925=base['ack912'],
                gain_ms=result['gain_vs925']/21477.272,seal=result['SEAL'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path);p.add_argument('out',type=Path);p.add_argument('variants',nargs='+')
    a=p.parse_args()
    result=dict(ARM_SHA256=sha(fit_arm()/'link/src/obj-nes-100/firmware.stm'),
                flash=(fit_arm()/'link/src/obj-nes-100/firmware.stm').stat().st_size,
                physical_timing=False,marker_cases=markers(),phases={})
    for variant in a.variants:
        rom=output(variant)
        info=json.loads((rom/'build.json').read_bytes())
        result['phases'][variant]=dict(ROM_SHA256=sha(rom/'sink165.sfc'),ROM_free=info['physical_free_B'],
                                       cases={f'{cache}-{phase}':measure(a.temp,variant,phase,cache)
                                              for cache in ('cold','warm') for phase in (1,2)})
        if (rom/'final-stops.json').exists():
            with patch.object(obj,'client',lambda _:rom):
                result['phases'][variant]['guards']=obj.recovery('final',rom,trial=fit_arm())
        for phase in (1,2):
            for case in ('stop','head'):
                edge=directory(a.temp,phase,'935'+variant+'final','cold')/f'edge935-{case}-verified.json'
                if edge.exists():
                    result['phases'][variant].setdefault('after_288_priority',{})[f'p{phase}-{case}']=json.loads(edge.read_bytes())
    if 'bounded' in a.variants:
        result['bounded_original_ARM']={f'{cache}-{phase}':measure(a.temp,'bounded',phase,cache,True)
                                        for cache in ('cold','warm') for phase in (1,2)}
    banks.check_invalidation(QueuedPages)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
