# SPDX-License-Identifier: MIT
"""Read-only SNES boot-pin diagnostics on480; no timeout/reset/ACK bypass.

Private board/firmware materialization. Not a claimed repair or hardware pass.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def once(s, old, new):
    assert s.count(old) == 1, old[:100]
    return s.replace(old, new)

p = argparse.ArgumentParser(description=__doc__)
for n in ['board', 'arm', 'out']:
    p.add_argument('--'+n, type=Path, required=True)
a = p.parse_args()
v = json.loads((ROOT/'analysis/mmc480-verification.json').read_text(encoding='utf8'))
pins = json.loads((ROOT/'analysis/mmc479-verification.json').read_text(encoding='utf8'))['whole_board_inputs']
for n, h in pins.items():
    assert sha(a.board/n) == h, n
a.out.mkdir(parents=True, exist_ok=False)
board = a.out/'board'
board.mkdir()
for n in [*pins, 'board.qpf']:
    q = board/n
    q.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(a.board/n, q)

def put(path, text):
    path.write_text(text, encoding='utf8', newline='\n')

q = board/'nes_screen_status151.sv'
s = q.read_text(encoding='utf8')
s = once(s, 'input wire [7:0] data_in,', 'input wire [7:0] data_in,input wire bus_drive,')
s = once(s, '// Flags: bit0 reset-vector-low read,bit1 high read,bit2 any program read.',
         '//481 Low3 flags sticky in RTL. Upper5 pins sampled per SPI73 and ORed by ARM.\n// No extra event latches, RESET/ownership feedback or pulse-capture guarantee.')
s = once(s, "snapshot<={8'he6,stage,error_code,5'd0,flags,frames,8'd2}",
         "snapshot<={8'he6,stage,error_code,bus_drive,active_sync[1],!write_n,!romsel_n,!read_n,flags,frames,8'd3}")
put(q, s)
q = board/'fxpak_nes_screen137_top.sv'
s = q.read_text(encoding='utf8')
s = once(s, '  .receive_write(status_receive),.selected(status_selected),.miso(status_miso));',
         '  .bus_drive(consumer_dir&&!consumer_oe),.receive_write(status_receive),.selected(status_selected),.miso(status_miso));')
put(q, s)
q = board/'nes_rom_spi.sv'
s = q.read_text(encoding='utf8')
assert s.count("8'h79,flags") == 2
put(q, s.replace("8'h79,flags", "8'h7a,flags"))
patch = a.out/'arm'
patch.mkdir()
for n in ['nes_menu_diagnostic.c', 'nes_checkpoint112.c', 'VERSION', 'nes_run136.inc', 'nes_mmc479.h']:
    s = (a.arm/n).read_text(encoding='utf8')
    s = s.replace('mmc480', 'mmc481').replace('MMC480', 'MMC481').replace('MMC3 480', 'MMC3 481')
    if n == 'nes_menu_diagnostic.c':
        s = once(s, 'board_expected_hex=79', 'board_expected_hex=7a')
    if n == 'nes_mmc479.h':
        s = once(s, 'BOARD_ID 0x79', 'BOARD_ID 0x7a')
    if n == 'nes_run136.inc':
        s = once(s, 'rx[1]!=0xe6||rx[7]!=2||(rx[4]&0xf8u)', 'rx[1]!=0xe6||rx[7]!=3')
        s = once(s, 'nes_run136.screen_flags=rx[4];', 'nes_run136.screen_flags|=rx[4];')
    put(patch/n, s)
r = {'scope': __doc__, 'base_board_inputs': pins,
     'board_inputs': {n: sha(board/n) for n in pins},
     'ARM_base_inputs': {q.name: sha(a.arm/q.name) for q in patch.iterdir()},
     'ARM_patch': {q.name: sha(q) for q in patch.iterdir()},
     'profile': '7a', 'status_version': 3,
     'timeout_ticks_unchanged': 500, 'ROM_unchanged': True,
     'flags': {'0': 'qualified vector-low', '1': 'qualified vector-high',
               '2': 'qualified program read', '3': 'sampled RD low',
               '4': 'sampled ROMSEL low', '5': 'sampled WR low',
               '6': 'sampled endpoint active', '7': 'sampled internal bus drive'},
     'upper_flags': 'instantaneous SPI73 snapshots accumulated by ARM; absence does not prove no short pulse',
     'hardware': False, 'root_cause_confirmed': False}
(a.out/'preparation.json').write_text(json.dumps(r, indent=2)+'\n', encoding='utf8')
print(json.dumps({'profile': '7a', 'status_version': 3, 'hardware': False}))
