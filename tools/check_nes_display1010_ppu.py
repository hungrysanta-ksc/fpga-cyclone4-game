"""Check the board observer's PPU port choice against the executed 978 client."""
import argparse
import csv
import json
from pathlib import Path
from check_nes_output970 import packet_path, replay
from nes_display1010 import ROOT, once

def run(temp,phase):
    trace=temp/f'nes-tile821-obj-jointmirror-p{phase}-978returned-cold-pair'
    out=temp/f'nes-display1010-ppu-p{phase}'
    packets=[json.loads(row) for row in (trace/'packets.jsonl').read_text().splitlines()]
    target=[bytes.fromhex(row[2]) for row in packets if int.from_bytes(bytes.fromhex(row[2])[8:10],'little')==912]
    commands,_=packet_path(trace,912,expected_shape=(len(target),sum(p[0]==7 for p in target)))
    def observe(script):
        s=once(script,'local function write(a,v)','''local function write(a,v)
 if a==0x2100 then sample516('inidisp1010',v) end''')
        return once(s,'if dmaRemaining==1 then sample516("ppu_last") end',
             '''if dmaRemaining==1 then sample516("ppu_last");sample516("port1010",regs[0x4304]*256+(a&255)) end''')
    replay(temp,trace,out,'fixed',commands,912,observe=observe)
    base=json.loads((ROOT/'analysis/demo-loss1009-results.json').read_bytes())['replay978'][str(phase)]
    with (out/'window.csv').open() as f:
        rows=list(csv.DictReader(f))
    for gen,r in base.items():
        within=[x for x in rows if r['SEAL_header']<=int(x['clock'])<=r['final_ACK']]
        show=[(int(x['clock']),int(x['value'])) for x in within if x['event']=='inidisp1010']
        dma=[x for x in within if x['event']=='port1010']
        assert show==[(r['show'],15)],(gen,show)
        assert dma and int(dma[-1]['clock'])==r['last_dma'] and int(dma[-1]['value'])>>8==0x7f,(gen,dma[-1:])
        assert int(dma[-1]['value'])&255 in (4,0x18,0x19,0x22)
    print('PASS1010 PPU phase',phase,'seven post-SEAL publishes and final DMA port/bank')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('temp',type=Path);p.add_argument('phase',type=int,choices=(1,2))
    args=p.parse_args();run(args.temp,args.phase)
