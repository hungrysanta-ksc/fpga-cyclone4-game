"""Replay recorded PUSH times and assert STOP/head priority at the last OBJ grant."""
import argparse
import json
from itertools import count
import os
import re
import shutil
import subprocess
from pathlib import Path

from analyze_nes_palette921 import directory, sha
from nes_chain935 import output
from nes_raw506 import once


def run(temp,variant,phase,case):
    rom=output(variant)
    trial=directory(temp,phase,'935'+variant+'final','cold')
    out=next(path for i in count(1) if not (path:=trial/f'edge935-{case}-{i:02d}').exists())
    out.mkdir()
    labels=json.loads((rom/'labels.json').read_bytes())
    assert sha(rom/'sink165.sfc')==sha(trial/'client.sfc')
    pushes=[json.loads(entry) for entry in (trial/'packets.jsonl').read_text().splitlines()]
    with (out/'commands.txt').open('w',encoding='ascii',newline='\n') as stream:
        for idx,(_,tick,payload,bulk) in enumerate(pushes,1):
            stream.write(f'{idx}\n{tick}\nPUSH\n{payload}\n{bulk}\n')
        stream.write(f'{idx+1}\n{tick+1}\nFINISH\n\n\n')
    lua=(trial/'capture.lua').read_text()
    lua=re.sub('^local ROOT=.*$',lambda _:'local ROOT='+json.dumps(out.as_posix()),lua,count=1,flags=re.M)
    lua=re.sub('^local cmds=.*$',"local cmds=assert(io.open(ROOT..'/commands.txt','rb'))",lua,count=1,flags=re.M)
    lua=re.sub('^local replies=.*$',"local replies={write=function()end,flush=function()end}",lua,count=1,flags=re.M)
    registers= (0x6001,128) if case=='stop' else (0x6000,1)
    hook=f"""
local armed935,read935,head935,done935=false,false,-1,false
checkedMem527(function()
 local s=emu.getState();local x=s['cpu.x']
 if word(0x1226)==912 and word(0x4002+x)==0x8440 and s['cpu.y']==32 and
    s['cpu.a']%256<=252 and s['cpu.a']%256>=225 and not packet then
  armed935=true;head935=x
 end
end,emu.callbackType.exec,{labels['limit935']})
checkedMem527(function()
 if armed935 then error('canceled OBJ reached MDMAEN') end
end,emu.callbackType.exec,{labels['grant935']})
checkedMem527(function()
 if armed935 and read935 and not done935 then
  assert(word(0x1252)==head935 and word(0x4002+head935)==0x8440)
  local f=assert(io.open(ROOT..'/edge.json','w'))
  f:write(string.format('{{"held":%d,"stop":%d,"line":%d}}',head935,rd(0x1236),emu.getState()['ppu.scanline']))
  f:close();done935=true;emu.stop(0)
 end
end,emu.callbackType.exec,{labels['skip8_523']})
"""
    lua=once(lua,'local function loaded()',hook+'local function loaded()')
    # Mesen processes stop at the next frame boundary. Do not inject future
    # recorded ARM packets after the observed priority decision.
    lua=once(lua,'if finished or inRpc527 then','if done935 or finished or inRpc527 then')
    entry=f' if a==0x{registers[0]:04x} then'
    lua=once(lua,entry,entry+f' if armed935 then read935=true;return {registers[1]} end;')
    lua=once(lua,' if a==0x6001 then',' if a==0x6001 then if done935 then return 128 end;')
    (out/'capture.lua').write_text(lua,encoding='utf8')
    for pattern in ('expected-*.bin','colors636-*.bin','map-*.bin','client.sfc'):
        for f in trial.glob(pattern):
            shutil.copyfile(f,out/f.name)
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([temp/'nes-bonus698-mesen/Mesen.exe','--testRunner',out/'capture.lua',out/'client.sfc',
                        '--timeout=180','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true',
                        '--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],
                       stdout=log,stderr=subprocess.STDOUT,check=True,timeout=200,creationflags=subprocess.CREATE_NO_WINDOW,
                       env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'))
    data=json.loads((out/'edge.json').read_bytes())
    assert data['stop']==int(case=='stop')
    # The two schedules must be identical up to the injected boundary.
    def preceding(path):
        return next(r for r in (path/'beam934.csv').read_text().splitlines() if
                    r.startswith('limit935,') and int(r.split(',')[6])<=252 and
                    int(r.split(',')[4])==0x8440 and 225<=int(r.split(',')[7])<=252)
    assert preceding(out)==preceding(trial)
    data['observed_at']=preceding(trial)
    (trial/f'edge935-{case}-verified.json').write_text(json.dumps(data)+'\n')
    return data


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path);p.add_argument('variant')
    p.add_argument('phase',type=int,choices=(1,2));p.add_argument('case',choices=('stop','head'))
    a=p.parse_args()
    print(run(a.temp,a.variant,a.phase,a.case))
