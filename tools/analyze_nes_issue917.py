"""Compare accepted heads, true early VRAM DMA and absolute reveal/ACK clocks."""
import argparse
import json
from collections import Counter
from pathlib import Path

from analyze_nes_section909 import coverage, measure, read_csv
from nes_issue917 import ARM, BG, LEAD, PAIR, WORK
from nes_raw506 import sha
from test_nes_raw506_joint import MASTER


def summarize(folder, arm):
    measured, packets = measure(folder, arm)
    trace = read_csv(folder, 'window.csv')
    frame = [r for r in trace if r['g']=='908']
    heads = [r for r in frame if r['event']=='load']
    def point(row):
        return [int(row[k]) for k in ('clock','frame','line')]
    def starts(section):
        return [point(r) for r in heads if int(r['section'])==section and r['op']!='3']
    rows = {r['event']:point(r) for r in frame if r['op']=='3'}
    ids = [r for r in frame if r['event']=='ppu_dma' and r['op']=='-1']
    jobs = [j for line in (folder/'producer.jsonl').read_text().splitlines()
            if (j:=json.loads(line))['generation']==908]
    commands = [[round(e['clock']),e['bytes']] for e in json.loads((folder/'events.json').read_bytes())
                if e.get('generation')==908 and e.get('opcode')=='0xe9']
    timing = dict(begin=point(heads[0]), palette=starts(3), OAM=starts(4), section5=starts(5),
                  tile=[point(r) for r in heads if r['op']=='7'],
                  early_DMA=[point(r)+[int(r['value'])] for r in ids], jobs=jobs,E9=commands,
                  SEAL=rows['load'], upload=rows['upload165_entry'], reveal=rows['reveal'],
                  final_ACK=rows['ack'], E0=measured['frames'][908]['masterclocks']['E0_response'])
    timing['SEAL_to_upload_clocks']=timing['upload'][0]-timing['SEAL'][0]
    if 'wait169' in rows:
        timing['upload_wait']=rows['wait169']
    return measured, packets, timing


def analyze(temp):
    result={'clock_Hz':MASTER,'flash_limit':212992,'variants':{}}
    for name,arm in [('915stepfinal',ARM),('917issue',WORK),('917bg',BG),('917lead',LEAD),('917pair',PAIR)]:
        fw=arm/'link/src/obj-nes-100/firmware.stm'
        record=dict(firmware=sha(fw),bytes=fw.stat().st_size,cases={})
        def proof(filename):
            return json.loads((arm/'proof'/filename).read_bytes())
        assert all(proof(f)['firmware']==sha(fw) for f in ('timer.json','loader.json','menu.json'))
        assert proof('base/result.json')['firmware_sha256']==sha(fw) and proof('base/result.json')['safe_return']
        assert proof('timer.json')['passed'] and proof('menu.json')['rows']['normal']['released']
        rx=proof('sram.json')['cases']
        assert len(rx['normal']['d0_sites'])==4 and rx['normal']['checked_retire'] and not rx['bad-crc']['checked_retire']
        record['guards']=dict(SRAM_sites=4,CRC_fault_rejected=True,STOP=True,base_menu=True)
        trace=temp/f'nes-tile821-obj-jointmirror-p1-{name}-warm-pair'
        for case,status in [('group-stop',228),('bad-seal',224)]:
            path=trace/f'guard-{case}'
            guard=json.loads((path/'result.json').read_bytes())
            assert guard['passed'] and guard['commits']==4 and guard['last_status']==status
            assert sha(path/'retained.rgb')==sha(trace/'frame-908.rgb')
            record['guards'][case]=status
        result['variants'][name]=record
        for phase in (1,2):
            for cache in ('warm','cold'):
                def path(tag):
                    return temp/f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{cache}-pair'
                ref,old,baseline=summarize(path('915stepfinal'), ARM)
                cand,new,actual=summarize(path(name),arm)
                assert cand['client']==ref['client'] and cand['parameters']==ref['parameters']
                for g in old:
                    for pattern in ('frame-{}.rgb','colors636-{}.bin','map-{}.bin'):
                        assert sha(path(name)/pattern.format(g))==sha(path('915stepfinal')/pattern.format(g))
                assert all(cand['frames'][g]['section5_hash']==ref['frames'][g]['section5_hash'] for g in ref['frames'])
                for g in old:
                    for head in (1,3):
                        assert [p for p in old[g] if p[0]==head]==[p for p in new[g] if p[0]==head]
                def early(g):
                    return cand['preDMA'][g]
                # Require the actual destination addresses as well as the amount.
                def same_coverage(g):
                    return coverage(early(g)).keys()==coverage(ref['preDMA'][g]).keys()
                def saved(a,b):
                    return round((a-b)*1000/MASTER,4)
                def first_boundary(group):
                    return saved(baseline[group][0][0],actual[group][0][0])
                def tail(t):
                    return t['section5'][-2][0]
                record['cases'][f'{phase}-{cache}']=dict(
                    timing908=actual,intervals=cand['intervals'],ACK912=cand['final_ACK'],
                    palette_ahead_ms=first_boundary('palette'),OAM_ahead_ms=first_boundary('OAM'),
                    section5_tail_ahead_ms=saved(tail(baseline),tail(actual)),
                    upload_ahead_ms=saved(baseline['upload'][0],actual['upload'][0]),
                    upload_ahead_from_BEGIN_ms=saved(baseline['upload'][0]-baseline['begin'][0],actual['upload'][0]-actual['begin'][0]),
                    ACK912_ahead_ms=saved(ref['final_ACK'],cand['final_ACK']),
                    early908=early(908),early912=early(912),same_early912=same_coverage(912),
                    first_range908_same=bool(early(908) and early(908)[0][:3]==ref['preDMA'][908][0][:3]) if ref['preDMA'][908] else None,
                    same_packet_multiset_generations=sum(Counter(old[g])==Counter(new[g]) for g in old),
                    E1_wire_bytes=cand['wire']['0xe1'],RGB=8)
    board=temp/'nes-trial816-board914/nes_tile_bulk206.sv'
    assert sha(board).lower()=='8354cbae96e390c681bb1ea52f4abffb94c5fa496b7ab43cb83b6ea957e263c2'
    result['board_source']=dict(file=board.name,SHA256=sha(board))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    a=p.parse_args()
    a.output.write_text(json.dumps(analyze(a.temp),indent=2)+'\n',encoding='utf8')
