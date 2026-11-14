# SPDX-License-Identifier: MIT
"""Probe the 65816 section cursor and STOP at the staged padding head."""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
from nes_raw506 import once, sha


def run(base, trace, mesen, out, stop=False, map_stop=False):
    stop = stop or map_stop
    out=out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    assert json.loads((base/'audit.json').read_bytes())['frames']==66
    assert sha(base/'client.sfc')==sha(trace/'client.sfc')
    # This replay reads the original input files and writes its own observer logs.
    for src in base.iterdir():
        if src.name=='client.sfc' or src.name=='arrivals.tsv' or src.name.startswith(('map-','expected-')):
            (out/src.name).write_bytes(src.read_bytes())
    for src in base.glob('colors636-*.bin'):
        (out/src.name).write_bytes(src.read_bytes())
    packets=[bytes.fromhex(json.loads(row)[2]) for row in (trace/'packets.jsonl').read_text().splitlines()]
    table,=[h for h in packets if h[:2]==bytes((2,5)) and h[8:10]==(969).to_bytes(2,'little') and len(h)==256]
    assert int.from_bytes(table[10:12],'little')>1121
    (out/'table.bin').write_bytes(table)
    s=(base/'capture.lua').read_text()
    s=once(s,json.dumps(base.resolve().as_posix()),json.dumps(out.as_posix()))
    s=once(s,"local MODE='normal'","local MODE='abort777'" if stop else "local MODE='table777'")
    s=once(s,'local FAULT=905','local FAULT=969')
    if stop:
        assert json.loads((trace/'joint.json').read_bytes())['commits']==66
        # Rebuild the immutable PUSH schedule from this candidate's actual
        # ARM trace. The consumer independently checks every earlier display.
        arrivals=[];first={}
        final_clock=0
        for _,clock,h,pixels in (json.loads(r) for r in (trace/'packets.jsonl').read_text().splitlines()):
            gen=int.from_bytes(bytes.fromhex(h)[8:10],'little')
            if gen>969:break
            first.setdefault(gen,clock)
            final_clock=clock
            arrivals.append(f'{clock}\t{h}\t{pixels}\n')
        (out/'arrivals.tsv').write_text(''.join(arrivals)+f'{final_clock+1}\tFINISH\t\n',newline='\n')
        s=re.sub(r'sourceRelease\[(\d+)\]=(\d+)',
                 lambda m:f"sourceRelease[{m[1]}]={first.get(int(m[1]),int(m[2]))}",s)
        s=once(s,"local function loaded()", "local interrupted=false\nlocal function loaded()")
        s=once(s," if a==0x6001 then",""" if a==0x6001 then
  if packet and pw(8)==FAULT and pb(0)==5 and pb(1)==5 and pw(10)==21 then
   interrupted=true;return 128
  end""")
        if map_stop:
            s=once(s, "local interrupted=false", "local mapStopPending=false;local interrupted=false")
            s=once(s, 'packet=requests[index];sample516("load")', '''packet=requests[index]
 if pw(8)==FAULT and pb(0)==2 and pb(1)==2 and pw(10)==1216 then mapStopPending=true end
 sample516("load")''')
            s=once(s, 'if packet and pw(8)==FAULT and pb(0)==5 and pb(1)==5 and pw(10)==21 then\n   interrupted',
                      'if mapStopPending then\n   interrupted')
        s=once(s,"local function write(a,v)", """local function write(a,v)
 if interrupted and a==0x420b then error('new DMA after sampled STOP') end""")
        s=once(s,"  if uniform545() then\n   assert(fillBytes545", """  if uniform545() and interrupted then
   assert(ack[1]==228 and fillBytes545<=pw(14),'unexpected cancelled fill ACK')
  elseif uniform545() then
   assert(fillBytes545""")
        s=once(s,"  if rejected then\n   local screen", """  assert(interrupted and lastStatus==228 and word(0x1248)==FAULT-905,'STOP identity')
  if rejected then
   local screen""")
    else:
        s=once(s,'local function loaded()', 'local replaced=false\nlocal function loaded()')
        s=once(s,' if pb(0)==7 then tile=tilePayload[index]',""" if pw(8)==FAULT and pb(1)==5 and pw(10)==0 then
  local t=file('table.bin')
  assert(not replaced and packet:sub(5,10)==t:sub(5,10))
  packet=t:sub(1,2)..packet:sub(3,4)..t:sub(5)
  replaced=true
 end
 if pb(0)==7 then tile=tilePayload[index]""")
        s=once(s,"  if rejected then\n   local screen", """  assert(replaced and lastStatus==224 and word(0x1248)==FAULT-905,'table accepted out of order')
  if rejected then
   local screen""")
    if map_stop:
        # An idle STOP may halt before another head exists to carry E4.
        # Keep clocking and checking all DMA and display writes for three blanks.
        s=once(s,'local mapStopPending=false','local sampledFrame=nil;local mapStopPending=false')
        s=once(s,'interrupted=true;return 128','interrupted=true;sampledFrame=sampledFrame or emu.getState().frameCount;return 128')
        s=once(s," if (rejected or index>TOTAL)and not packet and st.frameCount>shown+2 then",
               """ if sampledFrame and st.frameCount>=sampledFrame+3 then
  assert(commits==64 and captured==64 and word(0x1248)==64 and word(0x124a)==0,'STOP published identity')
  local screen=emu.getScreenBuffer();local f=assert(io.open(ROOT..'/retained.rgb','wb'))
  for y=0,238 do local row={};for x=0,255 do local b=screen[y*256+x+1];row[#row+1]=string.char((b>>16)&255,(b>>8)&255,b&255)end;f:write(table.concat(row))end;f:close()
  local proof=assert(io.open(ROOT..'/result.json','w'))
  proof:write(string.format('{"passed":true,"commits":%d,"last_status":%d,"blanks_after_STOP":%d}',commits,lastStatus,st.frameCount-sampledFrame))
  proof:close();emu.stop(0);return
 end
 if (rejected or index>TOTAL)and not packet and st.frameCount>shown+2 then""")
    (out/'capture.lua').write_text(s,encoding='utf8',newline='\n')
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([str(mesen),'--testRunner',str(out/'capture.lua'),str(out/'client.sfc'),
                        '--timeout=300','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true',
                        '--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],
                       cwd=out,env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                       stdout=log,stderr=subprocess.STDOUT,timeout=330,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    result=json.loads((out/'result.json').read_bytes())
    assert result['passed'] and result['commits']==64 and (result.get('blanks_after_STOP',0)>=3 if map_stop else result['last_status']==(228 if stop else 224))
    assert sha(out/'retained.rgb')==sha(trace/'frame-968.rgb')
    proof = dict(commits=64, retained=sha(out/'retained.rgb'), client=sha(out/'client.sfc'))
    if map_stop:
        proof.update(map_offset=1216, last_packet_status=result['last_status'],
                     blanks_after_STOP=result['blanks_after_STOP'])
    else:
        proof.update(reject=result['last_status'], table_offset=int.from_bytes(table[10:12],'little'),
                     table=sha(out/'table.bin'))
    (out/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('base','trace','mesen','out'):p.add_argument(key,type=Path)
    p.add_argument('--stop',action='store_true')
    p.add_argument('--map-stop',action='store_true')
    a=p.parse_args()
    run(a.base,a.trace,a.mesen,a.out,a.stop,a.map_stop)
