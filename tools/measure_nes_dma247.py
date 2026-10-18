# SPDX-License-Identifier: MIT
"""Observe unchanged232 instruction boundaries, excluding mailbox/VBlank waits.

Local Mesen instruction callbacks only; this is not new scheduler timing.
"""
from pathlib import Path
import argparse
import ctypes
import json
import os
import shutil
import subprocess
import tempfile
from nes_delta231 import BASE, sha


def short(p):
    buf = ctypes.create_unicode_buffer(32768)
    assert ctypes.windll.kernel32.GetShortPathNameW(str(p), buf, len(buf))
    return buf.value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--rom', type=Path, required=True)
    a = p.parse_args(); out = a.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    old = BASE/'probes/nes-sparse232/scroll02'
    mesen = Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe')
    rom = a.rom.resolve()
    assert sha(rom) == 'dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
    run = Path(tempfile.mkdtemp(prefix='nes-dma247-'))
    (out/'run-path.txt').write_text(str(run),encoding='utf-8')
    labels = json.loads((old/'client/labels.json').read_text())
    lua = (old/'run/capture.lua').read_text(encoding='utf-8').split('\n',1)[1]
    lua = 'local OUT_DIR='+json.dumps(run.as_posix())+'\n'+lua
    injection = r'''
local timing247=assert(io.open(OUT_DIR..'/dma247.csv','w'))
timing247:write('generation,type,bytes,master_clocks,waited\n')
local pending247=nil
local final247=nil
local function flush247(now)
 if pending247 then
  timing247:write(string.format('%d,list,%d,%d,%d\n',pending247.gen,pending247.bytes,now-pending247.start,pending247.waited and 1 or 0))
  pending247=nil
 end
end
local function hook247(name)
 local now=emu.getState().masterClock
 if name=='upload_loop212' then
  flush247(now)
  if word(0x1252)<word(0x1250) then
   local at=0x4004+word(0x1252)
   pending247={gen=pw(8),bytes=word(at),start=now,waited=false}
  end
 elseif name=='wait169' then
  if pending247 then pending247.waited=true end
  if final247 then final247.waited=true end
 elseif name=='final212' then
  flush247(now);final247={gen=pw(8),start=now,waited=false}
 elseif name=='final_upload212_return' and final247 then
  timing247:write(string.format('%d,final,%d,%d,%d\n',final247.gen,word(0x125c),now-final247.start,final247.waited and 1 or 0))
  final247=nil
 end
 timing247:flush()
end
'''
    for name in ('upload_loop212','wait169','final212','final_upload212_return'):
        injection += 'emu.addMemoryCallback(function()hook247('+json.dumps(name)+')end,emu.callbackType.exec,'+str(labels[name])+')\n'
    # Insert after helpers and packet local declarations, before callbacks.
    at = lua.index('emu.addMemoryCallback(')
    lua = lua[:at]+injection+lua[at:]
    (run/'capture.lua').write_text(lua,encoding='utf-8',newline='\n')
    for f in (old/'run').iterdir():
        if f.name == 'palette.bin' or f.name.startswith(('expected-','oam-')):
            shutil.copyfile(f,run/f.name)
    env = os.environ.copy(); env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    commands = [
        [str(old/'common/host.exe'),short(BASE/'probes/nes-geometry230/rtl02'),short(rom),'905','975',short(BASE/'probes/nes-delta231/test07')],
        [str(mesen),'--testRunner',str(run/'capture.lua'),str(old/'client/sink165.sfc'),'--timeout=300','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true']]
    children = []
    try:
        for cmd, name in zip(commands, ('host','mesen')):
            with (run/(name+'.log')).open('wb') as log:
                children.append(subprocess.Popen(cmd,cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW))
        mr=children[1].wait(timeout=320);hr=children[0].wait(timeout=5)
        assert mr==hr==0, (mr,hr)
        result=json.loads((run/'consumer-result.json').read_text())
        assert result['passed'] and result['commits']==71
        result.update(scope=__doc__,new_product_code=False,script_sha256=sha(Path(__file__)),
            timing_sha256=sha(run/'dma247.csv'),inputs={str(f.relative_to(BASE)):sha(f) for f in
                (old/'client/sink165.sfc',old/'client/labels.json',old/'common/host.exe',old/'run/capture.lua')},
            mesen_sha256=sha(mesen),rom_sha256=sha(rom))
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,indent=2))
    finally:
        for child in children:
            if child.poll() is None:child.kill();child.wait()
        # Preserve failed logs too; private ROM bytes are never copied here.
        shutil.copytree(run,out/'run',dirs_exist_ok=True)


if __name__=='__main__':main()
