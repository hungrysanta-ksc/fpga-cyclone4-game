# SPDX-License-Identifier: MIT
"""Compare short-repeat DMA with the identical completion-counter control."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_drain543 import delta
from analyze_nes_frontier536 import ledger
from analyze_nes_phase537 import Calendar, csv_groups, ms, one, read, sha
from analyze_nes_seal538 import inspect_run

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ((951, 1249, 194), (957, 1121, 66))


def packets(folder):
    return [bytes.fromhex(json.loads(line)[2]) for line in (folder/'packets.jsonl').read_text().splitlines()]


def target_cost(folder, audit, fixed):
    wire = packets(folder)
    cpu = csv_groups(folder/'window.csv')
    markers = csv_groups(audit/'decode544.csv')
    results = {}
    for gen, offset, length in TARGETS:
        idx, = [i for i,b in enumerate(wire,1) if b[:2] == bytes([4,5])
                and int.from_bytes(b[8:10],'little') == gen and int.from_bytes(b[10:12],'little') == offset]
        packet = wire[idx-1]
        assert int.from_bytes(packet[14:16],'little') == length and packet[16] == packet[17]
        rows = [r for r in cpu[gen] if r['index']==idx]
        marks = [r for r in markers[gen] if r['index']==idx]
        first = one(marks,'zero_chunk516' if fixed else 'repeat1814')['clock']
        accepted = one(marks,'accepted')['clock']
        ack = one(rows,'ack')
        assert ack['value']==0 and first < accepted < ack['clock']
        chunks = [r['value'] for r in rows if r['event']=='zero_dma']
        if fixed:
            expected = [min(64,length-at) for at in range(0,length,64)]
            assert chunks==expected
            checks = [r['value'] for r in rows if r['event']=='fill_service545' and first<=r['clock']<accepted]
            assert checks==[*range(0,length,64),length]
        else:
            assert chunks==[]
        seal = [r for r in cpu[gen] if r['op']==3]
        final = one(seal,'final212')['clock']
        waits = sum(r['event']=='wait169' and r['clock']>=final for r in seal)
        results[gen]=dict(packet=idx,offset=offset,length=length,DMA_chunks=chunks,loop_ms=ms(accepted-first),
                          load_to_packet_ACK_ms=ms(ack['clock']-one(rows,'load')['clock']),final_VBlank_waits=waits)
    return results


def analyze(args):
    prior = read(ROOT/'analysis/front544-verification.json')
    original = read(ROOT/'analysis/first539-verification.json')
    windows = read(ROOT/'analysis/windows541-verification.json')
    firmware = sha(args.arm/'obj-nes-100/firmware.stm')
    assert firmware == windows['firmware_SHA256']
    build = read(args.client/'build.json')
    candidate = sha(args.client/'sink165.sfc')
    reference = args.client.parent/'reference01'/'sink165.sfc'
    assert sha(reference)==original['client']
    assert (args.client/'sink165.sfc').read_bytes()[0x13be]==reference.read_bytes()[0x13be]==255
    assert build['body_bytes']==len((args.client/'body.bin').read_bytes())<=4960
    phases = []
    for phase in (1,2):
        base = args.traces/f'nes-drain543-base{phase}'
        run = args.traces/f'nes-repeat545-run{phase}'
        audit = args.traces/f'nes-repeat545-audit{phase}'
        base_audit = args.traces/f'nes-front544-audit-decode-base{phase}'
        control = prior['phases'][phase-1]['base']
        assert sha(base/'client.sfc')==original['client']
        assert all(sha(base/f)==h for f,h in control['pins'].items())
        assert sha(base_audit/'decode544.csv')==control['decode']['markers_SHA256']
        row = inspect_run(run,args.plans,Calendar(args.calendar),base,firmware,candidate)
        proof = read(audit/'audit.json')
        assert proof['frames']==53 and proof['trace']==sha(run/'window.csv')
        assert sha(run/'tile532.csv')==sha(audit/'tile532.csv')
        before = target_cost(base,base_audit,False)
        after = target_cost(run,audit,True)
        blanks = ledger(run,audit,targets=((951,2560),(957,2048)))
        last_blank = {}
        for gen in (951,957):
            def last_window(windows):
                last=max(windows,key=lambda w:w['open_ms'])
                return dict(queue_at_open=last['queue_at_open'],
                            packet_ms=sum(h['ms'] for h in last['head_service']),
                            early_map_B=sum(h['B'] for h in last['grants'] if h['offset'] is not None))
            last_blank[gen]=dict(base=last_window(control['map_VBlank'][str(gen)]['windows']),
                                 candidate=last_window(blanks[gen]['windows']))
        comparison = delta(row,control)
        versus_original = delta(row,original['phases'][phase-1]['row'])
        gate = all(d['last_ACK_ms']<0 and d['dense_ms']<0 and d['dense_VB']<0 and not d['later_BG_windows']
                   for d in (comparison,versus_original)) and not any(row['waits'].values())
        frozen = args.traces/f'nes-repeat545-fixed{phase}'
        fixed = read(frozen/'run/audit.json')
        assert fixed['frames']==53 and read(frozen/'pins.json')['packets']==control['pins']['packets.jsonl']
        def warm_span(folder):
            events=csv_groups(folder/'window.csv')
            def reveal(g):
                return one([r for r in events[g] if r['op']==3],'reveal')['clock']
            return ms(reveal(957)-reveal(906))/51
        phases.append(dict(phase=phase,base_dense_ms=control['dense_ms'],base_dense_VB=control['dense_VB'],
                           base_targets=before,targets=after,last_preSEAL_blank=last_blank,candidate=row,delta=comparison,versus_MMC540=versus_original,
                           mean_51_intervals_ms=dict(control=warm_span(base),candidate=warm_span(run)),
                           fixed_arrival_ACK_delta_ms=ms(fixed['last_ACK_delta_clocks']),gate=gate,replay=proof,
                           decode_SHA256=sha(audit/'decode544.csv')))
    guards={n:read(args.traces/f'nes-repeat545-{n}/result.json') for n in ('stop01','seal01','priority01')}
    assert len(guards['stop01'])==8 and all(r['status']==0xe4 and r['commits']==r['generation']-905 for r in guards['stop01'])
    assert len(guards['seal01'])==7 and all(r['status']==0xe4 for r in guards['seal01'])
    assert Counter(r['group'] for r in guards['priority01'])=={'single':12,'merge':6,'missing':2,'duplicate':2}
    menu=read(args.menu)
    assert menu['firmware']==firmware and menu['marker_cases']==4
    assert all(r['released']==int(k=='normal') for k,r in menu['rows'].items())
    return dict(control_firmware=firmware,completion_windows=windows['accepted'],program_SHA256=candidate,
                body_B=build['body_bytes'],mapped_B=build['program_bytes'],new_WRAM_B=build['new_WRAM_B'],
                phases=phases,gate=all(p['gate'] for p in phases),guards=guards,menu=menu,
                scope='Two coupled 53-frame schedules with linked ARM, SPI, IRQ, two slots and 65816. Fixed captures and repeating eight-frame boot ROM grants.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('traces','arm','client','plans','calendar','menu','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=analyze(args)
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'gate':result['gate'],'deltas':[p['delta'] for p in result['phases']]}))
