# SPDX-License-Identifier: MIT
"""Compare merged section-5 mode spans against the actual, labeled MMC551 workload."""
import argparse
import json
from pathlib import Path
from analyze_nes_phase537 import ROOT, Calendar, read, sha
from analyze_nes_seal538 import inspect_run
from analyze_nes_supply549 import compare, timeline
from analyze_nes_upload550 import last_frame
from analyze_nes_hardware552 import tail


def run(a):
    reference=read(ROOT/'analysis/upload550-verification.json')
    actual=read(ROOT/'analysis/trial551-verification.json')
    src=a.arm/'obj-nes-100/firmware.stm'
    phases=[]
    for i in (1,2):
        old=a.traces/f'nes-upload550-joint{i}'
        base=reference['phases'][i-1]['measured']
        assert all(sha(old/k)==h for k,h in base['pins'].items())
        folder=a.traces/f'nes-modes552-joint{i}'
        m=inspect_run(folder,a.plans,Calendar(a.traces/'nes-service509-rom03'),old,sha(src),reference['client'],first_bg_limit=3)
        audit=read(a.traces/f'nes-modes552-audit{i}'/'audit.json')
        assert audit['frames']==53 and audit['trace']==m['pins']['window.csv']
        d=compare(m,base)
        pre=timeline(folder,Calendar(a.traces/'nes-service509-rom03'))['display_to_head_VB']
        beam=last_frame(folder)['beam']
        later=[g for g,b in m['BG'].items() if b['relative_window']>base['BG'][str(g)]['relative_window']]
        gate=(not later and pre<=5 and not beam['waits'] and not any(m['waits'].values()) and all(v<0 for v in d.values()))
        phases.append(dict(start=m['pins'],phase=i,delta=d,dense_ms=m['dense_ms'],dense_VB=m['dense_VB'],pre952=pre,
            waits=m['waits'],beam957=beam,later_BG=later,gate=gate,delta_SPI_B=sum(m['SPI_B'].values())-sum(base['SPI_B'].values()),
            delta_E1_B=m['SPI_B']['0xe1']-base['SPI_B']['0xe1'],delta_packets=m['packets']-base['packets'],
            delta_ARM_instructions=m['ARM_instructions']-base['ARM_instructions'],ROM_reads=m['ROM_reads'],DMA_B=m['DMA_B'],
            tail={g:tail(folder,g) for g in (951,953,957)},audit=audit))
    return dict(phases=phases,gate=all(p['gate'] for p in phases),firmware=sha(src),Flash_B=src.stat().st_size,
                reference_firmware=actual['firmware_SHA256'],linked_reference=reference['ARM_SHA256'],
                scope='551 label executable text matches 550. Report-only candidate is a separate build. No new hardware FPS.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','traces','plans','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    a.out.write_text(json.dumps(run(a),indent=2)+'\n',newline='\n')
