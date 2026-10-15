# SPDX-License-Identifier: MIT
"""Run actual SNES client with real Mesen auto-poll, no injected JOY registers.

Idle mailbox isolates controller service from video transport. This is not
the FPGA pad CDC or a physical controller test. Preserve all raw commits.
"""
from pathlib import Path
import argparse, json, os, subprocess
from nes_game147 import sha

LUA=r'''
local OUT=OUTPATH
local f=assert(io.open(OUT..'/commits.tsv','w'))
local frames,lo=0,0
local reads=0
emu.addMemoryCallback(function(a,v)return 0 end,emu.callbackType.read,0x6000,0x6005)
emu.addMemoryCallback(function(a,v)
 local s=emu.getState();reads=reads+1
 -- Observation only: do not replace the auto-reader's register values.
end,emu.callbackType.read,0x4218,0x4219)
emu.addMemoryCallback(function(a,v)
 if a==0x6002 then lo=v else
  local s=emu.getState()
  f:write(string.format('%d %d %d %04x\n',frames,s.masterClock,s['ppu.scanline'],lo+v*256))
 end
end,emu.callbackType.write,0x6002,0x6003)
emu.addEventCallback(function()
 -- Long holds and releases; both low and high bytes carry meaningful bits.
 local phase=math.floor(frames/30)%4
 emu.setInput({a=phase==1,b=phase==1,start=phase==2,select=phase==2,
               down=phase==1,left=phase==1,right=phase==3},0)
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 frames=frames+1
 if frames==240 then f:close();emu.stop(0)end
end,emu.eventType.endFrame)
'''


def main():
    p=argparse.ArgumentParser()
    for n in ['out','client','mesen']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.client=a.client.resolve()
    assert str(a.out).isascii(), 'Mesen Lua io requires an ASCII result path on this host'
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'capture.lua').write_text(LUA.replace('OUTPATH',json.dumps(a.out.as_posix())),encoding='utf8')
    env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    with (a.out/'mesen.log').open('wb') as f:
        q=subprocess.run([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.client/'sink165.sfc'),
           '--timeout=35','--doNotSaveSettings','--enableStdout','--snes.port1.type=SnesController',
           '--debug.scriptWindow.allowIoOsAccess=true'],
           cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
    assert q.returncode==0,(a.out/'mesen.log').read_text(errors='replace')
    commits=[dict(frame=int(f),clock=int(t),line=int(y),value=int(v,16))
             for f,t,y,v in (s.split() for s in (a.out/'commits.tsv').read_text().splitlines())]
    # Exclude transition margins and boot, but never remove a bad steady hold.
    expected=[0,0x8680,0x3000,0x0100]
    stable=[c for c in commits if c['frame']>=10 and 4<=c['frame']%30<=27]
    bad=[c for c in stable if c['value']!=expected[c['frame']//30%4]]
    assert len(stable)>140 and len({c['frame']//30%4 for c in stable})==4
    assert any(c['value']==0x8680 for c in stable), 'no valid held input; fixture/controller config invalid'
    result=dict(scope=__doc__,rom_sha256=sha(a.client/'sink165.sfc'),mesen_sha256=sha(a.mesen),
                core_sha256=sha(a.mesen.parent/'MesenCore.dll'),script_sha256=sha(Path(__file__)),
                commits=len(commits),stable_samples=len(stable),bad_samples=bad,
                passed=not bad,physical=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='bad_samples'}|{'bad_count':len(bad)}))


if __name__=='__main__':main()
