"""Cross-check final-ACK latency against next-input timestamps and matched SPI replays."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from analyze_nes_map830 import window
from analyze_nes_output822 import CLK_MS
from read_nes_frame900 import read_trace
from replay_nes_ack902 import BASE, WORK


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ms(clocks):
    return round(clocks/CLK_MS, 4)


def physical(path):
    rows = read_trace(path)['rows']
    assert all('invalid' not in r for r in rows)
    comparisons = []
    for a, b in zip(rows, rows[1:]):
        if a['window'] != b['window'] or a['generation']+1 != b['generation']:
            continue
        time = a['elapsed_ms']
        if time['E0'][0]-time['ACK'][1] < 4:
            continue
        lo, hi = b['elapsed_ms']['input']
        prev_show = time['show'][0]
        comparisons.append(dict(window=a['window'], generation=a['generation'],
            next_input_minus_E0_ms=[round(lo+prev_show-time['E0'][1],3),
                                    round(hi+prev_show-time['E0'][0],3)]))
    return comparisons


def collect(folder):
    j = read(folder/'joint.json')
    assert j['passed'] and j['last_status'] == 1 and j['commits'] == 8
    events = [e for e in read(folder/'events.json') if e['event']=='SPI']
    w = window(folder)
    producers = {r['token']: r for r in map(json.loads,(folder/'producer.jsonl').read_text().splitlines())}
    packets = list(map(json.loads,(folder/'packets.jsonl').read_text().splitlines()))
    pushes = [e for e in events if e['opcode']=='0xe1']
    assert len(pushes) == len(packets)
    tiles = {}
    for index, (packet,e) in enumerate(zip(packets,pushes),1):
        b = bytes.fromhex(packet[2])
        if b[0] != 7:
            continue
        token = int.from_bytes(b[16:20],'little')
        g = int.from_bytes(b[8:10],'little')
        ready = producers[token]
        polled = next(r for r in events if r['opcode']=='0xe8' and
                      (rx:=bytes.fromhex(r['reply']))[6] and
                      int.from_bytes(rx[14:18],'little') == token)
        head, = [r for r in w if r['index']==index and r['event']=='load']
        stop, = [r for r in w if r['index']==index and r['event']=='ack']
        assert g==ready['generation']==head['g']==stop['g']==e['generation']
        stages = [ready['producer'], polled['clock'],e['start'],head['clock'],stop['clock']]
        assert stages == sorted(stages)
        waiting = [x for x in events if x['start']<stages[1] and x['clock']>stages[0]]
        descriptors = [bytes.fromhex(x['reply']) for x in waiting if x['opcode']=='0xe8']
        issues = []
        for outgoing, push in zip(packets,pushes):
            if push['start']<stages[1] and push['clock']>stages[0]:
                payload=bytes.fromhex(outgoing[2])
                issues.append([payload[0],payload[1],push['bytes']])
        tiles[g] = dict(token=token, kind=b[1], bytes=ready['bytes'], clocks=stages,
                        E8_tokens=[int.from_bytes(rx[14:18],'little') if rx[6] else None
                                   for rx in descriptors],
                        issues_before_E8=issues,
                        adjacent_ms=[ms(b-a) for a,b in zip(stages,stages[1:])])
    shows = {r['g']:r for r in w if r['event']=='reveal'}
    rows = []
    for fr in j['frames'][2:]:
        g, ack = fr['generation'],fr['ACK_masterclock']
        barrier, = [e for e in events if e['generation']==g and e['opcode']=='0xea']
        first = next(e for e in events if e['generation']==g and ack<=e['clock']<=barrier['start']
                     and e['opcode']=='0xe0' and (rx:=bytes.fromhex(e['reply']))[1]==0xf7 and
                     rx[2]&2 and rx[3:5]==rx[5:7] and rx[7:9]==b'\x01\x03' and
                     int.from_bytes(rx[15:17],'little')==g)
        after = first['clock']
        overlaps = [e for e in events if e['start']<after and e['clock']>ack]
        counts = Counter(e['opcode'] for e in overlaps)
        wire = sum(min(e['clock'],after)-max(ack,e['start']) for e in overlaps)
        assert 0 <= wire <= after-ack+1
        d1 = [e for e in overlaps if e['opcode']=='0xd1']
        assert all(e['input_generation']==g+1 for e in d1)
        pops = [e['clock'] for e in events if e['opcode']=='0xd2' and e.get('input_generation')==g+1]
        rows.append(dict(g=g, display=shows[g]['frame']-shows[g-1]['frame'], ACK=ack,
            next_D2_by_ACK=sum(c<=ack for c in pops),
            next_D2_by_EA=sum(c<=barrier['clock'] for c in pops),
            ack_to_first_E0_ms=ms(after-ack), SPI_ms=ms(wire), between_transfers_ms=ms(after-ack-wire),
            transactions=counts, D1_wire_B=sum(e['bytes'] for e in d1),
            E0_to_EA_ms=ms(barrier['clock']-after), last_tile=tiles[g]))
    return dict(firmware=j['firmware_SHA256'],client=j['client_SHA256'],rows=rows,
                intervals=sum(r['display'] for r in rows),final_ACK=rows[-1]['ACK'])


def analyze(temp, downloads):
    root = Path(__file__).resolve().parents[1]
    original = read(root/'analysis/hardware900-901-results.json')
    h = {}
    for edition in (900,901):
        path = downloads/f'nes-frame-mmc{edition}.bin'
        assert digest(path)==original[str(edition)]['hashes']['frame']
        h[edition]=physical(path)
    packages = read(root/'analysis/frame900-901-package.json')
    fw = WORK/'link/src/obj-nes-100/firmware.stm'
    tags = {'frame900':packages['900']['ARM'], 'frame901':packages['901']['ARM'],
            '898-897':digest(BASE/'src/obj-nes-100/firmware.stm'), '902-credit4':digest(fw)}
    results = {}
    for clip in ('early','late'):
        for phase in (1,2):
            base=f'nes-tile821-{clip}-jointmirror-p{phase}-'
            results[clip+str(phase)] = runs = {}
            for tag, image in tags.items():
                folder=temp/(base+tag)
                runs[tag]=run=collect(folder)
                assert run['firmware']==image
                if tag=='902-credit4':
                    original_folder=temp/(base+'898-897')
                    for g in range(905,913):
                        for name in (f'map-{g}.bin',f'frame-{g}.rgb'):
                            assert digest(folder/name)==digest(original_folder/name)
                    assert read(folder/'loads898.json')==read(original_folder/'loads898.json')
                    assert run['client']==runs['898-897']['client']
    return dict(master_clocks_per_ms=CLK_MS, physical_next_input=h, phases=results,
                firmware_B=fw.stat().st_size, guards=read(WORK/'guards.json'))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','downloads','out'):
        p.add_argument(k,type=Path)
    args=p.parse_args()
    args.out.write_text(json.dumps(analyze(args.temp,args.downloads),indent=2)+'\n')
