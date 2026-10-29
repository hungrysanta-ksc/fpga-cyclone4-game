# SPDX-License-Identifier: MIT
"""Bind482 same-edge error fix, diagnostics, exact build and limited trial gates."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from analyze_nes_mmc479 import resources

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf8'))
p = argparse.ArgumentParser(description=__doc__)
for n in ['candidate', 'board', 'arm', 'loader', 'host', 'bootbus', 'assembly', 'programmer', 'out']:
    p.add_argument('--'+n, required=True, type=Path)
a = p.parse_args()
prep = read(a.candidate/'preparation.json')
prior = read(ROOT/'analysis/mmc481-verification.json')
base = read(ROOT/'analysis/mmc479-verification.json')
for n, h in prep['board_inputs'].items():
    assert sha(a.board/n) == sha(a.bootbus/n) == h, n
assert sha(a.board/'board.sdc') == prep['unchanged_SDC'] == base['whole_board_inputs']['board.sdc']
changes = [n for n in prep['board_inputs'] if prep['board_inputs'][n] != prep['base481'][n]]
assert set(changes) == {'nes_rom_loader.sv', 'nes_rom_spi.sv'}
for n, h in prep['ARM_patch'].items():
    assert sha(a.arm/'src'/n) == h, n
for n, h in base['native476_unchanged'].items():
    assert sha(a.arm/'src'/n) == h, n
loader, host, boot, assembly, programmer = [read(q/'result.json') for q in [a.loader, a.host, a.bootbus, a.assembly, a.programmer]]
assert all(r['passed'] for r in [loader, host, boot, assembly, programmer])
assert loader['states'] == 294912 and loader['prior_code_cases'] == 131072
assert loader['old_SHA256'] == prep['base481']['nes_rom_loader.sv']
assert loader['new_SHA256'] == sha(a.board/'nes_rom_loader.sv')
assert host['cases'] == 22 and host['full_payload_compared'] == 393216
for key, n in [('loader_sha256', 'nes_h1_stm32.c'), ('verify_sha256', 'nes_rom_verify.c'), ('run136_sha256', 'nes_run136.inc')]:
    assert host[key] == sha(a.arm/'src'/n), n
assert boot['reads'] == 4100 and boot['profile_hex'] == '7b'
assert programmer['image_sha256'] == assembly['BI3_SHA256'] == sha(a.assembly/'fpga_mmc482.bi3')
assert programmer['rbf_sha256'] == assembly['RBF_SHA256'] == sha(a.board/'output_files/board.rbf')
assert assembly['fit_report_SHA256'] == sha(a.board/'output_files/board.fit.rpt')
program = bytes.fromhex((a.board/'sink-program.hex').read_text(encoding='utf8'))
assert hashlib.sha256(program).hexdigest() == boot['program_SHA256'] == prior['FPGA']['program_SHA256']
mifs = list((a.board/'db').glob('board.ram0_nes_sink_bus165*.hdl.mif'))
assert len(mifs) == 1
values = {int(i): int(x, 2) for i, x in re.findall(r'^\s*(\d+)\s*:\s*([01]{8})\s*;', mifs[0].read_text(encoding='utf8'), re.M)}
assert len(values) == 4096 and bytes(values[i] for i in range(4096)) == program
fit = resources(a.board/'output_files/board.fit.summary')
timing, paths = {}, {}
for view in ['implementation', 'nominal']:
    rows = list(csv.DictReader((a.board/(view+'-paths204.tsv')).open(encoding='utf8'), delimiter='\t'))
    paths[view] = {k: min((x for x in rows if x['kind'] == k and ((x['from_clock']=='nes') == (x['to_clock']=='nes'))), key=lambda x: float(x['slack'])) for k in ['setup', 'hold']}
    timing[view] = {k: float(x['slack']) for k, x in paths[view].items()}
assert all(v >= 0 for view in timing.values() for v in view.values())
sys.path.insert(0, str(ROOT.parent/'.tools/arm259-python'))
from elftools.elf.elffile import ELFFile
def allocated(p):
    with p.open('rb') as f:
        return {s.name: hashlib.sha256(s.data()).hexdigest() for s in ELFFile(f).iter_sections() if s['sh_flags']&2}
obj = a.arm/'src/obj-nes-100'
baseline = ROOT.parent/'probes/nes-mmc480/executed/ARM01/src/obj-nes-100'
changed = [q.relative_to(obj).as_posix() for q in obj.rglob('*.o') if allocated(q) != allocated(baseline/q.relative_to(obj))]
assert set(changed) == {'nes_h1_stm32.o', 'nes_rom_verify.o', 'nes_menu_diagnostic.o', 'nes_checkpoint112.o'}
fw = obj/'firmware.stm'
for marker in [b'NES MMC3 482.nh1', b'mmc482.nes', b'fpga_mmc482.bi3', b'nes-progress-mmc482.txt', b'nes-budget-mmc482.txt', b'nes-game-last-mmc482.txt', b'board_expected_hex=7b']:
    assert marker in fw.read_bytes(), marker
assert fw.stat().st_size <= 212992
# The status function/source is byte identical to the tested481 parser.
assert sha(a.arm/'src/nes_run136.inc') == prior['status_parser']['source_SHA256']
r = {'passed': True, 'candidate': 'MMC482 boot diagnostic', 'scope': __doc__,
     'diagnostic_trial_ready': True, 'hardware_verified': False, 'root_cause_confirmed': False,
     'physical_FPS': None, 'profile_hex': '7b', 'status_version': 3,
     'whole_board_inputs': prep['board_inputs'], 'ARM_patch': prep['ARM_patch'], 'ARM_objects_changed': changed,
     'ARM': {'firmware_SHA256': sha(fw), 'bytes': fw.stat().st_size, 'text': 202313, 'data': 10040, 'BSS': 18552,
             'Flash_tail': 212992-fw.stat().st_size, 'RUN_workspace': 31848, 'full_stack_proof': False},
     'FPGA': assembly, 'FIT': fit, 'remaining_LE': 15408-fit['LE'],
     'delta_vs481': {k: fit[k]-prior['FIT'][k] for k in fit},
     'delta_vs479': {k: fit[k]-base['FIT'][k] for k in fit},
     'related_timing_ns': timing, 'related_worst_paths': paths,
     'full_CDC_IO_signoff': False, 'loader_equivalence': loader, 'host22': host,
     'bootbus': boot, 'programmer': programmer, 'reused_status_parser': prior['status_parser'],
     'snapshot_flags': prior['diagnostic_flags'], 'timeout_ticks_unchanged': 500,
     'limits': ['No physical startup repair or game FPS proven', 'Raw reset/CDC/IO remain unsigned; related timing is not full board signoff',
                'SNES ROM pin test uses seeded loader, ideal PLL/ROM and bus transactions, not actual65816 or electrical timing',
                'Host22 executes actual C/FatFS/programmer/run136 with modeled GPIO/native/observer peers',
                'Upper status flags are instantaneous samples ORed by ARM; absent bits do not prove absent short pulses; boot_last_hex precedes STOP',
                '480 full pixel/CRC/coverage/receipt/ACK evidence retained within unchanged execution source; no new full game timing run claimed'],
     'preserved_failures': ['481 candidate01..03 remain rejected; not overwritten', '482 bootbus01 tried to map absent archived work library in full-compile mode; unnecessary mapping removed, bootbus02 fresh PASS'],
     'next': 'one user-installed482 boot test; analyze boot_last_hex and STOP/base/menu before game FPS work'}
a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps({'ready': True, 'FIT': fit, 'timing': timing, 'firmware_SHA256': sha(fw)}))
