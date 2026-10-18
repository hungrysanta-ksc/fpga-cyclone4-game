# SPDX-License-Identifier: MIT
"""Join recorded240/236/232 costs and observed231 decisions by frame, not FPS.

All inputs are read-only. Public output contains aggregate counts, never ROM,
graphics, physical CHR identities, raw observations or private absolute paths.
"""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import csv
import json
import struct
from nes_delta231 import BASE, ROOT, sha
from analyze_nes_geometry230 import packets, sections, summary
from analyze_nes_delta231 import merge


def read_json(p):
    return json.loads(p.read_text(encoding='utf-8'))


def csv_rows(p):
    with p.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def indexed(rows):
    result = {int(r['frame']):r for r in rows}
    assert len(result) == len(rows) == 71 and set(result) == set(range(905,976))
    return result


def semantic(m):
    return m['tag'], m['row'], m['alt']


def analyze(observer):
    obs = read_json(observer/'result.json')
    assert obs['passed'] and obs['exact_files'] == 355 and obs['cost_exact']
    pins = {}
    def pin(p):
        pins[str(p.relative_to(BASE)).replace('\\','/')] = sha(p)
        return p
    # Check only consumed entries against the sealed manifests, not a repeated
    # full-archive audit. The old archives are never rewritten.
    manifests = {}
    for stage in ('nes-delta231','nes-source240','nes-path236','nes-sparse232'):
        directory = BASE/'probes'/stage
        manifests[directory] = read_json(pin(directory/'manifest.json'))['files']
    prior_directory = BASE/'probes/nes-delta231'
    for name, digest in obs['input_pins'].items():
        assert manifests[prior_directory]['test07/'+name]['sha256'] == digest, name
    for name, digest in obs['observed_sources'].items():
        assert sha(observer/name) == digest, name
    for name, digest in obs['output_hashes'].items():
        assert sha(observer/name) == digest, name
        pin(observer/name)
    pin(observer/'result.json')
    source = BASE/'probes/nes-source240/test01'
    src_result = read_json(pin(source/'result.json'))
    assert src_result['passed'] and src_result['frames'] == 71
    cycles = indexed([{k:int(v) for k,v in r.items()} for r in csv_rows(pin(source/'cycles.csv'))])
    path = read_json(pin(BASE/'probes/nes-path236/analysis02/result.json'))
    full = indexed(path['cases']['full']['rows'])
    prior = read_json(pin(BASE/'probes/nes-delta231/analysis03/result.json'))
    costs = indexed(prior['frame_results'])
    snes = read_json(pin(BASE/'probes/nes-sparse232/analysis02/result.json'))
    snes_rows = indexed(snes['frame_results'])
    snes_exec = read_json(pin(BASE/'probes/nes-sparse232/scroll02/result.json'))
    onepass = indexed(read_json(pin(ROOT/'analysis/source234-verification.json'))['rows'])
    maps = defaultdict(list)
    slots = defaultdict(list)
    for r in csv_rows(observer/'map247.csv'):
        r = {k:(v if k in ('row','alt') else int(v)) for k,v in r.items()}
        maps[r['frame']].append(r)
    for r in csv_rows(observer/'slot247.csv'):
        r = {k:int(v) for k,v in r.items()}
        slots[r['frame']].append(r)
    lastmap = {}
    lastgroups = {}
    old_sections = [bytes(n) for n in (4096,512,544,3418)]
    bank_sections = [None, None]
    old_geometry = bytes(5741)
    old_wire = 0
    word_stale = [set(range(2048)),set(range(2048))]
    rows = []
    for f in range(905,976):
        c, a, t, v = costs[f], full[f], cycles[f], snes_rows[f]
        assert c['generation'] == f-904 == v['generation']
        assert t['total'] == sum(t[k] for k in ('prepare','blocked','ackwait','transfer'))
        metadata = sections((observer/f'frame{f}.metadata').read_bytes())
        pp = list(packets((observer/f'frame{f}.packets').read_bytes()))
        assert sum(len(p)+3 for p in pp) == c['metadata_spi']
        geometry = (observer/f'frame{f}.geometry').read_bytes()
        counts = struct.unpack_from('<6H',geometry,5728)
        query_fields = dict(zip(('map','row','object','exception','raster','palette'), counts))
        query_fields['raw'] = len((observer/f'frame{f}.raw').read_bytes())
        assert sum(query_fields.values()) == t['queries']
        group_rows = defaultdict(dict)
        causes = Counter()
        changed_addresses = set()
        semantic_changes = 0
        for m in maps[f]:
            at = m['at']
            assert struct.unpack_from('<H',old_sections[0],at)[0] == m['old']
            assert struct.unpack_from('<H',metadata[0],at)[0] == m['value']
            old = lastmap.get(at)
            if old is not None and semantic(old) != semantic(m):
                semantic_changes += 1
            if m['old'] != m['value']:
                changed_addresses.add(at)
                if old is None:
                    cause = 'previously_unwritten_address'
                elif semantic(old) == semantic(m):
                    cause = 'same_semantics_slot_change' if (old['value']^m['value'])&1023 else 'palette_priority_only'
                elif old['tag'] == m['tag']:
                    cause = 'same_tag_row_or_alternate_change'
                else:
                    cause = 'physical_tag_change_at_address'
                causes[cause] += 1
            group_rows[m['group']][m['column']] = (semantic(m),m['value']&0xfc00)
        # Exact semantic overlap under the already implemented horizontal ring.
        # A different ordinal match is evidence of layout churn, not yet a
        # safe reassignment: equal duplicate rows may make identity ambiguous.
        moved = unique_moved = same = ambiguous = 0
        for g, now in group_rows.items():
            matches=[]
            for before, prev in lastgroups.items():
                common = now.keys() & prev.keys()
                if len(common) >= 32 and all(now[k] == prev[k] for k in common):
                    matches.append(before)
            if g in matches:
                same += 1
            elif matches:
                moved += 1
                unique_moved += len(matches) == 1
                ambiguous += len(matches) > 1
        exact_changed = {at for at in range(0,4096,2) if old_sections[0][at:at+2] != metadata[0][at:at+2]}
        assert exact_changed == changed_addresses
        assert sum(causes.values()) == len(exact_changed)
        writes = Counter()
        writes_bytes = Counter()
        kinds = Counter()
        for s in slots[f]:
            if s['kind'] != 2 and s['equal'] and s['resident']:
                kinds['retained_hit'] += 1
                continue
            name = ('forced_zero' if s['kind'] == 2 else 'nonordinary_shape' if not s['retain'] else
                    'alternate_bank_refill' if s['equal'] else
                    'new_slot_key' if s['old'] == (4294967295 if s['kind'] == 1 else 65535) else 'slot_key_replacement')
            writes[name] += 1
            writes_bytes[name] += 32 if s['kind'] == 1 else 16
            kinds['obj' if s['kind'] == 1 else 'bg'] += 1
        assert sum(writes.values()) == c['plans']
        assert sum(writes_bytes.values()) == c['tile_bytes']
        plans = [tuple(map(int,l.split(','))) for l in (observer/f'frame{f}.plans').read_text().splitlines()]
        chunks = merge([(k,slot*n,n) for k,slot,n in plans],0)
        assert len(chunks) == c['pattern_chunks_model']
        ranges = list(chunks)
        out_payload = Counter()
        out_envelope = Counter()
        controls = 0
        map_sent = set()
        for p in pp:
            if p[0] in (1,3):
                controls += len(p)+3
                continue
            k = p[1]
            at,n,expanded = struct.unpack_from('<HHH',p,10)
            size = n if p[0] == 2 else expanded
            out_payload[str(k)] += n
            out_envelope[str(k)] += 19
            if k == 2:
                ranges.append((2,at,size))
                map_sent.update(range(at,at+size))
            elif k == 5 and 1121 <= at < 3169:
                ranges.append((5,at-1121,min(size,3169-at)))
        joined = merge(ranges,96)
        upload = {}
        for kind, name in ((0,'bg'),(1,'obj'),(2,'map'),(5,'raw')):
            rr = [r for r in joined if r[0] == kind]
            upload[name] = dict(bytes=sum(r[2] for r in rr), commands=len(rr),charge=sum(r[2]+96 for r in rr))
        fixed = 1568 if v['palette_upload'] else 960
        assert fixed + sum(r['charge'] for r in upload.values()) == v['charge_model']
        target = (f-905)%2
        before = bank_sections[target]
        dest_changed = set(range(4096)) if before is None else {i for i in range(4096) if before[0][i] != metadata[0][i]}
        assert dest_changed <= map_sent
        dirty_granules = {at//16 for at in changed_addresses}
        sent_granules = {at//16 for at in map_sent}
        dest_granules = {at//16 for at in dest_changed}
        batches = (c['plans']+6)//7
        nch = len(chunks)
        wire = dict(source_payload=a['payload'], source_block_framing=3*a['blocks'],
                    source_control=16*a['blocks']+32,
                    output_data_payload=sum(out_payload.values()),output_data_envelopes=sum(out_envelope.values()),
                    output_begin_seal=controls, plans=32*c['plans']+3+8*batches,
                    plan_control=20*batches,pattern_control=43*nch,final_control=67,
                    ready4_scenario=80+40*nch+20*((len(pp)-2+3)//4))
        assert sum(wire.values()) == a['ready4']
        word_stale[0].update(at//2 for at in changed_addresses)
        word_stale[1].update(at//2 for at in changed_addresses)
        # P1 representation models only. Preserve target-bank causality; never
        # infer inactive-bank equality from last-displayed equality alone.
        # A packet envelope is charged at existing19B, with at most240B payload.
        # Decoder/version/coverage implementation and its cycle cost are OPEN.
        model16 = [(g*16,metadata[0][g*16:g*16+16]) for g in sorted(sent_granules)]
        model2 = [(w*2,metadata[0][w*2:w*2+2]) for w in sorted(word_stale[target])]
        variants = {}
        old_map_wire = out_payload['2']+out_envelope['2']
        old_map_packets = out_envelope['2']//19
        for name, updates, unit, entries in (('batched16',model16,16,13),('causal_words',model2,2,60)):
            rebuilt = bytearray(4096) if before is None else bytearray(before[0])
            # Encode and independently parse the sorted offset/value payload.
            packet_count = 0
            payload_bytes = 0
            last_end = 0
            for start in range(0,len(updates),entries):
                payload = b''.join(struct.pack('<H',at)+data for at,data in updates[start:start+entries])
                assert 0 < len(payload) <= 240 and len(payload)%(unit+2) == 0
                for pos in range(0,len(payload),unit+2):
                    at = struct.unpack_from('<H',payload,pos)[0]
                    assert at >= last_end and at%unit == 0 and at+unit <= 4096
                    rebuilt[at:at+unit] = payload[pos+2:pos+2+unit]
                    last_end = at+unit
                packet_count += 1
                payload_bytes += len(payload)
            assert bytes(rebuilt) == metadata[0], (f,name,'semantic reconstruction')
            map_wire = payload_bytes+19*packet_count
            new_count = len(pp)-2-old_map_packets+packet_count
            changed_ready4 = a['ready4']-old_map_wire+map_wire+20*((new_count+3)//4-(len(pp)-2+3)//4)
            changed_ready1 = a['ready1']-old_map_wire+map_wire+20*(new_count-(len(pp)-2))
            mr = merge([(2,at,len(data)) for at,data in updates],96)
            new_map_charge = sum(n+96 for _,_,n in mr)
            variants[name] = dict(map_wire_bytes=map_wire,map_packets=packet_count,
                ready4_bytes=changed_ready4,ready1_bytes=changed_ready1,
                map_charge_model=new_map_charge,
                total_charge_model=v['charge_model']-upload['map']['charge']+new_map_charge,
                additional_arm_retained_bytes=0 if unit==16 else 448,
                cold_policy='existing full literal required; modeled warm format is inefficient on cold' if f<907 else 'warm',
                reconstructed_map_exact=True,implemented=False)
        word_stale[target].clear()
        # C relocation ceiling: these bytes vanish only if map construction
        # and delivery truly leave the ARM/shared-SPI route. This is not a new
        # design or a claim that the added SNES/FPGA work is free.
        variants['local_map_ceiling'] = dict(
            removable_map_wire_bytes=old_map_wire,
            residual_ready4_bytes_without_added_control=a['ready4']-old_map_wire,
            current_map_evaluations=len(maps[f]),new_compute_ms=None,
            fpga_area_delta=None,snes_code_bytes=None,implemented=False)
        wire_delta = t['wirebytes_cumulative']-old_wire
        assert wire_delta >= a['payload']+19*a['blocks']
        old_wire = t['wirebytes_cumulative']
        changes = {}
        for name, start, end in (('map',0,2112),('row',2112,2336),('object',2336,3360),('exception',3360,3872),('raster',3872,5664),('palette_counts',5664,5741)):
            changes[name] = sum(x != y for x,y in zip(geometry[start:end],old_geometry[start:end]))
        rows.append(dict(frame=f,generation=c['generation'],bank=target,
            phase='cold_source_and_destination' if f==905 else 'warm_source_cold_destination' if f==906 else 'warm',
            scene='observed_first_level_scroll_window',transition_annotation='UNKNOWN',
            source240=dict(cycles={k:t[k] for k in ('total','prepare','blocked','ackwait','transfer')},
                           total_ms=t['total']*45.454/1e6,prepare_ms=t['prepare']*45.454/1e6,
                           queries=query_fields,overlapped_payload_bytes=t['overlap'],
                           input_only_executed_spi_bytes=wire_delta,
                           prior234_minimal_schedule_cycles=onepass[f]['serialized_source_cycles_scenario']),
            spi=dict(ready4_components=wire,ready4_bytes=a['ready4'],ready1_bytes=a['ready1'],
                     ready4_wire_ms=a['ready4']*8/2625,ready4_margin_bytes=5468.75-a['ready4'],
                     output_section_payload_bytes=dict(out_payload),output_section_envelope_bytes=dict(out_envelope),
                     runtime_gap_ms=None,full_shared_bus_upper_bound_ms=None),
            arm=dict(transform_ms=None,full_new_input_run_irq_margin_bytes=None),
            snes=dict(upload=upload,fixed_charge=fixed,charge_model=v['charge_model'],
                      charge_margin=4192-v['charge_model'],executed_vblanks=v['after_vblanks'],
                      file_rpc_seal_master_cycles=snes_exec['seal_master_cycles'][str(c['generation'])],
                      runtime_commit_ms=None),
            changes=dict(source_changed_bytes=changes,map_word_causes=dict(causes),
                         map_changed_words=len(exact_changed),map_semantic_changes_at_address=semantic_changes,
                         map_current_dirty_granules=len(dirty_granules),map_sent_granules=len(sent_granules),
                         map_destination_changed_granules=len(dest_granules),
                         map_sent_without_current_dirty_granules=len(sent_granules-dirty_granules),
                         map_sent_but_equal_destination_granules=len(sent_granules-dest_granules),
                         map_actual_destination_changed_bytes=len(dest_changed),map_sent_bytes=len(map_sent),
                         groups=len(group_rows),same_ordinal_matching_groups=same,
                         different_ordinal_matching_groups=moved,unique_different_ordinal_matching_groups=unique_moved,
                         ambiguous_different_ordinal_matches=ambiguous,
                         slot_writes=dict(writes),slot_write_bytes=dict(writes_bytes),slot_kinds=dict(kinds)),
            capture_to_display_age_ms=None))
        rows[-1]['p1_models'] = variants
        lastmap.update({m['at']:m for m in maps[f]})
        lastgroups = group_rows
        old_sections = metadata
        bank_sections[target] = metadata
        old_geometry = geometry
    warm = rows[2:]
    # A wrong last-display-only delta is a concrete negative counterexample:
    # 955 has no new map writes but its alternate destination is still stale.
    r955 = next(r for r in rows if r['frame']==955)
    assert r955['changes']['map_changed_words'] == 0
    assert r955['changes']['map_actual_destination_changed_bytes'] == 100
    for rel, digest in list(pins.items()):
        p = BASE/rel
        for directory, manifest in manifests.items():
            if p.is_relative_to(directory) and p.name != 'manifest.json':
                key = str(p.relative_to(directory)).replace('\\','/')
                assert manifest[key]['sha256'] == digest, rel
    totals = {}
    for k in ('map_word_causes','slot_writes','slot_write_bytes','slot_kinds','source_changed_bytes'):
        count = Counter()
        for r in warm:
            count.update(r['changes'][k])
        totals[k] = dict(count)
    for k in ('map_changed_words','map_current_dirty_granules','map_sent_granules','map_destination_changed_granules',
              'map_sent_without_current_dirty_granules','map_sent_but_equal_destination_granules',
              'different_ordinal_matching_groups','unique_different_ordinal_matching_groups'):
        totals[k] = sum(r['changes'][k] for r in warm)
    return dict(stage=247,passed=True,scope=__doc__,base_commit='b6958f24fbe2173d0879da07ef56fe3b507b5420',
                frames=71,warm_frames=69,rows=rows,warm_totals=totals,
                remaining_snes_frames=[r['frame'] for r in warm if r['snes']['executed_vblanks']>1],
                stats={k:summary([r['spi'][k] for r in warm]) for k in ('ready4_bytes','ready1_bytes','ready4_wire_ms','ready4_margin_bytes')},
                p1_models={name:dict(
                    ready4_bytes=summary([r['p1_models'][name]['ready4_bytes'] for r in warm]),
                    ready1_bytes=summary([r['p1_models'][name]['ready1_bytes'] for r in warm]),
                    charge_model=summary([r['p1_models'][name]['total_charge_model'] for r in warm]),
                    over_charge4192=[r['frame'] for r in warm if r['p1_models'][name]['total_charge_model']>4192],
                    over_ready1=[r['frame'] for r in warm if r['p1_models'][name]['ready1_bytes']>5468.75],
                    additional_arm_retained_bytes=0 if name=='batched16' else 448,
                    new_input_arm_approved=False,snes_decoder_implemented=False,fpga_fit=False)
                    for name in ('batched16','causal_words')},
                input_hashes=pins,analyzer_sha256=sha(Path(__file__)),
                negative_counterexample=dict(frame=955,last_display_only_map_update_words=0,
                                             stale_target_bytes_if_skipped=100),
                evidence_levels=dict(source240='reused RTL execution, recorded stimuli and isolated input SPI',
                                     output='actual C packet/plan bytes; new observer replay exact355files and cost.csv',
                                     snes='reused actual65816 execution with fileRPC; charge is a model',
                                     wire='ready4/ready1 scheduling scenarios, not a shared-runtime upper bound',
                                     arm='UNKNOWN runtime time and full new-input RUN/IRQ',physical='not executed'),
                physical_fps=False,full_pipeline_upper_bound_ms=None,selected_implementation=None,
                exclusions=['Do not sum source240 total and shared wire: source already includes overlapped input SPI.',
                            'Do not add232 one-tile bulk fixture wire to grouped236 model; different schedules.',
                            'seal_master_cycles includes fileRPC waits; not SNES CPU or runtime commit time.',
                            'different-ordinal matching is observational; duplicate rows and ownership need a separate decision.',
                            'physical_tag_change_at_address mixes actual content changes and row placement; not unique new tiles.',
                            'unused resident slots may lack an alternate-bank copy; refill is not slot replacement.',
                            'UNKNOWN values are null, never zero cost.'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--observer',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--summary',type=Path)
    p.add_argument('--ledger',type=Path)
    a = p.parse_args()
    assert not a.out.exists()
    assert not a.summary or not a.summary.exists()
    assert not a.ledger or not a.ledger.exists()
    result = analyze(a.observer.resolve())
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if a.ledger:
        def flatten(d, prefix=''):
            flat = {}
            for k,v in d.items():
                key = prefix+k
                if isinstance(v,dict):
                    flat.update(flatten(v,key+'.'))
                else:
                    flat[key] = 'UNKNOWN' if v is None else v
            return flat
        rows = [flatten(r) for r in result['rows']]
        fields = list(dict.fromkeys(k for r in rows for k in r))
        with a.ledger.open('w',newline='',encoding='utf-8') as f:
            writer = csv.DictWriter(f,fieldnames=fields,lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)
    if a.summary:
        public = {k:v for k,v in result.items() if k not in ('rows','input_hashes')}
        public['residual_frames'] = [r for r in result['rows'] if r['frame'] in result['remaining_snes_frames']]
        public['consumed_inputs'] = len(result['input_hashes'])
        public['private_result_sha256'] = sha(a.out)
        public['input_hashes'] = {k:v for k,v in result['input_hashes'].items()
                                  if k.endswith(('result.json','manifest.json','cycles.csv','cost.csv','map247.csv','slot247.csv'))}
        if a.ledger:
            public['ledger_sha256'] = sha(a.ledger)
        a.summary.write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('passed','frames','warm_totals','remaining_snes_frames','stats')},indent=2))


if __name__ == '__main__':
    main()
