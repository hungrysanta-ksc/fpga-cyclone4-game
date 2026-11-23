"""Verify the linked ARM, PPU writes, measured SPI responses and placed mailbox paths."""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from analyze_nes_chr951 import board_cost, logtext
from analyze_nes_deadline922 import measure
from analyze_nes_palette921 import coverage
from analyze_nes_tail961 import milliseconds
from check_nes_blank959 import directory, read, sha, summary
from check_nes_case964 import check as check_case
from check_nes_menu533 import check as check_menu
from check_nes_obj964 import check as check_obj
from check_nes_sram897 import check_game_path
from nes_arm964 import ARM, WORK
from nes_order938 import empty_next_offer
from nes_page963 import PACKED

TAG='963bnes-mail964both'


def placed(board):
    with (board/'mail964.tsv').open() as f:
        rows=list(csv.DictReader(f,delimiter='\t'))
    edges={(f'held[{b}]',f'received[{b}]') for b in range(26)}
    edges.update([('request','req_sync[0]'),('acknowledge','ack_sync[0]'),
                  ('dr[1]','up_src[0]'),('sr[1]','up_dst[0]')])
    assert len(rows)==90 and len({r['corner'] for r in rows})==3
    for corner in {r['corner'] for r in rows}:
        assert {(r['from'],r['to']) for r in rows if r['corner']==corner}==edges
    result={}
    for kind in ('data','control'):
        chosen=[r for r in rows if r['from'].startswith('held')==(kind=='data')]
        slack=min(float(r['slack']) for r in chosen)
        delay=max(float(r['delay']) for r in chosen)
        assert slack>0 and delay<(23.808 if kind=='data' else 11.904)
        result[kind]=dict(paths=len(chosen),min_slack_ns=slack,max_delay_ns=delay)
    return result


def rtl(folder):
    stages={}
    for g in range(905,913):
        d=folder if g==912 else folder/f'gen{g}'
        log=d/'mail964.log'
        s=logtext(log)
        assert 'Errors: 0' in s
        chunks,size,hits,grants=map(int,re.search(r'PASS914 trace chunks=(\d+) bytes=(\d+) hits=(\d+) grants=(\d+)',s).groups())
        count,mismatches=map(int,re.search(r'E8914 compared=(\d+) different=(\d+)',s).groups())
        diffs=re.findall(r'E8914 difference edge=(\d+) token=(\d+)/(\d+) flags=(\d+)/(\d+) count=(\d+)/(\d+)',s)
        assert len(diffs)==mismatches
        origin=int((d/'origin914.txt').read_text())
        row=stages[g]=dict(chunks=chunks,bytes=size,hits=hits,foreground_grants=grants,polls=count,
                           E8_differences=mismatches,token_differences=sum(a!=b for _,a,b,*_ in diffs),
                           first_difference=(dict(clock=origin+int(diffs[0][0]),fields=list(map(int,diffs[0][1:]))) if diffs else None),
                           log_sha256=sha(log))
        if g==909:
            accept,base=map(int,re.search(r'PAGE964 accepted at=(\d+) base=(\d+)',s).groups())
            addresses=Counter(map(int,re.findall(r'AUX952 at=\d+ address=(\d+)',s)))
            assert base==3072 and addresses==Counter(base*16+t*16+r for t in range(16) for r in range(8))
            row.update(EB_latch_clock=origin+accept,unique_row_grants=len(addresses))
    return stages


def schedule(folder,reference,expected):
    outcome=summary(folder,reference)
    m,checks=measure(folder,ARM)
    charge=checks['params']['driver_extra_us']
    assert abs(charge.pop('0xeb')-charge['0xea'])<1e-6 and checks==expected
    f=m['frames'][912]
    pre=coverage([row for row in f['preDMA'] if row[3]==f['VBlank'][3]-1])
    assert (outcome['six'],outcome['D2_before_911_reveal'],len(pre))==(13,17,496)
    assert read(folder/'joint.json')['firmware_SHA256']==sha(ARM/'link/src/obj-nes-100/firmware.stm')
    assert sha(folder/'client.sfc')==sha(PACKED/'sink165.sfc')
    return dict(VBlanks=outcome['six'],reveals=outcome['reveals'],D2_before_show911=17,
                prior_DMA912_B=len(pre),ACK912=outcome['ACK912'],VRAM_bytes=outcome['VRAM_B'],
                EB=read(folder/'hint963.json')['hints'],joint_sha256=sha(folder/'joint.json'))


def analyze(temp):
    board=temp/'nes-trial816-board964'
    fw=ARM/'link/src/obj-nes-100/firmware.stm'
    base=read(ARM/'proof/base/result.json')
    menu=check_menu(ARM/'link/src','955')
    assert base['safe_return'] and base['base_restored'] and menu['rows']['normal']['released']
    assert base['firmware_sha256']==menu['firmware']==sha(fw)
    rx,ram,_=check_game_path(ARM/'link/src',order=empty_next_offer)
    assert rx['normal']['checked_retire'] and not rx['bad-crc']['checked_retire']
    guard=logtext(board/'guards964.log')
    assert 'PASS963 SPI CRC' in guard and 'Errors: 0' in guard
    fit=board_cost(board)
    assert fit['fit'] and min(fit['slack_ns'].values())>0 and fw.stat().st_size<=212992
    out=dict(reference='MMC955',hardware_FPS_measured=False, board=fit,mailbox=placed(board),
             flash_bytes=fw.stat().st_size,flash_margin=212992-fw.stat().st_size,firmware=sha(fw),
             case_mapping=check_case(),linked_page_selector_cases=check_obj(),base=base['config_paths'],
             menu_return_model=True,SRAM_D0_sites=len(rx['normal']['d0_sites']),SRAM_D0_address=hex(ram),
             bad_block_CRC_rejected=True,guard_sha256=sha(board/'guards964.log'),cases={})
    for p in (1,2):
        for cache in ('cold','warm'):
            reference=directory(temp,p,'961wirepair' if cache=='cold' else '961pair',cache)
            baseline,checks=measure(reference,WORK)
            folder=directory(temp,p,TAG,cache)
            result=out['cases'][f'{cache}-{p}']=schedule(folder,reference,checks)
            result['ACK_gain_vs961_ms']=milliseconds(baseline['final_ACK']-result['ACK912'])
            if cache=='warm':
                continue
            for name,status in [('bad-seal',224),('stop908',228)]:
                g=folder/('guard-'+name)
                r=read(g/'result.json')
                assert r['passed'] and r['commits']==3 and r['last_status']==status
                assert sha(g/'retained.rgb')==sha(folder/'frame-907.rgb')
            result['retained_after_STOP_and_bad_SEAL']=907
            result['rtl']=rtl(folder)
            replay=directory(temp,p,'964feedback','cold')
            result['feedback_schedule']=schedule(replay,reference,checks)
            result['measured_responses_used']=read(replay/'feedback964.json')
            result['feedback_rtl']=rtl(replay)
            if p==2:
                sample,=[r['at'] for r in result['measured_responses_used'] if r['changed']]
                def next_tile_spi(d):
                    return round(next(e['start'] for e in read(d/'events.json') if e.get('opcode')=='0xe1' and e['start']>sample))
                result['following_E1_clock']=[next_tile_spi(folder),next_tile_spi(replay)]
    return out


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.write_text(json.dumps(analyze(args.temp),indent=2)+'\n')
