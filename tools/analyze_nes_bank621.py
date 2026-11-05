# SPDX-License-Identifier: MIT
"""Compare both real 621 phases to 619, 620D and a one-byte 906 counterfactual."""
import argparse
import json
from pathlib import Path

from analyze_nes_bg620 import Calendar, csv_groups, lanes, measure, ms, one, read, sha, work


def schedule(folder, calendar, addresses):
    result = measure(folder, calendar, addresses)
    cpu = csv_groups(folder/'window.csv')
    bank_log = read(folder/'obj-phases.json')
    events = read(folder/'events.json')
    for gen in (906, 957):
        rows = [row for row in cpu[gen] if row['op'] == 3]
        prev = one([row for row in cpu[gen-1] if row['op'] == 3], 'reveal')
        packets = [r for r in events if r['generation'] == gen and r.get('packet_opcode') == 3]
        packet, = packets
        clocks = {'previous_display': prev['clock'], 'SEAL_issue': packet['start'], 'SEAL_push': packet['clock']}
        for event in ('load', 'validate181', 'upload165_entry', 'final212', 'reveal', 'ack'):
            clocks[event] = one(rows, event)['clock']
        assert list(clocks.values()) == sorted(clocks.values())
        spans = {k:ms(b-a) for k,a,b in zip(list(clocks)[1:], clocks.values(), list(clocks.values())[1:])}
        before_final = [r for r in rows if clocks['upload165_entry'] < r['clock'] < clocks['final212']]
        waits = [r for r in before_final if r['event'] == 'wait169']
        returns = [r for r in before_final if r['event'].startswith('wait_return_')]
        assert len(waits) == len(returns) and all(w['clock'] < b['clock'] for w,b in zip(waits,returns))
        upload_wait_ms = sum(ms(b['clock']-w['clock']) for w,b in zip(waits,returns))
        result[f'g{gen}'] = dict(counts=[b['count'] for b in bank_log[str(gen)]['banks557']],
                                  clocks=clocks, span_ms=spans,
                                  upload_wait_ms=upload_wait_ms, upload_service_ms=spans['final212']-upload_wait_ms,
                                  display_VB=result['all_VB'][gen], final_line=one(rows, 'final212')['line'])
    result['tile_DMA_before_SEAL_957'] = [r for r in csv_groups(folder/'tile532.csv').get(957,[]) if r['event']=='tile']
    result['sealed_DMA_957'] = [r for r in csv_groups(folder/'seal528.csv')[957] if r['event']=='dma']
    return result


def compare(a):
    calendar = Calendar(a.calendar)
    plans = read(a.plans/'frame954/plans.json')
    addresses = [addr for _,h in plans for q in [bytes.fromhex(h)] if q[6]==0 for _,addr in lanes(q)]
    archive = read(a.reference)
    arm_hash = sha(a.arm/'obj-nes-100/firmware.stm')
    phases = []
    for i in (1, 2):
        dirs = dict(reference=a.traces/f'nes-tile619-coverage{i}', D=a.traces/f'nes-bg620-arm06-{i}',
                    forced=a.traces/f'nes-bank621-control-{i}', trial=a.traces/f'nes-bank621-arm01-{i}')
        base = dirs['reference']
        joint = read(base/'joint.json')
        workload = work(base)
        data = {}
        for name, d in dirs.items():
            r = schedule(d, calendar, addresses)
            j = read(d/'joint.json')
            assert all(j[k] == joint[k] for k in ('parameters','ROM_read_allocations','client_SHA256','vram_DMA_B'))
            if name in ('reference','D'):
                assert r['pins'] == archive['phases'][i-1]['control' if name=='reference' else 'arm06']['pins']
            else:
                assert j['firmware_SHA256'] == arm_hash and work(d) == workload
                assert all(sha(d/f)==sha(base/f) for g in range(905,958) for f in (f'frame-{g}.rgb', f'map-{g}.bin'))
            data[name] = r
        ref, old, forced, trial = data.values()
        assert trial['g906']['clocks']['previous_display'] == forced['g906']['clocks']['previous_display']
        assert csv_groups(dirs['trial']/'window.csv')[905] == csv_groups(dirs['forced']/'window.csv')[905]
        assert trial['g906']['counts'] == ref['g906']['counts'] and forced['g906']['counts'] == old['g906']['counts']
        for r in data.values():
            r['delta_last_ms'] = ms(r['last_ACK'] - ref['last_ACK'])
            r['changed_VB'] = {g:v-ref['all_VB'][g] for g,v in r['all_VB'].items() if v!=ref['all_VB'][g]}
        for r in data.values():
            del r['all_VB']
        trial['pass'] = (trial['g906']['display_VB'] < forced['g906']['display_VB']
                         and trial['intervals'][954] == trial['intervals'][952] == 4
                         and trial['ROM96_in_first_window'] == 96 and trial['delta_last_ms'] < 0
                         and trial['first_map_955_B'] >= 192 and trial['last_map_955_B'] == 384
                         and trial['final_wait_957'] == 0)
        phases.append(data)
    guards = read(a.guards)
    assert guards['arm'] == arm_hash
    edges = read(a.traces/'nes-bank621-edges/edges.json')
    stop = read(a.traces/'nes-bank621-stop/result.json')
    assert len(stop) == 4 and all(s['status']==0xe4 for s in stop)
    assert {e['case'] for e in edges if e['grant']==0} >= {'stop','head','both'}
    assert {(r['generation'],r['fault']) for r in edges if 'fault' in r} == {
        (g,f) for g in (906,907) for f in ('missing','duplicate')}
    result = dict(phases=phases, passed=all(p['trial']['pass'] for p in phases),
                  Flash_B=(a.arm/'obj-nes-100/firmware.stm').stat().st_size, guards=guards, priority=edges, STOP=stop)
    a.out.write_text(json.dumps(result, indent=2)+'\n',encoding='utf8',newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for k in ('arm','plans','traces','reference','calendar','guards','out'):
        p.add_argument('--'+k, type=Path, required=True)
    compare(p.parse_args())
