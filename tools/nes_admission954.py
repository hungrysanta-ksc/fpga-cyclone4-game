"""Replay the first divergent writable response, bound to an observed bank seal."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from analyze_nes_chr951 import ROOT, directory, logtext
from nes_companion952 import complete_row_set, fixture, replay, supply
from test_nes_banks557 import batches, host_after, MASTER

TAG = '954first'
RATE = 2_625_000


def evidence(temp, phase):
    folder = directory(temp, phase, '952checkedrows', 'cold')
    change = json.loads((ROOT/'analysis/pr174-leadin.json').read_bytes())['first_ready'][phase-1]
    events = json.loads((folder/'events.json').read_bytes())
    commands = [e for e in events if e.get('generation') == 905 and e.get('opcode') == '0xe9']
    index, = [i for i,e in enumerate(commands) if round(e['start']) == change['before']['next_E9_start']]
    start = change['after']['next_E9_start']
    tx = bytes.fromhex(json.loads((folder/'e9wire914-905.jsonl').read_text().splitlines()[index])[1])
    assert len(tx) == 113 and hashlib.sha256(tx).hexdigest() == change['after']['payload_sha256']
    return folder, change, index, start, tx, commands[index]


def stage(temp, phase, prefix):
    base, change, i, start, tx, command = evidence(temp, phase)
    if prefix:
        d = temp/'nes-admission954'/f'p{phase}'
        d.mkdir(parents=True, exist_ok=True)
        for path in (base/'gen905').glob('*914.*'):
            if path.suffix in ('.hex', '.txt'):
                shutil.copyfile(path, d/path.name)
    else:
        for g in (905,906):
            fixture(temp, phase, True, g, TAG, include_bg=True)
        d = directory(temp, phase, TAG, 'cold')/'gen905'
    origin = int((d/'origin914.txt').read_text())
    lines = (d/'batch914.txt').read_text().splitlines()
    end = round(command['clock'] - command['start'] + start - origin)
    if prefix:
        lines[i] = ' '.join([str(end), *lines[i].split()[1:]])
        (d/'batch914.txt').write_text('\n'.join(lines[:i+1])+'\n')
    else:
        assert abs(int(lines[i].split()[0])-end) <= 2
    # Time every payload byte at the host port after the four-byte SPI header.
    samples = [round(host_after(start + 7.5*MASTER/RATE, 3))-origin]
    samples += [round(host_after(start + ((4+k)*8 + 7.5)*MASTER/RATE, 3))-origin
                for k in range(len(tx)-8)]
    (d/'admission954.txt').write_text(f'{i} '+ ' '.join(map(str,samples))+'\n')


def run(temp, phase):
    base, change, batch, start, payload, command = evidence(temp, phase)
    proof = logtext(temp/'nes-admission954'/f'p{phase}'/'prefix.log')
    assert 'PASS954 prefix' in proof and f'ACCEPT954 batch={batch} ' in proof
    first = change['sample']
    def tapped(parent):
        class Measured(supply(parent, 'checked')):
            verified_sample = None

            def snapshot557(self, tx, clock):
                sample = host_after(clock + 7.5*MASTER/RATE, 3)
                if self.generation == 905 and tx[0] == 0xe9 and round(clock) == start:
                    assert bytes(tx) == payload and self.accepted == batch
                    self.rpc(sample)
                    self.verified_sample = self.e9_snapshot557 = sample
                    return self.response(tx)
                answer = super().snapshot557(tx, clock)
                if self.generation == 905 and tx[0] == 0xe8 and round(sample) == first:
                    assert answer.hex() == change['before']['response']
                    return bytes.fromhex(change['after']['response'])
                return answer

            def seal557(self, tx, clock):
                if self.verified_sample is None:
                    return super().seal557(tx, clock)
                # Only this exact transfer obtained a bank grant from RTL.
                # decode557 still enforces the original NES-side service order.
                assert bytes(tx) == payload and self.generation == 905 and self.accepted == batch
                assert abs(clock-(command['clock']-command['start']+start)) <= 2
                rows = batches(self)
                assert len(rows) == batch
                rows.append(dict(seal=clock, sample=self.verified_sample, count=tx[3], first=self.plan_at))
                self.verified_sample = None
        return Measured
    with complete_row_set():
        replay(temp,phase,'cold','banked',wrap=tapped,tag=TAG)
    stage(temp,phase,False)


def safety(temp):
    from unittest.mock import patch
    from check_nes_supply905_arm import run as check_arm
    from nes_order938 import empty_next_offer
    from prepare_nes_trial950 import RELEASE, ROM
    import nes_return920

    out = temp/'nes-admission954'
    arm = out/'arm'
    shutil.copytree(RELEASE/'link',arm/'link')
    check_arm(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',
              arm,950,short_header=True,order=empty_next_offer,marker_values=(4,8,16,24))
    original = directory(temp,1,'952checkedrows','warm')
    trial = directory(temp,1,'954safety','warm')
    trial.mkdir()
    for pattern in ('packets.jsonl','capture.lua','client.sfc','map-*.bin','expected-*.bin',
                    'colors636-*.bin','frame-*.rgb'):
        for path in original.glob(pattern):
            shutil.copyfile(path,trial/path.name)
    with patch.object(nes_return920,'client',lambda _:ROM):
        nes_return920.guards(temp,'first',tag='954safety',destination=out/'consumer.json')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('prefix','run','safety'))
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2),nargs='?')
    a = p.parse_args()
    if a.mode == 'safety':
        safety(a.temp)
    elif a.phase is None:
        p.error('prefix and run require a starting phase')
    elif a.mode == 'run':
        run(a.temp,a.phase)
    else:
        stage(a.temp,a.phase,True)
