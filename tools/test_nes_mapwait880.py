"""Isolate the cost of holding 950's scroll on the original 879 boot schedule."""
import argparse
import json
from pathlib import Path

from analyze_nes_map830 import load,window
from check_nes_scroll874 import receipt
from test_nes_word873_idle import run_consumer
from nes_raw506 import once


def run(temp,phase,held,audit=None,generation=950):
    assert generation==950 or (generation==959 and audit)
    assert not (held and audit)
    trial=temp/f'nes-tile821-demo-jointmirror-p{phase}-{audit or "879-static"}'
    out=temp/f'nes-mapwait880-consumer-{phase}-{audit or int(held)}'
    if generation!=950:
        out=out.with_name(out.name+f'-g{generation}')
    out.mkdir()
    r=receipt(trial,generation)
    frame,line,returned=r['map_return']
    if held:assert 0<line<225
    # Put the SPI start near the opening of this VBlank. The consumer's actual
    # scanline and DMA callbacks below decide what work fits, including refresh.
    shift=max(0,returned+(225-line)*1364-r['scroll_E1_start']) if held else 0
    ops=[]
    changed=False
    for raw in (trial/'packets.jsonl').read_text().splitlines():
        _,clock,data,bulk=json.loads(raw)
        b=bytes.fromhex(data)
        if int.from_bytes(b[8:10],'little')==generation:
            if b[:2]==bytes((2,5)) and b[10:14]==bytes((0,0,21,0)):changed=True
        ops.append((clock+(shift if changed else 0),'PUSH',data,bulk))
        if b[0]==3 and int.from_bytes(b[8:10],'little')==generation:break
    assert changed
    def audit_dma(lua):
        lua=once(lua,'local function write(a,v)','''local range880=nil
local dest880=0
local audit880=assert(io.open(ROOT..'/idle-vram.csv','w'))
local function write(a,v)''')
        lua=once(lua,'  if visible then\n   if dmaRemaining==1', '''  if visible and range880 then
   assert(a==0x2118 or a==0x2119)
   local offset=dmaLength-dmaRemaining
   audit880:write(string.format('%d,%d,%d,%d\\n',range880+offset,dest880+offset,a,v))
   if dmaRemaining==1 then audit880:flush();range880=nil end
  end
  if visible then
   if dmaRemaining==1''')
        return once(lua,'dmaRemaining=dmaLength;sample516("ppu_dma",dmaLength);',
            f'''dmaRemaining=dmaLength;
  if not packet and word(0x1226)=={generation} and regs[0x4301]==0x18 then
   assert(regs[0x4300]==1)
   range880=regs[0x4302]+256*regs[0x4303]+65536*regs[0x4304]
   dest880=2*(regs[0x2116]+256*regs[0x2117])
  end
  sample516("ppu_dma",dmaLength);''')
    run_consumer(temp,trial,out,ops,generation-905+1,audit_dma if audit else None)
    result=dict(shift_clocks=shift)
    def row(path,g,event):
        return next(r for r in window(path) if r['g']==g and r['event']==event)
    assert row(trial,generation-1,'reveal')==row(out,generation-1,'reveal')
    assert (out/f'frame-{generation}.rgb').read_bytes()==(trial/f'frame-{generation}.rgb').read_bytes()
    for e in ('reveal','load','ppu_dma'):
        result[e]=[r for r in window(out) if r['g']==generation and r['event']==e and (e!='load' or r['op']==3)]
    result['final_ACK']=next(r for r in window(out) if r['g']==generation and r['event']=='ack' and r['op']==3)
    if not held:
        assert result['reveal']==[row(trial,generation,'reveal')] and result['final_ACK']['clock']==r['ACK']
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int)
    p.add_argument('--held',action='store_true')
    p.add_argument('--audit',choices=('878-once','880-progress','880-end','881-range','882-oam','882-single','882-direct','883-shared','883-ack','884-room','886-static','887-seal'))
    p.add_argument('--generation',type=int,choices=(950,959),default=950)
    run(**vars(p.parse_args()))
