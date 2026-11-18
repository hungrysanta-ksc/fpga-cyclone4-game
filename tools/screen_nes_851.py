"""Sample the first rendered SNES picture after each ACK using the recorded ARM packet timeline."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess

from analyze_nes_map830 import window
from nes_raw506 import once


def replay(run,mesen):
    out=run/'first-screen'
    out.mkdir()
    events=json.loads((run/'events.json').read_bytes())
    rows=[(math.ceil(e['clock']),'BEGIN',str(e['generation']),'') for e in events if e['event']=='source_begin']
    for line in (run/'packets.jsonl').read_text().splitlines():
        _,target,payload,bulk=json.loads(line)
        rows.append((target,'PUSH',payload,bulk))
    rows.sort(key=lambda v:v[0])
    rows.append((math.ceil(events[-1]['clock'])+1,'FINISH','',''))
    with (out/'commands.txt').open('w',encoding='ascii',newline='\n') as f:
        for seq,(t,cmd,p,b) in enumerate(rows,1):
            f.write(f'{seq}\n{t}\n{cmd}\n{p}\n{b}\n')
    lua=(run/'capture.lua').read_text()
    lua=re.sub(r'^local ROOT=.*$',lambda _: 'local ROOT='+json.dumps(out.as_posix()),lua,count=1,flags=re.M)
    lua=re.sub(r'^local cmds=.*$',"local cmds=assert(io.open(ROOT..'/commands.txt','rb'))",lua,count=1,flags=re.M)
    lua=re.sub(r'^local replies=.*$',"local replies={write=function()end,flush=function()end}",lua,count=1,flags=re.M)
    # The offline clock gate has no ARM to rendezvous with. Loading queued
    # packets happens at $6000, whose read callback calls rpc() itself.
    lua=once(lua,'checkedMem527(function()rpc()end,emu.callbackType.exec,0x7e0000,0x7effff)','')
    # The SNES increments frameCount at VBlank entry, after its EndFrame callback.
    # A VBlank reveal is therefore visible at the *equal* counter's next EndFrame.
    lua=once(lua,'not c.done and st.frameCount>c.frame','not c.done and st.frameCount==c.frame')
    (out/'capture.lua').write_text(lua,encoding='utf8')
    for pattern in ('expected-*.bin','map-*.bin','colors636-*.bin','client.sfc'):
        for file in run.glob(pattern):
            shutil.copyfile(file,out/file.name)
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([mesen,'--testRunner',out/'capture.lua',out/'client.sfc','--timeout=600',
                        '--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true',
                        '--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],
                        env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                        creationflags=subprocess.CREATE_NO_WINDOW,stdout=log,stderr=subprocess.STDOUT,
                        check=True,timeout=620)
    old=json.loads((run/'joint.json').read_bytes())
    new=json.loads((out/'result.json').read_bytes())
    assert new['passed'] and new['commits']==old['commits']==62
    assert [(r['generation'],r['ACK_masterclock']) for r in old['frames']]==[
        (r['generation'],r['ACK_masterclock']) for r in new['frames']]
    assert window(out)==window(run)
    assert len(list(out.glob('frame-*.rgb')))==62
    (out/'verified.json').write_text(json.dumps(dict(exact_window_rows=len(window(out)),display_ACKs=62)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path)
    p.add_argument('mesen',type=Path)
    a=p.parse_args()
    replay(a.run,a.mesen)
