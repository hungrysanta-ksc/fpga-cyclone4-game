# SPDX-License-Identifier: MIT
"""Fault both compound heads, including STOP during real WRAM execution."""
import argparse
import json
import shutil
from pathlib import Path
from check_nes_group628 import SAVE_MAPS,recover
from nes_raw506 import once
from replay_nes_tail631 import specialize
from test_nes_seal538_stop import exercise
from analyze_nes_map628 import packets

SAVE_REGIONS="""
 local f=assert(io.open(ROOT..'/stopped-tail.bin','wb'))
 for bank=0,1 do
  local bytes={};for i=0x6200,0x6960 do bytes[#bytes+1]=string.char(rd(0x10000+bank*0x8000+i)) end
  f:write(table.concat(bytes))
 end;f:close()"""

def cold_script(out,s,trace):
    saved=out.parent/'951-stop/stopped-tail.bin'
    assert saved.stat().st_size==2*0x761
    shutil.copyfile(saved,out/saved.name)
    s=once(s,'local function loaded()',"""local prior631=file('stopped-tail.bin');local j631=1
for bank=0,1 do for i=0x6200,0x6960 do
 emu.write(0x10000+bank*0x8000+i,prior631:byte(j631),emu.memType.snesWorkRam);j631=j631+1
end end
local function loaded()""")
    for gen,cmds in packets(trace).items():
        if gen>906:break
        expected=bytearray()
        for h,_,_ in cmds:
            if h[1]!=4:continue
            assert int.from_bytes(h[10:12],'little')==len(expected)
            body=h[16:]
            if h[0]!=2:
                assert h[0] in (4,8)
                body*=int.from_bytes(h[14:16],'little')//len(body)
            expected.extend(body)
        assert len(expected)==544
        (out/f'oam-{gen}.bin').write_bytes(expected)
    return once(s,"   local hdma=file(","""   local expected631=file('oam-'..pw(8)..'.bin')
   for i=0,543 do assert(rd(0x16200+word(0x1020)+i)==expected631:byte(i+1),'cold OAM') end
   local hdma=file(""")

def run(a):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    a.generation=951
    lines=[];rows=[]
    for line in (a.trace/'packets.jsonl').read_text().splitlines():
        _,tick,h,p=json.loads(line);head=bytes.fromhex(h)
        gen=int.from_bytes(head[8:10],'little')
        if gen>951:break
        if gen==951:rows.append((tick,head,p))
        else:lines.append(line)
    for t,h,p in specialize(rows,'both'):lines.append(json.dumps([0,t,h.hex(),p]))
    stream=a.out/'packets.jsonl';stream.write_text('\n'.join(lines)+'\n',newline='\n')
    labels=json.loads((a.client/'labels.json').read_text())
    results=[]
    cases=[('oam_length',4,12,116),('oam_offset',4,10,4),('oam_span',4,14,543),
           ('scroll_length',5,12,21),('scroll_span',5,14,1120),('serial',5,4,0),
           ('stop_oam',4,0,0),('stop',5,0,0),('cold',5,0,0)]
    for kind,section,offset,value in cases:
        stop=kind.startswith('stop')
        cold=kind=='cold'
        pc=labels['oamchunk631' if section==4 else 'scrollchunk631']
        edits=(f"packet=packet:sub(1,{offset})..string.pack('<I2',{value})..packet:sub({offset+3})" if not stop else '')
        if cold:edits="packet=string.char(9)..packet:sub(2)"
        def inject(s):
            s=once(s,'local function loaded()',f"""local chosen=nil;local chunks=0;local transfers=0
emu.addMemoryCallback(function() if index==chosen then chunks=chunks+1 end end,emu.callbackType.exec,{pc})
emu.addMemoryCallback(function() if index==chosen then transfers=transfers+1 end end,emu.callbackType.write,0x420b)
local function loaded()""")
            condition=f'pb(0)==9 and pb(1)=={section}' if not cold else 'pb(0)==2 and pb(1)==2'
            s=once(s,' if pb(0)==7 then tile=file',f""" if not chosen and pw(8)==FAULT and {condition} then chosen=index;{edits} end
 if pb(0)==7 then tile=file""")
            s=once(s,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end",'')
            if stop:s=once(s,'if a==0x6001 then','if a==0x6001 then if chosen==index and chunks==2 then return 128 end')
            expected=2 if stop else 0
            return once(s,"assert(lastStatus==0xe4,'STOP status')",
                        f"assert(chosen and transfers=={expected} and lastStatus=={228 if stop else 224},'unexpected write or status')"+(SAVE_MAPS+SAVE_REGIONS if kind=='stop' else ''))
        results.append(exercise(a,906 if cold else 951,kind,edit_packet_case=inject,
                                reject_status=228 if stop else 224,packet_trace=stream))
    restart=recover(a,receipt_tags=False,prepare_script=lambda out,s:cold_script(out,s,a.trace))
    restart['restored_tail_bytes']=2*0x761
    (a.out/'guards.json').write_text(json.dumps(dict(cases=results,restart=restart),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','client','mesen','out'):p.add_argument('--'+k,type=Path,required=True)
    run(p.parse_args())
