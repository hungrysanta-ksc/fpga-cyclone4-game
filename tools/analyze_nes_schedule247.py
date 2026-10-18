# SPDX-License-Identifier: MIT
"""Join source representation and post-SEAL DMA models on the same71 frames.

Read-only, Python models: no new RTL, ARM,65816 execution or timing claim.
Private input geometry/pattern bytes never appear in the public summary.
"""
from pathlib import Path
import argparse
import csv
import json
import struct
from nes_delta231 import BASE, ROOT, sha
from analyze_nes_geometry230 import packets
from analyze_nes_source234 import blocks


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def ordered_patterns(plans, valid, gap_limit):
    """Final descriptors only; retain incoming plan/bulk order and ownership."""
    out = []
    gaps = []
    invalid_gaps = []
    for kind, slot, size in sorted(plans):
        assert kind in (0, 1) and size == (16 if kind == 0 else 32)
        at = slot * size
        if out and out[-1][0] == kind:
            _, start, length = out[-1]
            end = start + length
            gap = at - end
            assert gap >= 0, 'duplicate or overlapping pattern write'
            base = 0 if kind == 0 else 1024
            covered = all(base + i in valid for i in range(end//size, slot))
            if 0 < gap <= gap_limit and not covered:
                invalid_gaps.append(dict(kind=kind,bytes=gap,
                    uninitialized_slots=sum(base+i not in valid for i in range(end//size,slot))))
            if gap <= gap_limit and covered and at+size-start <= 4096:
                out[-1] = (kind, start, at+size-start)
                if gap:
                    gaps.append((kind, end, gap))
                continue
        out.append((kind, at, size))
    return out, gaps, invalid_gaps


def masked_geometry(previous, current, cold):
    """Hypothetical new version: warm records=(block16 index,mask16,bytes).

    Keep existing cold literal format,20B header,10B geometry END and6B RAW
    END budgets. These are record-size models, not an implemented protocol.
    """
    if cold:
        records = [struct.pack('<HB',i,len(current[i:i+240]))+current[i:i+240]
                   for i in range(0,len(current),240)]
        rebuilt = bytearray(len(current))
        cursor = 0
        for record in records:
            at, count = struct.unpack_from('<HB',record)
            assert at == cursor and len(record) == count+3
            rebuilt[at:at+count] = record[3:]
            cursor += count
        assert cursor == len(current) and rebuilt == current
        return list(map(len,records))
    records = []
    for at in range(0, len(current), 16):
        mask = sum(1 << i for i, value in enumerate(current[at:at+16])
                   if value != previous[at+i])
        if mask:
            records.append(struct.pack('<HH', at//16, mask) +
                           bytes(value for i, value in enumerate(current[at:at+16]) if mask >> i & 1))
    # Decode from serialized values, independently of encoder offsets.
    rebuilt = bytearray(previous)
    last = -1
    for record in records:
        index, mask = struct.unpack_from('<HH', record)
        assert index > last and mask and len(record) == 4+mask.bit_count()
        pos = 4
        for bit in range(16):
            if mask >> bit & 1:
                at = index*16+bit
                assert at < len(rebuilt)
                rebuilt[at] = record[pos]
                pos += 1
        last = index
    assert bytes(rebuilt) == current
    return list(map(len, records))


def analyze(prior_path, observer):
    prior = read(prior_path)
    assert prior['passed'] and prior['frames'] == 71
    pins = {}
    def pin(p, expected=None):
        digest = sha(p)
        if expected is not None:
            assert digest == expected, p.name
        pins[p.relative_to(BASE).as_posix()] = digest
        return p
    pin(prior_path)
    for name, digest in prior['input_hashes'].items():
        pin(BASE/name, digest)
    observed = read(pin(observer/'result.json'))
    for name, digest in observed['output_hashes'].items():
        pin(observer/name, digest)
    for name, digest in observed['observed_sources'].items():
        pin(observer/name, digest)
    manifest = read(pin(BASE/'probes/nes-sparse232/manifest.json'))['files']
    paths = read(BASE/'probes/nes-path236/analysis02/result.json')
    assert paths['passed']
    path_rows = {mode:{r['frame']:r for r in case['rows']} for mode,case in paths['cases'].items()}
    # Static lifetime evidence is kept separate from measured/model values.
    for p in (ROOT/'tools/nes_sparse232.py', ROOT/'tools/nes_dirty212.py',
              ROOT/'tools/nes_banked169.py',
              BASE/'probes/nes-runtime233/arm01/src/nes_native_runtime165.c'):
        pin(p)
    # Host oracle poisons unused bytes with A5. This is not SNES initialization:
    # valid sets start empty, and no gap may copy an uninitialized slot.
    banks = [bytearray([0xa5])*20480, bytearray([0xa5])*20480]
    vram = [bytearray(20480), bytearray(20480)]
    valid = [set(), set()]
    previous = bytes(5741)
    rows = []
    compared = gap_bytes = gap_spans = 0
    for original in prior['rows']:
        f = original['frame']
        target = original['bank']
        gen = original['generation']
        obs = observer/f'frame{f}'
        plans = [tuple(map(int, line.split(','))) for line in obs.with_suffix('.plans').read_text().splitlines()]
        bp = BASE/f'probes/nes-sparse232/scroll02/run/bank-{gen}.bin'
        expected = pin(bp, manifest[f'scroll02/run/bank-{gen}.bin']['sha256']).read_bytes()
        assert len(expected) == 24576
        for kind, slot, size in plans:
            at = (0 if kind == 0 else 16384)+slot*size
            banks[target][at:at+size] = expected[at:at+size]
            valid[target].add(slot+(0 if kind == 0 else 1024))
        assert banks[target] == expected[:20480], (f, 'target shadow outside writes')
        ordered, _, _ = ordered_patterns(plans, valid[target], 0)
        joined, gaps, invalid_gaps = ordered_patterns(plans, valid[target], 96)
        for kind, at, size in joined:
            base = 0 if kind == 0 else 16384
            vram[target][base+at:base+at+size] = banks[target][base+at:base+at+size]
        pp = list(packets(obs.with_suffix('.packets').read_bytes()))
        seal = pp[-1]
        assert seal[0] == 3 and len(seal) == 16+222  # envelope + descriptor
        for slot in range(1152):
            if seal[40+slot//8] >> (slot%8) & 1:
                assert slot in valid[target], (f, 'used slot uninitialized')
                size = 16 if slot < 1024 else 32
                at = slot*16 if slot < 1024 else 16384+(slot-1024)*32
                assert vram[target][at:at+size] == expected[at:at+size], (f, slot)
                compared += size
        # Invalid holes must remain separate even when cheap to bridge.
        guarded, _, _ = ordered_patterns([(1,0,32),(1,2,32)], {1024,1026}, 96)
        assert len(guarded) == 2
        assert len(ordered_patterns([(1,0,32),(1,2,32)], {1024,1025,1026}, 96)[0]) == 1
        gap_bytes += sum(n for _,_,n in gaps)
        gap_spans += len(gaps)
        before = sum(original['snes']['upload'][k]['charge'] for k in ('bg','obj'))
        pattern = {}
        for name, ranges in (('received_order',None),('address_order',ordered),('address_order_valid_gap96',joined)):
            charge = before if ranges is None else sum(n+96 for _,_,n in ranges)
            pattern[name] = dict(charge=charge, delta=charge-before)
        new = obs.with_suffix('.geometry').read_bytes()
        raw = obs.with_suffix('.raw').read_bytes()
        lengths = ([20]+masked_geometry(previous,new,f==905)+[10]+
                   [3+len(raw[i:i+240]) for i in range(0,len(raw),240)]+[6])
        payload, count = sum(lengths), blocks(lengths)
        w = original['spi']['ready4_components']
        source_delta = payload-w['source_payload']+19*(count-w['source_block_framing']//3)
        sources = {mode:{k:values[f][k] for k in ('ready4','ready1')} for mode,values in path_rows.items()}
        sources['mask16'] = {k:original['spi'][k+'_bytes']+source_delta for k in ('ready4','ready1')}
        models = {}
        for source, wire in sources.items():
            for output in ('batched16','causal_words'):
                old = original['p1_models'][output]
                model = {k+'_bytes':wire[k]+old[k+'_bytes']-original['spi'][k+'_bytes'] for k in ('ready4','ready1')}
                model['snes_charge'] = old['total_charge_model']+pattern['address_order_valid_gap96']['delta']
                model['extra_arm_state'] = old['additional_arm_retained_bytes']
                models[source+'_'+output] = model
        rows.append(dict(frame=f,phase=original['phase'],original_charge=original['snes']['charge_model'],
                         pattern=pattern,gap_bytes=sum(n for _,_,n in gaps),gap_spans=len(gaps),
                         rejected_invalid_gaps=invalid_gaps,
                         mask16_payload=payload,mask16_blocks=count,models=models))
        previous = new
    warm = rows[2:]
    summaries = {}
    for name in warm[0]['models']:
        vals = [(r['frame'],r['models'][name]) for r in warm]
        summaries[name] = dict(
            ready4_max=max(v['ready4_bytes'] for _,v in vals),
            ready1_max=max(v['ready1_bytes'] for _,v in vals),
            over_ready4=[f for f,v in vals if v['ready4_bytes']>5468.75],
            over_ready1=[f for f,v in vals if v['ready1_bytes']>5468.75],
            snes_charge_max=max(v['snes_charge'] for _,v in vals),
            over_snes=[f for f,v in vals if v['snes_charge']>4192],
            extra_arm_state=vals[0][1]['extra_arm_state'],
            qualified_for_p2=False)
    return dict(stage=247,passed=True,scope=__doc__,frames=71,warm_frames=69,rows=rows,
                combinations=summaries,compared_used_pattern_bytes=compared,
                valid_gap_bytes=gap_bytes,valid_gap_spans=gap_spans,
                masked_geometry_exact_frames=71,
                prerequisites=['All current writes complete and SEAL coverage passes before sorted DMA.',
                               'Only target bank; every gap slot valid in that bank and epoch.',
                               'Plan generation/bulk/token order is unchanged; only final DMA descriptions reorder.',
                               'STOP invalidates candidate ownership; no commit before final display ACK and retire.'],
                caveats=['Models only; no assembled decoder/scheduler, cycle bound or FPGA area saving.',
                         'Gap copies use initialized target shadow, not active or last-displayed bytes.',
                         'Existing source240 cycles cannot be assigned to simplified source representations.',
                         'New source decoder/version/CRC/admission/ACK binding not implemented.',
                         '4192 is existing conservative charge gate, not measured master-clock duration.',
                         'Early VRAM transfer still consumes VBlank; double buffering does not add bandwidth.'],
                selected_implementation=None,full_new_input_arm=False,new_fit=False,physical_fps=False,
                input_hashes=pins,analyzer_sha256=sha(Path(__file__)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prior',type=Path,required=True)
    p.add_argument('--observer',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a = p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    result = analyze(a.prior.resolve(),a.observer.resolve())
    raw = a.out/'result.json'
    raw.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    public = {k:v for k,v in result.items() if k not in ('rows','input_hashes')}
    public['residual_rows'] = [r for r in result['rows'] if r['frame'] in (952,954,955,963,968)]
    public['input_count'] = len(result['input_hashes'])
    public['private_result_sha256'] = sha(raw)
    public['evidence_sha256'] = {k:v for k,v in result['input_hashes'].items()
                                if k.endswith(('result.json','manifest.json')) or '/tools/' in k or k.endswith('nes_native_runtime165.c')}
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    flat = []
    for r in result['rows']:
        row = {k:r[k] for k in ('frame','phase','original_charge','gap_bytes','gap_spans','mask16_payload','mask16_blocks')}
        for name, values in r['models'].items():
            row.update({name+'.'+k:v for k,v in values.items()})
        flat.append(row)
    with (a.out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w = csv.DictWriter(f,fieldnames=list(flat[0]),lineterminator='\n')
        w.writeheader()
        w.writerows(flat)
    print(json.dumps({k:result[k] for k in ('passed','frames','compared_used_pattern_bytes','valid_gap_bytes','valid_gap_spans','combinations')},indent=2))


if __name__ == '__main__':
    main()
