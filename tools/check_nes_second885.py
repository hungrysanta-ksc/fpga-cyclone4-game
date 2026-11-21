"""Verify the second D2 confirmation, protected DMA, and end-to-end display schedule."""
import argparse
import json
from pathlib import Path

from analyze_nes_map830 import load, window
from check_nes_oam882 import capture
from check_nes_packed883 import report
from check_nes_room884 import trace


def measure(folder):
    bus, output, t = trace(folder)
    display = window(folder)
    reads = [i for i,e in enumerate(bus) if e['opcode']=='0xd1' and e.get('input_generation')==963]
    pops = []
    for i in reads:
        d1, pop, status = bus[i:i+3]
        assert pop['opcode']=='0xd2' and status['opcode']=='0xd0'
        assert pop['input_generation']==status['input_generation']==963
        pops.append(round(status['clock']))
    def show(g):
        row = next(r for r in display if r['g']==g and r['event']=='reveal')
        return [row['frame'],row['line'],row['clock']]
    table, = t['table240_starts']
    stats = dict(last_OBJ_ACK=t['last_OBJ_ACK'], first_D1=t['first_D1'], second_D1=t['D1_trace'][1][1],
                 second_D2_end=round(bus[reads[1]+1]['clock']),second_D2_confirmed=pops[1],
                 confirmed_before_table=sum(clock<table for clock in pops),
                 confirmed_before_final=sum(clock<t['final962'] for clock in pops),
                 table=table,seal=t['SEAL_start'],show962=show(962),final962=t['final962'],
                 EA962_end=t['EA962_end'],data_END_confirmed=pops[-2],commit_confirmed=pops[-1],
                 show963=show(963))
    for event in ('load','upload165_entry'):
        r = next(e for e in display if e['g']==963 and e['op']==3 and e['event']==event)
        stats['963_'+event] = [r['frame'],r['line'],r['clock']]
    return bus,output,stats


def earlier_capture(folder):
    c = capture(folder,961)
    target = c['ready'] - 240*341*4 - 262*341*4
    status = next(e for e in load(folder/'events.json') if e.get('opcode')=='0xe0'
                  and round(e['clock'])==c['valid_E0'])
    duration = round(status['clock']-status['start'])
    remaining = c['D2']-c['valid_E0']
    rows = window(folder)
    dma = [[r['frame'],r['line'],r['value']] for r in rows if r['g']==959 and r['event']=='ppu_dma']
    waits = {r['event']:[r['frame'],r['line'],r['clock']] for r in rows
             if r['g']==959 and r['op']==3 and r['event'] in
             ('load','upload165_entry','wait169','wait_return_5781','reveal','ack')}
    return dict(capture=c,target_edge=target,D2_minus_edge=c['D2']-target,wait959=waits,
                valid_E0_duration=duration,after_valid_E0=remaining,
                earliest_excess_at_same_tail=c['prior_display_ACK']+duration+remaining-target,
                DMA959=dma)


def reconcile(temp, guards):
    tag='884-room'
    result={}
    prior_data=load(Path(__file__).resolve().parents[1]/'analysis/room884-results.json')
    for policy in ('palette','table'):
        candidate='885-'+policy
        full=report(temp,candidate,'demo')
        phases=[]
        for phase,scene in enumerate(full,1):
            prefix=f'nes-tile821-demo-jointmirror-p{phase}-'
            ref, new = [temp/(prefix+t) for t in (tag,candidate)]
            before,old_packets,a=measure(ref)
            after,new_packets,b=measure(new)
            assert old_packets==new_packets
            changes=load(new/'credit885.json')
            edge=changes[0]['clock']
            prior=[e for e in before if e['clock']<=edge]
            assert prior and prior==[e for e in after if e['clock']<=edge]
            assert a['first_D1']==b['first_D1'] and a['last_OBJ_ACK']==b['last_OBJ_ACK']
            assert b['second_D2_confirmed'] < b['table'] and b['confirmed_before_table']==2
            assert [r for r in window(ref) if r['g']==950]==[r for r in window(new) if r['g']==950]
            assert load(ref/'joint.json')['firmware_SHA256']==scene['ARM']
            reference=prior_data['candidate']['demo'][phase-1]
            def summary(s):
                return {k:s[k] for k in ('after_two_VBlanks','last_ACK','ARM_valid_final_E0',
                        'pictures','all_wire_B')} | {'intervals':{str(g):s['vblanks'][str(g)] for g in (950,952,962,963)}}
            phases.append(dict(first_changed=changes[0], identical_prior_SPI=len(prior),
                               before=a|summary(reference),after=b|summary(scene),arm=scene['ARM'],client=scene['client']))
        result[policy]=phases
    result['upstream_capture961'] = {
        tag:[earlier_capture(temp/f'nes-tile821-demo-jointmirror-p{p}-{tag}') for p in (1,2)]
        for tag in ('882-direct','883-shared','884-room')}
    result['second_block_guards']=load(guards)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('temp','guards','output'):
        parser.add_argument(key,type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(reconcile(args.temp,args.guards),indent=2)+'\n',encoding='utf-8',newline='\n')
