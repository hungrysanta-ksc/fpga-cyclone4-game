"""Matched MMC662 output costs; distinguish measured hardware averages from replay."""
import argparse
import json
from pathlib import Path
from analyze_nes_output615 import run, group, csv_groups, packets, one, read, ms, sha
from analyze_nes_export636 import run as verify
from analyze_nes_frontier536 import contents
from analyze_nes_dma542 import partition
from check_nes_fault641 import ROOT, evidence
from nes_schedule492 import funcs


def trace(folder, reference):
    checked = verify(folder, reference, expected_bg_hits=0)
    frames = run(folder, {})
    cpu = csv_groups(folder/'window.csv')
    cmds = packets(folder)
    events = read(folder/'events.json')
    obj = read(folder/'obj-phases.json')
    costs = partition(folder)
    tile_events = csv_groups(folder/'tile532.csv')
    early = {}
    for g in range(906,958):
        issued = dict(map=sum(int.from_bytes(h[14:16],'little') or int.from_bytes(h[12:14],'little')
                             for h,_,_ in cmds[g] if h[1]==2),
                      tile=sum(len(b) for h,b,_ in cmds[g] if h[0]==7))
        early[g] = {k: v-costs[g]['DMA_B'].get(k,0) for k,v in issued.items()}
        assert min(early[g].values()) >= 0
        assert early[g]['tile']==sum(r['n'] for r in tile_events.get(g,[]) if r['event']=='tile')
        grants=[r for r in cpu[g] if r['event']=='ppu_dma' and r['op']==-1]
        assert sum(r['value'] for r in grants)==sum(early[g].values())
        assert all(225<=r['line']<=261 for r in grants)
    details = {}
    intervals = {}
    for g in range(906,958):
        current=one([r for r in cpu[g] if r['op']==3],'reveal')
        previous=one([r for r in cpu[g-1] if r['op']==3],'reveal')
        intervals[g]=dict(VBlank=current['frame']-previous['frame'],
                          ms=ms(current['clock']-previous['clock']),
                          final_waits=frames[g]['final_waits'])
    for g in (914,915,*range(951,958)):
        previous = one([r for r in cpu[g-1] if r['op']==3], 'reveal')['clock']
        ev = [e for e in events if e['generation']==g]
        loads = [r for r in cpu[g] if r['event']=='load']
        acks = [r for r in cpu[g] if r['event']=='ack']
        spi = [e for e in ev if e['event']=='SPI' and e['opcode']=='0xe1']
        rows=[]
        for (h, bulk, push), load, ack in zip(cmds[g], loads, acks, strict=True):
            assert (h[0],h[1]) == (load['op'],load['section']) == (ack['op'],ack['section'])
            sent, = [e for e in spi if abs(e['clock']-push)<=1]
            offset=int.from_bytes(h[10:12],'little')
            seq=int.from_bytes(h[2:4],'little')
            wire=[e for e in ev if e['event']=='wire664' and e['sequence']==seq]
            ready=[e for e in ev if e['event']=='ready664' and e['section']==h[1] and e['offset']==offset and
                   e['op'] in ({2,4,24} if h[0]==4 else {2,24} if h[0]==2 else {7,23} if h[0]==7 else {h[0]}) and
                   e['clock']<=(wire[0]['clock'] if wire else sent['start'])]
            prepared=max((e['clock'] for e in ready),default=None)
            row=dict(op=h[0],section=h[1],offset=offset,wire_B=len(h)+3,
                     expanded_B=len(bulk) if h[0]==7 else int.from_bytes(h[14:16],'little') or int.from_bytes(h[12:14],'little'),
                     start=sent['start'],push=push,load=load['clock'],ack=ack['clock'],
                     prepared=prepared,ready_to_SPI_ms=ms(sent['start']-prepared) if prepared is not None else None,
                     SPI_ms=ms(sent['clock']-sent['start']),queue_ms=ms(load['clock']-push),
                     consumer_ms=ms(ack['clock']-load['clock']),load_line=load['line'])
            rows.append(row)
        seal=[r for r in cpu[g] if r['op']==3]
        marks={k:one(seal,k) for k in ('load','upload165_entry','final212','reveal','ack')}
        lasttile=max((r['ack'] for r in rows if r['op']==7),default=previous)
        cache=obj[str(g)]['cache611']
        details[g]=dict(previous_reveal=previous,terms=frames[g]['terms'],total_ms=frames[g]['total_ms'],
                        marks={k:{f:v[f] for f in ('clock','frame','line')} for k,v in marks.items()},
                        last_tile_ACK=lasttile,last_tile_to_SEAL_load_ms=ms(marks['load']['clock']-lasttile),
                        BG_ROM_transactions=sum(r[0]==0 and r[5]=='ROM' for r in cache),
                        last_ROM_response=max(r[4] for r in cache),packets=rows)
    return dict(checked=checked,frames=frames,intervals=intervals,early_DMA_B=early,all_warm=group(list(frames.values())),
                dense=group([frames[g] for g in range(951,956)]),details=details)


def analyze(a):
    pkg=evidence('trial662-package.json')
    physical=evidence('hardware663-mmc662.json')
    assert sha(a.base_arm/'obj-nes-100/firmware.stm')==pkg['firmware_SHA256']
    assert sha(a.base_arm/'obj-nes-100/sd2snes.elf')==pkg['ELF']
    assert funcs(a.base_arm/'obj-nes-100/sd2snes.elf')==funcs(a.old_arm/'obj-nes-100/sd2snes.elf')
    board=a.traces/'nes-reader661-mux/output_files'
    assert all(sha(board/k)==v for k,v in pkg['board661']['SHA'].items())
    changed={}
    for p in a.base_arm.glob('nes_*.[ch]'):
        if sha(p)!=sha(a.arm/p.name):changed[p.name]=sha(a.arm/p.name)
    assert set(changed)=={'nes_native_sink165.c'}
    phases={}
    for n in (1,2):
        base=a.traces/f'nes-output664-base{n}'
        candidate=a.traces/f'nes-output664-{a.mode}{n}'
        old=a.traces/f'nes-reader661-emit{n}'
        reference=a.traces/f'nes-front638-both{n}h'
        b=trace(base,reference);c=trace(candidate,reference)
        # Fresh MMC662 baseline must retain every previous frame's ACK clock.
        assert read(base/'joint.json')['frames']==read(old/'joint.json')['frames']
        assert sha(base/'client.sfc')==sha(old/'client.sfc')==sha(candidate/'client.sfc')==pkg['ROM_read']['client']
        work={g:f['work'] for g,f in b['frames'].items()}
        assert work=={g:f['work'] for g,f in c['frames'].items()}
        assert contents(base)[1]==contents(candidate)[1]
        for key,folder in (('base',base),('candidate',candidate)):
            assert read(folder/'joint.json')['firmware_SHA256']==sha((a.base_arm if key=='base' else a.arm)/'obj-nes-100/firmware.stm')
        dense_delta=c['checked']['dense_mean_ms']-b['checked']['dense_mean_ms']
        ack_delta=ms(c['checked']['last_ACK']-b['checked']['last_ACK'])
        preserved=c['checked']['rows'][951]['line']<=246 and c['checked']['rows'][957]['final_waits']==0
        regressions=[g for g in b['intervals'] if c['intervals'][g]['VBlank']>b['intervals'][g]['VBlank']]
        new_waits=[g for g in b['intervals'] if c['intervals'][g]['final_waits']>b['intervals'][g]['final_waits']]
        # Whole warm averages and a work hash per frame retain the reconciliation;
        # individual critical packet clocks are retained only for 952/954/955.
        for entry in (b,c):
            entry.pop('frames')
            for g in (951,953,956,957):
                entry['details'][g].pop('packets')
        phases[n]=dict(base=b,candidate=c,matched_work=work,
                       dense_delta_ms=dense_delta,last_ACK_delta_ms=ack_delta,
                       interval_regressions=regressions,new_final_waits=new_waits,
                       guard_lines=preserved,improves_both=preserved and dense_delta<0 and ack_delta<0)
    checks={}
    for name in ('routing-base','routing-prefix','rx','seal','menu'):
        f=a.probe/(name+'.json');checks[name]=dict(SHA256=sha(f),result=read(f))
    recovery={}
    for fault in ('none','program','done','busy','token'):
        f=a.probe/f'base-{fault}/result.json';r=read(f)
        assert r['passed'] and r['safe_return']==r['base_restored']==int(fault=='none')
        assert r['firmware_sha256']==sha(a.arm/'obj-nes-100/firmware.stm')
        recovery[fault]=sha(f)
    gate=all(p['improves_both'] and p['candidate']['checked']['dense_VB']<p['base']['checked']['dense_VB'] for p in phases.values())
    return dict(baseline='MMC662',candidate=a.mode,merged_PR153='9a1aa775871ea6d5f19eedc9dc97e3e05f339a31',
                physical_ms=physical['phases']['output_final_ack']['ms_per_display'],
                physical_evidence=sha(ROOT/'analysis/hardware663-mmc662.json'),phases=phases,
                numeric_both_faster=all(p['improves_both'] for p in phases.values()),
                candidate_gate=gate,release_ready=gate and not any(p['new_final_waits'] for p in phases.values()),
                gate_description='Report strict numeric deltas separately; selection also requires a VBlank reduction across dense 951-955 in both starts.',
                firmware=sha(a.arm/'obj-nes-100/firmware.stm'),Flash_B=(a.arm/'obj-nes-100/firmware.stm').stat().st_size,
                Flash_free_B=212992-(a.arm/'obj-nes-100/firmware.stm').stat().st_size,
                changed_ARM_sources=changed,checks=checks,recovery=recovery,board_unchanged=pkg['board661'],
                sources={n:sha(ROOT/'tools'/n) for n in ('prepare_nes_output664.py','test_nes_output664.py','check_nes_output664.py','analyze_nes_output664.py')},
                scope='Actual linked ARM and 65816, modeled CPI2/IRQ/SPI and measured repeating ROM calendar. Equal work in two starts. Hardware mean is not rescaled into replay buckets; DMA before SEAL overlaps issue time. No new board build or hardware run.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('traces','probe','base-arm','old-arm','arm','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--mode',choices=('prefix','all'),default='prefix')
    p.add_argument('--prefix-result',type=Path)
    a=p.parse_args()
    result=analyze(a)
    if a.prefix_result:
        result['prefix_trial']=read(a.prefix_result)
        result['prefix_trial_SHA256']=sha(a.prefix_result)
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
