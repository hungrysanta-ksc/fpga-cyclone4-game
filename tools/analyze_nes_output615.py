# SPDX-License-Identifier: MIT
"""Reconcile the MMC613 seal call with paired ARM and SNES clocks."""
import argparse
import json
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from statistics import mean

from analyze_nes_dma542 import partition
from analyze_nes_output531 import kind
from analyze_nes_phase537 import ROOT, csv_groups, ms, one, read, sha


def packets(folder):
    by_generation = defaultdict(list)
    for line in (folder / 'packets.jsonl').read_text().splitlines():
        _, push, header, bulk = json.loads(line)
        h = bytes.fromhex(header)
        generation = int.from_bytes(h[8:10], 'little')
        by_generation[generation].append((h, bytes.fromhex(bulk), push))
    return by_generation


def run(folder, pins):
    for name, digest in pins.items():
        assert sha(folder / name) == digest, name
    part = partition(folder)
    beam = csv_groups(folder / 'seal528.csv')
    cpu = csv_groups(folder / 'window.csv')
    events = defaultdict(list)
    for event in read(folder / 'events.json'):
        events[event['generation']].append(event)
    obj = read(folder / 'obj-phases.json')
    commands = packets(folder)
    frames = {}
    for g, p in part.items():
        ev = events[g]
        rows = [r for r in cpu[g] if r['op'] == 3]
        enter = one(ev, 'output_enter531')['clock']
        leave = one(ev, 'output_return531')['clock']
        load = one(rows, 'load')['clock']
        ack = one(rows, 'ack')['clock']
        cmd = commands[g]
        push = cmd[-1][2]
        assert cmd[-1][0][0] == 3 and enter <= push <= load <= ack <= leave
        spi = [e for e in ev if e['event'] == 'SPI' and enter <= e['start'] < push]
        sends = [e for e in spi if e['opcode'] == '0xe1']
        assert abs(sends[-1]['clock']-push) <= 1 and sends[-1]['packet_opcode'] == 3
        first = sends[0]['start']
        terms = dict(to_first_E1=ms(first-enter),first_E1_to_SEAL_push=ms(push-first),
                     SEAL_queue_to_CPU_load=ms(load-push),checks=p['checks_ms'],
                     upload_wait=p['serviced_VBlank_wait_ms']-p['final_wait_ms'],
                     DMA=sum(p['DMA_ms'].values()),other_CPU=p['other_setup_control_ms'],
                     last_blank_wait=p['final_wait_ms'],ACK_to_ARM_return=ms(leave-ack))
        total = ms(leave-enter)
        assert min(terms.values()) >= 0 and abs(sum(terms.values())-total) < 1e-8
        # Omit sequence, token and publication clock; compare all map and OBJ
        # destinations, lengths, payloads, multiplicity, and the ordered OBJ slots.
        work = sorted((h[:2].hex(), h[10:16].hex(), h[16:].hex() if h[0]!=7 else bulk.hex())
                      for h,bulk,_ in cmd if h[1]==2 or (h[0],h[1])==(7,1))
        obj_slots = [r['slot'] for r in obj[str(g)].get('obj_plans', [])]
        ident = sha256(json.dumps([work,obj_slots]).encode()).hexdigest()
        pre = Counter()
        for e in spi:
            pre[e['opcode']] += ms(min(e['clock'],push)-e['start'])
        assert sum(pre.values()) <= ms(push-enter)+1e-8
        # SNES ordinary work overlaps ARM issuance. Clip it to the pre-SEAL row.
        service = Counter()
        heads = {}
        for r in cpu[g]:
            if r['event']=='load':
                heads[r['index']] = r['clock']
            if r['event']=='ack':
                lo = heads.pop(r['index'])
                span = max(0, min(r['clock'],push)-max(lo,enter))
                if span:
                    service[f"{r['op']}/{r['section']}"] += ms(span)
        assert not heads and sum(service.values()) <= ms(push-enter)+1e-8
        packets_by_section = Counter()
        by_push = {t:h for h, _, t in cmd}
        for e in sends:
            t, = [t for t in by_push if abs(e['clock']-t)<=1]
            h = by_push[t]
            packets_by_section[f'{h[0]}/{h[1]}'] += ms(e['clock']-e['start'])
        markers = [r for r in beam[g] if r['event']=='latch' and r['clock'] >= one(rows,'final212')['clock']]
        credit = one(beam[g], 'final_credit')
        assert len(markers)<=1
        latch = [(r['line'],r['h']) for r in markers]
        map_runs = []
        if g==952:
            issued = [r for r in beam[g] if r['event']=='command']
            for a,b in zip(issued,issued[1:]):
                if kind(a['bank'],a['bytes'])=='map':
                    transfers = [r for r in beam[g] if r['event']=='dma' and a['clock']<=r['clock']<b['clock']]
                    map_runs.append(dict(destination=a['bytes'],bytes=sum(r['bytes'] for r in transfers),
                                         command_span_clocks=b['clock']-a['clock']))
        frames[g] = dict(terms=terms,total_ms=total,work=ident,map_packets=sum(h[1]==2 for h,_,_ in cmd),
            OBJ_B=sum(len(b) for h,b,_ in cmd if h[:2]==bytes([7,1])),OBJ_plans=len(obj_slots),
            final_credit=credit['bytes'],latch=latch,E1_op_section_ms=packets_by_section,
            nested_pre_CPU_ms=service,map_commands_952=map_runs,
            pre_SEAL_SPI_ms=dict(pre),output_E1=len(sends),final_waits=p['final_wait_count'])
    return frames


def group(rows):
    terms = rows[0]['terms']
    return dict(n=len(rows),ms=mean(r['total_ms'] for r in rows),
                terms={k:mean(r['terms'][k] for r in rows) for k in terms},
                pre_SPI_ms=mean(sum(r['pre_SEAL_SPI_ms'].values()) for r in rows),
                pre_E1_ms=mean(r['pre_SEAL_SPI_ms']['0xe1'] for r in rows),
                final_waits=sum(r['final_waits'] for r in rows))


def analyze(traces):
    files = [('577','nes-close561-run','close561-verification.json','early'),
             ('613','nes-board611-run','board611-verification.json','candidate')]
    groups = {}
    details = {}
    canonical = None
    for label, prefix, reference, variant in files:
        for phase in (1,2):
            pins = read(ROOT/'analysis'/reference)['phases'][phase-1][variant]['pins']
            frames = run(traces/(prefix+str(phase)),pins)
            keys = {g:r['work'] for g,r in frames.items()}
            if canonical is None:
                canonical = keys
            assert len(keys)==52 and keys==canonical
            name = f'{label}_p{phase}'
            groups[name] = {k:group([frames[g] for g in gens]) for k,gens in (
                ('warm',range(907,958)),('dense',range(951,956)))}
            details[name] = {g:frames[g] for g in (951,952,953,954,955,957)}
    return dict(units='milliseconds',physical=read(ROOT/'analysis/hardware614-mmc613.json')['phases'],
                source_reports=[f[2] for f in files],matched_work_SHA256=canonical,
                groups=groups,frames=details)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--traces',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    result=analyze(args.traces)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
