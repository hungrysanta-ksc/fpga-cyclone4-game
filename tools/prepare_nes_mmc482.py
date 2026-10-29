# SPDX-License-Identifier: MIT
"""Factor blocked-command error capture after decode, preserving every prior code.

Based on481 snapshot diagnostics. No extra cycle, latch, timeout/CRC bypass,
clock/SDC/seed change or claim of a physical startup repair.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

def transform(s):
    begin = s.index(' // 217: mutually exclusive error classes,')
    end = s.index(' // Each destination is selected independently;', begin)
    block = s[begin:end]
    assert block.count('!commands_blocked &&') == 4
    block = block.replace('!commands_blocked && ', '')
    block = block.replace('wire err5=command_conflict;', '''wire err5=(load_begin && (load_end || start || stop || load_valid)) ||
           (load_end && (start || stop || load_valid)) || (start && (stop || load_valid));''')
    assert block.count('(commands_blocked || !(load_begin || load_end || start))') == 1
    block = block.replace('(commands_blocked || !(load_begin || load_end || start))', '!(load_begin || load_end || start)')
    block = block.replace('  else if(!fault)begin\n', '''  else if(!fault)begin
   //482 Blocked commands can only add a timed WRITE/HOLD STOP error6.
   // Otherwise preserve the entire prior code, including unused bit3.
   // The late check_failed signal selects here, after unblocked decoding.
   if(commands_blocked)begin
    if(stop && (phase[WRITE] || phase[HOLD]))error_code<=4'd6;
   end else begin
''')
    assert block.count('  end\n end\n') == 1
    block = block.replace('  end\n end\n', '   end\n  end\n end\n')
    return s[:begin] + block + s[end:]

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ['board', 'arm', 'out']:
        p.add_argument('--'+n, required=True, type=Path)
    a = p.parse_args()
    old = json.loads((ROOT/'analysis/mmc481-verification.json').read_text(encoding='utf8'))
    for n, h in old['whole_board_inputs'].items():
        assert sha(a.board/n) == h, n
    for n, h in old['ARM_patch'].items():
        assert sha(a.arm/n) == h, n
    a.out.mkdir(parents=True, exist_ok=False)
    b = a.out/'board'
    b.mkdir()
    for n in [*old['whole_board_inputs'], 'board.qpf']:
        dest = b/n
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(a.board/n, dest)
    q = b/'nes_rom_loader.sv'
    q.write_text(transform(q.read_text(encoding='utf8')), encoding='utf8', newline='\n')
    q = b/'nes_rom_spi.sv'
    s = q.read_text(encoding='utf8')
    assert s.count("8'h7a,flags") == 2
    q.write_text(s.replace("8'h7a,flags", "8'h7b,flags"), encoding='utf8', newline='\n')
    patch = a.out/'arm'
    patch.mkdir()
    for n in old['ARM_patch']:
        s = (a.arm/n).read_text(encoding='utf8')
        s = s.replace('mmc481', 'mmc482').replace('MMC481', 'MMC482').replace('MMC3 481', 'MMC3 482')
        s = s.replace('board_expected_hex=7a', 'board_expected_hex=7b').replace('BOARD_ID 0x7a', 'BOARD_ID 0x7b')
        (patch/n).write_text(s, encoding='utf8', newline='\n')
    r = {'scope': __doc__, 'base481': old['whole_board_inputs'],
         'board_inputs': {n: sha(b/n) for n in old['whole_board_inputs']},
         'ARM_patch': {q.name: sha(q) for q in patch.iterdir()},
         'profile_hex': '7b', 'status_version': 3, 'hardware': False,
         'unchanged_SDC': sha(b/'board.sdc'), 'root_cause_confirmed': False}
    (a.out/'preparation.json').write_text(json.dumps(r, indent=2)+'\n', encoding='utf8')
    print(json.dumps({'prepared': True, 'profile': '7b', 'error_capture_only': True}))
