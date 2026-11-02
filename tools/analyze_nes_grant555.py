# SPDX-License-Identifier: MIT
"""Join actual 954 DMA register writes to the last packet that supplied each byte."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_phase537 import Calendar, csv_groups, ms, one, read, sha
from analyze_nes_prelude554 import packet_schedule
from analyze_nes_map553 import map_times
from analyze_nes_seal538 import inspect_run
from analyze_nes_supply549 import compare


def ledger(folder, audit):
    cpu = csv_groups(folder / 'window.csv')
    origin = one([r for r in cpu[953] if r['op'] == 3], 'reveal')['clock']
    bank = one(csv_groups(folder / 'seal528.csv')[954], 'final_credit')['bank']
    base = (0, 0x4000, 0x6000) if bank == 0 else (0xc000, 0x8000, 0xa000)
    accepted = {}
    for index, (_, push, header, payload) in enumerate(
            map(json.loads, (folder / 'packets.jsonl').read_text().splitlines()), 1):
        packet = bytes.fromhex(header)
        word = lambda off: int.from_bytes(packet[off:off+2], 'little')
        if word(8) != 954:
            continue
        kind = packet[1]
        if packet[0] == 7:
            n = len(bytes.fromhex(payload))
        elif kind == 2 and packet[0] == 2:
            n = word(12)
        else:
            continue
        ack = one([r for r in cpu[954] if r['index'] == index], 'ack')['clock']
        dst = base[kind] + word(10)
        for addr in range(dst, dst+n):
            assert addr not in accepted
            accepted[addr] = (index, push, ack)
    seen = set()
    with (audit / 'dma555.csv').open() as f:
        rows = [{k:int(v) for k,v in r.items()} for r in csv.DictReader(f)]
    for r in rows:
        dst = r['dst']
        r['ms'] = round(ms(r['clock']-origin), 6)
        if r['port'] != 24:
            r['kind'] = {34:'CGRAM', 4:'OAM'}[r['port']]
        elif dst not in accepted:
            raw = 0x9000 if bank else 0x5000
            assert r['owned']==3 and r['n']==64 and dst-raw in (2,18,34)
            r['kind'] = 'raster'
        else:
            addrs = range(dst, dst+r['n'])
            owners = {accepted[a] for a in addrs}
            assert all(a not in seen for a in addrs)
            seen.update(addrs)
            r['kind'] = 'map' if base[2] <= dst < base[2]+4096 else 'tile'
            r['source_packets'] = sorted(x[0] for x in owners)
            r['last_push_ms'] = round(ms(max(x[1] for x in owners)-origin), 6)
            last_ack = max(x[2] for x in owners)
            assert last_ack < r['clock']
            r['last_accept_ack_ms'] = round(ms(last_ack-origin), 6)
    assert seen == set(accepted) and sum(r['n'] for r in rows) == 3728
    return rows


def map_admission(folder):
    cpu = csv_groups(folder/'window.csv')[954]
    for i,(_,push,h,_) in enumerate(map(json.loads,(folder/'packets.jsonl').read_text().splitlines()),1):
        b = bytes.fromhex(h)
        if b[:2]!=bytes((2,2)) or int.from_bytes(b[8:10],'little')!=954 or int.from_bytes(b[10:12],'little')!=2432:
            continue
        assert int.from_bytes(b[12:14],'little')==192
        events = [r for r in cpu if r['index']==i]
        load,ack = (one(events,k) for k in ('load','ack'))
        return dict(index=i,push=push,load=load,ack=ack,push_to_load=load['clock']-push,load_to_ack=ack['clock']-load['clock'])
    raise AssertionError('missing 954 map packet at offset 2432')


def analyze(args):
    phases = []
    for phase in (1,2):
        variants = {}
        ref = args.traces / f'nes-prelude554-cut{phase}'
        for mode in ('cut', 'map', 'oam', 'both'):
            folder = ref if mode == 'cut' else args.traces / f'nes-grant555-{mode}{phase}'
            if mode != 'cut' and not (folder / 'joint.json').is_file():
                folder = args.traces / f'nes-grant555-{mode}-retry{phase}'
            audit = args.traces / f'nes-grant555-audit-{mode}{phase}'
            if mode != 'cut' and not (folder / 'joint.json').is_file():
                folder = args.traces / f'nes-grant555-{mode}-timed{phase}'
                audit = args.traces / f'nes-grant555-audit-{mode}-timed{phase}'
            client = args.client if mode in ('both','map') else args.old_client
            arm = args.arm if mode in ('both','oam') else args.old_arm
            replay = read(audit / 'audit.json')
            assert replay['frames'] == 53 and replay['trace'] == sha(folder / 'window.csv')
            cal = Calendar(args.traces / 'nes-service509-rom03')
            cost = inspect_run(folder,args.plans,cal,ref,sha(arm/'obj-nes-100/firmware.stm'),
                               sha(client/'sink165.sfc'),first_bg_limit=3)
            schedule = packet_schedule(folder,cal)
            maps = map_times(folder)['maps']
            seal957 = [r for r in csv_groups(folder/'window.csv')[957] if r['op']==3]
            final957 = one(seal957,'final212')['clock']
            variants[mode] = dict(trace_folder=folder.name,audit_folder=audit.name,cost=cost, schedule954=schedule, commands954=ledger(folder,audit),map2432=map_admission(folder),
                replay=replay, early957=sum(r['push_minus_last_tile_ACK_ms']<0 for r in maps),
                wait957=sum(r['event']=='wait169' and r['clock']>=final957 for r in seal957))
            if phase==2 and mode!='cut':
                partial = args.traces / f'nes-grant555-{mode}2'
                if (partial/'callback-error.txt').exists():
                    assert 'Maximum execution time' in (partial/'callback-error.txt').read_text(errors='replace')
                    prefix = {}
                    for name in ('packets.jsonl','window.csv'):
                        rows = (partial/name).read_bytes().splitlines()
                        assert rows and (folder/name).read_bytes().splitlines()[:len(rows)]==rows
                        prefix[name] = len(rows)
                    variants[mode]['repeated_prefix_lines'] = prefix
        baseline = variants['cut']['cost']
        for mode, row in variants.items():
            cost = row['cost']
            row['delta'] = compare(cost, baseline)
            row['late_BG'] = [g for g,v in cost['BG'].items() if v['relative_window']>baseline['BG'][g]['relative_window']]
            d = cost['dense_frames']
            row['gate'] = (not row['late_BG'] and d[952]['before_head']<=5 and not any(cost['waits'].values())
                and d[953]['before_head']+d[953]['after_head']<=5 and row['early957']>=2
                and row['wait957']==0 and row['schedule954']['before_head']<=4
                and row['schedule954']['display_VB']<=5 and all(v<0 for v in row['delta'].values()))
        fixed = args.traces / f'nes-grant555-fixed{phase}'
        assert sha(fixed/'input/packets.jsonl') == sha(ref/'packets.jsonl')
        cpu = csv_groups(fixed/'run/window.csv')
        seal = [r for r in cpu[954] if r['op']==3]
        previous = one([r for r in cpu[953] if r['op']==3],'reveal')
        variants['map']['fixed_554_arrivals'] = dict(audit=read(fixed/'run/audit.json'),
            before_head=one(seal,'load')['frame']-previous['frame'],
            display_VB=one(seal,'reveal')['frame']-previous['frame'])
        phases.append(variants)
    guards = {n:read(args.checks/(n+'.json')) for n in ('guards','credit','menu','window')}
    fw = sha(args.arm/'obj-nes-100/firmware.stm')
    assert guards['guards']['sha']==guards['credit']['sha']==guards['menu']['firmware']==guards['window']['firmware_SHA256']==fw
    guards['edges'] = read(args.traces/'nes-grant555-edge02'/'edges.json')
    guards['priority'] = read(args.traces/'nes-grant555-priority01'/'result.json')
    guards['staged_STOP'] = read(args.traces/'nes-grant555-stop01'/'result.json')
    assert len(guards['priority'])==22 and all(r['status']==228 and r['commits']==49 for r in guards['staged_STOP']) and len(guards['staged_STOP'])==3
    assert [r['size'] for r in guards['edges']]==[512,0,0,0] and guards['edges'][0]['end_line']<262
    return dict(phases=phases, guards=guards, gate={m:all(row[m]['gate'] for row in phases) for m in ('map','oam','both')},
                scope='Matched 53-capture simulated timelines, periodic measured boot ROM grants, CPI=2.')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for key in ('traces','client','old-client','arm','old-arm','plans','checks','out'):
        p.add_argument('--'+key,type=Path,required=True)
    args = p.parse_args()
    args.out.write_text(json.dumps(analyze(args),indent=2)+'\n',newline='\n')
