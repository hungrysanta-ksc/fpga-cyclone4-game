# SPDX-License-Identifier: MIT
"""Check the board's memory admission wiring, SPI START retirement and two-slot lifecycle."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from nes_raw506 import once, sha


def main():
    parser = argparse.ArgumentParser()
    for name in ('base', 'board', 'out', 'bin', 'wire', 'banks'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    d = a.out
    d.mkdir(parents=True, exist_ok=False)
    tests = Path(__file__).resolve().parents[1] / 'tests/nes-functional'

    def execute(tool, args, label, marker=None):
        log = d / (label + '.log')
        with log.open('wb') as f:
            subprocess.run([str(a.bin / (tool + '.exe')), *map(str,args)], cwd=d, stdout=f,
                           stderr=subprocess.STDOUT, check=True, timeout=150)
        output = log.read_text(errors='replace')
        if marker and (marker not in output or '** Fatal:' in output):
            raise AssertionError((label, output[-900:]))
        return output

    ref = once((a.base/'nes_rom_spi.sv').read_text(), 'module nes_rom_spi_check(', 'module ref_spi563(')
    (d/'reference.sv').write_text(ref)
    tb = (tests/'arg564_tb.sv').read_text()
    tb = once(tb, ' initial begin\n  if($test$plusargs("SHIFT"))',
              (tests/'start572.svh').read_text() + '\n initial begin\n  if($test$plusargs("SHIFT"))')
    tb = once(tb, '  $finish;', '  start_vetoes572();$finish;')
    (d/'loader.sv').write_text(tb)

    # Use the same top-level release chain in the guard fixture as in the fitted board.
    top = (a.board/'nes_live_joint.sv').read_text()
    wiring = top[top.index(' // Both heartbeat'):top.index(' wire diagnostic_reset;',top.index(' // Both heartbeat'))]
    guard = (a.wire/'guard.sv').read_text()
    guard = guard[:guard.index('`ifdef SPLIT')] + wiring + guard[guard.index(' nes_domain_reset124 diagnostic_release'):]
    (d/'guard.sv').write_text(guard)
    (d/'plans.hex').write_bytes((a.banks/'plans.hex').read_bytes())
    assert sha(d/'plans.hex')=='3c501203ace52bede32dbca9ed043835cc7a6444a66d8fbd3846da1f3f180f8d'
    files = ['nes_rom_spi.sv', 'nes_diag_clock_guard127.sv', 'nes_domain_reset124.sv',
             'nes_diag_startup_guard.sv', 'nes_rom_physical.sv', 'nes_native_mailbox206.sv', 'nes_plan_batch206.sv']
    execute('vlib', ['work'], 'lib')
    execute('vlog', ['-sv', *(a.board/n for n in files),d/'reference.sv',d/'loader.sv',d/'guard.sv',
                     a.banks/'banks.sv'], 'compile')
    phases=[]
    for i in (0,1):
        flags=['+SHIFT'] if i else []
        def sim(top,marker):
            return execute('vsim',['-c',top,*flags,'-do','run -all; quit -f'],top+str(i),marker)
        spi = sim('arg564_tb','PASS572 START 512')
        checks = re.search(r'PASS564 writes=266 trunc=56 armed=1 checks=(\d+)',spi)
        assert checks
        mem = sim('guard563_tb','PASS563 6 losses')
        assert 'BOTH570 active_read_no_edges' in mem
        losses = re.findall(r'LOSS563 (\d) (\d) (\d+)',mem)
        assert len(losses)==6
        bank = sim('plan569_tb','PASS569 STOP=16 faults=3 reuse=1 retire=1')
        phases.append(dict(SPI_cycles=int(checks[1]),live_vetoes=512,losses=losses,
                           release_ps=re.findall(r'ALLOW570 since_lock=(\d+) since_pair=(\d+)',mem),
                           starts_ps=re.findall(r'START563 (\d+)',mem),slot_events=bank.count('# EV')))
    (d/'result.json').write_text(json.dumps(dict(phases=phases,inputs={f:sha(a.board/f) for f in files},
        wiring=sha(a.board/'nes_live_joint.sv'),guard_fixture=sha(a.wire/'guard.sv'),
        slot_fixture=sha(a.banks/'banks.sv')),indent=2)+'\n')


if __name__=='__main__':
    main()
