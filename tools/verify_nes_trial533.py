# SPDX-License-Identifier: MIT
"""Bind MMC533 ROM, firmware, recovery, board and unfiltered timing to the selected 532 schedule."""
import argparse
from collections import Counter
import json
import re
import struct
import zlib
from pathlib import Path
from analyze_nes_transfer512 import fpga
from package_nes_window516 import ROOT, read, sha
from nes_schedule492 import funcs


def timing(board):
    raw=(board/'output_files/board.sta.summary').read_text()
    rows={k:[float(s),float(t)] for k,s,t in re.findall(
        r'Type\s*:\s*([^\n]+)\nSlack\s*:\s*([-\d.]+)\nTNS\s*:\s*([-\d.]+)',raw)}
    assert rows
    worst={}
    for k,(s,_) in rows.items():
        check=k.split(" Model ")[1].split(" '")[0]
        worst[check]=min(s,worst.get(check,s))
    unconstrained={}
    for view in ('implementation','nominal'):
        rpt=(board/(view+'-unconstrained204.rpt')).read_text()
        unconstrained[view]={k:[int(s),int(h)] for k,s,h in re.findall(
            r'; (Unconstrained [^;]+?)\s*;\s*(\d+)\s*;\s*(\d+)\s*;',rpt)}
        assert 'Unconstrained Input Ports' in unconstrained[view]
    return rows,worst,unconstrained


def verify(a):
    old=read(ROOT/'analysis/tile532-verification.json')
    assert old['target_met']['pair']
    assert sha(a.client/'sink165.sfc')==old['clients']['pair']['sha256']
    pins=read(a.board/'inputs533.json')
    assert len(pins)==73 and all(sha(a.board/n)==h for n,h in pins.items())
    assert [n for n in pins if sha(a.reference/n)!=pins[n]]==['sink-program.hex']
    assert sha(a.client/'sink-program.hex')==pins['sink-program.hex']
    # The physical ROM maps the LoROM header and vectors into its last 64 bytes.
    rom=(a.client/'sink165.sfc').read_bytes()
    assert len(rom)==32768 and bytes.fromhex((a.board/'sink-program.hex').read_text())==rom[:5056]+rom[-64:]
    base=read(ROOT/'analysis/flash529-package.json')
    assert sha(a.reference/'output_files/board.sof')==base['SOF_SHA256']
    result=fpga(a.board)
    selected=('implementation_setup_ns','implementation_hold_ns','nominal_setup_ns','nominal_hold_ns')
    assert 'Lite Edition' in (a.board/'flow.log').read_text(errors='replace')
    assert 'successful' in (a.board/'sta.log').read_text(errors='replace').lower()
    rows,worst,ucp=timing(a.board)
    prior,prior_worst,prior_ucp=timing(a.reference)
    # Quartus can print equally ranked endpoints in a different order. Compare
    # every reported column, including slack, delay, corner and multiplicity.
    def paths(folder,view):
        return Counter((folder/(view+'-paths204.tsv')).read_text().splitlines())
    board_cost={k:result[k] for k in ('LE','comb','FF','RAM_bits','M9K',*selected)}
    old_obj=a.old_arm/'obj-nes-100'
    obj=a.arm/'obj-nes-100'
    src,fw=[(p/'firmware.stm').read_bytes() for p in (old_obj,obj)]
    size,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==size+512<=0x34000 and crc==zlib.crc32(fw[512:]) and inv^crc==0xffffffff
    assert sha(old_obj/'firmware.stm')==old['ARM'] and src[32:].replace(b'529',b'533')==fw[32:]
    functions=funcs(obj/'sd2snes.elf')
    assert functions==funcs(old_obj/'sd2snes.elf')
    fwsha=sha(obj/'firmware.stm')
    windows=read(a.checks/'windows.json')
    assert windows['firmware_SHA256']==fwsha and [r['displays'] for r in windows['accepted']]==[2,2]
    assert windows['BSS_B']==old['BSS_B'] and windows['reset'] and windows['unfinished_excluded']
    guards=read(a.checks/'guards.json')
    assert guards['sha']==fwsha and guards['rows']==old['credit']['rows']
    menu=read(a.checks/'menu.json')
    assert menu['firmware']==fwsha and all(v['released']==int(k=='normal') for k,v in menu['rows'].items())
    base_return={}
    for k in ('none','program','done','busy','token'):
        v=read(a.checks/f'base-{k}/result.json')
        assert v['passed'] and v['firmware_sha256']==fwsha and v['safe_return']==v['base_restored']==int(k=='none')
        assert v['config_paths']==['/sd2snes/fpga_mmc533.bi3','/sd2snes/fpga_base.bi3']
        base_return[k]=v['safe_return']
    priority=read(a.priority/'result.json')
    assert priority==old['priority']['pair']
    replays=[]
    for p,d in zip(old['phases'],a.replays):
        proof=p['observations']['pair']['audit']
        assert read(d/'audit.json')==proof and sha(d/'window.csv')==proof['trace']
        assert all(p['variants']['pair']['targets'][str(g)]['final_waits']==0 for g in (952,954))
        replays.append(proof)
    return dict(candidate='MMC533',physical_verified=False,selected='pair',board=board_cost,
                relevant_paths_pass=all(result[k]>=0 for k in selected),all_STA_slacks_nonnegative=all(v>=0 for v in worst.values()),
                raw_worst_ns=worst,baseline_worst_ns=prior_worst,all_raw_summary_rows_equal=rows==prior,
                raw_summary_rows=len(rows),unconstrained=ucp,unconstrained_equal=prior_ucp==ucp,
                changed_board_inputs=['sink-program.hex'],inputs=pins,
                path_inventory_equal={v:paths(a.reference,v)==paths(a.board,v) for v in ('implementation','nominal')},
                SOF_SHA256=sha(a.board/'output_files/board.sof'),reports=result['report_SHA256'],
                raw_report_SHA256=sha(a.board/'output_files/board.sta.summary'),firmware_SHA256=fwsha,
                identical_functions=len(functions),Flash_B=len(fw),free_Flash_B=0x34000-len(fw),BSS_B=windows['BSS_B'],
                base_return=base_return,menu=menu,windows=windows['accepted'],priority_cases=len(priority),joint_replays=replays)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','reference','client','arm','old-arm','checks','priority','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--replays',nargs=2,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(verify(a),indent=2)+'\n',newline='\n')
