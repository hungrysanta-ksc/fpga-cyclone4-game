"""Matched MMC666 schedule: accepted map selection, subsequent packets and deadlines."""
import argparse
import json
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_frontier536 import contents
from analyze_nes_output615 import read, sha, ms, csv_groups, one
from nes_schedule492 import funcs


def summarize(folder, reference):
    result=trace(folder,reference)
    cpu=csv_groups(folder/'window.csv')
    work={g:f['work'] for g,f in result.pop('frames').items()}
    seal=[r for r in cpu[911] if r['op']==3]
    result['deadline911']={key:one(seal,key) for key in ('load','upload165_entry','reveal','ack')}
    for g,d in result['details'].items():
        packets=d.pop('packets')
        if g not in (954,957):continue
        d['packets']=packets
        d['idle_DMA']=[r for r in cpu[g] if r['event']=='ppu_dma' and r['op']==-1]
        selections=[r for r in cpu[g] if r['event']=='idle524']
        assert len(selections)==len(d['idle_DMA'])
        copied=set();grants=[]
        for r,sel in zip(d['idle_DMA'],selections,strict=True):
            assert 0<r['clock']-sel['clock']<100
            accepted=set()
            for p in packets:
                if p['section']==2 and p['ack']<sel['clock']:
                    accepted.update(range(p['offset'],p['offset']+p['expanded_B'],64))
            remaining=sorted(accepted-copied);ranges=[]
            for off in remaining:
                if ranges and ranges[-1][0]+ranges[-1][1]==off:ranges[-1][1]+=64
                else:ranges.append([off,64])
            off=sel['value']-65536 if sel['value']>=65536 else None
            if off is not None:
                sent=set(range(off,off+r['value'],64));assert sent<=accepted-copied
                copied.update(sent)
            grants.append(dict(clock=r['clock'],n=r['value'],line=r['line'],offset=off,
                accepted_map_B=64*len(accepted),remaining_map_ranges_before=ranges,
                subsequent_packet=next((p for p in packets if p['load']>r['clock']),None)))
        d['accepted_map_at_DMA']=grants
        # Upper bound on the end of the preceding blank, intentionally up to
        # one scanline late because window.csv omits horizontal position.
        # Positive lateness proves a DMA-selector-only change cannot reach it.
        reveal=d['marks']['reveal']
        prior_end_upper=reveal['clock']+(262-reveal['line'])*1364-341*262*4
        d['previous_VBlank_end_upper_clock']=prior_end_upper
        d['SEAL_after_prior_blank_lower_ms']=ms(d['marks']['load']['clock']-prior_end_upper)
        d['last_tile_ACK_after_prior_blank_lower_ms']=ms(d['last_tile_ACK']-prior_end_upper)
    return result,work


def analyze(a):
    phases={}
    client=sha(a.client/'sink165.sfc')
    old=Path('../probes/nes-output664/all/src/obj-nes-100')
    arm=Path('../probes/nes-trial666/arm01/src/obj-nes-100')
    functions=funcs(arm/'sd2snes.elf')
    assert functions==funcs(old/'sd2snes.elf')
    # MMC666 changes trial labels, not executable functions. The fresh668
    # MMC666 baseline also reproduced every selected665 ACK clock exactly.
    fresh=read(a.traces/'nes-output668-base1/joint.json')
    assert fresh['frames']==read(a.traces/'nes-entry665-a1/joint.json')['frames']
    assert fresh['firmware_SHA256']==sha(arm/'firmware.stm')
    for phase in a.phases:
        base=a.traces/f'nes-entry665-a{phase}'
        candidate=a.traces/f'nes-extent672-a{phase}'
        reference=a.traces/f'nes-front638-both{phase}h'
        b,bw=summarize(base,reference);c,cw=summarize(candidate,reference)
        assert bw==cw and contents(base)[1]==contents(candidate)[1]
        bj,cj=(read(p/'joint.json') for p in (base,candidate))
        assert bj['parameters']==cj['parameters']
        assert bj['firmware_SHA256']==sha(old/'firmware.stm')
        assert cj['firmware_SHA256']==sha(arm/'firmware.stm')
        assert sha(candidate/'client.sfc')==cj['client_SHA256']==client
        dense=c['checked']['dense_mean_ms']-b['checked']['dense_mean_ms']
        ack=ms(c['checked']['last_ACK']-b['checked']['last_ACK'])
        protected=dict(reveal951=c['details'][951]['marks']['reveal']['line']<=246,
            interval952=0<c['intervals'][952]['VBlank']<=3,
            final_wait957=c['intervals'][957]['final_waits']==0,
            deadline911=c['deadline911']['load']['line']<=b['deadline911']['load']['line'] and
                c['deadline911']['upload165_entry']['line']<=b['deadline911']['upload165_entry']['line'] and
                c['intervals'][911]['VBlank']<=b['intervals'][911]['VBlank'])
        regress=[g for g in b['intervals'] if c['intervals'][g]['VBlank']>b['intervals'][g]['VBlank']]
        waits=[g for g in b['intervals'] if c['intervals'][g]['final_waits']>b['intervals'][g]['final_waits']]
        phases[phase]=dict(base=b,candidate=c,matched_work=bw,protected=protected,
            dense_delta_ms=dense,last_ACK_delta_ms=ack,interval_regressions=regress,new_final_waits=waits,
            observed_SNES_stack_B={k:read(p/'result.json')['observed_stack_B'] for k,p in (('base',base),('candidate',candidate))},
            numeric_both_faster=all(protected.values()) and dense<0 and ack<0,
            selection_gate=all(protected.values()) and dense<0 and ack<0 and not waits and
                c['checked']['dense_VB']<b['checked']['dense_VB'])
    guards={name:read(a.traces/path) for name,path in (
        ('head_and_independent','nes-extent672-head01/edges.json'),
        ('beam','nes-extent672-beam01/result.json'),('tail_and_cold','nes-extent672-tail02/result.json'))}
    assert guards['beam']['client']==guards['tail_and_cold']['client_SHA256']==client
    assert guards['tail_and_cold']['passed'] and len(guards['head_and_independent'])==8
    basebody=(Path('../probes/nes-entry665/client02')/'body.bin').read_bytes()
    newbody=(a.client/'body.bin').read_bytes();build=read(a.client/'build.json')
    begin,end=build['replacement_range']
    assert newbody[:begin]==basebody[:begin] and newbody[end:len(basebody)]==basebody[end:]
    r=dict(baseline='MMC666',candidate='extent672',phases=phases,client_SHA256=client,guards=guards,
        client_build=read(a.client/'build.json'),
        ARM_Flash_B=212496,ARM_Flash_free_B=496,ARM_data_B=10040,ARM_BSS_B=19544,
        ARM_FPGA_unchanged=True,new_board_FIT_STA=False,new_delivery=False,
        equal_ARM_functions=len(functions),baseline_firmware=sha(old/'firmware.stm'),
        candidate_firmware=sha(arm/'firmware.stm'),fresh_baseline_same_ACKs=True,
        validation_DMA_STOP_final_ACK_code_unchanged=True,
        capture_and_menu='Selected MMC666 FPGA/ARM unchanged. Candidate STOP/quiet/retained bank and final ACK tested on actual65816; no new physical/menu/base run.',
        baseline_board_reference='analysis/entry665-verification.json',
        scope='Actual linked ARM and 65816; CPI2, modeled IRQ/shared SPI, measured repeating ROM calendar. Equal map/OBJ work and output bytes, 53 captures/start. Not physical FPS or full NES/PSRAM RTL concurrency.',
        selected='extent672' if len(phases)==2 and all(p['selection_gate'] for p in phases.values()) else 'MMC666',
        sources={p.name:sha(p) for p in Path('tools').glob('*672.py')})
    a.out.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({n:{k:p[k] for k in ('dense_delta_ms','last_ACK_delta_ms','protected','interval_regressions','new_final_waits','selection_gate')} for n,p in phases.items()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('traces','client','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--phases',type=int,nargs='+',default=[1,2])
    analyze(p.parse_args())
