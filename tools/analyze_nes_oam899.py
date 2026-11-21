"""Compare packet contents, scanlines and completion clocks in the paired 898 clips."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_latency898 import CLK_MS, CLIPS, collect, read
from nes_raw506 import sha
from oam_nes_899 import BASE, WORK


def scan(folder):
    packets = {}
    for row in (folder/'packets.jsonl').read_text().splitlines():
        data = bytes.fromhex(json.loads(row)[2])
        gen = int.from_bytes(data[8:10], 'little')
        packets.setdefault(gen, []).append(data)
    with (folder/'window.csv').open() as f:
        marks = list(csv.DictReader(f))
    return collect(folder), packets, marks


def compare(temp, tag, firmware):
    result = {}
    for clip, frames in CLIPS.items():
        for phase in (1, 2):
            folders = [temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{t}' for t in ('898-897', tag)]
            logs = [read(folder/'joint.json') for folder in folders]
            assert logs[0]['parameters'] == logs[1]['parameters']
            assert logs[0]['client_SHA256'] == logs[1]['client_SHA256']
            assert logs[1]['firmware_SHA256'] == sha(firmware)
            base, candidate = map(scan, folders)
            rows = []
            for i, source in enumerate(frames[2:], 2):
                gen = 905+i
                a, b = base[0][gen], candidate[0][gen]
                for key in ('load','rgb','map_sha256','d1_count','d1_wire'):
                    assert a[key] == b[key], (source,key)
                def video(run, event):
                    return [[int(r['frame']),int(r['line'])] for r in run[2]
                            if int(r['g']) == gen and r['event'] == event]
                gap = [run[0][gen]['display'][0]-run[0][gen-1]['display'][0] for run in (base,candidate)]
                delta = {k:round((b['clock'][k]-a['clock'][k])/CLK_MS,4)
                         for k in ('planner','seal_issue','seal_accept','first_residual_dma','last_dma_end',
                                   'reveal','final_ack','valid_e0') if None not in (a['clock'][k],b['clock'][k])}
                row = dict(source=source, load=a['load'], gap=gap, seal=[a['seal'],b['seal']],
                           display=[a['display'],b['display']], delta_ms=delta)
                row['DMA_end'] = [video(run,'ppu_last')[-1] for run in (base,candidate)]
                # Retirements and bulk arrivals may interleave. Compare the actual payload and address
                # of each ordinary packet independently of its transport sequence number.
                def ordinary(run):
                    return [p[:2]+p[8:] for p in run[1][gen] if p[0] not in (1,7)]
                assert sorted(ordinary(base)) == sorted(ordinary(candidate)), source
                if gen==910:
                    row['residual_DMA'] = [[[d[0],d[1],d[2]] for d in x['dma'] if d[3]>=x['clock']['seal_accept']]
                                           for x in (a,b)]
                    # An observed event on or after line 247 gives a conservative lower bound
                    # on the time already lost past the end of the previous line 246.
                    marks = [r for r in candidate[2] if int(r['frame'])==b['display'][0]-1 and
                             247<=int(r['line'])<=261 and int(r['clock'])<b['clock']['seal_accept']]
                    if marks:
                        first=min(marks,key=lambda r:int(r['clock']))
                        row['prior_blank_sample']=[int(first[k]) for k in ('frame','line','clock')]
                        row['seal_past_prior_246_at_least_ms']=round(
                            (b['clock']['seal_accept']-int(first['clock']))/CLK_MS,4)
                    order=[]
                    for run in (base,candidate):
                        chosen=[p for p in run[1][gen] if p[:2]==bytes((9,4)) or
                                (p[:2]==bytes((2,5)) and len(p) in (217,256))]
                        order.append([(p[0],len(p)) for p in chosen])
                    assert order==[[(2,217),(2,256),(9,132)],[(9,132),(2,217),(2,256)]],order
                    x,y = [z['oam_packets'][0] for z in (a,b)]
                    row['OAM_delta_ms_from_planner'] = {k:round(((y[k]-b['clock']['planner'])-
                        (x[k]-a['clock']['planner']))/CLK_MS,4) for k in ('issue','load','ack')}
                rows.append(row)
            result[f'{clip}-{phase}'] = dict(rows=rows, sum_VBlank=[sum(r['gap'][j] for r in rows)
                                              for j in (0,1)], last_ACK_delta_ms=rows[-1]['delta_ms']['final_ack'])
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('temp','firmware','out'):
        p.add_argument(name,type=Path)
    p.add_argument('--tag',required=True)
    a=p.parse_args()
    runs=compare(a.temp,a.tag,a.firmware)
    arm=read(WORK/'check-arm.json')
    recovery=read(WORK/'base-g/result.json')
    assert arm['firmware']==recovery['firmware_sha256']==sha(a.firmware)
    assert recovery['passed'] and recovery['base_restored'] and arm['menu']['rows']['normal']['released']
    base=BASE/'src/obj-nes-100/firmware.stm'
    oam=read(WORK/'check-oam.json')
    assert oam=={'commits':5,'status':224}
    report=dict(clock_per_ms=CLK_MS,physical=False,control_SHA256=sha(base),candidate_SHA256=sha(a.firmware),
                image_B=[base.stat().st_size,a.firmware.stat().st_size],limit_B=212992,
                client_SHA256=read(a.temp/f'nes-tile821-early-jointmirror-p1-{a.tag}/joint.json')['client_SHA256'],
                d0_SRAM=arm['SRAM'],arm_checks=list(arm['cases']),normal_d0_sites=arm['cases']['normal']['d0_sites'],
                stop_checkpoints=arm['cases']['normal']['control']['checkpoints'],menu=True,base_recovered=True,
                wrong_oam_serial=oam,runs=runs)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
