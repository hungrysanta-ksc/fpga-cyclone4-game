"""Match the MMC955 planner, wire, RTL and consumer on source frame 3412."""
import csv
import json
import re
import sys
from pathlib import Path

from analyze_nes_dense956 import report
from analyze_nes_chr951 import directory, logtext, read, sha
from test_nes_banks557 import MASTER, host_after


def arm_case(folder):
    joint = read(folder/'joint.json')
    assert joint['passed'] and joint['commits'] == 8
    events = read(folder/'events.json')
    e9 = [e for e in events if e.get('generation') == 906 and e.get('opcode') == '0xe9']
    jobs = [j for j in map(json.loads, (folder/'producer.jsonl').read_text().splitlines())
            if j['generation'] == 906 and j['kind'] == 1]
    rows = list(csv.DictReader((folder/'window.csv').open()))
    seal = [r for r in rows if r['g']=='906' and r['op']=='3']
    def stage(event):
        return [[int(r[k]) for k in ('clock','frame','line')] for r in seal if r['event']==event]
    vblanks = [int(r['frame']) for r in rows if r['event']=='reveal']
    assert len(vblanks)==8 and [j['bytes'] for j in jobs]==[576,96,64]
    return dict(firmware=joint['firmware_SHA256'], consumer=joint['client_SHA256'],
                vram_bytes=joint['vram_DMA_B'], batch_B=[e['bytes'] for e in e9],
                last_two_e9=[[round(e['start']),round(e['clock'])] for e in e9[-2:]],
                first576_ready=jobs[0]['producer'], last_OBJ_ready=jobs[-1]['producer'],
                seal=stage('load')[0], wait=stage('wait169'), resume=stage('wait_return_5781'),
                reveal=stage('reveal')[0], ACK=stage('ack')[0],
                DMA_by_blank={f:[int(r['value']) for r in rows if r['g']=='906' and
                              r['frame']==str(f) and r['event']=='ppu_dma']
                              for f in range(vblanks[0], vblanks[1]+1)},
                reveals=vblanks, six_intervals=vblanks[-1]-vblanks[1],
                final_ACK=joint['frames'][-1]['ACK_masterclock'])


def board_case(folder):
    d = folder/'gen906'
    origin = int((d/'origin914.txt').read_text())
    log = logtext(d/'timing958.log')
    assert 'PASS914 trace' in log and 'PASS914 trace' in logtext(folder/'gen905/timing958.log')
    accepted = re.search(r'ACCEPT954 batch=(\d+) edge=(\d+) bytes=(\d+) plans=(\d+)',log)
    polls = re.search(r'E8914 compared=(\d+) different=(\d+)',log)
    published = [(int(token),int(n),origin+int(at)) for token,n,at in re.findall(
        r'PUB914 token=(\d+) bytes=(\d+) at=(\d+)',log)]
    assert len(published)==7 and [r[1] for r in published[-3:]]==[576,96,64]
    obj = {}
    for slot in (3,10,16):
        tile = re.search(rf'PLAN958 kind=1 slot={slot} tag=(\d+) at=(\d+)(.*?)DONE958 at=(\d+)',log,re.S)
        obj[slot] = dict(tag=int(tile[1]), begin=origin+int(tile[2]), done=origin+int(tile[4]),
                         shared_grants=tile[3].count('ROM914 edge='))
    return dict(origin=origin, checked_batch=int(accepted[1])+1, checked_seal=origin+int(accepted[2]),
                body_B=int(accepted[3]), polls=list(map(int,polls.groups())),
                writable_for_batch6=origin+int(re.search(r'WRITABLE958 packets=5 edge=(\d+)',log)[1]),
                publication=published, OBJ=obj)


def analyze(temp, hardware):
    hw = report(hardware)
    focused, = [r for r in hw['targets'] if r and r['generation']==1410]
    physical, = [c for c in focused['chunks'] if c['token']==3678]
    cases = {}
    for phase in (1,2):
        folder = lambda mode: directory(temp,phase,'958'+mode,'cold')
        rows = {m:arm_case(folder(m)) for m in ('mark','control','short','credit')}
        boards = {m:board_case(folder(m)) for m in ('mark','short','credit')}
        closed_arm = arm_case(folder('closed'))
        closed_board = board_case(folder('closed'))
        assert closed_arm == rows['credit']
        assert closed_board['polls'][0] == boards['credit']['polls'][0]
        assert closed_board['polls'][1] == 0
        assert {**closed_board, 'polls': boards['credit']['polls']} == boards['credit']
        ref = rows['control']
        events = read(folder('mark')/'events.json')
        e9 = [e for e in events if e.get('generation')==906 and e.get('opcode')=='0xe9'][5]
        checked, = [e for e in events if e.get('opcode')=='0xe8'
                    and e['clock']<=e9['start'] and e['clock']>e9['start']-500]
        assert bytes.fromhex(checked['reply'])[3:6] == bytes([1,0,5])
        b = boards['mark']
        assert abs(b['checked_seal']-e9['clock'])<=2
        prior = [int(s)+b['origin'] for s in (folder('mark')/'gen906/grants914.txt').read_text().split()]
        last = max(a for a,z in zip(prior,prior[1:]) if z-a>200000 and a<e9['clock'])
        marks = read(folder('mark')/'emit958.json')
        batches = [x for x in read(folder('mark')/'e9931.json') if x['g']==906]
        assert all(bytes.fromhex(k)[0] in (0x80,0x81) for k in batches[5]['records'])
        emitted = {}
        for m in marks:
            if m['wire'] in batches[5]['records'] and m['wire'].startswith('81'):
                record=bytes.fromhex(m['wire'])
                slot=int.from_bytes(record[3:5],'little')
                if slot in b['OBJ']:
                    assert int.from_bytes(record[5:7],'little')==b['OBJ'][slot]['tag']
                    emitted[slot]=round(m['tick'])
        assert set(emitted)=={3,10}
        for mode,other in rows.items():
            assert other['consumer']==ref['consumer'] and other['vram_bytes']==ref['vram_bytes']
            assert all(sha(folder(mode)/f'frame-{g}.rgb')==sha(folder('control')/f'frame-{g}.rgb')
                       for g in range(905,913))
            if mode in boards:
                tested=boards[mode]
                entry=other['last_two_e9'][tested['checked_batch']-6]
                assert abs(tested['checked_seal']-entry[1])<=2
        probe=round(host_after(checked['start']+7.5*MASTER/2625000,3))
        cases[phase]=dict(arm=rows, rtl=boards, closed_E8_compared=closed_board['polls'][0],
                          closed_E8_differences=closed_board['polls'][1], complete_OBJ_records=emitted,
                          last_ROM_slot=last, credit_probe=probe,
                          best_seal_after_observed_credit=b['writable_for_batch6']+
                          round(e9['clock'])-probe)
    return dict(master_hz=MASTER,physical_generation=1410,physical_token=3678,
                physical_grants_4_11=[next(t['grants'] for t in physical['requested_tiles'] if t['tile']==i)
                                      for i in (3,10)], emulator_source_frame=3412,replay_generation=906,
                physical_source_frame=None, cache_case='cold replay, actual capture held for 906',cases=cases)


if __name__=='__main__':
    print(json.dumps(analyze(Path(sys.argv[1]),Path(sys.argv[2])),indent=2))
