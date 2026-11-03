# SPDX-License-Identifier: MIT
"""587 bounded ownership audit: linked586 semantic oracle + pinned577 RTL.

This is neither a replacement firmware nor an RTL/timing simulation. Synthetic
values only; do not publish captured ROM/geometry bytes with this report.
"""
import argparse, hashlib, json, struct
from pathlib import Path
from check_nes_combined586 import Probe
from analyze_nes_ownership585 import inventory

ROOT = Path(__file__).resolve().parents[1]
COUNTS = (66, 224, 128, 128, 224, 32)
BITS = (15, 8, 49, 32, 53, 6)
FIELDS = ('maps', 'rows', 'objects', 'exceptions', 'raster', 'palette')
WIDTHS = (2, 1, 8, 4, 8, 1)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def valid_value(k, v):
    if v >> BITS[k]: return False
    if k == 1: return v >> 3 < COUNTS[0] // 33
    if k == 3: return ((v >> 6) & 8191) < 7392
    if k == 4:
        if (v >> 49) & 1:
            return (v & ((1 << 49) - 1)) == 0 and ((v >> 50) & 7) < 2
        return v >> 49 == 0 and ((v >> 44) & 31) < COUNTS[5] // 32
    return True

def semantics(src):
    m = Probe(src, True, 128)
    layout = m.layout['nes_native165']
    def setfield(name, value, n=1):
        m.put(m.state, 'nes_native165', name, value, n)
    def reset(k):
        m.u.mem_write(m.state, bytes(layout['size']))
        setfield('state', 1); setfield('generation', 905, 2)
        setfield('base_valid586', 1)
        setfield('patch_count', 2); setfield('next_kind', k)
        m.u.mem_write(m.state + layout['counts'], struct.pack('<6H', *COUNTS))
        at = [COUNTS[j] if j < k else 0 for j in range(6)]
        m.u.mem_write(m.state + layout['at'], struct.pack('<6H', *at))
    def call(k, v, g=905, at=0):
        return bool(m.call('logical_record', [m.state, k, g, at, v & 0xffffffff, v >> 32]))
    rows = []
    extra = (15, 16, 63, 64, 8191, 8192, 7391 << 6, 7392 << 6,
             1 << 49, (1 << 49) | 1, (1 << 49) | (1 << 50),
             (1 << 49) | (2 << 50), (1 << 44) - 1)
    for k in range(6):
        good = bad = 0
        for v in sorted(set([0, (1 << 64) - 1, (1 << BITS[k]) - 1, *extra,
                             *(1 << b for b in range(64))])):
            reset(k); want = valid_value(k, v); got = call(k, v)
            assert got == want, (k, v, got, want)
            if got:
                good += 1
                stored = bytes(m.u.mem_read(m.state + layout[FIELDS[k]], WIDTHS[k]))
                assert int.from_bytes(stored, 'little') == v
                expected = bytearray(2048)
                if k in (0, 2, 3):
                    tag = v >> 19 if k == 3 else v & 8191
                    expected[tag >> 2] |= (2 if k == 2 else 1) << ((tag & 3) * 2)
                assert bytes(m.u.mem_read(m.state + layout['required'], 2048)) == expected
                assert m.get(m.state, 'nes_native165', 'records', 2) == 1
            else:
                bad += 1
                assert m.get(m.state, 'nes_native165', 'error', 1)
                assert not m.get(m.state, 'nes_native165', 'base_valid586', 1)
        rows.append(dict(kind=k, accepted=good, rejected=bad))
    # Pure value semantics accept 0; admission must still reject these contexts.
    guards = []
    for fault in ('generation', 'index', 'phase', 'state'):
        reset(0)
        if fault == 'phase': setfield('next_kind', 1)
        if fault == 'state': setfield('state', 2)
        assert valid_value(0, 0)
        assert not call(0, 0, 906 if fault == 'generation' else 905,
                        1 if fault == 'index' else 0)
        guards.append(fault)
    # Control ownership remains necessary even with a value-only executor.
    controls = []
    for fault in ('valid', 'missing_geometry', 'slot_order', 'slot_count',
                  'missing_tag_count', 'too_many_tags'):
        reset(5)
        m.u.mem_write(m.state + layout['at'], struct.pack('<6H', *COUNTS))
        setfield('records', sum(COUNTS), 2)
        m.u.mem_write(m.state + layout['raster'], struct.pack('<QQ', 1 << 49, (1 << 49) | (1 << 50)))
        if fault == 'missing_geometry':
            m.u.mem_write(m.state + layout['at'], struct.pack('<H', COUNTS[0] - 1))
        if fault == 'slot_order':
            m.u.mem_write(m.state + layout['raster'], struct.pack('<Q', (1 << 49) | (1 << 50)))
        if fault == 'slot_count': setfield('patch_count', 1)
        if fault == 'missing_tag_count': setfield('missing', 1, 2)
        if fault == 'too_many_tags': setfield('missing', 513, 2)
        assert call(7, sum(COUNTS) << 16, at=4) == (fault == 'valid'), fault
        controls.append('META_END:' + fault)
    for fault in ('valid', 'missing_geometry', 'raw_short', 'upper_bits',
                  'records', 'bytes', 'lane', 'missing'):
        reset(0); setfield('next_kind', 7); setfield('last_tile', 512, 2)
        setfield('records', sum(COUNTS) + 512, 2); setfield('bytes', 512, 2)
        m.u.mem_write(m.state + layout['at'], struct.pack('<6H', *COUNTS))
        value = ((sum(COUNTS) + 512) << 16) | 512
        if fault == 'missing_geometry':
            m.u.mem_write(m.state + layout['at'], struct.pack('<H', COUNTS[0] - 1))
        if fault == 'raw_short': setfield('last_tile', 511, 2)
        if fault == 'upper_bits': value |= 1 << 32
        if fault == 'records': value += 1 << 16
        if fault == 'bytes': value += 1
        if fault == 'lane': setfield('lane', 1)
        if fault == 'missing': setfield('missing', 1, 2)
        assert call(7, value, at=1) == (fault == 'valid'), fault
        controls.append('END:' + fault)
    for state in (1, 2, 3, 4):
        for gen in (905, 906):
            reset(0); setfield('state', state)
            assert call(7, 0, gen, 3) == (state == 3 and gen == 905)
            controls.append(f'COMMIT:state{state}:generation{gen}')
    return dict(value_cases=rows, count=sum(x['accepted']+x['rejected'] for x in rows),
                admission_counterexamples=guards, controls=controls,
                scope='actual linked586 M4 old semantic oracle vs Python value contract; no new executor')

def source_audit(board):
    pins = json.loads((ROOT/'analysis/whole580-manifest.json').read_text())['FPGA_inputs']
    names = ('board.qsf', 'fxpak_nes_screen137_top.sv', 'nes_live_joint.sv',
             'nes_native_export203.sv', 'nes_native_mailbox165.sv', 'nes_native_spi165.sv')
    hashes = {}
    for name in names:
        hashes[name] = sha(board/name)
        assert hashes[name] == pins[name]['sha256'], name
    texts = {n:(board/n).read_text() for n in names}
    checks = {
        'board.qsf': ['TOP_LEVEL_ENTITY fxpak_nes_screen137_top'],
        'fxpak_nes_screen137_top.sv': ['nes_live_joint core('],
        'nes_live_joint.sv': ['nes_native_export203 #(', 'nes_native_mailbox165 #(.WIDTH(96)) native_records(', 'nes_native_spi165 native_spi('],
        'nes_native_spi165.sv': ['buffer[0:255]', 'record_ready=!reset&&!sealed&&!encoding&&used<=244', 'block_crc<=crc16(block_crc,pack_byte)'],
    }
    for name, needles in checks.items():
        for needle in needles: assert needle in texts[name], (name, needle)
    return dict(hashes=hashes, input_storage_B=256, mailbox_bits=96,
                source_packet_slots=1, prior_probe_source_slots=4,
                crc_owner='host serialized compressed pack_byte; not NES canonical query values',
                proof='pinned source hierarchy/static audit, not new elaboration or simulation')

def query_crc():
    def crc(values):
        c = 65535
        for v in values:
            for b in v.to_bytes(2, 'little'):
                c ^= b << 8
                for _ in range(8): c = ((c << 1) ^ (0x1021 if c & 32768 else 0)) & 65535
        return c
    rows = []
    # Synthetic map-repeat subsection of export203: mismatch/full run queries
    # the same index again after VALUE. Not a model of all codec branches.
    for name, values in [('run_change', [7, 7, 9]), ('run_limit', [7]*257)]:
        at = 0; held = None; count = 0; responses = []; accepted = []
        while at < len(values):
            v = values[at]; responses.append(v)
            if held is None: held = v; count = 1
            elif v == held and count < 256: count += 1
            else: held = None; count = 0; continue
            accepted.append(v); at += 1
        assert accepted == values and len(responses) > len(values)
        assert crc(responses) != crc(values) and crc(accepted) == crc(values)
        rows.append(dict(case=name, logical_values=len(values), query_responses=len(responses),
                         accepted_index_crc_matches=True, every_response_crc_matches=False))
    return rows

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--arm', required=True, type=Path)
    ap.add_argument('--board', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args(); inv = inventory(a.arm)
    old = inv['modules']['nes_native165']['logical_record']
    assert old == 1136 and inv['gap_before_callees_IRQ_B'] == 4572
    report = dict(stage=587, passed=True, semantics=semantics(a.arm), source=source_audit(a.board),
                  query_crc=query_crc(),
                  budget=dict(firmware586_B=213852, limit_B=212992, old_executor_B=old,
                              optimistic_remaining_after_old_executor_removal_B=212992-(213852-old),
                              replacement_semantics_B=None, history_integrity_code_B=None,
                              pre_callees_IRQ_gap_B=4572, additional_shadow_mask_scratch_aligned_B=2448,
                              remaining_before_callees_IRQ_and_integrity_B=2124,
                              source_canonical_crc_LE=None, replacement_FIFO_M9K=None),
                  decision='R2 feasibility not established; reject unpriced direct-executor-only rescue, no R3',
                  pins=dict(tool=sha(Path(__file__)), arm_elf=sha(a.arm/'obj-nes-100/sd2snes.elf'),
                            arm_source=sha(a.arm/'nes_native165.c'), inventory_tool=sha(ROOT/'tools/analyze_nes_ownership585.py'),
                            probe_tool=sha(ROOT/'tools/check_nes_combined586.py'), probe_base=sha(ROOT/'tools/check_nes_transport584.py')),
                  new_firmware=False, new_RTL=False, new_timing=False)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(dict(passed=True, semantic_values=report['semantics']['count'],
                         admission_guards=4, control_cases=len(report['semantics']['controls']),
                         pinned_FPGA_files=6, flash_ceiling_B=276, source_slots=1)))

if __name__ == '__main__': main()
