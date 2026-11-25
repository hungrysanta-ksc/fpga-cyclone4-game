"""Bound the final OBJ delay using two real traces and five independent RTL controls."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

from read_nes_tail1012 import ARM_TICK, MS, decode


def frame(path, target):
    data = path.read_bytes()
    run = decode(data, 1025)
    sample, = [s for s in run['samples'] if s['generation']==target]
    row, = [r for r in run['rows'] if r['tick']==sample['tick'] and r['generation']==target]
    groups = [p for p in sample['packets'] if p['op']==7]
    valid, kind, length, offset, gen, token = struct.unpack('<BBHHHI',bytes.fromhex(row['descriptor_hex']))
    assert valid and kind==1 and gen==target and len(groups)==row['chunks']
    final = groups[-1]
    assert final['offset']==offset and final['section']==kind and final['seq']==sample['packets'][-1]['seq']-1
    lo,hi = sample['last_tile_after_begin_ms_bounds']
    issued_upper = (final['issue']+1)*ARM_TICK
    # In poll(), an op7 is prepared only after a qualified E8 returned its current head.
    # This also bounds the previous reader's return without assuming a CPU ACK-to-consume latency.
    previous_visible_upper = (groups[-2]['ready']+1)*ARM_TICK
    hi = min(hi, (final['ready']+1)*ARM_TICK)
    assert previous_visible_upper<lo<=hi<=issued_upper
    prev_to_first = row['spacing_ms']-row['last_tile_to_show_ms']-row['supply_ms']
    publish_to_seal = row['last_tile_to_show_ms']-row['seal_to_show_ms']
    assert abs(sum((prev_to_first,row['supply_ms'],publish_to_seal,row['seal_to_show_ms']))-row['spacing_ms'])<1e-8
    return dict(generation=gen,tick=row['tick'],sha256=hashlib.sha256(data).hexdigest(),
                tiles=row['tiles'],chunks=len(groups),final_token=token,final_OBJ_B=length,
                group_offsets_B=[g['offset'] for g in groups],group_kinds=[g['section'] for g in groups],
                vblanks=round(row['spacing_ms']/16.639),
                previous_show_to_first_E9_ms=prev_to_first,first_E9_to_last_publish_ms=row['supply_ms'],
                publish_to_SEAL_accept_ms=publish_to_seal,SEAL_accept_to_show_ms=row['seal_to_show_ms'],
                last_publish_after_BEGIN_ms=[lo,hi],final_issue_after_BEGIN_ms=final['issue']*ARM_TICK,
                publish_to_ARM_issue_upper_ms=issued_upper-lo,
                reused_bank_previous_token=token-2,previous_reader_visible_by_ms=previous_visible_upper,
                reused_bank_free_before_publish_min_ms=lo-previous_visible_upper,
                penultimate_packet_credit_observed_by_ms=(groups[-2]['first_credit_observed']+1)*ARM_TICK,
                previous_vblank_end_to_publish_min_ms=max(0,16.639-2.45-row['last_tile_to_show_ms']-MS),
                previous_vblank_end_to_SEAL_min_ms=max(0,16.639-2.45-row['seal_to_show_ms']-MS))


def controls(folder):
    rows = []
    for case in range(5):
        lines = (folder/f'case{case}.log').read_text()
        record, = re.findall(r'^# PASS1026 (.*)$',lines,re.M)
        fields = dict((key,int(value)) for key,value in re.findall(r'(\w+)=(\d+)',record))
        assert fields['case']==case and fields['bytes']==640 and fields['final_grants']==24
        rows.append(fields)
    base,rom,bank,end,poll = rows
    assert base['fg_wait_nes']==base['bank_wait_host']==0
    assert rom['fg_wait_nes']==800 and rom['bank_wait_host']==0 and rom['last_done']>base['last_done']
    assert bank['bank_wait_host']>=800 and bank['fg_wait_nes']==0 and bank['last_done']>base['last_done']
    assert end['last_done']==base['last_done'] and end['end']>base['end'] and end['fg_wait_nes']==0
    assert poll['publish']==base['publish'] and poll['visible']==base['visible'] and poll['poll']>base['poll']
    assert all(r['publish']>base['publish'] for r in (rom,bank,end))
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('first','second','rtl_logs','output'):
        parser.add_argument(name,type=Path)
    a=parser.parse_args()
    first,second=frame(a.first,1657),frame(a.second,1619)
    assert second['tiles']==22 and second['chunks']==7 and second['final_token']==3135 and second['final_OBJ_B']==96
    report=dict(physical=[first,second],rtl=controls(a.rtl_logs),
                scope='Physical tags, request/grant times, exact bank-return edges and END time not captured. Controlled RTL cases use fixture tags, earlier group lengths, ROM responses and consumer timing.')
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
