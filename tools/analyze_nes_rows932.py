"""Match row grants, tile returns, DMA coverage and the final ACK by generation."""
import argparse
import json
from pathlib import Path

from analyze_nes_obj923 import recovery
from analyze_nes_palette921 import coverage, directory, read, read_csv
from analyze_nes_return930 import jobs, supply
from analyze_nes_rows931 import job_times, stop_edges
from analyze_nes_section929 import timeline
from analyze_nes_window924 import sample
from nes_rows932 import MODES, ORIGINAL
from test_nes_service509_schedule import Calendar


def grant_windows(folder, calendar):
    grants = (line.split() for line in (folder/'fill1/rom.tsv').read_text().splitlines()
              if line.startswith('G '))
    # The calendar retains the original grant order and repeats eight NES frames.
    return {offset: int(row[2]) for offset, row in zip(calendar.starts, grants, strict=True)}


def accepted(path):
    bursts = [b for b in read(path/'e9931.json') if b['g'] == 912]
    banks = read(path/'banks904.json')['912']['banks557']
    matches = []
    for batch, (burst, bank) in enumerate(zip(bursts, banks, strict=True), 1):
        assert burst['seal'] == bank['seal'] and len(burst['records']) == bank['count']
        for position, wire in enumerate(map(bytes.fromhex, burst['records']), 1):
            if len(wire) == 8 and wire[0] == 0x81 and int.from_bytes(wire[5:7], 'little') == 3081:
                matches.append(dict(batch=batch, position=position, wire=wire.hex(),
                                    accepted=bank['seal'], first_check=bank['first_check']))
    assert len(matches) == 1
    m = matches[0]
    assert (m['batch'], m['position'], m['wire']) == (2, 3, '8190036e00090cff')
    return m


def original_dma_jobs(path, pre, times):
    destinations = {(address,size) for kind,address,size,frame in pre if kind=='tile'}
    returns = dict(read(path/'returns904.json'))
    result = []
    for line in (path/'packets.jsonl').read_text().splitlines():
        packet = bytes.fromhex(json.loads(line)[2])
        if packet[0] != 7 or int.from_bytes(packet[8:10], 'little') != 912:
            continue
        section = packet[1]
        offset = int.from_bytes(packet[10:12], 'little')
        size = int.from_bytes(packet[14:16], 'little')
        token = int.from_bytes(packet[16:20], 'little')
        # Physical SNES destination in this generation's inactive display bank.
        address = (0xc000 if section==0 else 0x8000) + offset
        if (address,size) in destinations:
            result.append(dict(token=token, address=address, bytes=size,
                               ready=times[912,token,section,size], returned=returns[token]))
    assert {(r['address'], r['bytes']) for r in result} == destinations
    return result


def report(temp):
    calendar_path = temp/'nes-service509-rom03'
    calendar = Calendar(calendar_path)
    windows = grant_windows(calendar_path, calendar)
    proof = recovery('final', ORIGINAL, trial=ORIGINAL)
    checked_rom = ORIGINAL.parent/'nes-rows932'
    guards = read(checked_rom/'guards.json')
    stops = read(checked_rom/'stops.json')
    assert guards == proof['STOP'] and stops == proof['last_byte_STOP']
    out = dict(master_Hz=21477272, calendar=calendar.summary, firmware_guards=proof,
               replay_guards=guards, replay_stops=stops, cases={})
    for phase in (1, 2):
        for cache in ('cold', 'warm'):
            case = out['cases'][f'{cache}-{phase}'] = {}
            base = directory(temp, phase, '925final', cache)
            ref, quality = sample(base, ORIGINAL)
            base_times = job_times(base)
            for name in ('931latest', *MODES):
                path = directory(temp, phase, name if name == '931latest' else '932'+name, cache)
                row, checked = sample(path, ORIGINAL)
                assert checked == quality and read(path/'joint.json')['passed']
                for key in ('firmware_SHA256', 'client_SHA256'):
                    assert read(path/'joint.json')[key] == read(base/'joint.json')[key]
                times = job_times(path)
                assert times.keys() == base_times.keys()
                other = [times[k]-t for k,t in base_times.items() if k[:2] not in ((912,37),(912,38))]
                head = accepted(path)
                selected = []
                canceled = 0
                for gen, address, grant, reply in read(path/'ahead911.json'):
                    tag, lane = divmod(address, 16)
                    if gen != 912 or not (tag in (3081,6264) or tag == 6265 and lane < 3):
                        continue
                    assert head['accepted'] + 8 + 20*7 <= grant < reply
                    cycle, offset = divmod(grant, calendar.period)
                    selected.append(dict(tag=tag, row=lane, grant=grant, reply=reply,
                                         window=[cycle, windows[offset]]))
                    if name in MODES:
                        canceled += stop_edges(MODES[name], calendar, address, grant, reply)
                tiles = jobs(path)
                tail = supply(path, tiles)[38]
                remaining = tail['demand_grants']
                largest = max(remaining, key=lambda r:r['grant']-r['request'], default=None)
                trace = read_csv(path, 'window.csv')
                reveal = next(r for r in trace if r['g']=='912' and r['event']=='reveal')
                pre = coverage(row['pre912']).keys()
                expected = coverage(ref['pre912']).keys()
                seal = timeline(path)['marks']['SEAL'][2]
                transfers = [{k:int(r[k]) for k in ('frame','line','clock','value')} for r in trace
                             if r['g']=='912' and r['event']=='ppu_dma']
                assert sum(d['value'] for d in transfers if d['clock'] < seal) == sum(s[2] for s in row['pre912'])
                prior_frame = transfers[0]['frame']-1
                # Unknown horizontal clock. Each observed line gives a conservative
                # upper bound for the end of VBlank (the next frame's line 0).
                end_bounds = [int(r['clock'])+(262-int(r['line']))*1364 for r in trace
                              if int(r['frame'])==prior_frame and 225<=int(r['line'])<262]
                if cache == 'cold' and name in MODES:
                    assert {s['row'] for s in selected if s['tag']==6265} == {0,1,2}
                    assert any(s['tag']==3081 and s['row']==0 for s in selected)
                    first = [s for s in selected if s['tag']==6265 or (s['tag']==3081 and s['row']==0)]
                    assert len({tuple(s['window']) for s in first}) == 1
                    assert all(r['address'] != 3081*16 for r in remaining)
                    assert end_bounds
                original_jobs = original_dma_jobs(path, ref['pre912'], times) if cache=='cold' else []
                case[name] = dict(plan=head, grants=selected, STOP_edges=canceled,
                    largest_remaining_demand=largest,
                    ready37=tiles[37]['clocks']['ready'], ready38=tiles[38]['clocks']['ready'],
                    ready35=tiles[35]['clocks']['ready'], ready36=tiles[36]['clocks']['ready'],
                    returned35=tiles[35]['clocks']['returned'],
                    returned36=tiles[36]['clocks']['returned'], returned38=tiles[38]['clocks']['returned'],
                    other_jobs_later=sum(dt>0 for dt in other), worst_other_delta=max(other),
                    D2=row['commit_D2'], capture_offset=row['capture_offset'],
                    preDMA=row['pre912'], pre_bytes=len(pre), retained_bytes=len(pre & expected),
                    SEAL=seal, display_VBlank=int(reveal['frame']), display_line=int(reveal['line']),
                    prior_VBlank=prior_frame, prior_VBlank_end_upper=min(end_bounds, default=None),
                    original_DMA_jobs=original_jobs,
                    DMA=transfers,
                    gaps=row['gaps'], total=row['intervals'], ACK=row['ack912'],
                    gain_clocks=ref['ack912']-row['ack912'])
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    args.output.write_text(json.dumps(report(args.temp), indent=2)+'\n', encoding='utf-8')
