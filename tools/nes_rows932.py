"""Prefetch the confirmed continuation of an OBJ slot run across two E9 batches."""
import argparse
from pathlib import Path
from unittest.mock import patch

import nes_window924
from nes_rows931 import LatestRecord, ORIGINAL
from test_nes_raw506_joint import wire_plan


class Continuation(LatestRecord):
    first_row_only = False
    whole_run = False

    def pump(self, now):
        super().pump(now)
        if self.stopped or not self.active or self.next_batch < 2:
            return
        banks = self.phases[self.owner]['banks557']
        previous, batch = banks[self.next_batch-2:self.next_batch]
        plans = self.plansets[self.owner]
        index = batch['first']
        if previous['first'] + previous['count'] != index or batch['count'] < 3:
            return
        prior = wire_plan(plans[index-1])
        if prior[0] != 0x81:
            return
        next_slot = int.from_bytes(prior[3:5], 'little') + 1
        # Two out-of-order records may precede the contiguous slot run.
        # Only inspect records in the currently CRC-accepted generation.
        for record in plans[index+2:index+batch['count']]:
            wire = wire_plan(record)
            if wire[0] != 0x81 or int.from_bytes(wire[3:5], 'little') != next_slot:
                break
            tag = int.from_bytes(wire[5:7], 'little')
            if tag not in self.tags:
                break
            at = self.scan_start(batch) + 20 * batch['count']
            for row in range(1 if self.first_row_only else 8):
                address = 16 * tag + row
                if not (wire[7] & (1 << row)) or address in self.ready_rows:
                    continue
                grant, reply = self.original_select(max(at, self.free))
                if grant >= now:
                    return
                self.free = reply + 1
                self.ready_rows[address] = (reply, self.chr[address], self.chr[address+8])
                self.spec.append((self.owner, address, grant, reply))
            if not self.whole_run:
                break
            next_slot += 1


class FirstRow(Continuation):
    first_row_only = True


class SlotRun(Continuation):
    whole_run = True


MODES = {'row': FirstRow, 'mask': Continuation, 'run': SlotRun}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=MODES)
    p.add_argument('temp', type=Path)
    p.add_argument('phase', type=int, choices=(1, 2))
    p.add_argument('--cold', action='store_true')
    args = p.parse_args()
    with patch.object(nes_window924, 'LeadingRecord', MODES[args.mode]):
        nes_window924.replay(args.temp, 'objheader', args.phase, args.cold, arm=ORIGINAL,
                             edition=925, tag='932'+args.mode, trace_last=True)
