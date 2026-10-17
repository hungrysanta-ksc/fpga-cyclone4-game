# SPDX-License-Identifier: MIT
"""Bind exact225/226 state proof, actualRUN, linked ARM and unchanged downstream path."""
from pathlib import Path
import argparse,json,re
from nes_fast226 import ROOT,BASE,sha,planner,runtime


def read(p):return json.loads(p.read_bytes())


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args();d=a.archive.resolve()
    assert not (d/'manifest01.json').exists()
    arm=d/'arm01';src=arm/'src';old=BASE/'probes/nes-scroll225';oldsrc=old/'arm01/src'
    prep=read(arm/'preparation-fast226.json')
    assert prep['source_sha256']==sha(ROOT/'tools/nes_fast226.py')
    for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(arm/n)==h,n
    assert (src/'nes_planner211.c').read_text()==planner((oldsrc/'nes_planner211.c').read_text())
    assert (src/'nes_native_runtime165.c').read_text()==runtime((oldsrc/'nes_native_runtime165.c').read_text())
    t=read(d/'test02/result.json');r=read(d/'runtime01/result.json');c=read(d/'check02/result.json')
    assert all(v['passed'] for v in [t,r,c])
    for n,h in t['public_sources'].items():assert sha(ROOT/n)==h,n
    assert sha(d/'test02/baseline/nes_planner211.c')==sha(oldsrc/'nes_planner211.c')
    assert sha(d/'test02/candidate/nes_planner211.c')==sha(src/'nes_planner211.c')
    traces=[d/f'test02/{kind}/trace.bin' for kind in ['baseline','candidate']]
    assert traces[0].read_bytes()==traces[1].read_bytes()
    for kind,path in zip(['baseline','candidate'],traces):assert sha(path)==t['results'][kind]['trace_sha256']
    assert all(t['results'][n]['rejected'] for n in ['negative_col0','negative_all'])
    work={}
    for kind in ['baseline','candidate']:
        text=t['results'][kind]['output'];assert 'frames=1939 ' in text and 'boundaries=11 ' in text
        m=re.search(r'WORK226 fine_calls=(\d+) fine_exception_scans=(\d+)',text);assert m
        work[kind]=dict(zip(['fine_calls','fine_exception_scans'],map(int,m.groups())))
    for n,h in r['source_hashes'].items():
        assert sha(d/'runtime01'/n)==h,n
        if (src/n).exists():assert sha(src/n)==h,n
    assert 'frames=9 ' in r['results']['runtime'] and r['results']['runtime'].count('PASS METADATA203 fault=')==6
    assert 'maximum_bytes=3521' in r['results']['budget']
    assert c['remaining_margin']==1792 and c['foreground_bound']==35008 and c['ram_static']==28116
    assert c['firmware_sha256']==sha(src/'obj-nes-100/firmware.stm')
    assert c['elf_sha256']==sha(src/'obj-nes-100/sd2snes.elf')
    unchanged={}
    for n in ['nes_resident211.c','nes_resident211.h','nes_native165.c','nes_native165.h',
              'nes_plan_service200.c','nes_plan_service200.h','nes_native_sink165.c','nes_native_sink165.h',
              'nes_sink_bulk195.inc','nes_sink_window184.c','nes_runtime_board165.inc','nes_run136.inc']:
        assert sha(src/n)==sha(oldsrc/n),n;unchanged[n]=sha(src/n)
    # Reuse actual C+65816 evidence only with exact old source pins and ROM.
    snes=read(old/'snes02/result.json');assert snes['passed']
    pixels=0
    for i in range(1,31):
        x=old/f'snes02/reference-normal/frame-{i}.rgb';y=old/f'snes02/candidate-normal/frame-{i}.rgb'
        assert x.read_bytes()==y.read_bytes() and x.stat().st_size==183552;pixels+=x.stat().st_size//3
    assert pixels==1835520
    public=['tools/nes_fast226.py','tools/test_nes_fast226.py','tools/test_nes_fast226_runtime.py','tools/check_nes_fast226_arm.py','tools/nes_fast226_evidence.py']
    result=dict(passed=True,trial_gates_pass=True,physical=False,fps60=False,new_fit=False,new_snes_rom=False,
        selected=dict(arm='arm01',test='test02',runtime='runtime01',check='check02'),
        equivalence=dict(frames=1939,trace_bytes=t['trace_bytes'],sha256=sha(traces[0]),
            scope='Exact emitted plan structs, full video, pointer-neutralized resident state and both banks; unchanged plan order/slot keys. Profile counters are separate host-only copies.',
            fault_boundaries=11,negative_controls=2),
        work_counts=work,work_scope='Synthetic fine() calls and scans inside fine(), not all CPU operations. New per-group exception mask scan is not included. No elapsed time/FPS inference.',
        reused_snes=dict(source='nes-scroll225/snes02',frames=30,pixels=pixels,reexecuted=False,
            reason='Same downstream source/ROM and exact plan/video/cache output. New actualRUN separately executed.',result_sha256=sha(old/'snes02/result.json')),
        runtime=dict(frames=9,faults=6,receiver_boundaries=9,source_hashes=r['source_hashes']),
        budget=dict(schema=226,fields=23,added_static_bytes=96,maximum_text_bytes=3521,buffer_bytes=4096,
            begin='guard + resident_begin + sink_begin',finish='plan finish: final flush/bulk drain/END; includes service and waits',
            caveat='10ms quantization; successful subphases may survive a later failed frame; no CPU-only/PSRAM-only or exact per-scene timing'),
        arm={k:c[k] for k in ['firmware_bytes','ram_static','foreground_bound','irq_reserve','remaining_margin','firmware_sha256']},
        baseline=dict(merge='db37aa3f8ad2e9c94718cb388804ff7cd11838d7',fpga_sha256=read(old/'release01/result.json')['fpga_sha256']),
        unchanged_sources=unchanged,gates={n:sha(d/n) for n in ['test02/result.json','runtime01/result.json','check02/result.json','arm01/preparation-fast226.json']},
        public_sources={n:sha(ROOT/n) for n in public},
        limitations=['No real SMB3 scrolling capture replay or full board cosimulation.',
            'Wire traffic/tile output unchanged for matched input. Faster planner may expose more E8 waiting; polling count alone is not acceptance.',
            'General exception fallback and whole ingress/finish/SEAL costs remain. 60fps unproven.',
            'ARM budget is conservative static call-graph bound, not measured high water. SaveSRAM/GBC164 unchanged.'],
        next='Package unchanged225FPGA+226ARM; actual first level numeric1+A thenRIGHT+B/A scrolling,3TXT/menu/audio/input/video. No newFIT/unchanged225044 repeat. Judge scroll presentation and receive/planner/begin/finish/seal together against16.67ms.')
    text=json.dumps(result,indent=2)+'\n';(d/'analysis.json').write_text(text,encoding='utf8')
    (ROOT/'analysis/fast226-verification.json').write_text(text,encoding='utf8')
    print(json.dumps(dict(passed=True,work_counts=work,arm=result['arm'],equivalence=result['equivalence'])))
if __name__=='__main__':main()
