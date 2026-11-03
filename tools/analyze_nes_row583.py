# SPDX-License-Identifier: MIT
"""Row address + coupled transaction cost; no retimed execution or FPS claim."""
import argparse
import json
import math
from pathlib import Path
from nes_abi582 import (ROOT, sha, read, canonical, input_packets, map_records, pack_records,
                        map_restore, output_decode)
from nes_row583 import encode_rows, restore_rows
from check_nes_game478 import encode


def output_sizes(path):
    groups = {}; histories = [{}, {}]; layouts = [None, None]; result = {}
    for line in path.read_text().splitlines():
        b = bytes.fromhex(json.loads(line)[2]); g = int.from_bytes(b[8:10], 'little')
        groups.setdefault(g, []).append(b)
    for g, packets in groups.items():
        bank = int.from_bytes(packets[0][18:20], 'little')
        layout = int.from_bytes(packets[-1][38:40], 'little')
        if layouts[bank] != layout: histories[bank][5] = {}
        b_sizes = []; c_sizes = []; omitted = []
        for b in packets:
            k = b[1]; data_op = b[0] in (2,4,5,8)
            if data_op and k == 2: continue
            b_sizes.append(len(b) + 3)
            equal = False
            if data_op and k >= 3:
                at = int.from_bytes(b[10:12], 'little'); v = output_decode(b)
                m = histories[bank].setdefault(k, {})
                equal = all(m.get(at + i) == x for i, x in enumerate(v))
                if equal: omitted.append((k,at,len(v)))
                m.update({at+i:x for i,x in enumerate(v)})
            if not equal: c_sizes.append(len(b) + 3)
        ranges = []
        for k,at,n in sorted(omitted):
            if ranges and ranges[-1][0] == k and sum(ranges[-1][1:]) == at:
                kk,aa,nn = ranges.pop(); ranges.append((kk,aa,nn+n))
            else: ranges.append((k,at,n))
        if ranges: c_sizes.append(27 + 7 * len(ranges))
        result[g] = dict(B=b_sizes, C=c_sizes)
        layouts[bank] = layout
    return result


def query_audit(events):
    last = {}; last_carrier = -1; counts = {}
    for e in events:
        if e['event'] != 'SPI': continue
        op = e['opcode']
        if op in ('0xe1','0xe9'): last_carrier = e['start']
        if op not in ('0xe0','0xe8'): continue
        d = counts.setdefault(op, dict(queries=0, repeated=0, changed=0, changed_without_intervening_carrier=0))
        d['queries'] += 1
        if op in last:
            prev = last[op]
            if e['reply'] == prev['reply']: d['repeated'] += 1
            else:
                d['changed'] += 1
                if last_carrier < prev['clock']: d['changed_without_intervening_carrier'] += 1
        last[op] = e
    return counts


def run(a):
    a.out.mkdir(parents=True, exist_ok=False)
    old = read(ROOT/'analysis/abi582-verification.json')
    body = read(ROOT/'analysis/body581-verification.json')
    whole = read(ROOT/'analysis/whole580-verification.json')
    old_frames = {f['generation']:f for f in old['frames']}
    event = {}; sizes = {}
    for phase in ('1','2'):
        d = a.traces/f'nes-close561-run{phase}'
        for name in ('events.json','packets.jsonl'):
            assert sha(d/name) == whole['phases'][int(phase)-1]['evidence'][name]
        event[phase] = read(d/'events.json'); sizes[phase] = output_sizes(d/'packets.jsonl')
    prior = None; frames = []; previous_map = bytes(4096)
    banks = [bytes(4096),bytes(4096)]; stale = [set(range(512)),set(range(512))]
    for g in range(905,958):
        files = [a.data/f'frame{g}.{suffix}' for suffix in ('geometry','raw')]
        for p in files: assert sha(p) == body['inputs'][p.name]
        arrays = encode(*(p.read_bytes() for p in files),g)[2]
        arrays.append(list(files[1].read_bytes()))
        blocks = encode_rows(arrays,prior)
        assert canonical(restore_rows(blocks,list(map(len,arrays)),prior)) == canonical(arrays)
        packets = input_packets(arrays, blocks, g-904, g-905)
        current_map_path = a.capture/f'frame{g}/expected-map.bin'
        assert sha(current_map_path) == body['inputs'][f'capture/frame{g}/expected-map.bin']
        current_map = current_map_path.read_bytes()
        bank = body['frames'][str(g)]['phases']['1']['bank']
        records,masks,runs = map_records(current_map,previous_map,[stale[bank],stale[1-bank]],g<=906)
        from nes_abi582 import crc
        assert map_restore(banks[bank],records,masks,crc(b''.join(records))) == current_map
        map_sizes = [89] + [len(p)+19 for p in pack_records(records)]
        assert sum(map_sizes) == old_frames[g]['map']['wire_B']
        shifts = {str(s):0 for s in (-1,0,1)}; literal_rows = 0; literals = 0
        for b in blocks:
            if b[0]: continue
            if b[1] == 0: literal_rows += 1; literals += 33
            else:
                s = int.from_bytes(b[6:7],'little',signed=True) if b[1]==4 else 0
                shifts[str(s)] += 1; off = 7 if b[1]==4 else 6
                literals += int.from_bytes(b[off:off+5],'little').bit_count()
        same_changed = None if prior is None else sum(i>=len(prior[0]) or v!=prior[0][i] for i,v in enumerate(arrays[0]))
        old_input = old_frames[g]['input']['map_row_base']
        old_protocol = sum(map(len,packets)) + 19*len(packets) + 8
        # Request16, turnaround2, reply header16, fixed payload256, CRC16=2.
        # Final source confirmation36 is separately charged, never a free last ACK.
        fixed_fetch = 292*len(packets)+36
        # Two SPI/DMA stages under one CS: request16+turnaround2+header16+
        # headerCRC2, then actual payload+CRC2. Charge TWO driver submissions.
        variable_fetch = sum(map(len,packets)) + 38*len(packets) + 36
        row = dict(generation=g, map_same_index_changes=same_changed, map_transmitted_literals=literals,
            map_shift_rows=shifts, map_literal_rows=literal_rows, input_packets=len(packets),
            input_payload_B=sum(map(len,packets)), input_582_wire_B=old_input['wire_with_one_D0_per_packet_B'],
            input_shift_legacy_calls_wire_B=old_protocol, input_fixed_fetch_wire_B=fixed_fetch,
            input_variable_fetch_wire_B=variable_fetch,
            input_fixed_transaction_padding_B=sum(256-len(p) for p in packets), phases={})
        for phase in ('1','2'):
            events = [e for e in event[phase] if e['generation']==g]
            ops = body['frames'][str(g)]['phases'][phase]['wire']
            extra = whole['phases'][int(phase)-1]['parameters']['driver_extra_us']
            plans = [e['bytes'] for e in events if e['event']=='SPI' and e['opcode']=='0xe9']
            outside = sum(v for k,v in ops.items() if k not in ('0xd0','0xd1','0xd2','0xd3','0xe0','0xe1','0xe8','0xe9'))
            queries = query_audit(events)
            actual_queries = sum(d['queries'] for d in queries.values())
            phase_result = dict(query_audit=queries,cases={})
            for label in ('B','C'):
                out_sizes = sizes[phase][g][label] + map_sizes
                padded = sum(max(n,52) for n in out_sizes+plans)
                pad_B = padded-sum(out_sizes+plans)
                # A deliberately optimistic 3-query anchor is NOT an achievable
                # schedule. Upper sensitivity preserves all old E0/E8 calls.
                fixed_B = fixed_fetch + padded + outside
                driver_fixed = (len(packets)*extra['0xd1'] + extra['0xd3'] +
                                len(out_sizes)*extra['0xe1'] + len(plans)*extra['0xe9'] + extra['0xea'])/1000
                def cost(q, variable=False):
                    wire = fixed_B + q*52 + (variable_fetch-fixed_fetch if variable else 0)
                    wire_ms = wire*8/2625000*1000
                    driver = driver_fixed + q*max(extra['0xe0'],extra['0xe8'])/1000 + (len(packets)*extra['0xd1']/1000 if variable else 0)
                    return dict(queries=q,wire_B=wire,wire_ms=wire_ms,driver_ms=driver,
                                serial_IO_ms=wire_ms+driver,calls=len(packets)*(2 if variable else 1)+1+len(out_sizes)+len(plans)+1+q)
                # Check unchanged582 output representation before adding padding.
                ref = old_frames[g]['phases'][phase]['map_row_base' + ('_reuse' if label=='C' else '')]
                original_sum = sum(out_sizes)+sum(plans)+outside+old_input['wire_with_one_D0_per_packet_B']
                original_sum += ops['0xe8'] + 20*(math.ceil(len(out_sizes)/4)+3)
                assert original_sum == ref['E0_batched_scenario_B'], (g,phase,label)
                budget_q = (1000/60 - cost(0)['serial_IO_ms'])/(52*8/2625000*1000+max(extra['0xe0'],extra['0xe8'])/1000)
                phase_result['cases'][label] = dict(progress_padding_B=pad_B,
                    output_packets=len(out_sizes), plan_calls=len(plans),
                    shift_only_582_IO_ms=ref['serial_wire_plus_driver_mean_ms'] +
                       (old_protocol-old_input['wire_with_one_D0_per_packet_B'])*8/2625000*1000 +
                       (len(packets)-old_input['packets'])*(extra['0xd0']+extra['0xd1']+extra['0xd2'])/1000,
                    optimistic_three_queries=cost(3),retain_old_query_count=cost(actual_queries),
                    variable_two_transfers_three_queries=cost(3,True),
                    variable_two_transfers_old_queries=cost(actual_queries,True),
                    max_queries_before_other_processing_60Hz=math.floor(budget_q),
                    physical_ms=None,new_IRQ_ROM_DMA_ms=None,net_Flash_B=None,net_LE=None)
            row['phases'][phase] = phase_result
        frames.append(row); prior=arrays; previous_map=current_map; banks[bank]=current_map; stale[bank].clear()
    groups = {}
    for name,subset in [('cold',frames[:2]),('initialized',frames[2:]),('dense',frames[46:51])]:
        summary = dict(n=len(subset),input_582_wire_B=sum(f['input_582_wire_B'] for f in subset)/len(subset),
            input_shift_legacy_wire_B=sum(f['input_shift_legacy_calls_wire_B'] for f in subset)/len(subset),
            input_fixed_fetch_wire_B=sum(f['input_fixed_fetch_wire_B'] for f in subset)/len(subset),phases={})
        summary['input_variable_fetch_wire_B'] = sum(f['input_variable_fetch_wire_B'] for f in subset)/len(subset)
        for phase in ('1','2'):
            summary['phases'][phase] = {}
            for label in ('B','C'):
                values = [f['phases'][phase]['cases'][label] for f in subset]
                summary['phases'][phase][label] = {
                    scenario:{key:sum(v[scenario][key] for v in values)/len(values)
                              for key in ('wire_ms','serial_IO_ms','calls','queries')}
                    for scenario in ('optimistic_three_queries','retain_old_query_count',
                                     'variable_two_transfers_three_queries','variable_two_transfers_old_queries')}
                summary['phases'][phase][label]['shift_only_582_IO_ms'] = sum(v['shift_only_582_IO_ms'] for v in values)/len(values)
                summary['phases'][phase][label]['optimistic_max_IO_ms'] = max(v['optimistic_three_queries']['serial_IO_ms'] for v in values)
                summary['phases'][phase][label]['variable_optimistic_max_IO_ms'] = max(v['variable_two_transfers_three_queries']['serial_IO_ms'] for v in values)
        groups[name] = summary
    result = dict(stage=583,passed=True,R3_selected=False,product_changed=False,frames=frames,groups=groups,
        evidence={name:sha(ROOT/'analysis'/name) for name in ('abi582-verification.json','body581-verification.json','whole580-verification.json')},
        analyzer_SHA256=sha(Path(__file__)),row_reference_SHA256=sha(ROOT/'tools/nes_row583.py'),
        scope='Exact input reconstruction and old output byte accounting. Fixed FETCH and coherent snapshot cost sensitivities; no achieved query reduction, retimed arrivals, ROM/IRQ/65816 or physical FPS.',
        protocol=dict(source_FETCH_success_B=292,source_final_confirm_B=36,output_snapshot_B=50,carrier_minimum_B=52,
                      variable_FETCH_overhead_B=38,variable_FETCH_driver_submissions=2,
                      source_busy_attempts_in_optimistic_case=0,output_queries_in_optimistic_case=3),
        unpriced=['Actual source-ready IRQ/retries and atomic cross-clock snapshot; variable FETCH header CRC/parse, CS-held CPU gap and continuation driver',
                  'Nonmap C retained integrity and producer history; B avoids this added history',
                  'Full ARM semantic/CRC/planner, FPGA row-query/base ports, actual65816 mask/CRC/DMA and VBlank',
                  'Net replacement of existing Flash/LE, fullRUN/IRQ stack and cancellation/identity implementation'])
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(groups['dense'],indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('data','capture','traces','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
