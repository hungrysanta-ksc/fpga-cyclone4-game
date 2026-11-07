# SPDX-License-Identifier: MIT
"""Compare the 665 wait/setup change against 664-all and physical-release MMC662."""
import argparse
import json
import re
from pathlib import Path
from analyze_nes_output664 import trace
from analyze_nes_output615 import csv_groups, one, ms, read, sha
from analyze_nes_frontier536 import contents
from analyze_nes_sender652 import budget
from analyze_nes_word660 import board_reports
from analyze_nes_reader661 import inventory


def analyze(a):
    phases={}
    for n in (1,2):
        folders={k:a.traces/f'{prefix}{n}' for k,prefix in
                 (('MMC662','nes-output664-base'),('all664','nes-output664-all'),('entry665','nes-entry665-a'))}
        rows={k:trace(p,a.traces/f'nes-front638-both{n}h') for k,p in folders.items()}
        for k,p in folders.items():
            assert read(p/'joint.json')['firmware_SHA256']==sha((a.base_arm if k=='MMC662' else a.arm)/'obj-nes-100/firmware.stm')
            assert contents(p)[1]==contents(folders['MMC662'])[1]
            assert {g:f['work'] for g,f in rows[k]['frames'].items()}=={g:f['work'] for g,f in rows['MMC662']['frames'].items()}
        assert sha(folders['entry665']/'client.sfc')==sha(a.client/'sink165.sfc')
        changes={}
        for k in ('MMC662','all664'):
            old=rows[k];new=rows['entry665']
            changes[k]=dict(dense_delta_ms=new['checked']['dense_mean_ms']-old['checked']['dense_mean_ms'],
                            last_ACK_delta_ms=ms(new['checked']['last_ACK']-old['checked']['last_ACK']),
                            interval_regressions=[g for g in old['intervals'] if new['intervals'][g]['VBlank']>old['intervals'][g]['VBlank']],
                            new_final_waits=[g for g in old['intervals'] if new['intervals'][g]['final_waits']>old['intervals'][g]['final_waits']])
        entry={};dma914={}
        for k,p in folders.items():
            cpu=csv_groups(p/'window.csv')[914]
            seal=[r for r in cpu if r['op']==3]
            entry[k]=[r for r in seal if r['event'].startswith('wait_return_') or r['event'] in ('load','wait169','final212','final_upload212_same_blank212','reveal','ack')]
            marks=csv_groups(p/'seal528.csv')[914]
            first_command=next(r for r in marks if r['event']=='command')
            first_dma=next(r for r in marks if r['event']=='dma')
            wake=next(r for r in seal if r['event'].startswith('wait_return_'))
            dma914[k]=dict(first_command=first_command,first_DMA=first_dma,wait_return=wake['clock'],
                           return_to_command_clocks=first_command['clock']-wake['clock'],
                           return_to_first_DMA_clocks=first_dma['clock']-wake['clock'])
        new=rows['entry665']
        gate=(new['intervals'][914]['VBlank']==3 and new['intervals'][914]['final_waits']==0 and
              new['intervals'][952]['VBlank']==3 and new['intervals'][957]['final_waits']==0 and
              new['details'][951]['marks']['reveal']['line']<=246 and
              changes['MMC662']['dense_delta_ms']<0 and changes['MMC662']['last_ACK_delta_ms']<0 and
              changes['all664']['last_ACK_delta_ms']<0 and not changes['all664']['interval_regressions'] and
              new['checked']['dense_VB']<=rows['all664']['checked']['dense_VB'] and
              not changes['MMC662']['new_final_waits'])
        for v in rows.values():
            v.pop('frames')
            for d in v['details'].values():d.pop('packets')
        phases[n]=dict(runs=rows,changes=changes,entry914=entry,DMA914=dma914,gate=gate,
                       strictly_faster_dense_than664=changes['all664']['dense_delta_ms']<0)
    guards=read(a.guards/'guards.json')
    assert guards['passed'] and guards['client_SHA256']==sha(a.client/'sink165.sfc')
    result=dict(candidate='entry665',physical_baseline='MMC662',phases=phases,
                timing_gate=all(p['gate'] for p in phases.values()),guards=guards,
                gate_description='Remove 914 extra wait; retain 952=3, dense<=664 VBlank count, 951<=246 and 957 final-wait=0; dense and last ACK faster than MMC662, last ACK faster than664. Report sub-line dense delta versus664 separately.',
                client=read(a.client/'build.json'),client_SHA256=sha(a.client/'sink165.sfc'),
                ARM_SHA256=sha(a.arm/'obj-nes-100/firmware.stm'),
                Flash_B=(a.arm/'obj-nes-100/firmware.stm').stat().st_size,
                source_hashes={n:sha(Path(__file__).with_name(n)) for n in ('nes_entry665.py','check_nes_entry665.py','analyze_nes_entry665.py','prepare_nes_entry665_board.py')},
                scope='Actual linked ARM and 65816; CPI2/IRQ/SPI model and repeating measured ROM calendar. No new physical FPS measurement.',
                inputs={str(p.relative_to(a.traces)):sha(p) for f in ('nes-entry665-a1','nes-entry665-a2') for p in (a.traces/f).iterdir() if p.name in ('joint.json','window.csv','seal528.csv','packets.jsonl','events.json','client.sfc')})
    if a.board:
        manifest=read(a.board/'inputs665.json')
        for name,h in manifest['inputs'].items():assert sha(a.board/name)==h
        changed=[n for n,h in manifest['inputs'].items() if h!=sha(a.base_board/n)]
        assert changed==['sink-program.hex'] and sha(a.board/'sink-program.hex')==sha(a.client/'sink-program.hex')
        boards={}
        for k,p in (('MMC662',a.base_board),('entry665',a.board)):
            b=budget(p);b['timing']=board_reports(p)
            b['LAB']=int(re.search(r'Total LABs:\s+partially or completely used\s+;\s*(\d+)',(p/'output_files/board.fit.rpt').read_text())[1])
            b['unconstrained']=inventory(p)
            assert b['SOF'] and b['LAB']<=963 and min(b['timing']['slack_ns'].values())>0
            assert all(float(v)==0 for v in re.findall(r'TNS\s+: ([-.\d]+)',(p/'output_files/board.sta.summary').read_text()))
            boards[k]=b
        for k in ('LE','comb','FF','RAM_bits','M9K','LAB','unconstrained'):
            assert boards['MMC662'][k]==boards['entry665'][k]
        assert boards['MMC662']['timing']['slack_ns']==boards['entry665']['timing']['slack_ns']
        result.update(boards=boards,board_inputs=manifest,
                      limited_delivery_gate=result['timing_gate'],
                      external_IO_signoff=False,new_hardware_test=False,
                      preserved_ARM_guards='analysis/output664-verification.json / checks and recovery; identical firmware',
                      capture_recovery='661 HDL and constraints byte-identical; prior RTL/physical662 recovery evidence retained')
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({n:dict(gate=p['gate'],changes=p['changes']) for n,p in phases.items()},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--board',type=Path)
    p.add_argument('--base-board',type=Path)
    for k in ('traces','base-arm','arm','client','guards','out'):p.add_argument('--'+k,type=Path,required=True)
    analyze(p.parse_args())
