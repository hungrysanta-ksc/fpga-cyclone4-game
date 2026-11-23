"""Replay measured E8 snapshots through the unchanged ARM SPI receive path."""
import argparse
import json
import re
import struct
from pathlib import Path

from analyze_nes_chr951 import directory, logtext
from fixture_nes_port914 import fixture
from nes_companion952 import complete_row_set, replay, supply
from prepare_nes_trial950 import RELEASE
from test_nes_banks557 import MASTER, crc, host_after

BASE = '952checkedrows'


def evidence(folder, generation, include_first_valid=False):
    trace = folder / f'gen{generation}'
    log = logtext(trace / 'port952-checked.log')
    assert 'PASS914 trace' in log
    origin = int((trace / 'origin914.txt').read_text())
    jobs = [j for j in map(json.loads, (folder / 'producer.jsonl').read_text().splitlines())
            if j['generation'] == generation]
    desc = {int(edge): tuple(map(int, fields)) for edge, *fields in re.findall(
        r'DESC914 edge=(\d+) local_token=(\d+) kind=(\d+) bytes=(\d+) slot=(\d+) gen=(\d+)', log)}
    sampled = {p[0]:p for p in (list(map(int,s.split())) for s in (trace/'polls914.txt').read_text().splitlines())}
    observed = {}
    differences = re.findall(r'E8914 difference edge=(\d+) token=(\d+)/(\d+) flags=(\d+)/(\d+) count=(\d+)/(\d+)', log)
    compared = re.search(r'E8914 compared=(\d+) different=(\d+)',log)
    publication={int(k):(int(n),int(t)) for k,n,t in re.findall(r'PUB914 token=(\d+) bytes=(\d+) at=(\d+)',log)}
    assert int(compared[1]) == len(sampled) and int(compared[2]) == len(differences)
    for edge, token, old, flags, old_flags, accepted, old_count in differences:
        at, token, flags, accepted = map(int, (edge, token, flags, accepted))
        assert sampled[at][1:] == list(map(int,(old_flags,old_count,old)))
        observed[at] = token, flags, accepted
    if include_first_valid:
        at = min(t for t,d in desc.items() if d[0]==len(jobs))
        observed.setdefault(at,(desc[at][0],sampled[at][1],sampled[at][2]))
    packets = [bytes.fromhex(json.loads(line)[2]) for line in (folder/'packets.jsonl').read_text().splitlines()]
    tiles = {int.from_bytes(p[16:20],'little'):p for p in packets if p[0]==7 and int.from_bytes(p[8:10],'little')==generation}
    result = {}
    for at,(token,flags,accepted) in observed.items():
        payload = bytes(12)
        if token:
            local, kind, count, slot, gen = desc[at]
            assert publication[local][0]==count and publication[local][1]<=at
            job = jobs[local-1]
            offset = slot * (32 if kind else 16)
            assert (local, gen, count, kind) == (token, generation, job['bytes'], job['kind'])
            # The bench restarts the counter at each lease. Verify the wire identity
            # and offset before passing the measured descriptor to the ARM.
            packet = tiles[job['token']]
            assert int.from_bytes(packet[10:12],'little') == offset
            payload = struct.pack('<BBHHHI', 1, kind, count, offset, gen, job['token'])
        result[generation, origin+at] = (flags, accepted, payload)
    return result


def run(temp, phase, cache, sources, tag, only_910=False, *, work_arm=RELEASE, edition=950):
    measured = {}
    if cache == 'cold':
        for source in sources:
            folder = directory(temp,phase,source,cache)
            for gen in ([910] if only_910 else [908,910] if phase==2 else [908]):
                measured.update(evidence(folder,gen,include_first_valid=source!=BASE and gen==910))
    def wrap(base):
        class Feedback(supply(base,'checked')):
            def snapshot557(self, tx, start):
                reply = super().snapshot557(tx,start)
                if tx[0] != 0xe8:
                    return reply
                edge = round(host_after(start+7.5*MASTER/2_625_000,3))
                key = self.generation, edge
                if key not in measured:
                    return reply
                flags, accepted, payload = measured[key]
                assert int.from_bytes(reply[4:6],'big') == accepted
                out = bytearray(reply)
                out[3], out[6:18] = flags, payload
                out[19] = crc(out[1:19],8,7,0)
                with (self.a.out/'feedback953.jsonl').open('a') as log:
                    print(json.dumps([*key,reply.hex(),out.hex()]),file=log)
                return bytes(out)
        return Feedback
    with complete_row_set():
        replay(temp,phase,cache,'banked',wrap=wrap,tag=tag,work_arm=work_arm,edition=edition)
    for gen in ((908,909,910,911,912) if cache=='cold' else (909,912)):
        fixture(temp,phase,cache=='cold',gen,tag,include_bg=True)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('temp',type=Path)
    ap.add_argument('phase',type=int,choices=(1,2))
    ap.add_argument('cache',choices=('warm','cold'))
    ap.add_argument('tag')
    ap.add_argument('previous',nargs='*')
    ap.add_argument('--only-910',action='store_true',help='Isolate 910 before applying any 908 feedback')
    args=ap.parse_args()
    run(args.temp,args.phase,args.cache,[BASE,*args.previous],args.tag,args.only_910)
