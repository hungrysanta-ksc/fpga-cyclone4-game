# SPDX-License-Identifier: MIT
"""Attribute the extra pre-SEAL VBlank and compare the linked ROM/map/raw policies."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

from analyze_nes_frontier536 import ROOT,Calendar,contents,csv_groups,ms,one,read,run_cost,sha,tiles
from test_nes_raw506_joint import ARM_HZ,MASTER,wire_plan


def stages(folder,calendar,plans,require_recorded=False):
    events=read(folder/'events.json');cpu=csv_groups(folder/'window.csv')
    obj=read(folder/'obj-phases.json')
    packets=[json.loads(l) for l in (folder/'packets.jsonl').read_text().splitlines()]
    result={}
    for g in (954,955):
        group=[r for r in events if r['generation']==g]
        spi=[r for r in group if r['event']=='SPI']
        prev=one([r for r in cpu[g-1] if r['op']==3],'reveal')
        seal=[r for r in cpu[g] if r['op']==3]
        load,reveal,ack=[one(seal,n) for n in ('load','reveal','ack')]
        pushed=packets[load['index']-1][1]
        send,=[r for r in spi if r['opcode']=='0xe1' and r['packet_opcode']==3]
        assert bytes.fromhex(packets[load['index']-1][2])[0]==3 and abs(send['clock']-pushed)<=1
        e9=[r for r in spi if r['opcode']=='0xe9']
        qs=[bytes.fromhex(q) for _,q in read(plans/f'frame{g}/plans.json')]
        assert [q[6] for q in qs[:2]]==[2,0] and sum(len(wire_plan(q)) for q in qs[:2])+8==e9[0]['bytes']
        # The first E9 contains exactly slot-zero fill followed by one BG read.
        # Charge the actual Link.advance zero-tile time and its producer handoff.
        req=e9[0]['clock']+16*4+math.ceil((2*16+8)*MASTER/ARM_HZ)
        grant,response=calendar.select(req)
        o=obj[str(g)]
        recorded=o.get('rom_service')
        if require_recorded:assert recorded,('missing measured ROM accesses',folder,g)
        if recorded:
            assert recorded[0][0]==0 and abs(recorded[0][1]-req)<0.001
            assert recorded[0][2:]==[grant,response]
            assert all(calendar.select(t)==(a,b) for _,t,a,b in recorded)
            objects=[r for r in recorded if r[0]==1]
            assert len(objects)==o['obj_rom_reads'] and objects[0][1]==o['first_obj_rom_request'] and objects[-1][3]==o['last_obj_rom_response']
        src=one(group,'source_begin')
        marks=dict(previous=prev['clock'],input=src['clock'],planner=one(group,'planner_enter')['clock'],
                   first_BG_request=req,first_BG_grant=grant,END=o['end_accepted'],
                   ROM_and_END_done=max(o['end_accepted'],o['last_obj_rom_response']),
                   SEAL_E1_start=send['start'],SEAL_push=pushed,SEAL_head=load['clock'])
        vals=list(marks.values())
        assert vals==sorted(vals) and abs(sum(b-a for a,b in zip(vals,vals[1:]))-(vals[-1]-vals[0]))<0.001
        def rel(clk):return ms(clk-vals[0])
        other=dict(bg_frozen=one(group,'bg_map_frozen')['clock'],output_enter=one(group,'output_enter531')['clock'],
                   first_input_payload=next(r['start'] for r in spi if r['opcode']=='0xd1'),
                   first_OBJ_E9=o['obj_plans'][0]['accepted_clock'],first_OBJ_request=o['first_obj_rom_request'],
                   last_OBJ_response=o['last_obj_rom_response'],reveal=reveal['clock'],final_ACK=ack['clock'])
        before_BG=[r for r in group if r['event']=='map_enqueue' and r['clock']<e9[0]['start']]
        control=[r for r in spi if r['start']<e9[0]['start'] and r['opcode'] in ('0xe1','0xe0','0xe8')]
        stages_ms={b:ms(marks[b]-marks[a]) for a,b in zip(marks,list(marks)[1:])}
        result[g]=dict(input_clock=src['clock'],capture_ready_clock=src['capture_ready'],
                       input_ROM_phase_clocks=src['clock']%calendar.period,
                       input_to_BG_request=req-src['clock'],BG_request_clock=req,
                       marks_ms={n:rel(t) for n,t in {**marks,**other}.items()},exclusive_ms=stages_ms,
                       E9_accept_ms=[rel(r['clock']) for r in e9],E9_bytes=[r['bytes'] for r in e9],
                       maps_before_first_BG_E9=[r['offset'] for r in before_BG],
                       control_bytes_before_BG=sum(r['bytes'] for r in control),
                       E1_before_BG=[dict(op=r['packet_opcode'],bytes=r['bytes'],ms=ms(r['clock']-r['start'])) for r in control if r['opcode']=='0xe1'],
                       early_map_ms=[rel(r['clock']) for r in group if r['event']=='map_packet_enter' and r['early']],
                       final_waits=sum(r['event']=='wait169' and r['clock']>=one(seal,'final212')['clock'] for r in seal),
                       previous_to_head_frames=load['frame']-prev['frame'],head_to_reveal_frames=reveal['frame']-load['frame'],
                       OBJ_reads=o['obj_rom_reads'])
    return result


def raw_shape(folder):
    groups={}
    for line in (folder/'packets.jsonl').read_text().splitlines():
        _,_,h,_=json.loads(line);b=bytes.fromhex(h);g=int.from_bytes(b[8:10],'little')
        at=int.from_bytes(b[10:12],'little');offset=at-1121
        groups.setdefault(g,[])
        if b[1]==5 and b[0] in (2,4,5) and offset>=0:
            groups[g].append((offset,b[0],int.from_bytes(b[12:14],'little'),int.from_bytes(b[14:16],'little')))
    return groups


def dense_frames(folder):
    cpu=csv_groups(folder/'window.csv')
    frames={}
    for g in range(951,956):
        prev=one([r for r in cpu[g-1] if r['op']==3],'reveal')
        seal=[r for r in cpu[g] if r['op']==3]
        head,reveal=[one(seal,k) for k in ('load','reveal')]
        frames[g]=dict(before_head=head['frame']-prev['frame'],after_head=reveal['frame']-head['frame'],
                       display_ms=ms(reveal['clock']-prev['clock']))
    return frames


def analyze(a):
    old=read(ROOT/'analysis/frontier536-verification.json')
    ref=read(ROOT/'analysis/prefix523-verification.json')['phases']
    where=a.traces;cal=Calendar(a.calendar)
    plans={r['generation']:r for r in read(ROOT/'analysis/obj518-verification.json')['plans']['frames']}
    oracle=tiles(a.fixture,957)
    names=('base','front','raw','add','both','only')
    arm=dict(zip(names[3:],a.arms))
    phases=[]
    for i in (1,2):
        variants={};raws={}
        for n in names:
            archived=n in ('base','front','raw')
            prefix='nes-frontier536' if archived else 'nes-phase537'
            d=where/f'{prefix}-{n}{i}'
            source=old['phases'][i-1]['base']
            if archived:
                c=old['phases'][i-1][n]
                assert all(sha(d/f)==c['pins'][f] for f in ('window.csv','events.json','obj-phases.json','packets.jsonl','joint.json'))
                summary={k:c[k] for k in ('firmware','client','Flash_B','BSS_B','final_ack','warm_ms','dense_ms','dense_VBlanks','SPI_B','irqs','instructions','dma_B','ROM_reads','packets','tiles')}
                summary['waits']={g:c['targets'][str(g)]['final_waits'] for g in (952,954)}
            else:
                fw=arm[n]/'obj-nes-100/firmware.stm'
                summary,_=run_cost(d,'row254',dict(ref[i-1]['candidate'],firmware=sha(fw)),plans,cal,oracle,map_chunk=128)
                rows=summary.pop('frames')
                summary.update(firmware=sha(fw),Flash_B=fw.stat().st_size,BSS_B=int((arm[n].parent/'size.log').read_text().splitlines()[-1].split()[2]),
                               dense_VBlanks=sum(r['display_VBlanks'] for r in rows if 951<=r['g']<=955),
                               waits={g:rows[g-905]['final_waits'] for g in (952,954)})
                assert all(summary[k]==source[k] for k in ('client','tiles','dma_B','ROM_reads'))
                assert contents(d)==canonical
                assert all(sha(d/f'frame-{g}.rgb')==sha(base/f'frame-{g}.rgb') for g in range(905,958))
                audit=where/f'{prefix}-audit-{n}{i}'
                summary['audit']=read(audit/'audit.json')
                assert summary['audit']['frames']==53 and summary['audit']['trace']==sha(d/'window.csv')
                assert sha(audit/'tile532.csv')==sha(d/'tile532.csv')
                assert all(not (d/f).exists() for f in ('map-error.txt','callback-error.txt'))
            if n=='base':base=d;canonical=contents(d)
            summary['stages']=stages(d,cal,a.plans,require_recorded=not archived)
            summary['dense_frames']=dense_frames(d)
            summary['dense_reveal_ms']=sum(v['display_ms'] for v in summary['dense_frames'].values())/5
            assert sum(r['before_head']+r['after_head'] for r in summary['dense_frames'].values())==summary['dense_VBlanks']
            raws[n]=raw_shape(d)
            if n in arm:
                modes={g:('same' if v==raws['base'][g]==raws['raw'][g] else 'split' if v==raws['base'][g] else 'merged' if v==raws['raw'][g] else 'invalid') for g,v in raws[n].items()}
                assert 'invalid' not in modes.values()
                summary['raw_policy']=dict(counts=dict(Counter(modes.values())),dense={g:modes[g] for g in range(951,956)})
            for g,q in summary['stages'].items():
                b=q if n=='base' else variants['base']['stages'][g]
                # Change only input phase or only request offset, not both.
                def wait(phase,offset):
                    clk=phase+offset
                    return ms(cal.select(clk)[0]-clk)
                q['swap_wait_ms']=dict(base_phase_new_offset=wait(b['input_clock'],q['input_to_BG_request']),
                                       new_phase_base_offset=wait(q['input_clock'],b['input_to_BG_request']))
            summary['last_ACK_change_ms']=ms(summary['final_ack']-source['final_ack'])
            variants[n]=summary
        phases.append(variants)
    guards={}
    for n in names[3:]:
        arm_cases=read(a.checks/f'guards-{n}.json')
        snes=read(where/('nes-phase537-priority-both02' if n=='both' else f'nes-phase537-priority-{n}')/'result.json')
        assert arm_cases['elf_firmware']==phases[0][n]['firmware']
        assert [len(arm_cases[k]) for k in ('first','end','gated')]==[9,6,0 if n=='only' else 16]
        assert len(snes)==22
        guards[n]=dict(ARM=arm_cases,SNES=snes)
    simultaneous={}
    whole_vblank={}
    for n in names[3:]:
        simultaneous[n]=all(p[n]['dense_reveal_ms']<p['base']['dense_reveal_ms'] and p[n]['last_ACK_change_ms']<0
                            and not any(p[n]['waits'].values()) for p in phases)
        whole_vblank[n]=simultaneous[n] and all(p[n]['dense_VBlanks']<p['base']['dense_VBlanks'] for p in phases)
    return dict(phases=phases,guards=guards,simultaneous_ms=simultaneous,gate=whole_vblank)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('traces','plans','calendar','fixture','checks','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--arms',nargs=3,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',newline='\n')
