"""Replay the first-screen guard with extra pending E0 reads while input is received."""
import json
from unittest.mock import patch

import check_nes_sram897 as guard
from check_nes_menu533 import check
from nes_raw506 import sha
from replay_nes_ack902 import WORK


class CreditReplay(guard.GameReplay):
    def exchange(self, cpu, tx, rx, n):
        request = bytes(cpu.mem_read(tx, n))
        wanted, _ = self.rows[self.index]
        if request != wanted and request[0] == 0xe0 and wanted[0] == 0xd1:
            # D1/D2 do not mutate the output queue. Allow a repeated *pending*
            # SEAL status from this recording, never synthesize a final ACK.
            seal = next(i for i, (t, _) in enumerate(self.rows) if t[:2] == b'\xe1\x03')
            pending = next(i for i in range(seal+1, len(self.rows)) if self.rows[i][0][0] == 0xe0)
            status, reply = self.rows[pending]
            assert seal < self.index and request == status and not self.retired
            assert self.rows[self.index-1][0][0] == 0xd0
            assert reply[2] & 1 and reply[3:5] != reply[5:7]
            self.rows.insert(self.index, (status, reply))
        return super().exchange(cpu, tx, rx, n)


if __name__ == '__main__':
    src = WORK/'link/src'
    with patch.object(guard,'GameReplay',CreditReplay):
        cases, ram, sp = guard.check_game_path(src)
    result = dict(firmware=sha(src/'obj-nes-100/firmware.stm'), D0=hex(ram), entry=hex(sp),
                  cases=cases, menu=check(src,'897'))
    (WORK/'guards.json').write_text(json.dumps(result, indent=2)+'\n')
