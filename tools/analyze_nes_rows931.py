"""Compare accepted row masks, real grant slots and displayed work on MMC925."""
import argparse
import json
from pathlib import Path

from analyze_nes_obj923 import recovery
from analyze_nes_palette921 import coverage, directory, read, read_csv
from analyze_nes_return930 import jobs, supply
from analyze_nes_section929 import timeline
from analyze_nes_window924 import sample
from nes_rows931 import MODES, ORIGINAL
from test_nes_service509_schedule import Calendar


TAG = 6265


def job_times(path):
    records = map(json.loads, (path/'producer.jsonl').read_text().splitlines())
    return {(r['generation'], r['token'], r['kind'], r['bytes']): r['producer'] for r in records}


def stop_edges(cls, calendar, address, grant, reply):
    assert calendar.select(grant) == (grant, reply)
    for edge in range(grant-1, reply+2):
        port = object.__new__(cls)
        port.owner = port.generation = 912
        port.queue = [(address, grant)]
        port.peer = (912, address+8)
        port.ready_rows = {address: (reply, 17, 34)}
        port.free = reply+1 if edge >= grant else edge
        port.cancel_supply()
        port.pump(edge)
        assert port.owner is None and not port.ready_rows and not port.queue and port.peer is None
        port.restart_supply()
        assert port.owner == 912 and not port.active and not port.ready_rows and not port.seen_rows
        port.original_select = calendar.select
        port.grants = []
        port.read_kind = 1
        following, _ = port.select(edge)
        assert following >= edge and (edge < grant or following > reply)
    return reply-grant+3


def report(temp):
    calendar = Calendar(temp/'nes-service509-rom03')
    guard_dir = ORIGINAL.parent/'nes-rows931'
    guards = read(guard_dir/'guards.json')
    stops = read(guard_dir/'stops.json')
    assert guards == read(ORIGINAL/'final-guards.json') and stops == read(ORIGINAL/'final-stops.json')
    out = dict(master_Hz=21477272, calendar=calendar.summary,
               replay_guards=guards, replay_obj_stops=stops,
               unchanged_link_guards=recovery('final', ORIGINAL, trial=ORIGINAL), cases={})
    for phase in (1, 2):
        for cache in ('warm', 'cold'):
            case = out['cases'][f'{cache}-{phase}'] = {}
            reference = directory(temp, phase, '925final', cache)
            ref, expected = sample(reference, ORIGINAL)
            prior_jobs = job_times(reference)
            hashes = read(reference/'joint.json')
            for mode, cls in MODES.items():
                path = directory(temp, phase, '931'+mode, cache)
                row, checked = sample(path, ORIGINAL)
                assert checked == expected
                joint = read(path/'joint.json')
                assert joint['passed'] and all(joint[k] == hashes[k] for k in ('firmware_SHA256','client_SHA256'))
                if mode == 'base':
                    assert row == ref and (reference/'events.json').read_bytes() == (path/'events.json').read_bytes()
                banks = read(path/'banks904.json')['912']['banks557']
                bursts = [b for b in read(path/'e9931.json') if b['g'] == 912]
                accepted = []
                for number, (bank, burst) in enumerate(zip(banks, bursts, strict=True), 1):
                    assert bank['seal'] == burst['seal'] and bank['count'] == len(burst['records'])
                    for idx, wire in enumerate(map(bytes.fromhex, burst['records']), 1):
                        if len(wire) == 8 and wire[0] == 0x81 and int.from_bytes(wire[5:7], 'little') == TAG:
                            accepted.append(dict(batch=number, position=idx, mask=wire[-1], seal=bank['seal'],
                                                 first_check=bank['first_check'], wire=wire.hex()))
                assert [(a['batch'], a['position'], a['mask']) for a in accepted] == [(1,14,248),(2,2,7),(2,6,224)]
                tiles = jobs(path)
                details = supply(path, tiles)
                demand = [v for v in details[37]['demand_grants'] if v['address']//16 == TAG]
                spec = [[a%16, grant, end] for g,a,grant,end in read(path/'ahead911.json') if g == 912 and a//16 == TAG]
                tested = 0
                for lane, grant, end in spec:
                    if lane < 3:
                        assert grant > accepted[1]['seal']
                        tested += stop_edges(cls, calendar, TAG*16+lane, grant, end)
                actual_jobs = job_times(path)
                assert prior_jobs.keys() == actual_jobs.keys()
                changes = [(actual_jobs[k]-v,k) for k,v in prior_jobs.items() if k[:2] not in ((912,37),(912,38))]
                latest, key = max(changes)
                before = coverage(ref['pre912']).keys()
                after = coverage(row['pre912']).keys()
                reveal = next(r for r in read_csv(path, 'window.csv')
                              if r['g'] == '912' and r['event'] == 'reveal')
                next_wait = max(details[38]['demand_grants'],
                                key=lambda v: v['grant']-v['request'], default=None)
                case[mode] = dict(accepted=accepted, demand=demand, spec=spec, STOP_edges=tested,
                    total_jobs=len(actual_jobs), other_jobs_later=sum(d>0 for d,k in changes),
                    max_other_ready_delta=latest, max_other_job=key,
                    ready37=tiles[37]['clocks']['ready'],ready38=tiles[38]['clocks']['ready'],
                    next_OBJ_largest_wait=next_wait,
                    second_E9_to_first_primary_check=banks[1]['first_check']-banks[1]['seal'],
                    SEAL=timeline(path)['marks']['SEAL'][2],
                    reveal={k:int(reveal[k]) for k in ('clock','frame','line')},
                    gaps=row['gaps'],total=row['intervals'],ACK=row['ack912'],
                    D2_minus_capture=row['capture_offset'],D2=row['commit_D2'],preDMA=row['pre912'],
                    preDMA_bytes=len(after), preserved_preDMA_bytes=len(before & after))
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    args.output.write_text(json.dumps(report(args.temp), indent=2)+'\n', encoding='utf-8')
