"""Time row masks from CRC-accepted E9 packets against the shared PSRAM calendar."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import nes_window924
from nes_return930 import ORIGINAL, SupplyTrace
from test_nes_raw506_joint import wire_plan


class PlanTrace(SupplyTrace):
    def __init__(self, args):
        super().__init__(args)
        self.bursts = []

    def accept(self, tx, t):
        start = self.plan_at
        result = super().accept(tx, t)
        if tx[0] == 0xe9:
            records = [wire_plan(q) for q in self.plansets[self.generation][start:self.plan_at]]
            body = b''.join(records)
            # END can be synthesized by the original consumer past the last plan.
            suffix = tx[4:-4][len(body):]
            if suffix:
                assert suffix == b'\x83'+self.generation.to_bytes(2, 'little')
                records.append(suffix)
            assert b''.join(records) == tx[4:-4] and len(records) == tx[3]
            self.bursts.append(dict(g=self.generation, seal=t, records=[q.hex() for q in records]))
        return result

    def exchange(self, seq, t, op, args):
        result = super().exchange(seq, t, op, args)
        if op == 'FINISH':
            (self.a.out/'e9931.json').write_text(json.dumps(self.bursts)+'\n')
        return result


class EarlyScan(PlanTrace):
    def row_scan_time(self, batch, scan_end, record_index):
        # Cost the complete auxiliary scan after the last byte and CDC,
        # including the other accepted records. Consumer CHECK stays in order.
        return scan_end


class SecondRecord(PlanTrace):
    """Check accepted second descriptors only for a tag already in refill."""

    def retained_batches(self, batches):
        return batches[:self.next_batch]

    def pump(self, now):
        super().pump(now)
        if self.stopped or not self.active:
            return
        batches = self.phases.get(self.owner, {}).get('banks557', [])
        for batch in self.retained_batches(batches):
            if batch['count'] < 2:
                continue
            records = self.plansets[self.owner][batch['first']:batch['first'] + 2]
            if len(records) != 2 or records[1][6] != 1:
                continue
            record = wire_plan(records[1])
            assert len(record) == 8 and record[0] == 0x81
            tag = int.from_bytes(record[5:7], 'little')
            base = 16 * tag
            if tag not in self.tags or not any(base+i in self.ready_rows for i in range(8)):
                continue
            at = self.scan_start(batch) + 20 * batch['count']
            for row in range(8):
                address = base + row
                if not (record[7] & (1 << row)) or address in self.ready_rows:
                    continue
                grant, reply = self.original_select(max(at, self.free))
                if grant >= now:
                    return
                self.free = reply + 1
                self.ready_rows[address] = (reply, self.chr[address], self.chr[address+8])
                self.spec.append((self.owner, address, grant, reply))


class LatestRecord(SecondRecord):
    """One second-descriptor latch, replaced at the next valid E9."""

    def retained_batches(self, batches):
        return batches[self.next_batch-1:self.next_batch] if self.next_batch else []


MODES = {'base': PlanTrace, 'scan': EarlyScan, 'second': SecondRecord, 'latest': LatestRecord}


def run(temp, phase, cold, mode):
    with patch.object(nes_window924, 'LeadingRecord', MODES[mode]):
        nes_window924.replay(temp, 'objheader', phase, cold, arm=ORIGINAL, edition=925,
                             tag='931'+mode, trace_last=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=MODES)
    p.add_argument('temp', type=Path)
    p.add_argument('phase', type=int, choices=(1, 2))
    p.add_argument('--cold', action='store_true')
    a = p.parse_args()
    run(a.temp, a.phase, a.cold, a.mode)
