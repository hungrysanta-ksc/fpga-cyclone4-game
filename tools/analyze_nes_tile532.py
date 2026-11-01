# SPDX-License-Identifier: MIT
"""Compare MMC529, ARM-only and joint schedules at identical source, tile, map and pixel workload."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_map526 import ROOT,Calendar,ms,read,run_cost,sha,tiles
from analyze_nes_output531 import breakdown,csv_groups,one
from analyze_nes_quiet528 import packet_content


def target(folder,g,frame,baseline_frame,cpu,samples,events,records,old):
    packets=[bytes.fromhex(r[2]) for r in records]
    source=one(events,'source_begin')['clock']
    e9=read(folder/'obj-phases.json')[str(g)]['end_accepted']
    start=one(events,'end_enter')['clock']
    receipts=[]
    for r in cpu:
        if r['event']!='ack':continue
        pkt=packets[r['index']-1]
        if pkt[0] not in (2,4,7):continue
        section=pkt[1]
        if pkt[0]!=7 and section!=2:continue
        pos=int.from_bytes(pkt[10:12],'little')
        length=int.from_bytes(pkt[12:14] if pkt[0]==2 else pkt[14:16],'little')
        receipts.append(dict(section=section,offset=pos,B=length,clock=r['clock']))
    def completion(section,first,count):
        hits=[r for r in receipts if r['section']==section and max(first,r['offset'])<min(first+count,r['offset']+r['B'])]
        units=sum(min(first+count,r['offset']+r['B'])-max(first,r['offset']) for r in hits)
        assert units==count
        return ms(max(r['clock'] for r in hits)-source)
    old_map,=[r for r in old['commands'] if r['kind']=='map']
    # Heavy frames 952 and 954 both target bank one.
    assert one(samples,'final_credit')['bank']==1
    map_off=old_map['dst']-0xa000
    sub=breakdown(g,events,cpu,samples,packets,[r[1] for r in records])
    seal=[r for r in cpu if r['op']==3]
    probe=one(samples,'final_credit')
    reveal,ack=one(seal,'reveal'),one(seal,'ack')
    assert reveal['frame']==ack['frame'] and 225<=reveal['line']<=ack['line']<=261
    if sub['decision']=='credit':
        assert 225<=probe['line']<=246 and frame['final_waits']==0
    tile_ids=set()
    for c in sub['commands']:
        if c['kind']=='tile':tile_ids.update(range(c['dst'],c['dst']+c['B']))
    moved=[]
    for c in old['commands']:
        if c['kind']=='tile':
            moved.append(dict(dst=c['dst'],B=c['B'],preuploaded=c['B']-len(tile_ids.intersection(range(c['dst'],c['dst']+c['B'])))))
    return dict(g=g,final_waits=frame['final_waits'],seal_waits=frame['seal_waits'],decision=sub['decision'],
                miss_clocks=sub['miss_clocks'],gap_ms=frame['gap_ms'],display_VBlanks=frame['display_VBlanks'],
                final_probe_line=probe['line'],reveal_line=reveal['line'],ack_line=ack['line'],
                ACK=frame['ack'],delta_ACK_ms=ms(frame['ack']-baseline_frame['ack']),seal_bytes=sub['seal_bytes'],
                early_map_B=len(frame['map_offsets'])*64,early_all_B=frame['early_B'],tile_moved=moved,
                remaining_map_offset=map_off,remaining_map_B=old_map['B'],
                first_suffix_row_ms=completion(2,map_off,64),whole_suffix_ms=completion(2,map_off,old_map['B']),
                last_OBJ_ms=ms(max(r['clock'] for r in receipts if r['section']==1)-source),
                END_E0=sum(r['event']=='SPI' and r['opcode']=='0xe0' and start<=r['start']<e9 for r in events),
                quiet_maps=sum(r['event']=='map_packet_enter' and start<=r['clock']<e9 for r in events),
                output_ms=sub['call_ms'])


def analyze(a):
    verified=read(ROOT/'analysis/flash529-verification.json');ref=read(ROOT/'analysis/output531-verification.json')
    firmware=a.arm/'obj-nes-100/firmware.stm'
    plans={f['generation']:f for f in read(ROOT/'analysis/obj518-verification.json')['plans']['frames']}
    calendar=Calendar(a.calendar);oracle=tiles(a.fixture,957)
    cap=read(ROOT/'analysis/prefix523-verification.json')
    phases=[]
    for i,base in enumerate(a.base):
        variants={};observations={}
        clients=dict(zip(('joint','pair','scan'),a.clients))
        for name,folder in [('529',base),('ARM',a.control[i]),('joint',a.both[i]),('pair',a.pair[i]),('scan',a.scan[i])]:
            fw=verified['firmware_SHA256'] if name=='529' else sha(firmware)
            chunk=128 if name in ('pair','scan') else 64
            s,_=run_cost(folder,'row254',dict(cap['phases'][i]['candidate'],firmware=fw),plans,calendar,oracle,map_chunk=chunk)
            assert not (folder/'callback-error.txt').exists()
            if name=='529':
                assert s['pins']['window.csv']==verified['phases'][i]['cost']['pins']['window.csv']
                baseline=s['frames'];content=packet_content(base)
            else:
                assert packet_content(folder)==content
                assert all(sha(folder/f'frame-{g}.rgb')==sha(base/f'frame-{g}.rgb') for g in range(905,958))
                assert s['dma_B']==variants['529']['dma_B'] and s['ROM_reads']==variants['529']['ROM_reads']
            assert s['client']==(sha(clients[name]/'sink165.sfc') if name in clients else verified['phases'][i]['cost']['client'])
            cpu=csv_groups(folder/'window.csv');samples=csv_groups(folder/'seal528.csv');events=read(folder/'events.json')
            records=[json.loads(l) for l in (folder/'packets.jsonl').read_text().splitlines()]
            s['targets']={g:target(folder,g,s['frames'][g-905],baseline[g-905],cpu[g],samples[g],
                         [r for r in events if r['generation']==g],records,ref['phases'][i]['frames'][g-907]) for g in (952,954)}
            s['changed_display_intervals']=[
                dict(g=f['g'],VBlanks=f['display_VBlanks']-b['display_VBlanks'],delta_ms=f['gap_ms']-b['gap_ms'])
                for f,b in zip(s['frames'][2:],baseline[2:]) if f['display_VBlanks']!=b['display_VBlanks']]
            s.pop('frames');s['delta_last_ms']=ms(s['final_ack']-verified['phases'][i]['cost']['final_ack'])
            variants[name]=s
            if name in clients:
                audit={'joint':a.audit,'pair':a.auditpair,'scan':a.auditscan}[name][i]
                check=read(audit/'audit.json')
                assert check['trace']==sha(folder/'window.csv') and check['frames']==53
                assert sha(folder/'tile532.csv')==sha(audit/'tile532.csv')
                with (folder/'tile532.csv').open() as f:trace=list(csv.DictReader(f))
                for g in (952,954):
                    early=set()
                    for row in trace:
                        if int(row['g'])==g and row['event']=='tile':
                            start,n=int(row['dst']),int(row['n'])
                            early.update(range(start,start+n))
                    for tile in s['targets'][g]['tile_moved']:
                        assert tile['preuploaded']==len(early.intersection(range(tile['dst'],tile['dst']+tile['B'])))
                observations[name]=dict(audit=check,natural_merges=sum(r['event']=='merge' for r in trace),
                                        tail_tiles=sum(r['event']=='tile' and r['other']=='1' for r in trace),
                                        interior_tiles=sum(r['event']=='tile' and r['other']=='2' for r in trace),
                                        heavy_tile_events=[r for r in trace if int(r['g']) in (952,954)])
        phases.append(dict(start=ref['phases'][i]['start'],variants=variants,observations=observations))
    guards={};edges={}
    for name,folder,edge in zip(clients,a.priority,a.edges):
        guards[name]=read(folder/'result.json')
        assert len(guards[name])==22 and all(r['size']==80 for r in guards[name] if r['group']=='merge' and r['grant'])
        edges[name]=read(edge/'edges.json')
        assert [r['size'] for r in edges[name]]==[64 if name=='joint' else 128,0,0,0]
    interior=read(a.interior/'interior.json')
    assert len(interior)==6 and all(r['size']>0 for r in interior if r['grant'])
    credit=read(a.checks/'guards.json');assert credit['sha']==sha(firmware) and len(credit['rows'])==6
    first=read(a.checks/'first-map.json');assert first['sha256']==sha(firmware) and len(first['rows'])==9
    responses=read(a.checks/'responses/result.json')
    assert responses['passed'] and responses['cases']==40 and responses['candidate_SHA256']==sha(firmware)
    met={name:all(p['variants'][name]['delta_last_ms']<0 and
                  all(p['variants'][name]['targets'][g]['final_waits']<p['variants']['529']['targets'][g]['final_waits']
                      for g in (952,954)) for p in phases) for name in clients}
    return dict(target_met=met,phases=phases,priority=guards,edges=edges,interior=interior,credit=credit,response_cases=40,first_map_cases=9,
                ARM=sha(firmware),Flash_B=firmware.stat().st_size,Flash_free_B=0x34000-firmware.stat().st_size,
                BSS_B=int((a.arm.parent/'size.log').read_text().splitlines()[-1].split()[2]),
                clients={n:dict(sha256=sha(c/'sink165.sfc'),body_B=(c/'body.bin').stat().st_size) for n,c in clients.items()})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','control','both','audit','pair','scan','auditpair','auditscan'):p.add_argument('--'+n,nargs=2,required=True,type=Path)
    for n in ('clients','priority','edges'):p.add_argument('--'+n,nargs=3,required=True,type=Path)
    for n in ('arm','fixture','calendar','checks','interior','out'):p.add_argument('--'+n,required=True,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(analyze(a),indent=2)+'\n',encoding='utf8',newline='\n')
