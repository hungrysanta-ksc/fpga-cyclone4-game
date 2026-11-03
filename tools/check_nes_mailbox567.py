# SPDX-License-Identifier: MIT
"""Compare both instantiated mailbox widths with 565 on the same clocks and bus."""
import argparse
from pathlib import Path
import re
import subprocess
import json
from nes_raw506 import once, sha


def run(base, board, bins, out):
    out.mkdir(parents=True, exist_ok=False)
    bench = Path(__file__).resolve().parents[1] / 'tests/nes-functional/mailbox567_tb.sv'
    module = 'nes_native_mailbox165.sv'
    ref = out / 'reference.sv'
    ref.write_text(once((base/module).read_text(), 'module nes_native_mailbox165', 'module mailbox565'))
    top = (board/'nes_live_joint.sv').read_text()
    types = [re.findall(r'(nes_native_mailbox\d+) #\(\.WIDTH\('+str(width)+r'\)\) '+name+r'\(', top)
             for width, name in [(96, 'native_records'), (17, 'native_prepared')]]
    assert len(types[0]) == 1 and types[0] == types[1]
    name = types[0][0]
    selected = board/(name+'.sv')
    paired = out/'paired.sv'
    paired.write_text(once(bench.read_text(), 'nes_native_mailbox165 #', name+' #'))
    def execute(exe, args, log):
        path = out / (log + '.log')
        with path.open('wb') as f:
            subprocess.run([str(bins/(exe+'.exe')), *map(str, args)], cwd=out,
                           stdout=f, stderr=subprocess.STDOUT, check=True, timeout=90)
        return path.read_text(errors='replace')
    execute('vlib', ['work'], 'lib')
    execute('vlog', ['-sv', ref, selected, paired], 'compile')
    phases = []
    for phase in range(2):
        log = execute('vsim', ['-c', 'mailbox567_tb', *(['+SHIFT'] if phase else []),
                               '-do', 'run -all; quit -f'], 'phase'+str(phase))
        rows = re.findall(r'PASS567 width=(\d+) accepted=81 delivered=33 canceled=48 checks=(\d+)', log)
        assert sorted(int(w) for w, _ in rows)==[17,96] and '** Fatal' not in log, log[-500:]
        phases.append(dict(rows))
    (out/'result.json').write_text(json.dumps(dict(base=sha(base/module), candidate=sha(selected), module=name,
        checks=phases, per_width_phase=dict(offered=81, received=33, canceled=48)),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','board','bin','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    run(a.base,a.board,a.bin,a.out)
