# SPDX-License-Identifier: MIT
"""Audit frozen181 traces; prototype packed colors OFFLINE, never emit firmware.

The ingress and client fixtures are different scenes. Their times must not be
added as an end-to-end measurement. SPI times are optimistic lower bounds.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDTHS = (2, 1, 7, 4, 7, 1, 2, 8)
SPI_HZ = 2_625_000


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pack_colors(colors, generation):
    """Experimental96-bit records: kind7/index4096+start/count4+colors60.

    Not allocated in any production protocol. A future paired version MUST
    negotiate this; old1811/1812 receivers must never receive these records.
    """
    if not 0 <= generation < 65536 or len(colors) > 1792:
        raise ValueError('generation/capacity')
    if any(not 0 <= c < 64 for c in colors):
        raise ValueError('color')
    out = []
    for start in range(0, len(colors), 10):
        group = colors[start:start + 10]
        value = (len(group) << 60) | sum(c << (6*i) for i, c in enumerate(group))
        out.append((7 << 93) | (generation << 77) | ((4096+start) << 64) | value)
    return out


def unpack_colors(records, count, generation):
    if not 0 <= count <= 1792 or not 0 <= generation < 65536:
        raise ValueError('descriptor')
    colors = []
    for record in records:
        if not 0 <= record < (1 << 96):
            raise ValueError('record width')
        kind, gen, index = record >> 93, (record >> 77) & 65535, (record >> 64) & 8191
        value = record & ((1 << 64)-1)
        n, payload = value >> 60, value & ((1 << 60)-1)
        if kind != 7 or gen != generation or index != 4096 + len(colors):
            raise ValueError('ownership/order')
        if not 1 <= n <= 10 or n != min(10, count-len(colors)) or payload >> (6*n):
            raise ValueError('count/padding')
        colors.extend((payload >> (6*i)) & 63 for i in range(n))
    if len(colors) != count:
        raise ValueError('incomplete')
    return colors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workspace', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    a.workspace = a.workspace.resolve()
    a.out.mkdir(parents=True, exist_ok=False)
    pins = {}

    def pin(p):
        pins[p.relative_to(a.workspace).as_posix()] = sha(p)
        return p

    wire = json.loads(pin(ROOT/'analysis/wire181-verification.json').read_bytes())['wire']
    ingress = []
    for old in wire['cases']:
        d = a.workspace/f"probes/nes-wire181/evidence/test02/patch{old['patches']}"
        rp, tp = pin(d/'records.hex'), pin(d/'transactions.txt')
        assert sha(rp) == old['records_sha256'] and sha(tp) == old['transactions_sha256']
        records = [int(s, 16) for s in rp.read_text().splitlines()]
        assert len(records) == old['records']
        raw, after_chr, record_bytes = [], False, 0
        by_kind = [0]*8
        for r in records:
            k, index, value = r >> 93, (r >> 64) & 8191, r & ((1 << 64)-1)
            assert ((r >> 77) & 65535) == 12
            by_kind[k] += 1
            record_bytes += 4+WIDTHS[k]
            if k == 7 and index == 4:
                after_chr = True
            elif k == 6 and after_chr:
                assert index == len(raw) and value < 64
                raw.append(value)
        assert len(raw) == old['pixels']
        packed = pack_colors(raw, 12)
        assert unpack_colors(packed, len(raw), 12) == raw
        tx_bytes = 0
        for line in tp.read_text().splitlines():
            n, tx, rx = line.split()
            assert len(bytes.fromhex(tx)) == len(bytes.fromhex(rx)) == int(n)
            tx_bytes += int(n)
        assert tx_bytes == old['wire_bytes']
        ingress.append(dict(rows=old['patches'], pixels=len(raw), records_by_kind=by_kind,
            record_bytes=record_bytes, wire_bytes=tx_bytes,
            framing_poll_bytes=tx_bytes-record_bytes,
            bit_time_lower_ms=tx_bytes*8000/SPI_HZ,
            prior_rtl_model_ms=old['modeled_cycles']/84000,
            raw_record_bytes=6*len(raw), packed_raw_record_bytes=12*len(packed),
            packed_all_records_lower_bytes=record_bytes-6*len(raw)+12*len(packed)))

    # Payload extrema, every tail length, and invalid ownership/truncation.
    for n in (0, 1, 9, 10, 11, 255, 256, 1792):
        for shift in range(64):
            colors = [(i+shift)&63 for i in range(n)]
            assert unpack_colors(pack_colors(colors, 65535), n, 65535) == colors
    good = pack_colors([63]*11, 12)
    invalid = [([], 11, 12), (good[:-1], 11, 12), (good+good[-1:], 11, 12),
               (good, 11, 13), (good[::-1], 11, 12),
               ([good[0] ^ (1 << 93)] + good[1:], 11, 12),
               ([good[0] & ~((15) << 60)] + good[1:], 11, 12),
               ([good[0] | (15 << 60)] + good[1:], 11, 12),
               (good[:-1] + [good[-1] | (1 << 6)], 11, 12)]
    for args in invalid:
        try:
            unpack_colors(*args)
        except ValueError:
            continue
        raise AssertionError('malformed packed record accepted')

    # Actual C sink request bytes from the real65816/filebus client test.
    d = a.workspace/'probes/nes-client181/evidence/test05/normal'
    prior = json.loads(pin(d/'consumer-result.json').read_bytes())
    assert prior['passed'] and prior['commits'] == 7 and prior['acks'] == 275
    frames, current, previous_sections = [], None, None
    reqs = sorted(d.glob('req-*.bin'))
    assert len(reqs) == 275
    for ordinal, p in enumerate(reqs, 1):
        assert p.name == f'req-{ordinal:04d}.bin'
        b = pin(p).read_bytes()
        ack = pin(d/p.name.replace('req-', 'ack-')).read_bytes()
        assert ack == bytes([1 if b[0] == 3 else 0, b[0]]) + b[2:10] + bytes.fromhex('659a')
        u16 = lambda offset: int.from_bytes(b[offset:offset+2], 'little')
        assert len(b) == 16+u16(12)
        op, section, gen = b[0], b[1], u16(8)
        if op == 1:
            assert current is None
            current = dict(generation=gen, packets=0, request_bytes=0, sections={})
        assert current is not None and gen == current['generation'] and u16(2) == current['packets']
        current['packets'] += 1
        current['request_bytes'] += len(b)
        if op == 2:
            buf = current['sections'].setdefault(section, bytearray())
            assert u16(10) == len(buf)
            buf.extend(b[16:])
        if op == 3:
            sections = current.pop('sections')
            assert len(b) == 40 and u16(36) == 0x1812
            assert [len(sections.get(i, b'')) for i in range(6)] == [u16(16+2*i) for i in range(6)]
            current['raw_rows'] = u16(38)
            current['section_bytes'] = {str(k): len(v) for k, v in sections.items()}
            current['same_section_bytes_as_previous'] = sections == previous_sections
            previous_sections = sections
            # E0 before/E1 command+CRC/E0 successful first ACK; extra polls excluded.
            lower = current['request_bytes'] + 35*current['packets']
            current['spi_min_bytes'] = lower
            current['spi_min_ms_including_8us_per_transaction'] = lower*8000/SPI_HZ + current['packets']*3*.008
            frames.append(current)
            current = None
    assert current is None and len(frames) == 7 and frames[4]['same_section_bytes_as_previous']

    sources = ['src/nes/firmware/nes_native_sink181.c', 'src/nes/firmware/nes_sink_spi165.c',
               'src/nes/firmware/nes_sink_trace168.c',
               'src/nes/firmware/nes_native_runtime165.c', 'src/nes/video/nes_native_export181.sv',
               'tools/nes_client181.py', 'tests/nes-functional/client181_host.c',
               'tests/nes-functional/wire181_source.svh', 'tools/nes_cadence181.py']
    for name in sources:
        pin(ROOT/name)
    for name in ('nes_native165_bulk.inc', 'nes_runtime_board165.inc'):
        pin(a.workspace/'probes/nes-board181/arm02/src'/name)
    fetch = pin(a.workspace/'probes/nes-replyjoin181/evidence/map02/nes_native_fetch165.sv').read_text()
    assert 'scanline==7 && dot==257' in fetch and 'scanline==232 && dot==1' in fetch
    assert '!owned && !retiring' in fetch and 'scrub==8191' in fetch
    bulk = (a.workspace/'probes/nes-board181/arm02/src/nes_native165_bulk.inc').read_text()
    assert '84000000' in bulk and '(4u<<SPI_CR1_BR_Pos)' in bulk
    assert bulk.count('io->wait_us(io->ctx,2)') == 4
    result = dict(passed=True, scope='Frozen fixture audit + OFFLINE codec only; no RTL/C endpoint implementation, FIT, firmware, hardware or FPS pass.',
        spi_hz=SPI_HZ, target_hz=60, shared_bus_bytes_per_period=SPI_HZ/8/60,
        ingress=ingress, client=frames, codec_roundtrips=512, codec_negative_cases=len(invalid),
        capture_model=dict(lines=262, dots_per_line=341, start=[7,257], end=[232,1],
            capture_dots=76469, next_start_gap_dots=12873,
            next_start_gap_ms_at_60hz=12873/(262*341)*1000/60,
            warning='Reference raster model only; exporter COMMIT release and MCU display ACK release are different. No measured FPS inferred.'),
        source_and_evidence_sha256=pins)
    (a.out/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k != 'source_and_evidence_sha256'}, indent=2))


if __name__ == '__main__':
    main()
