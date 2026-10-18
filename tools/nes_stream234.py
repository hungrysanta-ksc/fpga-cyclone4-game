# SPDX-License-Identifier: MIT
"""Single-forward-read source algorithm and END-count wire specification.

Executable memory-access model, not RTL, a cycle model, or production SPI.
Only Memory owns the old image. The current image is an immutable fixture
behind a query port. The encoder cannot index either full image directly.
"""
import binascii, struct

SIZE = 5741


def crc(b, seed=0xffff):
    return binascii.crc_hqx(b, seed)


class Memory:
    def __init__(self, old, current):
        assert len(old) == len(current) == SIZE
        self.base = bytearray(old)
        self.current = current
        self.cursor = self.reads = self.queries = self.writes = 0
        self.max_fetch = 0
        self.full = False

    def fetch(self, at, n):
        assert at == self.cursor and 0 < n <= 66 and at+n <= SIZE
        self.cursor += n
        self.reads += n
        self.queries += n
        self.max_fetch = max(self.max_fetch, n)
        old, new = bytes(self.base[at:at+n]), self.current[at:at+n]
        self.writes += n if self.full else sum(a != b for a, b in zip(old, new))
        # Speculative base update: any abort invalidates this entire base.
        self.base[at:at+n] = new
        return old, new


class Literals:
    """Online coalescing of <=3-byte gaps; no change-index list or rescan."""
    def __init__(self, emit):
        self.emit = emit
        self.data = bytearray()
        self.at = self.used = self.gap = self.peak = 0

    def flush(self):
        if self.used:
            b = bytes(self.data[:self.used])
            self.emit(self.at, len(b), struct.pack('<HB', self.at, len(b))+b)
        self.data.clear()
        self.used = self.gap = 0

    def byte(self, at, old, new):
        if old == new:
            if not self.data:
                return
            self.gap += 1
            if self.gap > 3 or len(self.data) == 240:
                self.flush()
                return
            self.data.append(new)
        else:
            if len(self.data) == 240:
                self.flush()
            if not self.data:
                self.at = at
            self.data.append(new)
            self.used = len(self.data)
            self.gap = 0
        self.peak = max(self.peak, len(self.data))


def records(mem, cold, emit):
    """emit must accept/hold a record before the producer advances.

    Scratch capacity: row pair132 + literal240 + cheap-raster12 + mask8
    + pending record243 =635 bytes; conservative non-aliased upper bound.
    Scalars/address counters and physical RAM ports need a separate RTL fit.
    """
    mem.full = cold
    if cold:
        # Bounded 240-byte staging, not the complete geometry.
        for at in range(0, SIZE, 240):
            b = bytearray()
            for i in range(at, min(at+240, SIZE)):
                _, new = mem.fetch(i, 1)
                b += new
            emit(at, len(b), struct.pack('<HB', at, len(b))+b)
        assert mem.cursor == SIZE and mem.writes == SIZE and mem.base == mem.current
        return
    lit = Literals(emit)
    for at in range(0, 2112, 66):
        old, new = mem.fetch(at, 66)
        if old == new:
            continue
        if old[2:] == new[:-2]:
            emit(at, 66, struct.pack('<HBBB', at, 0, 2, 1)+new[-2:])
        elif old[:-2] == new[2:]:
            emit(at, 66, struct.pack('<HBBB', at, 0, 2, 255)+new[:2])
        else:
            for i, (a, b) in enumerate(zip(old, new)):
                lit.byte(at+i, a, b)
            lit.flush()
    for at in range(2112, 3872):
        a, b = mem.fetch(at, 1)
        lit.byte(at, a[0], b[0])
    lit.flush()
    # Retain cheap literal encoding only while its cost is <13 bytes.
    # Once it reaches13, a constant mask plus row count is sufficient.
    pending = []
    cost = 0
    expensive = False

    def cheap(at, n, b):
        nonlocal cost, expensive
        cost += len(b)
        if cost >= 13:
            expensive = True
            pending.clear()
        elif not expensive:
            pending.append((at, n, b))

    small = Literals(cheap)
    mask = rows = start = 0

    def finish():
        nonlocal cost, expensive, rows
        if rows and mask:
            small.flush()
            if expensive:
                emit(start, rows*8, struct.pack('<HBBBQ', start, 0, 1, rows, mask))
            else:
                for r in pending:
                    emit(*r)
        pending.clear()
        cost = 0
        expensive = False
        rows = 0

    for at in range(3872, 5664, 8):
        old, new = mem.fetch(at, 8)
        next_mask = int.from_bytes(old, 'little') ^ int.from_bytes(new, 'little')
        if next_mask != mask:
            finish()
            mask, start = next_mask, at
        rows += 1
        if mask and not expensive:
            for i, (a, b) in enumerate(zip(old, new)):
                small.byte(at+i, a, b)
                if cost + (3+small.used if small.used else 0) >= 13:
                    expensive = True
                    pending.clear()
                    small.data.clear()
                    small.used = small.gap = 0
                    break
    finish()
    for at in range(5664, SIZE):
        a, b = mem.fetch(at, 1)
        lit.byte(at, a[0], b[0])
    lit.flush()
    assert mem.cursor == SIZE and mem.base == mem.current


def encode(old, new, raw, serial, generation, epoch=1):
    """Returned packet list is a test collector, not producer frame storage."""
    cold = serial == 1
    mem = Memory(old, new)
    packets = [struct.pack('<2sBBIIIHH', b'N4', 1, int(cold), epoch,
                           0 if cold else serial-1, serial, generation, 0)]
    checksum = crc(packets[0])
    spans = expanded = 0

    def emit(at, n, b):
        nonlocal checksum, spans, expanded
        assert len(b) <= 243
        packets.append(b)
        checksum = crc(b, checksum)
        spans += 1
        expanded += n

    records(mem, cold, emit)
    trailer = struct.pack('<HBBHH', 0xffff, 0, 3, spans, expanded)
    checksum = crc(trailer, checksum)
    packets.append(trailer+struct.pack('<H', checksum))
    for at in range(0, len(raw), 240):
        b = raw[at:at+240]
        p = struct.pack('<HB', at, len(b))+b
        packets.append(p)
        checksum = crc(p, checksum)
    trailer = struct.pack('<HBB', 0xffff, 0, 4)
    checksum = crc(trailer, checksum)
    packets.append(trailer+struct.pack('<H', checksum))
    return packets, dict(base_reads=mem.reads, current_byte_queries=mem.queries,
                         changed_base_writes=mem.writes, max_fetch=mem.max_fetch,
                         spans=spans, expanded_bytes=expanded)
