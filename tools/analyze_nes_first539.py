# SPDX-License-Identifier: MIT
"""Measure the first BG request, its actual ROM grant, visible intervals and final ACK together."""
import argparse
import json
from pathlib import Path

from analyze_nes_seal538 import Calendar, ROOT, csv_groups, inspect_run, ms, one, read, sha
from check_nes_game478 import encode

POLICIES={'row':'01','fine':'02','poll':'03','both':'04'}


def boundaries(folder, bg, calendar, target_window):
    events=read(folder/'events.json')
    cpu=csv_groups(folder/'window.csv')
    prev=one([r for r in cpu[912] if r['op']==3],'reveal')['clock']
    prev_ack=one([r for r in cpu[912] if r['op']==3],'ack')['clock']
    retire=[r for r in events if r['generation']==912 and r.get('opcode')=='0xea']
    assert len(retire)==1
    current=[r for r in events if r['generation']==913]
    source_event=one(current,'source_begin')
    source=source_event['clock']
    first=next(r for r in current if r.get('opcode')=='0xe9')
    heads=[r for r in current if r.get('opcode')=='0xe1' and r['clock']<first['start']]
    assert all(r['packet_opcode']==1 for r in heads) and len(heads)==1
    stamps=dict(reveal=prev,ack=prev_ack,input=source,begin=heads[0]['clock'],
                planner=one(current,'planner_enter')['clock'],E9_start=first['start'],E9_done=first['clock'],
                request=first['clock']+75,grant=bg['grant_clock'])
    values=list(stamps.values())
    assert values==sorted(values) and abs(source-retire[0]['clock'])<=1
    # Last admitted read in the same relative boot-calendar frame as MMC533.
    window=prev*8//calendar.period+target_window
    cycle,within=divmod(window,8)
    last=max(g for g in calendar.starts if g*8//calendar.period==within)+cycle*calendar.period
    return dict(after_reveal_ms={n:ms(v-prev) for n,v in stamps.items()},
                exclusive_ms={n:ms(v-u) for (n,v),u in zip(list(stamps.items())[1:],values)},
                capture_ready_after_reveal_ms=ms(source_event['capture_ready']-prev),
                first_payload_after_input_ms=ms(next(r['start'] for r in current if r.get('opcode')=='0xd1')-source),
                input_wire_B=sum(r['bytes'] for r in current if r.get('opcode') in ('0xd0','0xd1','0xd2','0xd3')),
                last_grant_in_target_window=last,deadline_margin_ms=ms(last-stamps['request']),
                prior_ack_polls=[ms(r['clock']-prev) for r in events if r['generation']==912 and r.get('opcode')=='0xe0' and r['clock']>=prev])


def row_counts(data):
    geom=(data/'frame913.geometry').read_bytes()
    _,_,arrays=encode(geom,(data/'frame913.raw').read_bytes(),913)
    maps,rows,_,exceptions,raster,_=arrays
    def fine(y):
        return next(((v>>3)&7 for v in exceptions if (v>>6)&8191==33*y),rows[y]&7)
    calls=same=equal_other=0
    for y in range(1,224):
        if ((raster[y]|raster[y-1])>>49)&1 or fine(y)==0 or fine(y)!=fine(y-1)+1 or ((raster[y]^raster[y-1])>>44)&31:
            continue
        a,b=rows[y]>>3,rows[y-1]>>3
        calls+=1
        same+=a==b
        equal_other+=a!=b and maps[a*33:(a+1)*33]==maps[b*33:(b+1)*33]
    return dict(comparisons=calls,identical_index=same,distinct_equal=equal_other,exceptions=len(exceptions))


def analyze(a):
    old=read(ROOT/'analysis/seal538-verification.json')
    control_hash=read(ROOT/'analysis/frontier536-verification.json')['phases'][0]['base']['firmware']
    client=sha(a.client/'sink165.sfc')
    assert client==old['inline_build']['client_SHA256']
    cal=Calendar(a.calendar)
    phases=[]
    for i in (1,2):
        base=a.traces/f'nes-frontier536-base{i}'
        phase={}
        for name in ('base','inline',*POLICIES):
            if name in ('base','inline'):
                d=base if name=='base' else a.traces/f'nes-seal538-inline{i}'
                r=old['phases'][i-1][name].copy()
                assert all(sha(d/f)==digest for f,digest in r['pins'].items())
                r['BG']={int(k):v for k,v in r['BG'].items()}
            else:
                d=a.traces/f'nes-first539-{name}{i}'
                binary=a.builds/f'ARM{POLICIES[name]}'/'src/obj-nes-100/firmware.stm'
                r=inspect_run(d,a.plans,cal,base,sha(binary),client)
                audit=a.traces/f'nes-first539-audit-{name}{i}'
                r['replay']=read(audit/'audit.json')
                assert r['replay']['frames']==53 and r['replay']['trace']==sha(d/'window.csv')
                assert sha(audit/'tile532.csv')==sha(d/'tile532.csv')
                r['ARM_SHA256']=sha(binary)
                r['Flash_B']=binary.stat().st_size
                r['BSS_B']=int((binary.parents[2]/'size.log').read_text().splitlines()[-1].split()[2])
            phase[name]=r
            ref=phase['base']
            assert r['BG'].keys()==ref['BG'].keys() and len(r['BG'])==30
            r['timing_913']=boundaries(d,r['BG'][913],cal,ref['BG'][913]['relative_window'])
            r['later_BG_windows']=[g for g,v in r['BG'].items() if v['relative_window']>ref['BG'][g]['relative_window']]
            r['last_ACK_delta_ms']=ms(r['last_ACK']-ref['last_ACK'])
            r['pass']=(not r['later_BG_windows'] and r['dense_VB']<ref['dense_VB'] and r['dense_ms']<ref['dense_ms']
                       and r['last_ACK_delta_ms']<0 and not any(r['waits'].values()) and r['after_951']['head_to_reveal_VB']==1
                       and r['after_951']['final_waits']==0)
        phases.append(phase)
    guards=read(a.builds/'guards.json')
    windows={}
    for name,k in POLICIES.items():
        guards_for_elf=read(a.builds/f'window{k}.json')
        assert guards_for_elf['elf_firmware']==phases[0][name]['ARM_SHA256']
        assert len(guards_for_elf['first'])==9 and len(guards_for_elf['end'])==6
        windows[name]=guards_for_elf
    assert len(old['guard']['inline_priority'])==22 and len(old['guard']['inline_STOP'])==7
    return dict(phases=phases,gate={n:all(p[n]['pass'] for p in phases) for n in POLICIES},
                control_ARM=control_hash,client=client,planner_guards=guards,ARM_window_guards=windows,
                input_913=row_counts(a.data))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('traces','plans','builds','data','client','calendar','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',newline='\n')
