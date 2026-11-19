"""Trace the 37.62 s hardware signature and compare full-width, matched replay links."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean

from analyze_nes_ack861 import CLOCK_MS, ROOT, observe
from analyze_nes_map830 import load, packets, window
from prepare_nes_trial802 import PROBES
from analyze_nes_output852 import measure
from analyze_nes_output857 import section5
from check_nes_game478 import sha


def elapsed(clocks):
    return round(clocks/CLOCK_MS,6)


def evidence(folder, generation):
    """Join actual E1 completion to the receiving command index, independent of local generation shifts."""
    w=window(folder)
    payload=packets(folder)
    clocks=[json.loads(line)[1] for line in (folder/'packets.jsonl').read_text().splitlines()]
    loads={r['index']:r for r in w if r['event']=='load'}
    acks={r['index']:r for r in w if r['event']=='ack'}
    selected=[i for i,b in enumerate(payload,1) if int.from_bytes(b[8:10],'little')==generation]
    obj=next(i for i in reversed(selected) if payload[i-1][:2]==bytes((7,1)))
    tail=[]
    for i in selected:
        if i<obj:continue
        b=payload[i-1]
        tail.append(dict(index=i,op=b[0],section=b[1],offset=int.from_bytes(b[10:12],'little'),
                    payload_B=len(b)-16,expanded=int.from_bytes(b[14:16],'little'),
                    arrival=clocks[i-1],load=loads[i]['clock'],ack=acks[i]['clock'],
                    queue_ms=elapsed(loads[i]['clock']-clocks[i-1]),
                    service_ms=elapsed(acks[i]['clock']-loads[i]['clock'])))
    return tail


def boundaries(folder,g):
    with (folder/'seal528.csv').open() as stream:
        dma=[r for r in csv.DictReader(stream) if int(r['g'])==g and r['event']=='dma']
    ppu=[r for r in window(folder) if r['g']==g and r['op']==3]
    first=[r for r in ppu if r['event']=='ppu_dma']
    last=[r for r in ppu if r['event']=='ppu_last']
    rows=[]
    for r,a,b in zip(dma,first,last,strict=True):
        port=int(r['port'])
        source=int(r['src'])&32767
        kind=('palette' if port==34 else 'OAM' if port==4 else 'BG' if source<0x4000 else
              'OBJ' if source<0x5000 else 'map' if source<0x6000 else 'raw')
        rows.append(dict(kind=kind,B=int(r['bytes']),first=a['clock'],last=b['clock'],
                         frame=a['frame'],line=a['line']))
    return [dict(before=x,after=y,wait_ms=elapsed(y['first']-x['last']))
            for x,y in zip(rows,rows[1:]) if x['frame']!=y['frame']]


def gate_budget(folder):
    g=942
    tail=evidence(folder,g)
    baseline=tail[-1]
    modes={}
    for mode in ('branches864','budget864-seal','budget864-raw-tail'):
        src=folder/mode
        ppu=[r for r in window(src) if r['g']==g and r['op']==3]
        stamps={k:next(r['clock'] for r in ppu if r['event']==k) for k in ('load','reveal','ack')}
        assert stamps['load']==baseline['load'] and stamps['ack']==baseline['ack']
        assert stamps['reveal']==next(r['clock'] for r in window(folder) if r['g']==g and r['event']=='reveal')
        timing=load(src/'timing.json') if mode!='branches864' else {}
        modes[mode]=dict(stamps,earlier_wire_ms=elapsed(baseline['arrival']-timing.get('seal_available',baseline['arrival'])))
    with (folder/'branches864/branches.csv').open() as stream:
        branch=[(r[1],*map(int,r[2:])) for r in csv.reader(stream) if int(r[0])==g]
    raw=[r for r in branch if r[-2]==0x9000 and r[5]!=r[4]]
    names=[r[0] for r in raw]
    assert names[:5]==['group538','test_size','test_raw_bank0','test_raw_bank1','fresh618']
    assert 'wait169' in names and 'raw_dispatch489' in names
    return dict(tail=tail,raw_branches=raw,arrivals=modes)


def scene_check(temp, clip, phase, firmware):
    root=temp/('nes-trans850-c0' if clip=='transition' else 'nes-comparison851')
    work=load(root/clip/clip/'work.json')
    trials={}
    for tag in ('855','864joined'):
        # 857ref runs the unchanged final 855 image at the measured 855 SPI cost.
        archive='857ref' if tag=='855' else tag
        folder=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{archive}-on'
        metrics,geometry,_=measure(temp,clip,phase,'on',archive,column=True)
        assert metrics['arm']==firmware[tag]
        reveal=[r for r in window(folder) if r['event']=='reveal']
        checks=(geometry,section5(folder),metrics['client'],load(folder/'joint.json')['parameters'],
                (folder/'startup-clock.txt').read_text().split())
        if clip=='opening':
            prefix=[b for b in packets(folder) if int.from_bytes(b[8:10],'little')<=910]
            assert len(prefix)==101 and all(b[1]!=5 or int.from_bytes(b[10:12],'little')<1121 for b in prefix)
            checks+=(prefix,)
        if tag=='855':
            reference=checks
        else:
            assert checks==reference
        trials[tag]={k:metrics[k] for k in ('verified_pictures','held_blank_VBlanks','display_VBlanks','final_ACK')}
        trials[tag]['opening_deadlines']={w['source_frame']:[r['frame'],r['line']] for w,r in zip(work,reveal,strict=True)
                                         if clip=='opening' and w['source_frame'] in (703,759)}
    return trials


def analyze(temp):
    hw=load(ROOT/'analysis/frame863-hardware.json')['same_tick_OBJ_raw']
    target=[hw[0][k] for k in ('BG','OBJ','map')]
    assert all(r['tick']==3762 and [r[k] for k in ('BG','OBJ','map')]==target for r in hw)
    result=dict(hardware_work=target,hardware_generation=[r['gen'] for r in hw],phases={})
    for ph in (1,2):
        base=temp/f'nes-tile821-demo-jointmirror-p{ph}-861-855-128-high'
        reference=observe(temp,855,ph,128,high=True)
        phase=dict(trials={},hardware_work_matches=sum(r['work']==target for r in reference),
                   fixed_receiver=gate_budget(base))
        result['phases'][ph]=phase
        for arm,cpu,tail_only in [(855,855,False),(860,860,False),(855,860,False),(860,855,False),(855,855,True),(855,855,'control')]:
            tag='tail864' if tail_only else f'{arm}-{cpu}'
            out=temp/f'nes-tile821-demo-jointmirror-p{ph}-861-{arm}-128-high'
            if arm!=cpu:out=out.with_name(out.name+f'-cpu{cpu}-864')
            if tail_only:out=out.with_name(out.name+'-tail864')
            if tail_only=='control':
                tag+='-control'
                out=out.with_name(out.name+'-control')
            if (out/'map-error.txt').exists():
                assert arm==855 and cpu==860 and ph==1 and not (out/'joint.json').exists()
                failure=(out/'failed-beam864/map-error.txt').read_text()
                phase['trials'][tag]=dict(passed=False,reason=failure.split('beam864 ')[-1])
                continue
            rows=observe(temp,arm,ph,128,high=True,consumer=cpu if arm!=cpu else None,tail864=tail_only)
            assert len(rows)==60
            for a,b in zip(reference,rows,strict=True):
                assert (a['source'],a['work'])==(b['source'],b['work'])
                assert sorted(a['map'])==sorted(b['map']) and sorted(a['tile'])==sorted(b['tile'])
                assert b['SEAL_payload_B']==168
            def seals(path):return [p[16:] for p in packets(path) if p[0]==3]
            assert seals(base)==seals(out) and section5(base)==section5(out)
            r=next(x for x in rows if x['g']==942)
            end_diff=rows[-1]['marks'][6]-reference[-1]['marks'][6]
            t=evidence(out,942)
            phase['trials'][tag]=dict(passed=True,intervals=sum(x['gap'] for x in rows),
                final_ACK_clock=rows[-1]['marks'][6],last_ACK_change_ms=elapsed(end_diff),
                multi_VBlank_SEAL_DMA=sum(x['crosses_VBlank'] for x in rows),
                mean_output_ms=round(mean(x['total_ms'] for x in rows),6),
                mean_to_SEAL_ms=round(mean(x['ms']['issue']+x['ms']['queue'] for x in rows),6),
                last_ARM_E0_change_ms=elapsed(rows[-1]['marks'][7]-reference[-1]['marks'][7]),
                target=dict(source=r['source'],work=r['work'],gap=r['gap'],events=r['marks'],
                            beam={e['event']:[e['frame'],e['line']] for e in window(out) if e['op']==3
                                  and e['g']==942 and e['event'] in ('load','reveal','ack')},
                            last_OBJ_ACK_to_SEAL_ms=elapsed(t[-1]['load']-t[0]['ack']),
                            issue_ms=r['ms']['issue'],queue_ms=r['ms']['queue'],arm_sees_ACK_ms=r['ms']['until_E0'],
                            tail_E1_B=sum(x['payload_B']+19 for x in t if x['section']==5),
                            DMA_boundary=boundaries(out,942)))
    root=PROBES/'nes-tail864'
    binaries={'855':PROBES/'nes-trial855/link','864joined':root/'link','control':root/'control',
              'over_limit':root/'over-limit'}
    result['links']={}
    for tag,folder in binaries.items():
        image=folder/'src/obj-nes-100/firmware.stm'
        stack_file=image.parent/'nes_native_sink165.su'
        stack,=[int(line.split('\t')[1]) for line in stack_file.read_text().splitlines() if ':nes_sink212_seal\t' in line]
        bss=int((folder/'size.log').read_text().splitlines()[-1].split()[2])
        result['links'][tag]=dict(bytes=image.stat().st_size,free_B=212992-image.stat().st_size,sha256=sha(image),
                                  bss_B=bss,seal_stack_B=stack)
    assert result['links']['864joined']['free_B']>=0 and result['links']['over_limit']['free_B']<0
    firmware={k:v['sha256'] for k,v in result['links'].items()}
    result['scenes']={clip:{ph:scene_check(temp,clip,ph,firmware) for ph in (1,2)} for clip in ('opening','transition')}
    guards=result['guards']=load(root/'guards.json')
    assert guards['stop']==dict(commits=1,status=228) and guards['restart']==dict(commits=2,status=1)
    assert list(guards['rejected'].values())==[224]*3
    guards['layout']=load(root/'layout/result.json')
    menu=load(root/'menu.json')
    timer=load(root/'timer.json')
    base=load(root/'base/result.json')
    assert timer['firmware']==menu['firmware']==firmware['864joined'] and timer['passed']
    assert menu['rows']['normal']['released'] and base['safe_return'] and base['base_restored']
    guards.update(timer_pass=True,base_restored=True,menu_released=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    args=p.parse_args()
    args.output.write_text(json.dumps(analyze(args.temp),indent=2)+'\n',encoding='utf8',newline='\n')
