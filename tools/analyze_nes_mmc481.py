# SPDX-License-Identifier: MIT
"""Bind481 read-only boot diagnostic; physical startup remains unproven."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
from nes_cf68_pair_preflight import encode, decode

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf8'))
p = argparse.ArgumentParser(description=__doc__)
for n in ['candidate', 'board', 'arm', 'bootbus', 'status', 'assembly', 'out']:
    p.add_argument('--'+n, required=True, type=Path)
p.add_argument('--programmer480', required=True, type=Path)
a = p.parse_args()
prep = read(a.candidate/'preparation.json')
for n, h in prep['board_inputs'].items():
    assert sha(a.board/n) == h, n
for n, h in prep['ARM_patch'].items():
    assert sha(a.arm/'src'/n) == h, n
old = read(ROOT/'analysis/mmc479-verification.json')
programmer480 = read(a.programmer480/'result.json')
delivered480 = read(ROOT/'analysis/mmc480-verification.json')
assert programmer480['passed'] and programmer480['image_sha256'] == delivered480['FPGA']['BI3_SHA256']
for n, h in old['native476_unchanged'].items():
    assert sha(a.arm/'src'/n) == h, n
for f in ['nes_h1_stm32.c', 'nes_rom_verify.c']:
    assert sha(a.arm/'src'/f) == sha(ROOT.parent/'probes/nes-mmc480/executed/ARM01/src'/f)
boot = read(a.bootbus/'result.json')
status = read(a.status/'result.json')
assert boot['passed'] and boot['reads'] == 4100 and status['passed'] and status['flag_combinations'] == 256
for n, h in prep['board_inputs'].items():
    assert sha(a.bootbus/n) == h, n
assert status['source_SHA256'] == sha(a.arm/'src/nes_run136.inc')
for name in ['map', 'fit']:
    assert 'Successful' in (a.board/f'output_files/board.{name}.summary').read_text(encoding='utf8')
fit_text = (a.board/'output_files/board.fit.summary').read_text(encoding='utf8')
labels = {'LE': 'Total logic elements', 'comb': 'Total combinational functions',
          'FF': 'Dedicated logic registers', 'RAM_bits': 'Total memory bits'}
fit = {k: int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)', fit_text)[1].replace(',', '')) for k, label in labels.items()}
timing = {}
worst_paths = {}
for view in ['implementation', 'nominal']:
    rows = list(csv.DictReader((a.board/(view+'-paths204.tsv')).open(encoding='utf8'), delimiter='\t'))
    timing[view] = {k: min(float(x['slack']) for x in rows if x['kind'] == k and ((x['from_clock']=='nes') == (x['to_clock']=='nes'))) for k in ['setup', 'hold']}
    worst_paths[view] = {k: min((x for x in rows if x['kind'] == k and ((x['from_clock']=='nes') == (x['to_clock']=='nes'))), key=lambda x: float(x['slack'])) for k in ['setup', 'hold']}
ready = all(v >= 0 for view in timing.values() for v in view.values())
program = bytes.fromhex((a.board/'sink-program.hex').read_text(encoding='utf8'))
assert hashlib.sha256(program).hexdigest() == boot['program_SHA256'] == 'f96338528a1c88ae655ef1dcc48b410374ab3abfb6b5329f5fed1e9424fa85ca'
assert len(program) == 4096
mifs = list((a.board/'db').glob('board.ram0_nes_sink_bus165*.hdl.mif'))
assert len(mifs) == 1
values = dict((int(i), int(x, 2)) for i, x in re.findall(r'^\s*(\d+)\s*:\s*([01]{8})\s*;', mifs[0].read_text(encoding='utf8'), re.M))
assert set(values) == set(range(4096)) and bytes(values[i] for i in range(4096)) == program
raw = (a.board/'output_files/board.rbf').read_bytes()
packed = encode(raw)
assert decode(packed) == raw
a.assembly.mkdir(parents=True, exist_ok=False)
(a.assembly/'fpga_mmc481.bi3').write_bytes(packed)
fw = a.arm/'src/obj-nes-100/firmware.stm'
assert fw.stat().st_size <= 212992
for marker in [b'NES MMC3 481.nh1', b'mmc481.nes', b'fpga_mmc481.bi3',
               b'nes-progress-mmc481.txt', b'nes-budget-mmc481.txt', b'nes-game-last-mmc481.txt', b'board_expected_hex=7a']:
    assert marker in fw.read_bytes(), marker
sys.path.insert(0, str(ROOT.parent/'.tools/arm259-python'))
from elftools.elf.elffile import ELFFile
def allocated(p):
    with p.open('rb') as f:
        return {s.name: hashlib.sha256(s.data()).hexdigest() for s in ELFFile(f).iter_sections() if s['sh_flags']&2}
obj = a.arm/'src/obj-nes-100'
base = ROOT.parent/'probes/nes-mmc480/executed/ARM01/src/obj-nes-100'
changed = [q.relative_to(obj).as_posix() for q in obj.rglob('*.o') if allocated(q) != allocated(base/q.relative_to(obj))]
assert set(changed) == {'nes_h1_stm32.o', 'nes_rom_verify.o', 'nes_menu_diagnostic.o', 'nes_checkpoint112.o'}, changed
r = {'passed': True, 'scope': __doc__, 'candidate': 'MMC481 boot diagnostic',
     'diagnostic_trial_ready': ready, 'hardware_verified': False, 'root_cause_confirmed': False,
     'physical_FPS': None, 'profile_hex': '7a', 'status_version': 3,
     'whole_board_inputs': prep['board_inputs'], 'ARM_patch': prep['ARM_patch'],
     'ARM_objects_changed': changed, 'ARM': {'firmware_SHA256': sha(fw), 'bytes': fw.stat().st_size,
          'text': 202313, 'data': 10040, 'BSS': 18552, 'Flash_tail': 212992-fw.stat().st_size,
          'RUN_workspace': 31848, 'full_stack_proof': False},
     'FPGA': {'RBF_SHA256': sha(a.board/'output_files/board.rbf'), 'BI3_SHA256': sha(a.assembly/'fpga_mmc481.bi3'),
              'program_SHA256': boot['program_SHA256'], 'fitted_MIF_matches_program': True},
     'FIT': fit, 'delta_vs479': {k: fit[k]-old['FIT'][k] for k in fit},
     'related_timing_ns': timing, 'related_worst_paths': worst_paths, 'full_CDC_IO_signoff': False,
     'bootbus': boot, 'status_parser': status, 'delivered480_programmer': programmer480, 'diagnostic_flags': prep['flags'],
     'sampling_limit': prep['upper_flags'], 'timeout_ticks_unchanged': 500,
     'preserved_candidates': {'candidate01_board01': 'hardware event latches: related setup -0.034ns; rejected',
                             'candidate02_board02': 'targeted stricter loader path budget: different path -0.491ns; rejected; not retained in candidate03 SDC',
                             'candidate03_board03': 'SPI snapshot + ARM accumulation; see related timing; do not package unless diagnostic_trial_ready'},
     'preserved_harness_failures': ['programmer01 sandbox GCC DLL load error; actual test run elevated in fresh directory',
                                  'bootbus02 searched old480 library before newly compiled modules; fixed library binding in03/04',
                                  'board01 external Tcl path contains Korean; local ASCII copy executed unchanged'],
     'limits': ['No physical startup repair proven', 'Bootbus is pin transactions with ideal PLL/ROM and seeded verified loader, not physical timing or 65816 execution',
                'Existing480 pixels/live DMA/CRC/coverage/STOP evidence is prior evidence; no new full game run claimed',
                'Snapshot upper flags are sampled and ORed by ARM; zero does not prove no short physical pulse'],
     'next': 'If not ready, withhold481 and review the measured failing path before further implementation/FIT; physical boot cause remains unknown. No seed/constraint waiver search.'}
a.out.write_text(json.dumps(r, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print(json.dumps({'diagnostic_trial_ready': ready, 'FIT': fit, 'related_timing_ns': timing, 'ARM_objects_changed': changed}))
