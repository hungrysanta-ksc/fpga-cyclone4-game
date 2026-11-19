"""Replay recorded ARM arrivals and observe actual $2180 writes, including the last byte."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess

from analyze_nes_map830 import load,window
from nes_raw506 import once


def verify(temp,phase,tag):
    folder=temp/f'nes-tile821-demo-jointmirror-p{phase}-{tag}-on'
    out=folder/'wram859-bus'
    out.mkdir()
    lua=(folder/'capture.lua').read_text()
    lua=once(lua,'local ROOT=',f'local INPUT={json.dumps(folder.as_posix())}\nlocal ROOT=')
    lua=once(lua,'local ROOT='+json.dumps(folder.as_posix()),'local ROOT='+json.dumps(out.as_posix()))
    lua=once(lua,"io.open(ROOT..'/'..name,'rb')","io.open(INPUT..'/'..name,'rb')")
    records=[json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines()]
    with (out/'push.txt').open('w') as f:
        for _,clock,data,bulk in records:
            f.write(f'{clock} {data} {bulk}\n')
    release={r['generation']:r['release_masterclock'] for r in load(folder/'joint.json')['frames']}
    start=lua.index('local cmds=assert(')
    end=lua.index('local progressLog=',start)
    lua=lua[:start]+'''
local stream=assert(io.open(ROOT..'/push.txt','r'))
local function advance()
 local row=stream:read('*l')
 if not row then finished=true;TOTAL=sent;return end
 local clk,a,b=row:match('^(%d+) (%x+) (%x*)$')
 target=assert(tonumber(clk));args={a,b}
end
advance()
rpc=function()
 local clk=emu.getState().masterClock
 while not finished and clk>=target do
  assert(sent-retired<4)
  sent=sent+1;requests[sent]=unhex(args[1]);tilePayload[sent]=unhex(args[2])
  local g=requests[sent]:byte(9)+256*requests[sent]:byte(10)
  frames[sent]=g-905;frameRelease[g-905]=assert(sourceRelease[g])
  if requests[sent]:byte(1)==3 then sealIndex[g-905]=sent end
  advance()
 end
end
local count=0
local writes=assert(io.open(ROOT..'/writes.csv','w'))
checkedMem527(function(a,v)
 if packet and pw(8)==964 and pb(0)==2 and pb(1)==5 and pw(10)>=1121 then
  assert(count<pw(12) and v==pb(16+count),'wrong WRAM DMA byte')
  if count==0 or count+1==pw(12) then
   writes:write(string.format('%d,%d,%d,%d\\n',index,count,pw(12),emu.getState().masterClock));writes:flush()
  end
  count=count+1
  if count==pw(12) then count=0 end
 end
end,emu.callbackType.write,0x2180)
'''+lua[end:]
    lua=once(lua,'advance()\nrpc=', ''.join(f'sourceRelease[{g}]={v}\n' for g,v in release.items())+'advance()\nrpc=')
    # In a recorded run the CPU samples the head only at $6000. The poll
    # callback already supplies every PUSH up to that clock. Verify this
    # substitution against every actual head, ACK and display clock below.
    lua=once(lua,'checkedMem527(function()rpc()end,emu.callbackType.exec,0x7e0000,0x7effff)','')
    (out/'capture.lua').write_text(lua)
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([temp/'nes-bonus698-mesen/Mesen.exe','--testRunner',out/'capture.lua',folder/'client.sfc',
                        '--timeout=600','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true',
                        '--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],
            stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True,creationflags=subprocess.CREATE_NO_WINDOW,
            env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'))
    original=window(folder)
    def times(rows):
        return [(r['index'],r['event'],r['clock']) for r in rows if r['event'] in ('load','ack','reveal')]
    assert times(original)==times(window(out)) and load(out/'result.json')['passed']
    with (out/'writes.csv').open() as f:
        markers=[tuple(map(int,r)) for r in csv.reader(f)]
    assert len(markers)==4
    for first,last in zip(markers[::2],markers[1::2]):
        assert first[0]==last[0] and first[1]==0 and last[1]+1==first[2]==last[2] and first[3]<last[3]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int)
    p.add_argument('tag')
    verify(**vars(p.parse_args()))
