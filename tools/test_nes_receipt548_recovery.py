# SPDX-License-Identifier: MIT
"""Cancel receipt, SEAL or partial raw DMA, then restore the exact invalidated bank."""
import argparse
import csv
import json
from pathlib import Path
from types import SimpleNamespace
from nes_raw506 import once
from replay_nes_receipt548 import observe
import replay_nes_map527 as replay
from test_nes_seal538_stop import exercise


def cancel(lua,labels,mode):
    size=12 if 'generic548' in labels else 2
    base=0x14ac if size==12 else 0x14a2
    hooks=f"""local armed548,sampled548=false,false
local writes548=0
local function target548()return packet and pw(8)==FAULT end
emu.addMemoryCallback(function()
 if target548() and pb(0)==3 then writes548=writes548+1 end
end,emu.callbackType.exec,{labels['write547']})
"""
    if mode=='partial-receipt':
        hooks+="""emu.addMemoryCallback(function()
 if target548() and pb(0)==4 and pb(1)==5 and pw(14)>64 and word(0x60)==pw(14)-64 then armed548=true end
end,emu.callbackType.exec,ADDR)
""".replace('ADDR',str(labels['zero_chunk516']))
    elif mode=='before-raw':
        hooks+=f"emu.addMemoryCallback(function()if target548() and pb(0)==3 then armed548=true end end,emu.callbackType.exec,{labels['exit547']})\n"
    else:
        hooks+=f"emu.addMemoryCallback(function()if target548() and pb(0)==3 and writes548==1 then armed548=true end end,emu.callbackType.exec,{labels['advance547']})\n"
    lua=once(lua,'local function loaded()',hooks+'local function loaded()')
    lua=once(lua,'if a==0x6001 then','if a==0x6001 then if armed548 then sampled548=true;return 128 end')
    lua=once(lua,'if a>=0x4300 and a<=0x4306 then',"if sampled548 and a==0x420b then error('DMA after sampled STOP') end\n if a>=0x4300 and a<=0x4306 then")
    return once(lua,"assert(lastStatus==0xe4,'STOP status')",f"""assert(sampled548 and lastStatus==0xe4 and word(0x125a)==0)
   local bank=word(0x1034);local f=assert(io.open(ROOT..'/partial.bin','wb'))
   for i=0,{size-1} do f:write(string.char(rd({base}+bank*{size}+i))) end
   for i=0,2047 do f:write(string.char(emu.read((bank==0 and 0x5000 or 0x9000)+i,emu.memType.snesVideoRam))) end
   f:write(string.char(rd(0x125a+bank),writes548));f:close()""")


def test(args,gen,mode):
    exercise(args,gen,mode,edit_packet_case=lambda s:cancel(s,args.labels,mode))
    image=args.out/f'{gen}-{mode}'/'partial.bin'
    data=image.read_bytes()
    size=12 if 'generic548' in args.labels else 2
    base=0x14ac if size==12 else 0x14a2
    assert len(data)==size+2050 and data[-2:]==bytes([0,int(mode=='after-write')])
    def restore(source):
        return once(source,'local function loaded()',f"""emu.addMemoryCallback(verify526(function()
 if not packet or pw(8)~={gen} then return end
 local f=assert(io.open({json.dumps(image.as_posix())},'rb'));local b=f:read('*a');f:close()
 local bank=word(0x1034);assert(rd(0x125a+bank)==2)
 for i=0,{size-1} do emu.write({base}+bank*{size}+i,b:byte(i+1),emu.memType.snesWorkRam) end
 for i=0,2047 do emu.write((bank==0 and 0x5000 or 0x9000)+i,b:byte({size+1}+i),emu.memType.snesVideoRam) end
 emu.write(0x125a+bank,b:byte({size+2049}),emu.memType.snesWorkRam)
end),emu.callbackType.exec,{args.labels['compact_rows489']})
local function loaded()""")
    sub=SimpleNamespace(trace=args.trace,client=args.client,mesen=args.mesen,out=args.out/f'restore-{gen}-{mode}',frames=gen-904)
    replay.observer=observe
    replay.run(sub,edit_script=restore,compare_trace=lambda _,actual:dict(recovered_events=len(actual)))
    with (sub.out/'history547.csv').open() as f:row,=[r for r in csv.DictReader(f) if int(r['g'])==gen]
    assert int(row['prior'])==-1 and int(row['writes'])==6 and int(row['mask'])==0
    return dict(g=gen,case=mode,status=228,raw_writes_before_STOP=data[-1],restored_rows=6)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('trace','client','mesen','out'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();args.out=args.out.resolve();args.out.mkdir(parents=True,exist_ok=False)
    args.labels=json.loads((args.client/'labels.json').read_text())
    result=[test(args,g,k) for g in (907,908) for k in ('partial-receipt','before-raw','after-write')]
    (args.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
