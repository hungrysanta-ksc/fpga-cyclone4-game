# SPDX-License-Identifier: MIT
"""Exercise the zero-fill DMA, word fallback and STOP without changing the deployed program."""
import argparse
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path
from nes_raw506 import once, sha
from test_nes_output489_snes import LUA
from test_nes_trim514_schedule import MAP_ORACLE

SETUP="""
local target=nil;local bytes=0;local prior=nil;local stopNow=false;local accepted516=false
local function dst()return 0x16500+word(0x1020)+pw(10)end
local function snapshot()
 local s={};for i=0,pw(14)-1 do s[i+1]=string.char(rd(dst()+i))end;return table.concat(s)
end
local function check_output(part)
 local data=snapshot();local rep=string.rep(packet:sub(17,18),part//2)
 assert(data==rep..prior:sub(part+1),'changed beyond completed prefix')
end
"""
def check(a):
    a.out.mkdir(parents=True,exist_ok=False)
    records=[]
    for line in (a.trace/'packets.jsonl').read_text().splitlines():
        _,_,b,t=json.loads(line);b=bytes.fromhex(b)
        if int.from_bytes(b[8:10],'little')>907:break
        records.append((b,bytes.fromhex(t)))
    target=next(i for i,(b,_) in enumerate(records) if b[:2]==bytes([5,5]) and b[8:10]==struct.pack('<H',907))
    results={}
    for mode in ('stop64','stop_tail','tail242','two_chunks_plus','first_nonzero','second_nonzero','odd','overflow'):
        d=a.out/mode;d.mkdir()
        rows=records.copy()
        packet,tile=rows[target];p=bytearray(packet)
        if mode=='tail242':struct.pack_into('<H',p,14,242)
        if mode=='two_chunks_plus':struct.pack_into('<H',p,14,258)
        if mode=='first_nonzero':p[16]=0xa5
        if mode=='second_nonzero':p[17]=0x5a
        if mode=='odd':p[14]|=1
        if mode=='overflow':struct.pack_into('<H',p,14,4098)
        rows[target]=bytes(p),tile
        # Positive synthetic lengths/words need no matching synthetic SEAL.
        # End the probe on the following ordinary header with a stale sequence.
        if mode in ('tail242','two_chunks_plus','first_nonzero','second_nonzero'):
            end=next(i for i in range(target+1,len(rows)) if rows[i][0][0]!=7)
            bad=bytearray(rows[end][0]);bad[2]^=64;rows[end]=(bytes(bad),rows[end][1])
        (d/'requests.bin').write_bytes(b''.join(struct.pack('<H',len(b))+b for b,_ in rows))
        for i,(_,t) in enumerate(rows,1):
            if t:(d/f'tile-{i:04d}.bin').write_bytes(t)
        for g in range(905,908):
            for prefix in ('expected','map'):shutil.copyfile(a.trace/f'{prefix}-{g}.bin',d/f'{prefix}-{g}.bin')
        shutil.copyfile(a.client/'sink165.sfc',d/'client.sfc')
        s=once(LUA,'local function loaded()',SETUP+'\nlocal function loaded()')
        s=once(s,' packet=requests[index];reads=0;',f''' packet=requests[index];if index=={target+1} then target=index;prior=snapshot() end;reads=0;''')
        s=once(s,' if a==0x6001 then',' if a==0x6001 then if stopNow and packet and pb(0)~=7 then return 128 end')
        s=once(s,' if a==0x420b and v==1 and(regs[0x4301]',""" if a==0x420b and v==1 and regs[0x4301]==0x80 and regs[0x4300]==8 and target and index==target then
  local n=regs[0x4305]+256*regs[0x4306];assert(n>0 and n<=64 and pw(16)==0);bytes=bytes+n
  if MODE=='stop64' or (MODE=='stop_tail' and bytes==pw(14))then stopNow=true end
 end
 if a==0x420b and v==1 and(regs[0x4301]""")
        s=once(s,'  lastStatus=ack[1]',"""  lastStatus=ack[1]
  if target and index==target then
   if lastStatus==0 then
    accepted516=true;check_output(pw(14))
    assert(bytes==(pw(16)==0 and pw(14) or 0),'DMA/fallback mismatch')
   else check_output(bytes) end
  end""")
        s=once(s,"   local hdma=file(",MAP_ORACLE+"   local hdma=file(")
        s=once(s,"  assert(captured==commits)", """  assert(captured==commits and target)
  local report=assert(io.open(ROOT..'/fill.txt','w'));report:write(bytes,' ',accepted516 and 1 or 0);report:close()""")
        for k,v in dict(ROOT=json.dumps(d.as_posix()),MODE=json.dumps(mode),TOTAL=len(rows),FRAMES=3,SCHEDULE='"continuous"',
                        START=3000000,FAULT=907,POISON='false',COMPACT='true').items():
            s=s.replace('@'+k+'@',str(v))
        (d/'capture.lua').write_text(s,encoding='utf8')
        with (d/'mesen.log').open('wb') as log:
            subprocess.run([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(d/'client.sfc'),'--timeout=120','--doNotSaveSettings',
                            '--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true',
                            '--debug.scriptWindow.scriptTimeout=90'],cwd=d,env=dict(os.environ,DOTNET_ROOT=str(a.dotnet)),
                           stdout=log,stderr=subprocess.STDOUT,timeout=135,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        r=json.loads((d/'result.json').read_text());n,accepted=map(int,(d/'fill.txt').read_text().split())
        assert r['commits']==2 and r['last_status']==(228 if mode in ('stop64','stop_tail') else 224)
        assert sha(d/'retained.rgb')==sha(d/'frame-906.rgb')
        assert bool(accepted)==(mode in ('tail242','two_chunks_plus','first_nonzero','second_nonzero'))
        if mode=='stop64':assert n==64
        if mode=='stop_tail':assert n==int.from_bytes(p[14:16],'little')
        results[mode]=dict(DMA_B=n,packet_accepted=bool(accepted),commits=2,status=r['last_status'])
        print(mode,n,accepted,flush=True)
    (a.out/'fill.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','out','client','mesen'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--dotnet',type=Path,default=Path('C:/works/dotnet'))
    a=p.parse_args();a.out=a.out.resolve();check(a)
