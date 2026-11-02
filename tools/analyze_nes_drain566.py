# SPDX-License-Identifier: MIT
"""Combine ARM, CPU bus strobes, RTL consumes and the existing 565 STA endpoints."""
import argparse
import csv
import json
from pathlib import Path
from nes_raw506 import sha


def main():
    p=argparse.ArgumentParser()
    for k in ('phase1','phase2','rtl','paths','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    rtl=json.loads(a.rtl.read_text())
    summary=dict(board_sources=rtl['board_files'],runs={},paths565=[],physical_baseline='MMC558',new_fit=False)
    normal_cases=['one_byte_left_reset','last_read_reset','before_first_store_reset','two_token_bytes_reset']
    for phase,path in enumerate([a.phase1,a.phase2],1):
        trace=json.loads(path.read_text())
        if phase==1:
            summary.update(arm=trace['arm'],rom=trace['rom'],mesen=trace['mesen'],spi_hz=trace['spi_hz'],
                           master_hz=trace['clock_hz'],stop_clock=trace['stop_clock'],earliest_start_clock=trace['start_clock'])
        assert trace['arm']==summary['arm'] and trace['rom']==summary['rom'] and trace['mesen']==summary['mesen']
        cases={}
        for k in normal_cases+['last_read_bypass']:
            rows=trace['cases'][k]
            clock=lambda e:next(r['clock'] for r in rows if r['event']==e)
            writes=[r for r in rows if r['event'] in ('old_write','unread_write','stopped_write')]
            bus=[(r['value']>>8,r['value']&255) for r in writes]
            assert bus==[(0x604c,1),(0x604d,0),(0x604e,0),(0x604f,0),(0x6050,165)]
            stage=writes[-1]['event']
            returns=rtl['cases'][f'phase{phase}_{k}']
            assert returns==(2 if stage=='old_write' else 1)
            cases[k]=dict(old_last_read=clock('old_last_read'),cut=clock('cancel'),old_write_clocks=[r['clock'] for r in writes],
                          old_commit_owner=stage.removesuffix('_write'),RTL_consumes=returns)
            if k in normal_cases:
                assert stage!='unread_write' and next(r for r in rows if r['event']=='fresh_commit')['reads']==320
                cases[k].update(new_reset_vector=clock('reset_vector'),new_last_read=clock('fresh_last_read'),
                                new_commit=clock('fresh_commit'),new_ordinary_ack=clock('fresh_packet_ack'))
            else:assert stage=='unread_write'
        summary['runs'][phase]=dict(arrivals=trace['arrivals'],raw_sha256=sha(path),cases=cases)
    prior=json.loads((Path(__file__).resolve().parents[1]/'analysis/reuse565-verification.json').read_text())
    with a.paths.open() as f:paths=list(csv.DictReader(f,delimiter='\t'))
    for key,(base,new) in prior['regressions'].items():
        clock=key.split("'")[1]
        matches=[r for r in paths if r['cut']==clock and float(r['slack'])==new[0] and r['check'] in key.lower()]
        assert len(matches)==1,key
        summary['paths565'].append(dict(**matches[0],MMC558_slack=base[0]))
    summary['bus_strobes']=['604c=01','604d=00','604e=00','604f=00','6050=a5']
    summary['limits']='Wire-only STOP/START bound. Modeled GPIO readback, verified image, transport replies and frame-loop return. 65816 local clock restarts on Mesen reset. RTL replays the ACK window against two synthetic 320-byte OBJ chunks. No physical reset, new fit, FPS or field failure measurement.'
    a.out.write_text(json.dumps(summary,indent=2)+'\n')


if __name__=='__main__':
    main()
