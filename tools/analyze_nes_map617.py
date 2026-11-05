# SPDX-License-Identifier: MIT
"""Match map bytes, acceptance, early DMA, upload waits and final ACK across two phases."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from analyze_nes_dense519 import consumed_tiles
from analyze_nes_dma542 import partition
from analyze_nes_output531 import prior_blank_windows
from analyze_nes_phase537 import ROOT, contents, csv_groups, ms, one, read, sha
from analyze_nes_prefix523 import packet_trace, verified_visible_dma


def timing(folder):
    joint = read(folder/'joint.json')
    assert joint['passed'] and joint['commits'] == joint['map_WRAM_VRAM_verified'] == 53
    assert joint['last_status'] == 1 and joint['max_bulk_banks'] <= 2
    cpu = csv_groups(folder/'window.csv')
    beam = csv_groups(folder/'seal528.csv')
    packets = [json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
    events = defaultdict(list)
    for event in read(folder/'events.json'):
        events[event['generation']].append(event)
    tiles = read(folder/'obj-phases.json')
    cache = Counter(r[5] for frame in tiles.values() for r in frame.get('cache611', []))
    assert sum(cache.values()) == 5616 and cache['BG_hit'] == 48 and cache['OBJ_capture'] == 1200
    # Source capture starts 240 scanlines before its ready indication. Reusing
    # either of the two banks must follow its preceding checked EA retirement.
    reuse = [one(events[g+2],'source_begin')['capture_ready']-240*341*4-tiles[str(g)]['ea']
             for g in range(905,956)]
    assert min(reuse)>=0
    costs = partition(folder)
    display = {}
    watched = {}
    for g in range(905,958):
        rows = cpu[g]
        seal = [r for r in rows if r['op']==3]
        ack = one(seal,'ack')
        reveal = one(seal,'reveal')
        assert ack['value']==1 and ack['frame']==reveal['frame'] and reveal['line']>=225
        assert ack['clock']==joint['frames'][g-905]['ACK_masterclock']
        display[g] = reveal
        if g not in (951,952,953,954,955,957):
            continue
        prev = display[g-1]
        watched[g] = dict(display_VB=reveal['frame']-prev['frame'],
                          display_ms=ms(reveal['clock']-prev['clock']),
                          final_waits=costs[g]['final_wait_count'])
        if g not in (954,955):
            continue
        opened = one([r for r in rows if r['op']==1],'ack')['clock']
        def rel(t):
            return round(ms(t-opened),6)
        frozen = one(events[g],'bg_map_frozen')
        assert frozen['sha256']==sha(folder/f'map-{g}.bin')
        expected = (folder/f'map-{g}.bin').read_bytes()
        accepted = {}
        records = []
        sends = [r for r in events[g] if r['event']=='SPI' and r['opcode']=='0xe1']
        sends_by_end = {round(r['clock']):r for r in sends}
        grants = []
        for i,row in enumerate(rows):
            if row['section']==2 and row['event']=='ack':
                _,push,h,_ = packets[row['index']-1]
                b = bytes.fromhex(h)
                start = int.from_bytes(b[10:12],'little')
                data = b[16:]
                if b[0]==4:
                    assert len(data)==2
                    data = data*(int.from_bytes(b[14:16],'little')//2)
                assert b[0] in (2,4) and len(data)%64==0 and expected[start:start+len(data)]==data
                send, = [sends_by_end[t] for t in range(push-1,push+2) if t in sends_by_end]
                head, = [r for r in rows if r['index']==row['index'] and r['event']=='load']
                assert send['start']<push<=head['clock']<row['clock']
                for pos in range(start,start+len(data),64):
                    assert pos not in accepted
                    accepted[pos]=row['clock']
                records.append(dict(offset=start,B=len(data),E1_start_ms=rel(send['start']),push_ms=rel(push),
                                    load_ms=rel(head['clock']),accepted_ms=rel(row['clock'])))
            if row['event']=='idle524' and row['value']>=65536:
                dma=one(rows[i+1:i+2],'ppu_dma')
                offset=row['value']-65536
                assert all(accepted[j]<=row['clock'] for j in range(offset,offset+dma['value'],64))
                grants.append(dict(offset=offset,B=dma['value'],ms=rel(dma['clock']),line=dma['line'],
                                   blank_after_display=dma['frame']-prev['frame']))
        anchor=next(r for r in beam[g] if r['event']=='dma')
        matching,=[r for r in rows if r['event']=='ppu_dma' and r['clock']==anchor['clock']]
        head=one(seal,'load')
        blanks=sorted(prior_blank_windows(anchor,matching['frame'],opened,head['clock'],252))
        first_full_blank=sorted(prior_blank_windows(anchor,matching['frame'],opened,head['clock'],261))[0]
        waits=costs[g]
        watched[g].update(bg_frozen_ms=rel(frozen['clock']),map=records,early=grants,
                          BG_credit_attempts=[dict(ms=rel(r['clock']),used=r['outstanding'])
                            for r in events[g] if r['event']=='map_credit_attempt' and r['clock']<=frozen['clock']],
                          first_window_accepted_B=sum(r['B'] for r in records if r['accepted_ms']<rel(blanks[0][1])),
                          first_window_DMA_B=sum(r['B'] for r in grants if rel(first_full_blank[0])<=r['ms']<rel(first_full_blank[1])),
                          windows_ms=[[rel(lo),rel(hi)] for lo,hi in blanks],
                          last_window_heads=[dict(section=r['section'],op=r['op'],line=r['line'],ms=rel(r['clock']))
                            for r in rows if r['event']=='load' and blanks[-1][0]<=r['clock']<blanks[-1][1]],
                          SEAL_head_ms=rel(head['clock']),SEAL_head_line=head['line'],
                          SEAL_E1_start_ms=rel(one([r for r in sends if r['packet_opcode']==3],'SPI')['start']),
                          checks_ms=waits['checks_ms'],
                          upload_entry_line=one(seal,'upload165_entry')['line'],
                          wait_lines=[r['line'] for r in seal if r['event']=='wait169'],
                          upload_wait_ms=waits['serviced_VBlank_wait_ms']-waits['final_wait_ms'],
                          after_SEAL_DMA_B=waits['DMA_B'])
    rows,_,_,_ = packet_trace(folder)
    warm_dma = verified_visible_dma([r for r in rows if int(r['g'])>=905])
    return dict(watched=watched,last_ACK=ack['clock'],dense_VB=display[955]['frame']-display[950]['frame'],
                dense_ms=ms(display[955]['clock']-display[950]['clock'])/5,warm_DMA_checked=warm_dma,
                all_display_VB={g:display[g]['frame']-display[g-1]['frame'] for g in range(906,958)},
                wire_B=joint['wire_B'],cache=cache,min_capture_reuse_ms=ms(min(reuse)))


def compare(base,new,pins,firmware):
    for name,digest in pins.items():
        assert sha(base/name)==digest
    old,trial=[read(d/'joint.json') for d in (base,new)]
    for field in ('parameters','client_SHA256','ROM_read_allocations','vram_DMA_B'):
        assert old[field]==trial[field],field
    assert trial['firmware_SHA256']==sha(firmware)
    for d in (base,new):
        assert not any((d/f).exists() for f in ('fault.json','map-error.txt','callback-error.txt'))
    maps,raw=contents(base)
    other,other_raw=contents(new)
    assert raw==other_raw and consumed_tiles(base)==consumed_tiles(new)
    assert {k:v for k,v in maps.items() if k[0][0]!=7}=={k:v for k,v in other.items() if k[0][0]!=7}
    for g in range(905,958):
        for name in (f'frame-{g}.rgb',f'map-{g}.bin'):
            assert sha(base/name)==sha(new/name)
    b,c=timing(base),timing(new)
    gate=(c['watched'][952]['display_VB']==4 and c['watched'][957]['final_waits']==0
          and c['dense_VB']<b['dense_VB'] and c['dense_ms']<b['dense_ms'] and c['last_ACK']<b['last_ACK']
          and all(c['watched'][g]['upload_wait_ms']<b['watched'][g]['upload_wait_ms']
                  and c['watched'][g]['first_window_DMA_B']>b['watched'][g]['first_window_DMA_B']
                  for g in (954,955)))
    return dict(base=b,candidate=c,delta_last_ACK_ms=ms(c['last_ACK']-b['last_ACK']),gate=gate,
                pins={n:sha(new/n) for n in pins})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('traces','firmware','arm_guards','edges','staged','out'):
        parser.add_argument('--'+key,required=True,type=Path)
    args=parser.parse_args()
    ref=read(ROOT/'analysis/map616-beam-verification.json')
    phases=[compare(args.traces/f'nes-map616-beam{i}',args.traces/f'nes-map617-run{i}',
                    ref['phases'][i-1]['pins'],args.firmware) for i in (1,2)]
    arm=read(args.arm_guards)
    assert arm['firmware']==sha(args.firmware)
    assert {r['mode'] for r in arm['cases']}=={'normal','STOP','old_bulk','three_credits','tile_ready','bad_E8_CRC','ambiguous_E1'}
    edges=read(args.edges)
    assert {(r['generation'],r['fault']) for r in edges if 'fault' in r}=={
        (g,f) for g in (906,907) for f in ('missing','duplicate')}
    assert all(r['grant']==0 for r in edges if r['case'] in ('stop','head','both'))
    staged=read(args.staged)
    assert {r['boundary'] for r in staged}=={'staged-3','staged-4','staged-5'}
    assert all((r['generation'],r['status'],r['commits'])==(954,228,49) for r in staged)
    result=dict(phases=phases,gate=all(p['gate'] for p in phases),arm_guards=arm['cases'],SNES_edges=edges,staged_STOP=staged,
                ARM=sha(args.firmware),Flash_B=args.firmware.stat().st_size,client=ref['client_SHA256'])
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
