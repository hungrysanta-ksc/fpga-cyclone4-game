"""Same-work direct-map supply budget. Offline oracle, not target execution."""
import argparse
import binascii
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import struct
from statistics import mean

from nes_transfer512 import legacy_packets
from analyze_nes_body581 import output_decode
from analyze_nes_output615 import packets, csv_groups, one
from nes_schedule492 import funcs

ROOT = Path(__file__).resolve().parents[1]
MASTER = 21477272


def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def crc(b): return binascii.crc_hqx(b, 65535)
def ms(n): return n * 1000 / MASTER
def wire_ms(n): return n * 8 / 2625
def word(b, i): return int.from_bytes(b[i:i+2], 'little')


def source_maps(blocks, generation, expected):
    """Independently decode actual RTL sender's packed and fallback map blocks."""
    result = []; used = []
    for index, block in enumerate(blocks):
        if len(result) == len(expected): break
        b = bytes.fromhex(block['wire']); pos = 12 if index == 0 else 0
        start = len(result)
        if b[pos:pos+2] == b'\xff\xff':
            _, gen, offset, count, digest = struct.unpack_from('>5H', b, pos)
            assert gen == generation and offset == start
            pos += 10; cells = []
            while pos < len(b):
                code = b[pos]; pos += 1
                n = (code & 31) + 1 if code & 128 else code + 1
                if code & 128:
                    back = (1, 2, 4, 33)[(code >> 5) & 3]
                    assert back <= len(cells)
                    for _ in range(n): cells.append(cells[-back])
                else:
                    cells.extend(struct.unpack_from('<'+'H'*n, b, pos)); pos += 2*n
            assert len(cells) == count and crc(struct.pack('<'+'H'*count, *cells)) == digest
            result.extend(cells)
        else:
            while pos < len(b) and len(result) < len(expected):
                key, gen = struct.unpack_from('>HH', b, pos)
                assert gen == generation
                if key >> 12 == 1:
                    value = int.from_bytes(b[pos+4:pos+12], 'big'); n = value >> 60
                    assert key & 4095 == len(result) and 1 <= n <= 4
                    result.extend((value >> (15*i)) & 32767 for i in reversed(range(n)))
                    pos += 12
                elif key >> 8 == 0xd0:
                    value = int.from_bytes(b[pos+4:pos+6], 'big')
                    result.extend([value] * ((key & 255)+1)); pos += 6
                else: raise AssertionError(('map boundary', generation, index, key))
        assert result == expected[:len(result)]
        used.append(dict(index=index, cells=len(result)-start, source_B=2*(len(result)-start),
                         wire_B=len(b)+3))
    assert result == expected
    return used


def layout(arrays):
    maps, rows, objects, exceptions, raster, palette = arrays
    assert not exceptions  # all 53 pinned scenes; exceptional fallback remains unpriced
    groups = []
    for y in range(224):
        if raster[y] >> 49 & 1: continue
        src, fy, epoch = rows[y] >> 3, rows[y] & 7, raster[y] >> 44 & 31
        split = y == 0 or fy == 0 or bool(raster[y-1] >> 49 & 1)
        if y and not raster[y-1] >> 49 & 1:
            prev = rows[y-1] >> 3
            split |= fy != (rows[y-1] & 7)+1 or epoch != (raster[y-1] >> 44 & 31)
            split |= src != prev and maps[src*33:src*33+33] != maps[prev*33:prev*33+33]
        if split:
            groups.append((src, len(groups), (raster[y] & 31) | ((raster[y] >> 5) & 32), epoch))
    assert len(groups) <= 32
    return groups


def reconstruct(raw, groups, bindings, mask, previous, target, source_crc, row_crcs):
    assert len(raw) % 2 == 0 and crc(raw) == source_crc
    cells = struct.unpack('<'+'H'*(len(raw)//2), raw)
    out = bytearray(target)
    for row in range(64):
        if mask >> row & 1: out[row*64:row*64+64] = previous[row*64:row*64+64]
    seen = set()
    for src, dest, col, epoch in groups:
        assert src*33+33 <= len(cells) and dest < 32 and col < 64 and epoch < 2
        for x in range(33):
            c = (col+x) & 63; at = ((c//32)*1024+dest*32+c%32)*2
            if not mask >> (at//64) & 1: continue
            assert at not in seen; seen.add(at)
            cell = cells[src*33+x]; assert cell < 32768
            slot = bindings[cell & 8191]; assert 0 < slot < 1024
            out[at:at+2] = struct.pack('<H', slot | ((epoch*4+(cell >> 13)) << 10) | 0x2000)
    for row, expected in row_crcs.items():
        assert mask >> row & 1 and crc(out[row*64:row*64+64]) == expected
    assert len(row_crcs) == mask.bit_count()
    return bytes(out), len(seen)


def run(a):
    package = read(ROOT/'analysis/trial666-package.json')
    assert sha(a.arm/'obj-nes-100/firmware.stm') == package['firmware_SHA256']
    selected = read(ROOT/'analysis/entry665-verification.json')
    for name, expected in selected['inputs'].items():
        assert sha(a.traces/Path(name.replace('\\','/'))) == expected, name
    manifest = read(a.board/'inputs665.json')
    assert all(sha(a.board/n)==h for n,h in manifest['inputs'].items())
    fixture = read(a.data/'result.json'); assert fixture['passed']
    sender = read(a.sender); inputs = {}; phases = {}; plans = {}
    slots = {}; dictionaries = {}; source_blocks = {}; raw_maps = {}; groups = {}
    for g in range(905, 958):
        geom = a.data/f'frame{g}.geometry'; raw = a.data/f'frame{g}.raw'
        for p in (geom, raw):
            assert sha(p) == fixture['evidence_files'][p.name]; inputs[p.name] = sha(p)
        _, counts, arrays = legacy_packets(geom.read_bytes(), raw.read_bytes(), g)
        raw_maps[g] = struct.pack('<'+'H'*counts[0], *arrays[0])
        source_blocks[g] = source_maps(sender[str(g)], g, arrays[0])
        groups[g] = layout(arrays)
        pp = a.plans/f'frame{g}/plans.json'; plans[str(g)] = sha(pp)
        for bank, value in read(pp):
            q = bytes.fromhex(value); gen, slot, tag = struct.unpack_from('<3H', q)
            assert gen == g
            if q[6] == 0:
                assert q[7] == 255 and q[8:24] == bytes(i//2 for i in range(16))
                assert q[24:40] == b'\xff'*16
                slots[slot] = tag
            elif q[6] == 2: slots[slot] = None
        # Bind from actual historical plans, not inferred from the expected output.
        inverse = defaultdict(list)
        for slot, tag in slots.items():
            if tag is not None: inverse[tag].append(slot)
        dictionaries[g] = dict(inverse)
    guards = Counter()
    for phase in (1, 2):
        folder = a.traces/f'nes-entry665-a{phase}'
        cmd = packets(folder); events = read(folder/'events.json'); cpu = csv_groups(folder/'window.csv')
        by_input = defaultdict(list)
        for e in events:
            if e['event'] == 'SPI' and e['opcode'] in ('0xd1', '0xd2'):
                by_input[e.get('input_generation', e['generation'])].append(e)
        histories = [bytes(4096), bytes(4096)]; previous = bytes(4096); frames = {}
        for g in range(905, 958):
            wire = [bytes.fromhex(b['wire']) for b in sender[str(g)]]
            d1 = [e for e in by_input[g] if e['opcode'] == '0xd1']
            assert [e['bytes']-3 for e in d1] == list(map(len, wire)), (phase, g, 'D1 binding')
            bank = (g-905) % 2; target = bytearray(histories[bank]); mask = 0
            begin, = [h for h,_,_ in cmd[g] if h[0]==1]
            assert word(begin,18) == bank
            map_commands = [(h, t) for h, _, t in cmd[g] if h[1] == 2]
            for h, t in map_commands:
                off = word(h, 10); data = output_decode(h)
                assert off % 64 == len(data) % 64 == 0
                bits = ((1 << (len(data)//64))-1) << (off//64)
                assert not mask & bits; mask |= bits
                target[off:off+len(data)] = data
            expected = (folder/f'map-{g}.bin').read_bytes(); assert target == expected
            needed = []; bindings = {}; raw = raw_maps[g]
            for desc in groups[g]:
                src, dest, col, epoch = desc
                if not (mask >> dest & 1 or mask >> (dest+32) & 1): continue
                needed.append(desc)
                for x in range(33):
                    c = (col+x) & 63; at = ((c//32)*1024+dest*32+c%32)*2
                    if not mask >> (at//64) & 1: continue
                    tag = word(raw, (src*33+x)*2) & 8191
                    candidates = dictionaries[g][tag]
                    # Multiple current slots for a tag need a context-specific binding.
                    assert len(candidates) == 1, (g, tag, candidates)
                    bindings[tag] = candidates[0]
            digests = {r:crc(expected[r*64:r*64+64]) for r in range(64) if mask >> r & 1}
            restored, writes = reconstruct(raw, needed, bindings, mask, previous,
                                            histories[bank], crc(raw), digests)
            assert restored == expected
            source_damage = bytes([raw[0] ^ 1]) + raw[1:]
            try: reconstruct(source_damage, needed, bindings, mask, previous, histories[bank], crc(raw), digests)
            except AssertionError: guards['source_CRC'] += 1
            else: raise AssertionError('source corruption accepted')
            if bindings:
                bad = dict(bindings); tag = next(iter(bad)); bad[tag] ^= 1
                try: reconstruct(raw, needed, bad, mask, previous, histories[bank], crc(raw), digests)
                except AssertionError: guards['wrong_slot'] += 1
                else: raise AssertionError('slot corruption accepted')
            try: reconstruct(raw, needed, bindings, mask, previous, histories[bank], crc(raw), {})
            except AssertionError: guards['missing_row_expected'] += 1
            else: raise AssertionError('missing coverage accepted')
            # Hypothetical fixed16B payload header + row descriptors + tag/slot pairs
            # + independently produced CRC per uploaded64B row. E1 envelope19B/chunk.
            payload = 16 + 4*len(needed) + 4*len(bindings) + 2*mask.bit_count()
            chunks = math.ceil(payload/240); new_wire = payload+19*chunks
            old_wire = sum(len(h)+3 for h, _ in map_commands)
            es = [e for e in events if e['event'] == 'SPI' and e['opcode'] == '0xe1']
            map_spi = [next(e for e in es if abs(e['clock']-t)<=1) for _, t in map_commands]
            frozen = one([e for e in events if e['generation'] == g], 'bg_map_frozen')
            loads = {r['index']:r['clock'] for r in cpu[g] if r['event']=='load' and r['section']==2}
            consume_ms = sum(ms(r['clock']-loads[r['index']]) for r in cpu[g]
                             if r['event']=='ack' and r['section']==2)
            input_map = source_blocks[g]
            #12B immutable header (gen/token/start/count/CRC/flags),4B token/gen ACK.
            mirror_read = len(raw)+12*len(input_map); mirror_ack = 4*len(input_map)
            delta = sum(a != b for a, b in zip(previous, histories[bank]))
            reveal = one([r for r in cpu[g] if r['op'] == 3], 'reveal')
            final = one([r for r in cpu[g] if r['op'] == 3], 'ack')
            frame = dict(input_map_B=len(raw), input_map_blocks=len(input_map),
                input_D1_wire_B=sum(e['bytes'] for e in d1), input_map_D1_wire_B=sum(x['wire_B'] for x in input_map),
                input_D1_removed_B=0, extra_status_polls=None,
                map_packets=len(map_commands), map_E1_wire_B=old_wire, map_expanded_B=64*mask.bit_count(),
                upload_rows=mask.bit_count(), layout_groups=len(needed), dictionary_entries=len(bindings),
                reconstructed_cells=writes, full_row_base_copy_B=64*mask.bit_count(),
                proposed_payload_B=payload, proposed_E1_packets=chunks, proposed_E1_wire_B=new_wire,
                E1_wire_saving_B=old_wire-new_wire, gross_wire_saving_ms=wire_ms(old_wire-new_wire),
                current_map_SPI_call_ms=sum(ms(e['clock']-e['start']) for e in map_spi),
                current_map_consumer_ms=consume_ms,
                BG_frozen_clock=frozen['clock'],
                whole_recipe_delay_from_first_map_ms=ms(frozen['clock']-map_spi[0]['start']),
                mirror_read_B=mirror_read, mirror_ACK_B=mirror_ack,
                mirror_data_only_lower_ms=ms(8*mirror_read),
                conversion_check_setup_and_contention_budget_ms=wire_ms(old_wire-new_wire)-ms(8*mirror_read),
                FPGA_retained_snapshot_plus_recipe_B=len(raw)+payload,
                previous_vs_target_different_B=delta,
                first_map_D1_start=d1[0]['start'], last_map_D1_end=d1[len(input_map)-1]['clock'],
                first_map_E1_start=map_spi[0]['start'], last_map_ACK=max(r['clock'] for r in cpu[g] if r['event']=='ack' and r['section']==2),
                map_source_hold_ms=ms(map_spi[0]['start']-d1[len(input_map)-1]['clock']),
                reveal_clock=reveal['clock'], reveal_line=reveal['line'], last_ACK=final['clock'],
                map_SHA256=hashlib.sha256(expected).hexdigest())
            frames[g] = frame; histories[bank] = expected; previous = expected
        phases[phase] = dict(frames=frames, pins={n:sha(folder/n) for n in
            ('events.json','window.csv','packets.jsonl','joint.json','client.sfc')})
    assert all({k:v for k,v in phases[1]['frames'][g].items() if k not in
        ('BG_frozen_clock','whole_recipe_delay_from_first_map_ms','first_map_D1_start','last_map_D1_end','first_map_E1_start','last_map_ACK','map_source_hold_ms','reveal_clock','reveal_line','last_ACK','current_map_SPI_call_ms','current_map_consumer_ms')} ==
        {k:v for k,v in phases[2]['frames'][g].items() if k not in
        ('BG_frozen_clock','whole_recipe_delay_from_first_map_ms','first_map_D1_start','last_map_D1_end','first_map_E1_start','last_map_ACK','map_source_hold_ms','reveal_clock','reveal_line','last_ACK','current_map_SPI_call_ms','current_map_consumer_ms')}
        for g in range(905,958))
    symbols = funcs(a.arm/'obj-nes-100/sd2snes.elf')
    sizes = {name:size for name, address, size in symbols if name in
             ('map527','nes_sink527_early','packet_wire','span','span_piece','nes_sink212_seal',
              'build211','nes_resident211_slot','nes_native165_packet','restore650','nes_window184_drain')}
    entity_rows = []
    for line in (a.board/'output_files/board.fit.rpt').read_text(encoding='latin1').splitlines():
        fields = [x.strip() for x in line.split(';')]
        if len(fields)>15 and fields[-3] in ('nes_native_spi165','nes_geometry_sender653',
                'nes_native_export203','nes_sink_spi165','nes_bulk_aperture188','nes_tile_bulk206'):
            entity_rows.append(fields[1:-1])
    summary = {}
    for label, gs in [('cold',range(905,907)),('warm',range(907,958)),('dense',range(951,956))]:
        summary[label] = {key:mean(phases[1]['frames'][g][key] for g in gs) for key in
            ('map_E1_wire_B','proposed_E1_wire_B','E1_wire_saving_B','gross_wire_saving_ms',
             'conversion_check_setup_and_contention_budget_ms')}
    result = dict(stage=670, selected='MMC666', implementation=False, new_target_timing=False,
        new_synthesis=False, new_delivery=False, hypothetical_wire_is_not_speedup=True,
        source='actual653 sender bytes plus pinned geometry; map slots from cumulative actual538 plans',
        model='ordinary no-exception captures only; CRC16 is error detection, not collision-free proof',
        independent_reference_reconstructions=106, reference_guard_rejections=dict(guards),
        phases=phases, summary=summary, ARM_function_envelopes_B=sizes, net_verified_code_deletion_B=0,
        budget_gate=dict(passed=False, reason='Data representation proved; new target conversion/check/port latency and net linked resources unmeasured',
            A_existing_capture_reread='reject: COMMIT releases storage for next capture',
            A_retained_FPGA_snapshot='unselected:52/53 snapshots+recipes exceed one2KiB bank; tile ownership and full1056-cell bound not replaced',
            B_mirror_WRAM='bounded target-kernel/port budget probe only, not selected implementation',
            new_D1_bytes_removed=0, new_E0_polls_saved=0,
            recipe_readiness='Whole-BG OAM-clear marker is later than current early-map issue in some frames; incremental descriptors and repeated headers/bindings are unpriced',
            proposed_generic_snapshot_recipe_B=2112+16+4*1023+4*32+2*64,
            B_direct_LUT_WRAM_B=16384+2048+2112+128+128+16,
            B_full_LUT_clear_data_only_ms=ms(8*16384),
            Flash_free_B=496,LE_free=84,LAB_free=1,M9K_free=0,SNES_ROM_free_B=11),
        fit_entity_fields=entity_rows, net_verified_LE_deletion=0,
        pins=dict(sender=sha(a.sender), firmware=package['firmware_SHA256'], fixture=inputs, plans=plans,
                  fit=sha(a.board/'output_files/board.fit.rpt'),
                  ownership={n:sha(a.board/n) for n in ('nes_capture_lease201.sv','nes_native_spi165.sv',
                      'nes_native_compact181.sv','nes_sink_spi165.sv','nes_bulk_aperture188.sv')}))
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(reconstructions=106,guards=dict(guards),ARM_envelopes=sizes,
        frames={g:{k:v for k,v in phases[1]['frames'][g].items() if k in
            ('map_E1_wire_B','proposed_E1_wire_B','E1_wire_saving_B','input_map_blocks',
             'dictionary_entries','reconstructed_cells','conversion_check_setup_and_contention_budget_ms')}
             for g in (905,906,911,951,952,953,954,955,956,957)}),indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('data','plans','sender','traces','arm','board','out'):
        p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
