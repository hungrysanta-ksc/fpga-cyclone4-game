# SPDX-License-Identifier: MIT
"""Execute reset, verify every WRAM program byte, and fault the verification pass."""
import argparse
import json
import os
import subprocess
from pathlib import Path
from nes_raw506 import sha


def check(a):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    build=json.loads((a.client/'build.json').read_text())
    image=(a.base/'sink165.sfc').read_bytes()[96:96+build['body_bytes']]
    (a.out/'body.bin').write_bytes(image)
    results={}
    for case,client in [('original',a.base),('packed',a.client),('corrupt',a.client)]:
        result=a.out/(case+'.txt')
        lua=f"""
local bad={str(case=='corrupt').lower()};local touched=false
local f=assert(io.open({json.dumps((a.out/'body.bin').as_posix())},'rb'))
local body=f:read('*a');f:close()
local function finish()
 local f=assert(io.open({json.dumps(result.as_posix())},'w'))
 f:write(tostring(emu.getState().masterClock));f:close();emu.stop(0)
end
emu.addMemoryCallback(function()
 assert(not bad,'corrupted image ran')
 for i=1,#body do assert(emu.read(0x2000+i-1,emu.memType.snesWorkRam)==body:byte(i),'bad WRAM byte '..i)end
 finish()
end,emu.callbackType.exec,0x7e2000)
if bad then
 emu.addMemoryCallback(function()
  if not touched then local p=emu.getState()['cpu.y']
   emu.write(p,emu.read(p,emu.memType.snesWorkRam)~1,emu.memType.snesWorkRam)
   touched=true end
 end,emu.callbackType.exec,{build['verify_entry']})
 emu.addMemoryCallback(function(a,v)if v==225 and touched then finish() end end,emu.callbackType.write,0x7000)
end
emu.addEventCallback(function()if emu.getState().frameCount>50 then emu.stop(1)end end,emu.eventType.endFrame)
"""
        script=a.out/(case+'.lua');script.write_text(lua,newline='\n')
        with (a.out/(case+'.log')).open('wb') as log:
            subprocess.run([str(a.mesen),'--testRunner',str(script),str((client/'sink165.sfc').resolve()),
                            '--timeout=60','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],
                           env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                           stdout=log,stderr=subprocess.STDOUT,timeout=70,check=True)
        results[case]=int(result.read_text())
    (a.out/'result.json').write_text(json.dumps(dict(clocks=results,body_B=len(image),body_SHA=sha(a.out/'body.bin'),
                  ROM=sha(a.client/'sink165.sfc'),extra_boot_ms=(results['packed']-results['original'])/21477.272),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('mesen','base','client','out'):p.add_argument('--'+k,type=Path,required=True)
    check(p.parse_args())
