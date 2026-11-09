"""Budget a DMA progress boundary from pinned 678 traces; no retimed replay."""
import argparse
import json
from pathlib import Path

from analyze_nes_output615 import csv_groups, ms, read, sha
from nes_rom636 import BOOT, STORED, DEST, pack


def unpack(prefix, stream):
    """Independent byte decoder, including overlapping backwards references."""
    out = bytearray(prefix)
    i = 0
    counts = dict(literal_tokens=0, reference_tokens=0, decoded_B=0)
    while stream[i]:
        token = stream[i]
        i += 1
        if token < 128:
            out.extend(stream[i:i+token])
            i += token
            counts['literal_tokens'] += 1
            counts['decoded_B'] += token
        else:
            length = (token & 63) + 3
            if token & 64:
                source = len(out) - stream[i]
                i += 1
            else:
                source = int.from_bytes(stream[i:i+2], 'little') - DEST
                i += 2
            assert 0 <= source < len(out)
            for offset in range(length):
                out.append(out[source+offset])
            counts['reference_tokens'] += 1
            counts['decoded_B'] += length
    assert i + 1 == len(stream)
    return bytes(out), counts


def run(a):
    prior = read(Path('analysis/handoff678-verification.json'))
    board = read(Path('analysis/entry665-verification.json'))
    pins = {}
    for name in ('nes_sink_bus165.sv', 'nes_sink_bridge165.sv', 'nes_sink_spi165.sv'):
        pins[name] = sha(a.board / name)
        assert pins[name] == board['board_inputs']['inputs'][name]
    assert sha(a.client / 'sink165.sfc') == board['client_SHA256']
    assert sha(a.arm / 'obj-nes-100/firmware.stm') == prior['firmware']
    phases = {}
    for n in (1, 2):
        old = prior['phases'][str(n)]
        folder = a.traces / f'nes-handoff678-credit{n}'
        for name, digest in old['pins'].items():
            assert sha(folder / name) == digest, (n, name)
        d = old['details']['956']['678']
        base = d['previous_reveal']
        rows = csv_groups(folder / 'window.csv')[956]
        fill = [p for p in d['packets'] if p['section'] == 5 and p['expanded_B'] == 1100]
        assert len(fill) == 1
        fill = fill[0]
        after = next(p for p in d['packets'] if p['load'] > fill['ack'])
        guards = [r for r in rows if r['event'] == 'fill_service545' and fill['load'] < r['clock'] < fill['ack']]
        chunks = [r for r in rows if r['event'] == 'zero_dma' and fill['load'] < r['clock'] < fill['ack']]
        assert len(chunks) == 18 and sum(r['value'] for r in chunks) == 1100
        vb = [r for r in guards if 225 <= r['line'] <= 252 and r['value'] < 1100]
        # A follower is already queued throughout every eligible fill boundary.
        blocked = [r for r in vb if after['push'] <= r['clock'] < after['load']]
        assert vb and len(blocked) == len(vb)
        maps = [p for p in d['packets'] if p['section'] == 2]
        last_map = max(p['ack'] for p in maps)
        assert last_map < fill['load']
        accepted = set()
        for p in maps:
            accepted.update(range(p['offset'], p['offset'] + p['expanded_B'], 64))
        early = d['early_DMA_B']['map']
        remaining = len(accepted) * 64 - early
        assert early == 128 and remaining == 896
        dma = [r for r in rows if r['event'] == 'ppu_dma' and r['op'] == 3]
        assert [r['value'] for r in dma[1:4]] == [384, 128, 384]
        map_span = ms(dma[4]['clock'] - dma[1]['clock'])
        map952 = max(p['ack'] for p in old['details']['952']['678']['packets'] if p['section'] == 2)
        phases[n] = dict(
            reference_dense_delta_ms=old['dense_delta_ms'],
            reference_last_ACK_delta_ms=old['last_ACK_delta_ms'],
            protected=old['protected'],
            last_map_ACK_ms=ms(last_map-base),
            fill_load_ms=ms(fill['load']-base), fill_ACK_ms=ms(fill['ack']-base),
            fill_consumer_ms=ms(fill['ack']-fill['load']),
            fill_wire_B=fill['wire_B'], fill_expanded_B=1100,
            fill_DMA_B=sum(r['value'] for r in chunks),
            fill_guard_points=guards, eligible_nonterminal_guard_count=len(vb),
            follower_queued_at_every_eligible_guard=True,
            priority_preserving_opportunities_inside_fill=0,
            follower_push_ms=ms(after['push']-base), follower_load_ms=ms(after['load']-base),
            map_accepted_B=len(accepted)*64, map_early_B=early, map_remaining_B=remaining,
            final_three_map_starts_to_next_DMA_ms=map_span,
            map_data_only_lower_bound_ms=ms(remaining*8),
            positive_net_gain_required_ms=max(0,old['last_ACK_delta_ms']),
            last_map952_ACK_clock=map952,
            last_map952_ACK_ms=ms(map952-old['details']['952']['678']['previous_reveal']),
            pins=old['pins'],
        )
        assert all(old['protected'].values())
    info = read(a.client/'build.json')
    body = (a.client/'body.bin').read_bytes()
    assert len(body) == info['body_bytes'] == 5792
    packing = []
    for prefix in range(896, 127, -128):
        encoded = pack(body, prefix)
        decoded, counts = unpack(body[:prefix], encoded)
        assert decoded == body
        packing.append(dict(prefix_B=prefix, encoded_B=len(encoded),
            physical_free_B=STORED-BOOT-prefix-len(encoded),
            extra_tail_B_per_boot_pass=896-prefix, **counts))
    assert packing[0]['physical_free_B'] == 11 and packing[-1]['physical_free_B'] == 207
    result = dict(stage=679, kind='boundary_budget_review_not_target_implementation',
        selected='MMC666', experimental_base='678 credit', phases=phases,
        proposed_boundary=dict(name='E0 bit3 MAP_DMA_PROGRESS',
            meaning='At least one accepted map DMA returned and its cursor retired while the packet queue stayed empty since the last E1 acceptance. Not full-map completion.',
            io_proposal='00601D <- A5, through existing synchronized SNES write capture',
            publish='After synchronous MDMAEN return and actual map cursor retirement only; never on admission or READ.',
            invalidate='E1 acceptance, ACK staging/publish, reset, disable, STOP/fault dominate publication; drop publication while used!=0, !ack_valid or checking.',
            observe='Atomic existing E0 snapshot+CRC8; only with empty queue, accepted=retired=sent and full latest ACK identity/magic/status validation in current BEGIN context.',
            authority='Advisory scheduling only. Never releases staging, changes bank history, retires a queue packet, substitutes for final ACK, or authorizes a new COMMIT.',
            stale='Loss is allowed: no wait-until-bit loop, no timeout dependency. One-bit event is not a count, frontier, or all-DMA-done certificate.',
            wire_B_added_to_existing_E0=0, extra_E0_if_needed_B=20,
            allocated_extra_host_register_bits=2, allocated_extra_snapshot_bits=0,
            allocated_new_identity_bits=0, allocated_new_FPGA_RAM_B=0,
            allocated_ARM_static_B=0, allocated_SNES_persistent_WRAM_B=0,
            implementation_verified=False, CDC_races_verified=False),
        alternatives=dict(
            independent_mailbox='Not selected: duplicates identity/CDC/lifetime and cannot be credited free.',
            queued_fence=dict(min_E1_B=19,min_E0_B=20,wire_lower_bound_ms=39*8/2625000*1000,
                verdict='Not selected: holding head for next VBlank adds latency and changes packet priority; no phase-safe completion budget.'),
            ACK_bit_annotation='Not selected as live feedback: a later idle DMA would leave old ACK unchanged; rewriting/publishing ACK while empty faults or changes retirement.',
            cooperative_fill='Not selected under unchanged new-packet priority: every eligible 64B guard already has a follower queued.'),
        resource_caps=dict(whole_LE=15408,whole_LAB=963,whole_M9K=56,
            selected_LE=15324,selected_LAB=962,selected_M9K=56,
            incremental_LE_ceiling=84,incremental_LAB_ceiling=1,new_M9K_ceiling=0,
            ARM_Flash_B=212800,ARM_Flash_cap_B=212992,ARM_net_growth_ceiling_B=192,
            SNES_body_B=5792,SNES_body_cap_B=5984,SNES_net_body_growth_ceiling_B=192,
            FPGA_measured_delta=None,ARM_measured_delta=None,SNES_measured_delta=None,
            allocated_deleted_legacy_registers=0,allocated_deleted_LE=0,
            note='Hard pass/fail caps, not measured costs or a fit prediction. New port decode/gating/routing charged; existing snapshot/CRC/CDC reused only after edge tests.'),
        unchanged_body_packing=packing, packing_scope='Offline exact-byte roundtrip only; no new executable ROM or boot cycle measurement. Smaller prefix decodes and compares more bytes on both boot passes.',
        source_pins=dict(board=pins,client=sha(a.client/'sink165.sfc'),body=sha(a.client/'body.bin'),
            ARM=prior['firmware'],prior=sha(Path('analysis/handoff678-verification.json')),
            packer=sha(Path('tools/nes_rom636.py')),analyzer=sha(Path(__file__))),
        next_gate='First bounded publication/clear/STOP/identity race prototype with full ARM link and exact ROM packing. Pair only with an event-driven ARM producer yield that makes a genuinely empty queue; no new-packet priority bypass. If full caps pass, replay unchanged work on both starts before one whole Lite FIT/STA.',
        new_full_replay=False,new_FIT_STA=False,new_physical_test=False,
        simultaneous_timing_improvement_proven=False,
        scope='Pinned 678 actual linked M4/65816 trace audit plus byte-exact offline ROM repacking. No synthetic timing values are reported as a candidate run.')
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({n:{k:p[k] for k in ('fill_consumer_ms','eligible_nonterminal_guard_count','priority_preserving_opportunities_inside_fill','map_remaining_B','final_three_map_starts_to_next_DMA_ms')} for n,p in phases.items()},indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('traces','board','client','arm','out'):
        parser.add_argument('--'+key,type=Path,required=True)
    run(parser.parse_args())
