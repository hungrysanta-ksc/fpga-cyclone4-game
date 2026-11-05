# SPDX-License-Identifier: MIT
"""Audit consumer timestamps against an independent no-pipe player of immutable PUSH arrivals."""
import argparse
import csv
import json
import os
import shutil
import subprocess
from pathlib import Path
from nes_raw506 import once,sha
from test_nes_raw506_joint import lua_rpc
from test_nes_trim514_schedule import MAP_ORACLE
from test_nes_idle524_schedule import observe
from test_nes_map526_schedule import observer
from trace_nes_tail522 import CLOCKED_INPUT


def run(a, *, edit_script=None, compare_trace=None, source_client=None):
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    expected_client=source_client if source_client is not None else a.client
    assert sha(a.trace/'client.sfc')==sha(expected_client/'sink165.sfc')
    shutil.copyfile(a.client/'sink165.sfc',a.out/'client.sfc')
    first,last=905,905+a.frames
    for g in range(first,last):
        for n in (f'map-{g}.bin',f'expected-{g}.bin'):
            shutil.copyfile(a.trace/n,a.out/n)
    rows=list(csv.DictReader((a.trace/'window.csv').open()))
    rows=[r for r in rows if int(r['g'])<last]
    clock=max(int(r['clock']) for r in rows)
    arrivals={}
    with (a.out/'arrivals.tsv').open('w',newline='\n') as f:
        for line in (a.trace/'packets.jsonl').read_text().splitlines():
            _,t,b,p=json.loads(line);g=int.from_bytes(bytes.fromhex(b)[8:10],'little')
            if g>=last:break
            arrivals.setdefault(g,t)
            f.write(f'{t}\t{b}\t{p}\n')
        f.write(f'{clock+1}\tFINISH\t\n')
    assert len(arrivals)==a.frames
    a.start=3000000;a.candidate=True
    lua_rpc(a);path=a.out/'capture.lua';s=path.read_text()
    s=once(s,'   local hdma=file(',MAP_ORACLE+'   local hdma=file(')
    s=observe(s,a,observer)
    start=s.index('local sequence=0;');end=s.index('emu.addMemoryCallback(function()rpc()end',start)
    releases='\n'.join(f'sourceRelease[{g}]={t}' for g,t in arrivals.items())
    s=s[:start]+releases+"\nlocal function unhex(b)return (b:gsub('..',function(c)return string.char(tonumber(c,16))end))end\n"+CLOCKED_INPUT+s[end:]
    s=once(s,'emu.addMemoryCallback(function()rpc()end,emu.callbackType.exec,0x7e0000,0x7effff)','')
    start=s.index('emu.addEventCallback(function()\n if sequence==1');end=s.index('end,emu.eventType.endFrame)',start)+len('end,emu.eventType.endFrame)')
    script=s[:start]+s[end:]
    path.write_text(edit_script(script) if edit_script else script,encoding='utf8',newline='\n')
    with (a.out/'mesen.log').open('wb') as log:
        subprocess.run([str(a.mesen),'--testRunner',str(path),str(a.out/'client.sfc'),'--timeout=1800',
                        '--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true',
                        '--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],
                       cwd=a.out,env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                       stdout=log,stderr=subprocess.STDOUT,timeout=1850,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    result=json.loads((a.out/'result.json').read_text())
    assert result['passed'] and result['commits']==a.frames and not (a.out/'map-error.txt').exists()
    with (a.out/'window.csv').open() as f:
        actual=list(csv.DictReader(f))
    if compare_trace:
        proof=compare_trace(rows,actual)
    else:
        assert actual==rows
        proof=dict(matched_events=len(rows))
    for g in range(first,last):assert sha(a.out/f'frame-{g}.rgb')==sha(a.trace/f'frame-{g}.rgb')
    (a.out/'audit.json').write_text(json.dumps(dict(frames=a.frames,**proof,trace=sha(a.out/'window.csv')))+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('trace','out','mesen','client'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--frames',type=int,default=53)
    run(p.parse_args())
