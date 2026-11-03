# SPDX-License-Identifier: MIT
"""Reference of a pre-command coherent output snapshot, not a deployed protocol.

Source FETCH carries a separate input identity. Its contract is in583 results.
This checker does not stand in for FPGA CDC/STOP or independent DMA checks.
"""
import struct
from dataclasses import dataclass, field
from nes_abi582 import crc

FORMAT = struct.Struct('<BBHII6H12s12sH')
assert FORMAT.size == 50


def snapshot(epoch=1, serial=1, generation=905, sequence=1, accepted=0,
             retired=0, plan=0, flags=0, ack=bytes(12), bulk=bytes(12), reserved=0):
    b = FORMAT.pack(0x83, 1, flags, epoch, serial, generation, sequence,
                    accepted, retired, plan, reserved, ack, bulk, 0)
    return b[:-2] + struct.pack('<H', crc(b[:-2]))


@dataclass
class Receiver:
    epoch: int = 1
    serial: int = 1
    generation: int = 905
    sent: int = 0
    plan_sent: int = 0
    accepted: int = 0
    retired: int = 0
    plan: int = 0
    sequence: int | None = None
    previous: bytes = b''
    expected_ack: dict = field(default_factory=dict)
    bulk: bytes = bytes(12)
    bulk_until: int | None = None
    stopped: bool = False

    def stop(self):
        self.stopped = True

    def observe(self, b):
        assert not self.stopped and len(b) == 50 and crc(b[:-2]) == int.from_bytes(b[-2:], 'little')
        magic, version, flags, epoch, serial, gen, seq, a, r, p, reserved, ack, bulk, _ = FORMAT.unpack(b)
        assert (magic, version, epoch, serial, gen, reserved) == (0x83, 1, self.epoch, self.serial, self.generation, 0)
        assert flags & ~15 == 0  # fault/STOP snapshots never publish progress
        assert not (flags & 8 and flags & 2)
        if self.sequence is not None:
            if seq == self.sequence:
                assert b == self.previous
                return False
            assert 0 < ((seq - self.sequence) & 65535) < 32768
        assert ((self.sent - self.accepted) & 65535) <= 4
        assert ((a - self.accepted) & 65535) <= ((self.sent - self.accepted) & 65535)
        assert ((r - self.retired) & 65535) <= ((a - self.retired) & 65535) <= 4
        assert ((a - r) & 65535) <= 4
        assert ((self.plan_sent - self.plan) & 65535) < 32768
        assert ((p - self.plan) & 65535) <= ((self.plan_sent - self.plan) & 65535)
        if flags & 1:
            assert r in self.expected_ack and ack == self.expected_ack[r]
        else:
            assert ack == bytes(12) and r == self.retired
        token = int.from_bytes(bulk[8:12], 'little')
        prior_token = int.from_bytes(self.bulk[8:12], 'little')
        pending = self.bulk_until is not None and ((r - self.bulk_until) & 65535) >= 32768
        if flags & 2:
            # Full kind/bank/span semantics remain with the existing bulk validator.
            assert bulk[0] == 1 and token != 0
            assert token >= prior_token and (token != prior_token or bulk == self.bulk)
            assert token == prior_token or not pending
        else:
            assert bulk == bytes(12)
        if flags & 8: assert not pending  # END never substitutes for actual consumption
        self.accepted, self.retired, self.plan = a, r, p
        self.sequence, self.previous = seq, b
        if flags & 2: self.bulk = bulk
        return True
