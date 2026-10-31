# SPDX-License-Identifier: MIT
"""Isolate packet-ready to ACK service on the two 65816 programs using actual ARM packets."""
import argparse
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path
from test_nes_output489_snes import LUA
from test_nes_trim514_schedule import MAP_ORACLE

def run(a,trace,d):
    d.mkdir(parents=True,exist_ok=False)
    packets=[]
    for line in (trace/'packets.jsonl').read_text().splitlines():
        _,_,b,t=json.loads(line)
        packets.append(bytes.fromhex(b))
        if t:(d/f'tile-{len(packets):04d}.bin').write_bytes(bytes.fromhex(t))
    (d/'requests.bin').write_bytes(b''.join(struct.pack('<H',len(b))+b for b in packets))
    shutil.copyfile(trace/'client.sfc',d/'client.sfc')
    for g in range(905,917):
        shutil.copyfile(trace/f'expected-{g}.bin',d/f'expected-{g}.bin')
        shutil.copyfile(a.candidate/f'map-{g}.bin',d/f'map-{g}.bin')
    s=LUA.replace('local function loaded()',"""local loadedAt=0
local costs=assert(io.open(ROOT..'/service.csv','w'))
costs:write('index,generation,op,section,offset,bytes,expanded,clocks\\n')
local function loaded()""").replace(' packet=requests[index];',' loadedAt=st.masterClock;packet=requests[index];')
    s=s.replace('  lastStatus=ack[1]',"""  costs:write(string.format('%d,%d,%d,%d,%d,%d,%d,%d\\n',index,pw(8),pb(0),pb(1),pw(10),pw(12),pw(14),st.masterClock-loadedAt))
  lastStatus=ack[1]""")
    s=s.replace("   local hdma=file(",MAP_ORACLE+"   local hdma=file(",1).replace("f:close();emu.stop(0)","f:close();costs:close();emu.stop(0)")
    for key,value in dict(ROOT=json.dumps(d.as_posix()),MODE='"normal"',TOTAL=len(packets),FRAMES=12,SCHEDULE='"continuous"',
                          START=3000000,FAULT=906,POISON='false',COMPACT='true').items():
        s=s.replace('@'+key+'@',str(value))
    (d/'capture.lua').write_text(s)
    with (d/'mesen.log').open('wb') as log:
        subprocess.run([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(d/'client.sfc'),'--timeout=120',
                        '--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true',
                        '--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],
                       env=dict(os.environ,DOTNET_ROOT=str(a.dotnet)),cwd=d,stdout=log,stderr=subprocess.STDOUT,
                       check=True,timeout=135,creationflags=subprocess.CREATE_NO_WINDOW)
    assert json.loads((d/'result.json').read_text())['commits']==12
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('reference','candidate','out','mesen'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--dotnet',type=Path,default=Path('C:/works/dotnet'))
    a=p.parse_args();a.out=a.out.resolve()
    run(a,a.reference,a.out/'original')
    run(a,a.candidate,a.out/'trim')
