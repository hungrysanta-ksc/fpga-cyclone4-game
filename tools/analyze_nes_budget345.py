# SPDX-License-Identifier: MIT
"""NES345 serialized record-store model and audited budget, NOT RTL timing."""
import json
from pathlib import Path
from nes_delta231 import BASE, ROOT, sha
from probe_nes_decode280 import golden, encode280, chunks, records
from nes_hybrid340 import encode340


def main():
    pins = {}
    def read(p):
        pins[str(p)] = sha(p)
        return p.read_text(encoding='utf-8-sig')
    def js(p):
        return json.loads(read(p))
    prior = [js(ROOT / f'analysis/{s}-verification.json') for s in
             ('ingress338', 'hybrid340', 'order343', 'record344')]
    verified = {}
    for a in prior:
        for p, h in a['pins'].items():
            assert sha(Path(p)) == h, p
            verified[p] = h
    for n in ('nes_core257.sv', 'nes_mux260.sv', 'nes_queue260.sv'):
        read(BASE / 'probes/nes-ingress338/window03' / n)
    for n in ('nes_hybrid340.py', 'nes_record344.py', 'analyze_nes_budget345.py'):
        read(ROOT / 'tools' / n)
    old = bytes(4398)
    raw_old = None
    rows = []
    for f in range(905, 976):
        g, raw = golden(f)
        rr = encode340(old, g, raw, raw_old, f-904, f-904)
        p = BASE / f'probes/nes-hybrid340/arm03/frame{f}.records'
        read(p)
        assert records(p) == rr
        ref = encode280(old, g, raw, raw_old, f-904, f-904)
        counts = dict(mask=0, shift=0, nonmap=0, literal=0, repeat8=0, repeat16=0)
        writes = overhead = maximum = 0
        for r in rr[1:]:
            if r[:3] == b'\xff\xff\0':
                continue  # H/GEO/END CRC production unchanged; not free or modelled here.
            store = bytearray(128)
            if (r[0] & 127) < 32:
                if r[0] & 128:
                    counts['shift'] += 1
                    prefix = 4
                else:
                    counts['mask'] += 1
                    prefix = 1  # deferred 9 mask bytes charged as normal store writes
            else:
                assert 65 <= r[0] <= 72
                mode, count = r[3] >> 6, (r[3] & 63)+1
                assert mode <= 2
                assert len(r) == 4 + (count if mode == 0 else mode)
                counts['nonmap'] += 1
                counts[('literal', 'repeat8', 'repeat16')[mode]] += 1
                prefix = 4
            # Single write port, final data position first, prefix backfill second.
            # No concurrent output allowed until prefix is complete.
            order = list(range(prefix, len(r))) + list(range(prefix))
            assert len(set(order)) == len(r) and len(r) <= 128
            for i in order:
                store[i] = r[i]
            assert bytes(store[:len(r)]) == r
            writes += len(order)
            overhead += prefix
            maximum = max(maximum, len(r))
        wire = lambda rs: sum(map(len, rs)) + 15*len(chunks(rs)) + 8
        rows.append(dict(frame=f, reference_wire_B=wire(ref), compressed_wire_B=wire(rr),
                         records=counts, serialized_record_writes=writes,
                         prefix_write_cycles=overhead, max_record_B=maximum,
                         prefix_write_only_ms_at22MHz=overhead/22000))
        old, raw_old = g, raw
    assert sum(r['reference_wire_B'] for r in rows) == 52113
    assert sum(r['compressed_wire_B'] for r in rows) == 32236
    assert all(r['compressed_wire_B'] <= r['reference_wire_B'] for r in rows)
    h = prior[1]['runs']['fixed01']['rows'][-1]
    request = h['first_request_ms'] - h['start_ms']
    area = prior[2]
    assert sum(area['area_current'].values()) == 6324
    assert sum(area['area_caps'].values()) == 4303
    result = dict(stage=345, passed=True, selected_RTL=338, selected_ARM=336,
        new_RTL=False, new_ARM=False, new_MAP=False, new_measured_gain_ms=0,
        new_measured_comb_gain=0, evidence_rehashed=len(verified), rows=rows,
        wire_totals_B=dict(baseline=52113, compressed=32236),
        max_record_B=max(r['max_record_B'] for r in rows),
        max_prefix_write_cycles=max(r['prefix_write_cycles'] for r in rows),
        model_scope='Serialized final record storage only; existing340 bytes/CRC preserved. Not query/compare/CRC/RAM arbitration or new decoder/RTL execution. Prefix writes are additional builder work, not frame latency.',
        fixed907=dict(measured340_request_relative_ms=request, prior_ROM_close_relative_ms=6.089722,
            necessary_request_advance_ms=request-6.089722,
            measured_source_ms=h['source_ms'], measured_after_source_to_request_ms=request-h['source_ms'],
            source_successful_wire_only_ms=206*8/2625000*1000,
            total_ms=h['total_ms']),
        selected_gap_ms=4.022994145333332, selected_comb_deficit=1866,
        whole_baseline_comb=17274, whole_comb_cap=15253,
        area_current=area['area_current'], area_caps=area['area_caps'],
        net_required=2021, retained_outside=10950,
        host_source_only_at_caps_comb=15613,
        pins=pins)
    (ROOT/'analysis/budget345-verification.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','pins')}, indent=2))


if __name__ == '__main__':
    main()
