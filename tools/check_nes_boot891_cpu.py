"""Run each delivered reset image up to the first WRAM main and stage 3 in Mesen."""
import argparse
import csv
import json
import os
from pathlib import Path
import subprocess

from package_nes_trial872 import PROBES, sha


def run(temp,out):
    out.mkdir(parents=True)
    runs={}
    for n in (872,890):
        d=out/str(n)
        d.mkdir()
        client=PROBES/f'nes-trial{n}/client02'
        lua=r"""
local f=assert(io.open(ROOT..'/cpu.csv','w'))
local function mark(kind,a,v)
 f:write(string.format('%s,%d,%d,%d\n',kind,a,v,emu.getState().masterClock));f:flush()
end
emu.addMemoryCallback(function(a)mark('entry',a,0)end,emu.callbackType.exec,0x8000)
emu.addMemoryCallback(function(a)mark('first_store_pc',a,0)end,emu.callbackType.exec,0x8024)
emu.addMemoryCallback(function(a)mark('wram_main',a,0)end,emu.callbackType.exec,0x7e2000)
emu.addMemoryCallback(function(a,v)
 mark('stage',a,v)
 if v==3 then emu.stop(0)end
end,emu.callbackType.write,0x7000)
emu.addEventCallback(function()
 if emu.getState().frameCount>100 then emu.stop(1)end
end,emu.eventType.endFrame)
"""
        script=d/'boot.lua'
        script.write_text('local ROOT='+json.dumps(d.as_posix())+'\n'+lua,encoding='utf8')
        with (d/'mesen.log').open('wb') as f:
            subprocess.run([temp/'nes-bonus698-mesen/Mesen.exe','--testRunner',script,
                client/'sink165.sfc','--timeout=40','--doNotSaveSettings','--enableStdout',
                '--debug.scriptWindow.allowIoOsAccess=true'],stdout=f,stderr=subprocess.STDOUT,
                env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                creationflags=subprocess.CREATE_NO_WINDOW,timeout=60,check=True)
        with (d/'cpu.csv').open() as f:
            rows=[dict(event=k,address=int(a),value=int(v),clock=int(c)) for k,a,v,c in csv.reader(f)]
        assert rows[0]['event']=='entry' and rows[1]['event']=='first_store_pc'
        assert rows[2]['event']=='stage' and rows[2]['value']==1 and rows[-1]['value']==3
        assert any(r['event']=='wram_main' for r in rows)
        runs[str(n)]=dict(client=sha(client/'sink165.sfc'),events=rows)
    (out/'result.json').write_text(json.dumps(runs,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    run(a.temp,a.out)
