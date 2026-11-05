# SPDX-License-Identifier: MIT
"""Bounded R1 data audit: actual packet boundaries, semantic changes and owners.

Reuses recorded schedules; no cycle, hardware, or hypothetical ABI speed claims.
Raw inputs/payloads stay private; public results contain counts and hashes only.
"""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import struct

from nes_transfer512 import legacy_packets
from check_nes_game478 import next_y
from nes_schedule492 import funcs

ROOT=Path(__file__).resolve().parents[1]
NAMES=['map','row','object','exception','raster','palette','raw']
WIDTH=[2,1,8,4,8,1,1]
MASTER=21477272


def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ms(c):return c/MASTER*1000
def u16(b,at):return int.from_bytes(b[at:at+2],'little')


def records(packets,g,expected):
    restored=[[] for _ in NAMES];out=[];controls=[]
    for packet in packets:
        at=0
        while at<len(packet):
            key,gen=struct.unpack_from('>HH',packet,at);k,idx=key>>13,key&8191
            w=8 if k==0 and idx&4096 else [2,1,7,4,7,1,2,8][k]
            record=packet[at:at+4+w];assert len(record)==4+w and gen==g
            v=int.from_bytes(record[4:],'big');at+=len(record)
            if k==7 and idx<0x800:
                controls.append(idx);out.append(dict(section='control',control=idx,wire_B=len(record)));continue
            if k==0 and idx&4096:
                n=v>>60;values=[(v>>(15*(n-1-i)))&32767 for i in range(n)];section=0
                assert (idx&4095)==len(restored[0])
            elif k==6 and idx&0x1f00==0x1000:
                section=0;values=[v]*((idx&255)+1)
            elif k==7 and 0x1000<=idx<0x1700:
                section=6;n=v>>60
                if n:values=[(v>>(6*(n-1-i)))&63 for i in range(n)]
                else:values=[v&63]*(v>>6)
                assert idx-0x1000==len(restored[6])
            elif k==7 and idx&0x1f00==0x1c00:
                section=4;values=[v]
                for _ in range(idx&255):values.append(next_y(values[-1]))
            elif k==7 and idx&0x1800==0x1800:
                section=(idx>>8)&7;n=(idx&255)+1
                assert section in (1,5);values=list(v.to_bytes(8,'big')[-n:])
            elif k==7 and idx&0x1800==0x800:
                section=(idx>>8)&7;values=[v]*((idx&255)+1)
            else:
                section=k;values=[v];assert idx==len(restored[section])
            start=len(restored[section]);restored[section].extend(values)
            out.append(dict(section=NAMES[section],start=start,count=len(values),wire_B=len(record)))
    assert controls==[0,4,1,3],controls
    assert restored==expected
    return out


def changed(a,b):
    # Removed tails are represented by new count/layout, not bytes to retransmit.
    return sum(i>=len(b) or x!=b[i] for i,x in enumerate(a))


def data_stats(current,previous,rs):
    result={}
    for k,name in enumerate(NAMES):
        a=current[k];b=[] if previous is None else previous[k]
        aa=b''.join(v.to_bytes(WIDTH[k],'little') for v in a)
        bb=b''.join(v.to_bytes(WIDTH[k],'little') for v in b)
        rec=[r for r in rs if r['section']==name]
        reusable=[r for r in rec if b[r['start']:r['start']+r['count']]==a[r['start']:r['start']+r['count']]]
        result[name]=dict(active_values=len(a),canonical_B=len(aa),changed_values=changed(a,b),
            changed_B=changed(aa,bb),count_changed=len(a)!=len(b),encoded_record_B=sum(r['wire_B'] for r in rec),
            records=len(rec),unchanged_record_B=sum(r['wire_B'] for r in reusable),
            unchanged_records=len(reusable),whole_section_equal=a==b,
            dirty16B_groups=sum(aa[i:i+16]!=bb[i:i+16] for i in range(0,len(aa),16)))
    return result


def output_decode(b):
    op,sec=b[:2];n,e=u16(b,12),u16(b,14);v=b[16:];assert len(v)==n
    if op==2:return v
    if op in (4,5):assert n==2 and e%2==0;return v*(e//2)
    if op==8:assert sec==4 and n==4 and e%4==0;return v*(e//4)
    raise AssertionError(('unhandled ordinary opcode',op))


def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    sealed=read(a.data/'result.json');assert sealed['passed']
    prior=read(ROOT/'analysis/whole580-verification.json')
    inputs={};frames={};previous=None
    schedules={i:read(a.traces/f'nes-close561-run{i}/events.json') for i in (1,2)}
    for i in (1,2):
        assert sha(a.traces/f'nes-close561-run{i}/events.json')==prior['phases'][i-1]['evidence']['events.json']
    for g in range(905,958):
        geometry=a.data/f'frame{g}.geometry';raw=a.data/f'frame{g}.raw'
        for p in (geometry,raw):
            assert sha(p)==sealed['evidence_files'][p.name];inputs[p.name]=sha(p)
        packets,counts,arrays=legacy_packets(geometry.read_bytes(),raw.read_bytes(),g)
        values=arrays+[list(raw.read_bytes())];rs=records(packets,g,values)
        for i,events in schedules.items():
            d1=[x for x in events if x['generation']==g and x['event']=='SPI' and x['opcode']=='0xd1']
            assert [len(p)+3 for p in packets]==[x['bytes'] for x in d1],('D1 boundaries',g,i)
        section=data_stats(values,previous,rs);body=sum(map(len,packets))
        assert sum(r['wire_B'] for r in rs)==body
        # Address skips/base identity are deliberately not invented here.
        # Repack retained records only to show how much the old packet count
        # overcharges a projection; this is still not an executable protocol.
        retained=[]
        for r in rs:
            k=NAMES.index(r['section']) if r['section']!='control' else None
            same=(k is not None and previous is not None and
                previous[k][r['start']:r['start']+r['count']]==values[k][r['start']:r['start']+r['count']])
            if not same:retained.append(r)
        fill=0;ideal_packets=0
        for r in retained:
            fill+=r['wire_B'];assert fill<=256
            if fill>244 or r.get('control',0)>0:ideal_packets+=1;fill=0
        assert fill==0
        frames[g]=dict(input=dict(section=section,packet_count=len(packets),body_B=body,
            hypothetical_retained_record_packets=ideal_packets,
            hypothetical_repack_D1_D2_saving_B=(len(packets)-ideal_packets)*11,
            control_B=sum(r['wire_B'] for r in rs if r['section']=='control'),
            generation_field_B=2*len(rs),record_count=len(rs),D1_wire_B=body+3*len(packets),
            canonical_active_B=sum(s['canonical_B'] for s in section.values()),
            payload_sha256=hashlib.sha256(b''.join(packets)).hexdigest()),phases={})
        previous=values
    for phase in (1,2):
        d=a.traces/f'nes-close561-run{phase}';events=schedules[phase]
        assert sha(d/'packets.jsonl')==prior['phases'][phase-1]['evidence']['packets.jsonl']
        entries=[json.loads(s) for s in (d/'packets.jsonl').read_text().splitlines()]
        rows=list(csv.DictReader((d/'window.csv').open(encoding='utf8')))
        assert sha(d/'window.csv')==prior['phases'][phase-1]['evidence']['window.csv']
        cpu=defaultdict(list)
        for r in rows:cpu[int(r['index'])].append(r)
        packet_groups=defaultdict(list)
        for ordinal,(rpc,t,h,tile) in enumerate(entries,1):
            b=bytes.fromhex(h);packet_groups[u16(b,8)].append((ordinal,t,b))
        # Analysis-only histories. Existing hardware retains map history, not
        # a free persistent cache for every section. Do not claim zero RAM cost.
        histories=[defaultdict(dict),defaultdict(dict)];layouts=[None,None];committed_at=[None,None]
        for g in range(905,958):
            ev=[r for r in events if r['generation']==g];pack=packet_groups[g]
            begin=pack[0][2];seal=pack[-1][2]
            assert begin[0]==1 and seal[0]==3
            bank=u16(begin,18);assert bank in (0,1)
            base_commit=committed_at[bank]
            assert base_commit is None or pack[0][1]>base_commit
            patch_count=u16(seal,38)
            if layouts[bank]!=patch_count:histories[bank][5]={}
            state={k:dict(v) for k,v in histories[bank].items()}
            totals=defaultdict(Counter);timeline=[];written=defaultdict(set)
            spi=[x for x in ev if x['event']=='SPI' and x['opcode']=='0xe1']
            assert [len(b)+3 for _,_,b in pack]==[x['bytes'] for x in spi]
            for (ordinal,t,b),sp in zip(pack,spi):
                op,sec=b[:2];name='control' if op in (1,3) else 'BG_tile' if op==7 and sec==0 else 'OBJ_tile' if op==7 else {2:'map',3:'palette',4:'OAM',5:'HDMA_raw'}[sec]
                stats=totals[name];stats['packets']+=1;stats['wire_B']+=len(b)+3;stats['data_B']+=len(b)-16
                matches=[r for r in cpu[ordinal] if int(r['g'])==g and int(r['op'])==op]
                load=[int(r['clock']) for r in matches if r['event']=='load'];ack=[int(r['clock']) for r in matches if r['event']=='ack']
                assert len(load)==len(ack)==1,(phase,g,ordinal,op,load,ack)
                # RPC publishes at ceil(M4 floating master clock).
                assert t<=math.ceil(sp['clock']) and t<=load[0]<=ack[0],(phase,g,ordinal,t,sp['clock'],load,ack)
                timeline.append(dict(section=name,op=op,offset=u16(b,10),wire_B=len(b)+3,
                    ARM_SPI_end=sp['clock'],queue_publish=t,SNES_load=load[0],SNES_ACK=ack[0]))
                if op in (1,3,7):continue
                value=output_decode(b);at=u16(b,10);stats['expanded_B']+=len(value)
                old=state.setdefault(sec,{})
                assert not (set(range(at,at+len(value))) & written[sec])
                written[sec].update(range(at,at+len(value)))
                eq=sum(old.get(at+i)==x for i,x in enumerate(value));stats['same_target_bank_B']+=eq
                for size in (2,8,16,64):
                    stats[f'different_{size}B_groups']+=sum(any(old.get(at+i+j)!=x for j,x in enumerate(value[i:i+size])) for i in range(0,len(value),size))
                if eq==len(value):stats['whole_packet_equal_wire_B']+=len(b)+3;stats['whole_packet_equal_count']+=1
                for i,x in enumerate(value):old[at+i]=x
            # Map reconstruction compared to the recorded actual planner hash.
            maps=bytes(state[2][i] for i in range(4096))
            frozen=[r for r in ev if r['event']=='bg_map_frozen'];assert len(frozen)==1
            assert hashlib.sha256(maps).hexdigest()==frozen[0]['sha256']
            expected=a.capture/f'frame{g}'
            for sec,file in [(2,'map'),(3,'cgram'),(4,'oam')]:
                p=expected/f'expected-{file}.bin';data=p.read_bytes()
                assert bytes(state[sec][i] for i in range(len(data)))==data,(g,sec)
                inputs[f'capture/frame{g}/{p.name}']=sha(p)
            histories[bank]=state;layouts[bank]=patch_count;committed_at[bank]=timeline[-1]['SNES_ACK']
            marks={name:next(r['clock'] for r in ev if r['event']==name) for name in ['source_begin','planner_enter','prepare_enter','output_enter531','end_enter']}
            marks.update(first_D1_end=next(r['clock'] for r in ev if r['event']=='SPI' and r['opcode']=='0xd1'),
                final_D1_end=[r['clock'] for r in ev if r['event']=='SPI' and r['opcode']=='0xd1'][-1],
                input_D3_end=next(r['clock'] for r in ev if r['event']=='SPI' and r['opcode']=='0xd3'),
                capture_ready=next(r['capture_ready'] for r in ev if r['event']=='source_begin'),
                SEAL_load=timeline[-1]['SNES_load'],final_ACK=timeline[-1]['SNES_ACK'])
            wire=Counter()
            for r in ev:
                if r['event']=='SPI':wire[r['opcode']]+=r['bytes']
                elif r['event']=='observer':wire[r['opcode']]+=8
            assert sum(x['wire_B'] for x in totals.values())==wire['0xe1']
            frames[g]['phases'][phase]=dict(bank=bank,patch_count=patch_count,analysis_history_prior_final_ACK=base_commit,output=dict(totals),wire=dict(wire),marks=marks,packets=timeline,
                physical_capture_count=None,physical_NES_advancement=None,physical_input_latency_ms=None)
    groups={}
    for name,gs in [('cold_banks',[905,906]),('initialized',list(range(907,958))),('dense_regression',list(range(951,956)))]:
        group=dict(n=len(gs),input={})
        for sec in NAMES:
            group['input'][sec]={k:sum(frames[g]['input']['section'][sec][k] for g in gs)/len(gs) for k in ['canonical_B','changed_B','encoded_record_B','unchanged_record_B','records','dirty16B_groups']}
        group['input_totals']={k:sum(frames[g]['input'][k] for g in gs)/len(gs) for k in ['body_B','generation_field_B','packet_count','canonical_active_B','hypothetical_retained_record_packets','hypothetical_repack_D1_D2_saving_B']}
        group['phases']={}
        for phase in (1,2):
            names=set(n for g in gs for n in frames[g]['phases'][phase]['output'])
            out={n:{k:sum(frames[g]['phases'][phase]['output'].get(n,{}).get(k,0) for g in gs)/len(gs) for k in ['wire_B','data_B','expanded_B','same_target_bank_B','whole_packet_equal_wire_B','different_2B_groups','different_8B_groups','different_16B_groups','different_64B_groups']} for n in sorted(names)}
            ops={op:sum(frames[g]['phases'][phase]['wire'].get(op,0) for g in gs)/len(gs) for op in sorted({op for g in gs for op in frames[g]['phases'][phase]['wire']})}
            # Optimistic reuse envelope only: missing skip/base/CRC/rollback costs.
            saving=sum(group['input'][s]['unchanged_record_B'] for s in NAMES)+sum(x['whole_packet_equal_wire_B'] for x in out.values())
            nonquery=sum(v for k,v in ops.items() if k not in ('0xd0','0xe0','0xe8'))
            group['phases'][phase]=dict(output=out,wire=ops,nonquery_B=nonquery,
                input_unchanged_record_B=sum(group['input'][s]['unchanged_record_B'] for s in NAMES),
                output_whole_packet_equal_wire_B=sum(x['whole_packet_equal_wire_B'] for x in out.values()),
                optimistic_unchanged_record_and_packet_saving_B=saving,
                optimistic_remaining_before_new_protocol_B=nonquery-saving,
                optimistic_wire_ms=(nonquery-saving)*8/2625000*1000,
                hypothetical_repacked_B=nonquery-saving-group['input_totals']['hypothetical_repack_D1_D2_saving_B'],
                hypothetical_repacked_wire_ms=(nonquery-saving-group['input_totals']['hypothetical_repack_D1_D2_saving_B'])*8/2625000*1000)
        groups[name]=group
    coverage={sec:sorted({frames[g]['input']['section'][sec]['active_values'] for g in frames}) for sec in NAMES}
    selected=read(ROOT/'analysis/whole580-manifest.json')
    elf=a.arm/'obj-nes-100/sd2snes.elf'
    assert sha(elf)==selected['artifacts']['ELF']
    names={'logical_record','nes_native165_packet','nes_native165_reset','map_word185',
           'map527','nes_sink212_seal','nes_resident211_prepare','packet_wire'}
    symbols=[dict(name=n,address=hex(at),bytes=size,sha256=hashlib.sha256(b).hexdigest())
             for (n,at,size),b in funcs(elf).items() if n in names]
    assert {s['name'] for s in symbols}==names
    result=dict(stage=581,passed=True,baseline='MMC577',new_product_code=False,new_simulation=False,
        groups=groups,frames=frames,workload_active_counts=coverage,inputs=inputs,tools={n:sha(ROOT/'tools'/n) for n in ['analyze_nes_body581.py','nes_transfer512.py','nes_raw506.py','check_nes_game478.py','nes_schedule492.py']},
        gross_function_boundaries=dict(ELF_sha256=sha(elf),symbols=symbols,verified_net_deletion_B=0,
            limit='Gross enclosing function sizes; independent checks/callers remain. No free Flash gain.'),
        provenance=dict(dataset_result=sha(a.data/'result.json'),whole580=sha(ROOT/'analysis/whole580-verification.json'),
            data='WORKSPACE/probes/nes-delta231/test07',capture='WORKSPACE/probes/nes-output489/audit01',
            input_binding='Sealed dataset hashes, independent semantic restoration, exact per-packet D1 byte sizes for all106 frame/phase pairs. Old D1 payload bytes are not recorded by the simulator.',
            output_binding='Pinned PUSH bytes and CPU load/ACK for every packet, reconstructed map/hash and captured palette/OAM.'),
        limits=['Reuse counts are optimistic omission envelopes, not an executable ABI or hardware time gain.',
            'Input base, skip addressing, CRC/coverage, STOP rollback and new framing must be charged before selection.',
            'Output cache here is analysis-only; section5 comparisons require identical patch layout and no canonical raw VRAM identity proof.',
            'Only existing53 captures; scene classes are workload labels, not video-certified static/moving/dense coverage.',
            'Physical capture/NES progress/input latency and first-level ROM grant timing remain unmeasured.'])
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(groups=groups,input_pins=len(inputs)),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['data','capture','traces','arm','out']:p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
