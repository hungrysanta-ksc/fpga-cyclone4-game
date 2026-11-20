"""Replay screen 952's unmodified packets, varying only their availability time.

A sensitivity test on the 65816. A common advance does not grant the ARM
earlier capture, ROM or credit. Only coupled runs may establish those gains.
"""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_map830 import load, window
from test_nes_word873_idle import run_consumer


def run(temp, phase, lines, labels, seal_lines=None):
    base=temp/f'nes-tile821-demo-jointmirror-p{phase}-874-drain'
    suffix='' if seal_lines is None else f'-seal{seal_lines}'
    out=temp/f'nes-deadline875-consumer-p{phase}-lines{lines}{suffix}'
    out.mkdir()
    trace=window(base)
    def event(records,g,kind):
        return next(e for e in records if e['g']==g and e['event']==kind and
                    (kind!='ack' or e['op']==3))
    previous=event(trace,951,'ack')['clock']
    pushes=[]
    for entry in (base/'packets.jsonl').read_text().splitlines():
        _,clock,payload,bulk=json.loads(entry)
        wire=bytes.fromhex(payload)
        g=int.from_bytes(wire[8:10],'little')
        if g==952:
            advance=seal_lines if wire[0]==3 and seal_lines is not None else lines
            clock-=advance*1364
            assert previous<clock
        assert not pushes or clock>=pushes[-1][0]
        pushes.append((clock,'PUSH',payload,bulk))
        if g==952 and wire[0]==3:
            break
    else:
        raise ValueError('missing 952 SEAL')
    def instrument(lua):
        probes=['seal','coverage212','covered619','validate181','upload165_entry','group_ready538','wait169']
        return lua+'\n'+'\n'.join(
            f"emu.addMemoryCallback(function()log528('{name}',0)end,emu.callbackType.exec,{labels[name]})"
            for name in probes)
    result=run_consumer(temp,base,out,pushes,48,instrument)
    actual=window(out)
    assert event(trace,951,'reveal')==event(actual,951,'reveal')
    assert (base/'frame-952.rgb').read_bytes()==(out/'frame-952.rgb').read_bytes()
    ack=event(actual,952,'ack')['clock']
    if not lines:
        assert ack==event(trace,952,'ack')['clock']
    with (out/'seal528.csv').open() as f:
        marks=[[r['event'],int(r['clock']),int(r['line']),int(r['h'])] for r in csv.DictReader(f)
               if r['g']=='952' and r['event'] not in ('raw_enter','command')]
    assert {'validate181','upload165_entry','wait169','final_credit'}<={m[0] for m in marks}
    info=dict(advance_clocks=lines*1364,seal_advance_clocks=(lines if seal_lines is None else seal_lines)*1364,
              marks=marks,ack=ack,
              show=event(actual,952,'reveal'),previous=event(actual,951,'reveal'),
              seal=next(e for e in actual if e['g']==952 and e['event']=='load' and e['op']==3),
              dma=[[e['frame'],e['line'],e['value']] for e in actual if e['g']==952 and e['event']=='ppu_dma'])
    assert result['frames'][-1]['ACK_masterclock']==ack
    (out/'summary.json').write_text(json.dumps(info,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('lines',type=int)
    p.add_argument('labels',type=Path)
    p.add_argument('--seal-lines',type=int)
    a=p.parse_args()
    run(a.temp,a.phase,a.lines,load(a.labels),a.seal_lines)
