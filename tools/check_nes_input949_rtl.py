"""Exercise the held-slot export witness on the 914I production module sources."""
import argparse
import json
import subprocess
from pathlib import Path

from check_nes_fault641 import MODULES, ROOT, digest
from check_nes_receive649_rtl import bench


def test(board, out, bin_dir):
    out.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'tests/nes-functional'
    modules = [board / f'nes_{n}.sv' for n in
               [*MODULES, 'native_export203', 'e9_scan914', 'e9_rows914']]
    (out / 'reject643.svh').write_text(bench((source / 'reject643.svh').read_text()))
    base = (source / 'fault641_tb.sv').read_text()
    # The vector is all zero. Drive both lanes of the packed ROM reader.
    base = base.replace('.mem_data(', ".bg_word(8'd0),.mem_data(")
    (out / 'fault641_tb.sv').write_text(base)
    (out / 'spi200_bus.svh').write_bytes((source / 'spi200_bus.svh').read_bytes())
    commands = [('vlib', ['work']), ('vlog', ['-sv', '+define+WITNESS642+REJECT643+DEFER643',
                 *modules, 'fault641_tb.sv']), ('vsim', ['-c', 'fault641_tb', '-gGEN643=97',
                 '-gHOST_PHASE=8', '-gNES_HALF=23.281', '-gSPI_HALF=190.476', '-do',
                 'onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0'])]
    for tool, args in commands:
        with (out / f'{tool}.log').open('wb') as log:
            subprocess.run([bin_dir / f'{tool}.exe', *args], cwd=out, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=120)
    log = (out / 'vsim.log').read_text()
    assert 'HELD649 next=98' in log and 'PASS643 gen=97 STOP' in log
    result = dict(modules={p.name: digest(p) for p in modules},
                  witness=next(line for line in log.splitlines() if 'HELD649 next=98' in line),
                  stop='PASS643 gen=97 STOP')
    (out / 'result.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('board','out','bin'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    test(args.board.resolve(),args.out.resolve(),args.bin.resolve())
