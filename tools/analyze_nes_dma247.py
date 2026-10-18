# SPDX-License-Identifier: MIT
"""Summarize instruction-boundary measurements; never turn samples into WCET."""
from pathlib import Path
import argparse
import csv
import json
from nes_delta231 import BASE, sha


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def span(values):
    assert values
    return dict(samples=len(values),minimum=min(values),maximum=max(values))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--measurement',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();d=a.measurement.resolve();out=a.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    measured=read(d/'result.json');assert measured['passed'] and measured['commits']==71
    assert sha(d/'run/dma247.csv')==measured['timing_sha256']
    labels=read(BASE/'probes/nes-sparse232/scroll02/client/labels.json')
    rows=[{k:(v if k=='type' else int(v)) for k,v in r.items()}
          for r in csv.DictReader((d/'run/dma247.csv').open())]
    commands=[r for r in rows if r['type']=='list']
    finals=[r for r in rows if r['type']=='final']
    assert len(commands)==measured['vram_commands']==478
    assert sum(r['bytes'] for r in commands)==measured['vram_bytes']==133600
    assert len(finals)==71 and {r['generation'] for r in finals}==set(range(1,72))
    ack={}
    for line in (d/'run/bus.tsv').read_text().splitlines():
        cols=line.split('\t')
        if len(cols)==8 and cols[1]=='3' and cols[3]=='1':
            ack[int(cols[2])]=int(cols[7])
    assert len(ack)==71 and all(v>=225 for v in ack.values())
    no_wait=[r for r in commands if not r['waited']]
    warm_final=[r for r in finals if r['generation']>=3 and not r['waited']]
    assert all(r['bytes']==960 for r in warm_final)
    frame_rows=[]
    for gen in range(1,72):
        cc=[r for r in commands if r['generation']==gen]
        ff=next(r for r in finals if r['generation']==gen)
        frame_rows.append(dict(frame=gen+904,commands=len(cc),dma_bytes=sum(r['bytes'] for r in cc),
            commands_including_wait=sum(r['waited'] for r in cc),
            no_wait_command_master_clocks=sum(r['master_clocks'] for r in cc if not r['waited']),
            final_master_clocks=ff['master_clocks'],final_including_wait=ff['waited'],
            display_ack_scanline=ack[gen]))
    result=dict(stage=247,passed=True,frames=71,actual_65816_unchanged232=True,
        observed_commands=len(commands),observed_dma_bytes=sum(r['bytes'] for r in commands),
        no_wait_command_clocks=span([r['master_clocks'] for r in no_wait]),
        # 8 clocks/byte is a diagnostic normalization, not an asserted bound.
        no_wait_command_residual_after_8x_payload=span([r['master_clocks']-8*r['bytes'] for r in no_wait]),
        no_wait_warm_final_master_clocks=span([r['master_clocks'] for r in warm_final]),
        display_ack_scanline=span(list(ack.values())),
        body=dict(bytes=3910,capacity=3936,free=26,
            shared_append_bytes=labels['coverage212']-labels['append212'],
            list_loop_bytes=labels['final212']-labels['upload_loop212'],
            note='Shared append remains needed by metadata. These byte spans are not all reclaimable.'),
        retained_checks='71 commits; complete metadata, used VRAM, map/raw and all visible PPU writes inside VBlank checked by existing Lua.',
        limitations=['Waiting commands excluded from setup sample, not subtracted approximately.',
            'Final interval starts at final212 and ends before its final routine RTS; ACK/retire follows.',
            'Charge96/960 are scheduling units, not measured CPU cycles or independent time bounds.',
            'Observed maxima are not WCET; different alignment/IRQ/pad/raw/mode paths remain unbounded.',
            'No new scheduler/map decoder, no changed4192 gate, no physical or full-pipeline FPS proof.',
            'ACK scanline is observed remaining position only; no new safe deadline derived.'],
        new_scheduler_code_bytes=None,new_scheduler_cycle_bound=None,
        physical_fps=False,selected_implementation=None,
        input_hashes={str(f.relative_to(BASE)):sha(f) for f in
            (d/'result.json',d/'run/dma247.csv',d/'run/bus.tsv',d/'run/capture.lua',BASE/'probes/nes-sparse232/scroll02/client/labels.json')},
        measurement_script_sha256=measured['script_sha256'],analyzer_sha256=sha(Path(__file__)))
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    with (out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(frame_rows[0]),lineterminator='\n');w.writeheader();w.writerows(frame_rows)
    print(json.dumps({k:v for k,v in result.items() if k!='input_hashes'},indent=2))


if __name__=='__main__':main()
