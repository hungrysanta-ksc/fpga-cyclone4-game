# SPDX-License-Identifier: MIT
"""Move only the final gate's entry time in a diagnostic ROM; exercise the real PPU beam and final DMA."""
import argparse
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path
from nes_window516 import build, emit_final516
from test_nes_output489_snes import LUA
from test_nes_trim514_schedule import MAP_ORACLE
from nes_raw506 import once, sha

def emit_test(c,generation):
    emit_final516(c)
    c.label('paced516');c.absolute(0xad,0x1226);c.emit(0xc9);c.word(generation)
    c.branch(0xd0,'real516')
    c.emit(0xe2,0x20);c.label('hold516');c.absolute(0xad,0x605f);c.branch(0xf0,'hold516')
    c.emit(0xc2,0x20);c.label('real516');c.jump('wait_final516')

OBSERVER = """
local lastLine,firstClock=-1,0
local entered,borrowed,fresh,grantFrame,grantClock=false,false,false,-1,0
local beamFile=assert(io.open(ROOT..'/beam.csv','w'))
beamFile:write('event,clock,line,frame\\n')
local function beam(name)
 local st=emu.getState()
 beamFile:write(string.format('%s,%d,%d,%d\\n',name,st.masterClock,st['ppu.scanline'],st.frameCount))
 beamFile:flush()
 return st
end
emu.addMemoryCallback(function()
 local st=emu.getState();local line=st['ppu.scanline']
 if line~=lastLine then lastLine=line;firstClock=st.masterClock end
 if line==@LINE@ and st.masterClock-firstClock>=900 then
  entered=true;beam('released');return 1
 end
 return 0
end,emu.callbackType.read,0x605f)
emu.addMemoryCallback(function()
 if entered then local st=beam('borrow');borrowed=true;grantFrame=st.frameCount;grantClock=st.masterClock end
end,emu.callbackType.exec,@BORROW@)
emu.addMemoryCallback(function()if entered then fresh=true;beam('fresh')end end,emu.callbackType.exec,@FRESH@)
if MODE=='stale' then
 emu.addMemoryCallback(function()if entered then return 0 end end,emu.callbackType.read,0x213f)
end
"""

def run(a):
    a.out.mkdir(parents=True,exist_ok=False)
    client=a.out/'paced';build(client,emitter=lambda c:emit_test(c,a.generation),entry='paced516',fill=a.fill)
    labels=json.loads((client/'labels.json').read_text())
    packets=[]
    for line in (a.trace/'packets.jsonl').read_text().splitlines():
        _,_,b,t=json.loads(line);b=bytes.fromhex(b)
        if int.from_bytes(b[8:10],'little')>a.generation:break
        packets.append((b,bytes.fromhex(t)))
    assert packets[-1][0][0]==3 and packets[-1][0][8:10]==struct.pack('<H',a.generation)
    results={}
    for tag,target in [('active',224),('early',225),('last',246),('late',247),('high',256),('stale',230),('stop',235),('bad_version',230)]:
        d=a.out/tag;d.mkdir()
        mode=tag if tag in ('stale','stop','bad_version') else 'normal'
        (d/'requests.bin').write_bytes(b''.join(struct.pack('<H',len(b))+b for b,_ in packets))
        for i,(_,tile) in enumerate(packets,1):
            if tile:(d/f'tile-{i:04d}.bin').write_bytes(tile)
        for g in range(905,a.generation+1):
            for p in ('map','expected'):shutil.copyfile(a.trace/f'{p}-{g}.bin',d/f'{p}-{g}.bin')
        shutil.copyfile(client/'sink165.sfc',d/'client.sfc')
        s=once(LUA,'local function loaded()',OBSERVER+'\nlocal function loaded()')
        s=once(s,' if a==0x6001 then',' if a==0x6001 then\n  if entered and MODE=="stop" then beam("stop");return 128 end')
        s=once(s,"   local hdma=file(",MAP_ORACLE+"   local hdma=file(")
        s=once(s,'  lastStatus=ack[1]',"""  lastStatus=ack[1]
  if pw(8)==@FAULT@ and pb(0)==3 then
   local st=beam('ACK')
   if lastStatus==1 then
    assert(entered and (borrowed~=fresh),'missing branch')
    if borrowed then assert(st.frameCount==grantFrame and st['ppu.scanline']>=225,'missed VBlank') end
   end
  end""")
        # Stale-latch injection expects an ordinary successful commit.
        s=s.replace("MODE=='normal'","(MODE=='normal' or MODE=='stale')")
        for k,v in dict(ROOT=json.dumps(d.as_posix()),MODE=json.dumps(mode),TOTAL=len(packets),FRAMES=a.generation-904,
                        SCHEDULE='"continuous"',START=3000000,FAULT=a.generation,COMPACT='true',POISON='false',LINE=target,
                        BORROW=labels['borrow516'],FRESH=labels['fresh516']).items():
            s=s.replace('@'+k+'@',str(v))
        (d/'capture.lua').write_text(s,encoding='utf8')
        with (d/'mesen.log').open('wb') as log:
            subprocess.run([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(d/'client.sfc'),'--timeout=120',
                            '--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true',
                            '--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],
                           env=dict(os.environ,DOTNET_ROOT=str(a.dotnet)),cwd=d,stdout=log,stderr=subprocess.STDOUT,
                           check=True,timeout=135,creationflags=subprocess.CREATE_NO_WINDOW)
        r=json.loads((d/'result.json').read_text())
        import csv
        with (d/'beam.csv').open() as f:events=list(csv.DictReader(f))
        branches=[e['event'] for e in events if e['event'] in ('fresh','borrow')]
        if tag in ('stop','bad_version'):
            assert r['commits']==a.generation-905 and r['last_status']==(228 if tag=='stop' else 224) and not branches
            assert sha(d/'retained.rgb')==sha(d/f'frame-{a.generation-1}.rgb')
        else:
            assert branches==(['borrow'] if tag in ('early','last') else ['fresh']) and r['commits']==a.generation-904,(tag,events)
            assert sha(d/f'frame-{a.generation}.rgb')==sha(a.trace/f'frame-{a.generation}.rgb')
        results[tag]=dict(masterclock_events=events,commits=r['commits'],status=r['last_status'])
        print(tag,branches,r['commits'],flush=True)
    (a.out/'edges.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('trace','out','mesen'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--fill',action='store_true')
    p.add_argument('--generation',type=int,default=909)
    p.add_argument('--dotnet',type=Path,default=Path('C:/works/dotnet'))
    a=p.parse_args();a.out=a.out.resolve();run(a)
