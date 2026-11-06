# SPDX-License-Identifier: MIT
"""Reconcile accepted uploads and visible ACKs in each paired 53-screen run."""
import argparse
import json
from pathlib import Path
from analyze_nes_dma542 import csv_groups, ms, one, read, sha
from analyze_nes_export636 import run, board
from analyze_nes_oam618 import work


def trace(folder, source):
    r = run(folder, source)
    heads = [json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
    cpu = csv_groups(folder/'window.csv')[952]
    tiles = csv_groups(folder/'tile532.csv').get(952, [])
    ordinary = {}
    issued = dict(map=0,tile=0)
    for row in cpu:
        if row['event'] != 'ack':
            continue
        _,push,hex_packet,_ = heads[row['index']-1]
        packet = bytes.fromhex(hex_packet)
        op, section = packet[:2]
        offset = int.from_bytes(packet[10:12],'little')
        literal = int.from_bytes(packet[12:14],'little')
        expanded = int.from_bytes(packet[14:16],'little')
        if section==2 and op in (2,4,6):
            issued['map'] += expanded or literal
        if op==7:
            issued['tile'] += expanded
        if section==5 and offset in (0,21):
            ordinary[offset] = dict(push=push,accepted=row['clock'])
    # The pre-SEAL MDMA groups contain only checked map and tile grants.
    early_tile = sum(row['n'] for row in tiles if row['event']=='tile')
    sealed = r['sealed952']['DMA_B']
    early = {k:total-sealed.get(k,0) for k,total in issued.items()}
    assert early['tile']==early_tile
    grants = [row for row in cpu if row['event']=='ppu_dma' and row['op']==-1]
    assert sum(row['value'] for row in grants)==sum(early.values())
    assert all(225<=row['line']<=261 for row in grants)
    event_stream=read(folder/'events.json')
    seal952=next(e['start'] for e in event_stream if e['generation']==952 and e.get('packet_opcode')==3)
    early953=sum(e['generation']==952 and e.get('input_generation')==953 and e.get('opcode')=='0xd2'
                 and e['clock']<seal952 for e in event_stream)
    ui = r['rows']
    accepted_map=max(row['clock'] for row in cpu if row['event']=='ack' and row['op'] in (2,4,6) and row['section']==2)
    accepted_tile=max(row['clock'] for row in cpu if row['event']=='ack' and row['op']==7)
    capture=one([e for e in event_stream if e['generation']==953],'source_begin')['capture_ready']
    seal951=[row for row in csv_groups(folder/'window.csv')[951] if row['op']==3]
    old_display=one([row for row in cpu if row['op']==3],'reveal')
    seal953=[row for row in csv_groups(folder/'window.csv')[953] if row['op']==3]
    obj953=read(folder/'obj-phases.json')['953']
    milestones953={key:ms(obj953[key]-old_display['clock']) for key in ('first_BG561','end_accepted','last_obj_rom_response')}
    first_rom=next(row for row in obj953['cache611'] if row[0]==0 and row[-1]=='ROM')
    milestones953['first_BG_ROM_request_ms']=ms(first_rom[2]-old_display['clock'])
    milestones953['first_BG_ROM_response_ms']=ms(first_rom[4]-old_display['clock'])
    for event in ('load','reveal','ack'):
        row=one(seal953,event)
        milestones953[event]=dict(ms=ms(row['clock']-old_display['clock']),line=row['line'],blanks=row['frame']-old_display['frame'])
    checked=one(seal951,'final212')
    revealed=one(seal951,'reveal')
    return dict(pins=r['pins'], image=r['measured']['firmware_SHA256'], client=r['measured']['client_SHA256'],
                parameters=r['measured']['parameters'], slots=r['measured']['max_bulk_banks'],
                conservative_source_margin_ms=ms(r['min_first_D1_after_conservative_ready_clocks']),
                bank_reuse_margin_ms=ms(r['min_bank_reuse_gap_clocks']),
                IRQ=r['measured']['SysTick_calls'], cache=r['cache'], accepted952=issued,
                before_SEAL952=early, sealed952=r['sealed952'], grants=[(row['frame'],row['line'],row['value']) for row in grants],
                scroll_ACK_to_padding_push_ms=ms(ordinary[21]['push']-ordinary[0]['accepted']),
                display951=[ui[951]['interval_VB'],ui[951]['line']],display952=ui[952]['interval_VB'],
                ready953_minus_last_map_tile_ms=ms(capture-max(accepted_map,accepted_tile)),
                check_to_reveal951_ms=ms(revealed['clock']-checked['clock']),final_entry951_line=checked['line'],
                pre_SEAL_953_pops=early953,pre_ACK_953_pops=ui[953]['pops_before_old_ACK'],
                from_display952_to_953=milestones953,intervals=[ui[g]['interval_VB'] for g in range(951,956)],display952_line=ui[952]['line'], wait957=ui[957]['final_waits'],dense_VB=r['dense_VB'],
                dense_mean_ms=r['dense_mean_ms'], last_ACK=r['last_ACK'])


def compare(a, name, firmware, check_suffix):
    cases=[]
    previous=read(Path('analysis/export636-verification.json'))
    head_first=name in ('head','rx','late','one','two')
    for tag in ('d','h'):
        for phase in (1,2):
            suffix=f'{phase}{tag}'
            prior=a.traces/f'nes-export636-run{suffix}'
            trial=a.traces/f'nes-dma637-{name}{suffix}'
            assert all(sha(prior/key)==digest for key,digest in previous['phases'][phase-1][tag]['pins'].items())
            assert work(trial)==work(prior)
            if head_first:
                assert sha(trial/'client.sfc')==sha(a.build/'client01/sink165.sfc')
            else:
                assert sha(prior/'client.sfc')==sha(trial/'client.sfc')
            base, candidate=(trace(d,prior) for d in (prior,trial))
            assert base['parameters']==candidate['parameters'] and base['accepted952']==candidate['accepted952']
            delta=ms(candidate['last_ACK']-base['last_ACK'])
            saved={kind:candidate['before_SEAL952'][kind]-base['before_SEAL952'][kind] for kind in ('map','tile')}
            gates=dict(frame952=candidate['display952']==4, frame951=candidate['display951'][0]==3 and candidate['display951'][1]<=246,
                       frame957=candidate['wait957']==0, dense=candidate['dense_VB']<base['dense_VB'],ACK=delta<0)
            dense_delta_ms=candidate['dense_mean_ms']-base['dense_mean_ms']
            cases.append(dict(boot='during' if tag=='d' else 'after',phase=phase,reference=base,candidate=candidate,
                              extra_early_B=saved,delta_ACK_ms=delta,dense_delta_ms=dense_delta_ms,both_ms_faster=(delta<0 and dense_delta_ms<0),gates=gates,pass_all=all(gates.values())))
    arm=a.build/firmware/'src/obj-nes-100/firmware.stm'
    assert all(c['candidate']['image']==sha(arm) for c in cases)
    checks={k:read(a.build/(k+check_suffix+'.json')) for k in ('quiet','rx','history')}
    checks['menu']=read(a.build/f'menu{firmware[-2:]}.json')
    assert all(ch['firmware']==sha(arm) for ch in checks.values())
    bss=int((a.build/firmware/'size.log').read_text().splitlines()[1].split()[2])
    return dict(phases=cases,pass_all=all(c['pass_all'] for c in cases),Flash_B=arm.stat().st_size,BSS_B=bss,ARM_checks=checks)


def analyze(a):
    result=dict(after_scroll=compare(a,'run','arm01',''),after_map=compare(a,'map','arm02','-map'),
                head_map=compare(a,'head','arm02','-map'),receive=compare(a,'rx','arm03','-rx'),
                late_receive=compare(a,'late','arm04','-late'),
                two=compare(a,'two','arm05','-two'),one=compare(a,'one','arm06','-one'),
                edges=read(a.traces/'nes-dma637-edges01/edges.json'),
                head_edges=read(a.traces/'nes-dma637-head-edges05/edges.json'),
                head_late_horizontal='Directed head fixture did not reach a latch at horizontal clock >=1000 on line 252.',
                head_boot=read(a.traces/'nes-dma637-boot01/result.json'),
                board={k:board(a.traces/k) for k in ('nes-export636-board01','nes-dma637-board01')},
                source_sha={path.name:sha(path) for path in [*Path(__file__).parent.glob('*637.py'),
                    Path(__file__).with_name('nes_rom636.py'),Path(__file__).with_name('check_nes_overlap634_arm.py')]},
                scope='53 displays per run using the linked ARM and emulated 65816, measured SPI costs, recorded ROM arbitration and actual SysTick. FPGA RTL from 636.')
    # Only the last 1/2/3 receive slots differ. Verify that each compiled
    # intervention starts from the same observed ARM and PPU history at 952.
    matched={}
    for mode in ('one','two'):
        for phase in ('1d','2d','1h','2h'):
            source=a.traces/f'nes-dma637-late{phase}'
            trial=a.traces/f'nes-dma637-{mode}{phase}'
            def prefix(folder):
                rows=read(folder/'events.json')
                end=next(i for i,e in enumerate(rows) if e['generation']==952 and e['event']=='source_begin')
                # Early source_begin(952) can occur while output 951 is live.
                return rows[:end], [x['ACK_masterclock'] for x in read(folder/'joint.json')['frames'][:47]]
            base_prefix, base_ACK=prefix(source)
            other_prefix,other_ACK=prefix(trial)
            assert base_prefix==other_prefix and base_ACK==other_ACK
            matched[f'{mode}{phase}']=dict(events=len(base_prefix),ACKs=len(base_ACK))
    result['matched_prefix']=matched
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('traces','build','out'):p.add_argument('--'+n,required=True,type=Path)
    analyze(p.parse_args())
