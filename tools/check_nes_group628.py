# SPDX-License-Identifier: MIT
"""Corrupt a real inactive-bank delta, or interrupt after one reconstructed row."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from nes_raw506 import once
from test_nes_seal538_stop import exercise
from test_nes_output489_snes import LUA
from test_nes_trim514_schedule import MAP_ORACLE


SAVE_MAPS="""
 local f=assert(io.open(ROOT..'/stopped-maps.bin','wb'))
 for _,bank in ipairs({0,1}) do for _,vram in ipairs({false,true}) do
  local buf={};local at=vram and (0x6000+bank*0x4000) or (0x15000+bank*0x8000)
  for i=0,4095 do buf[#buf+1]=string.char(emu.read(at+i,vram and emu.memType.snesVideoRam or emu.memType.snesWorkRam)) end
  f:write(table.concat(buf))
 end end
 f:close()"""


def inject(s,labels,kind):
    cold=kind=='cold'
    condition='pb(0)==2 and pb(1)==2 and pw(10)>=2048' if cold else 'pb(0)==9 and pw(14)>=128'
    action={
        'cold':"packet=string.char(9)..packet:sub(2,12)..string.pack('<I2I2I4I4I2',10,64,1,0,0)",
        'identity':"packet=packet:sub(1,16)..string.char(pb(16)~1)..packet:sub(18)",
        'checksum':"packet=packet:sub(1,20)..string.char(pb(20)~1)..packet:sub(22)",
        'trailing':"packet=packet:sub(1,12)..string.pack('<I2',pw(12)+1)..packet:sub(15)..string.char(0)",
        'short':"packet=packet:sub(1,12)..string.pack('<I2',pw(12)-1)..packet:sub(15,-2)",
        'retained':"""local pos=nil
 for j=0,pw(14)//4-1 do
  if (pb(24+j//8)&(1<<(j%8)))==0 then pos=j*4;break end
 end
 assert(pos,'expected omitted group')
 local a=0x10000+word(0x1020)+0x5000+pw(10)+pos
 emu.write(a,rd(a)~1,emu.memType.snesWorkRam)""",
        'stop':""
    }[kind]
    s=once(s,'local function loaded()',f"""local touched628=false
local sampled628=false
local selected628=nil
local rows628=0
emu.addMemoryCallback(function()
 if selected628==index then rows628=rows628+1;if rows628==2 then sampled628=true end end
end,emu.callbackType.exec,{labels['row628']})
local function loaded()""") if kind=='stop' else once(s,'local function loaded()','local touched628=false\nlocal function loaded()')
    s=once(s," if pb(0)==7 then tile=file",f""" if not touched628 and pw(8)==FAULT and {condition} then
 touched628=true;{action}
 {'selected628=index' if kind=='stop' else ''}
 end
 if pb(0)==7 then tile=file""")
    s=once(s,"if MODE=='stop_final'and rd(0x1025)==2 then return 128 end",'')
    if kind=='stop':
        # row628 is entered once per row. From the second row on, assert
        # STOP at the next service sample and observe the real reject ACK.
        s=once(s,'if a==0x6001 then','if a==0x6001 then if sampled628 then return 128 end')
    status=228 if kind=='stop' else 224
    checks=f"""assert(touched628 and lastStatus=={status},'expected injected fault')
 for i=0,6,2 do assert(word(0x14d0+i)==0,'bank receipt survived fault')end"""
    if kind=='stop':
        checks+=SAVE_MAPS
    return once(s,"assert(lastStatus==0xe4,'STOP status')",checks)


def recover(args, *, receipt_tags=True):
    out=args.out/'restart'
    out.mkdir()
    for src in (args.out/'906-cold').glob('*.bin'):
        shutil.copyfile(src,out/src.name)
    shutil.copyfile(args.out/f'{args.generation}-stop/stopped-maps.bin',out/'stopped-maps.bin')
    assert (out/'stopped-maps.bin').stat().st_size==16384
    packet_data=(out/'requests.bin').read_bytes()
    at=count=0
    while at<len(packet_data):
        n=int.from_bytes(packet_data[at:at+2],'little')
        assert packet_data[at+2]!=9
        at+=n+2
        count+=1
    assert at==len(packet_data)
    s=once(LUA,'local function loaded()',"""local prior628=file('stopped-maps.bin')
local j628=1
for _,bank in ipairs({0,1}) do for _,vram in ipairs({false,true}) do
 local at=vram and (0x6000+bank*0x4000) or (0x15000+bank*0x8000)
 for i=0,4095 do
  emu.write(at+i,prior628:byte(j628),vram and emu.memType.snesVideoRam or emu.memType.snesWorkRam)
  j628=j628+1
 end
end end
for i=0,7 do emu.write(0x14d0+i,0xa5,emu.memType.snesWorkRam) end
local function loaded()""")
    s=once(s,'   local hdma=file(',MAP_ORACLE+'   local hdma=file(')
    if receipt_tags:
        s=once(s,'packet=requests[index];','''if index==1 then for i=0,6,2 do assert(word(0x14d0+i)==0,'cold tag')end end
 packet=requests[index];''')
    else:
        s=once(s,'for i=0,7 do emu.write(0x14d0+i,0xa5,emu.memType.snesWorkRam) end','')
    for k,v in dict(ROOT=json.dumps(out.as_posix()),MODE='"normal"',SCHEDULE='"continuous"',START=3000000,
                    FAULT=0,COMPACT='true',POISON='false',TOTAL=count,FRAMES=2).items():
        s=s.replace('@'+k+'@',str(v))
    lua=out/'restart.lua'
    lua.write_text(s,newline='\n')
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([str(args.mesen),'--testRunner',str(lua),str((args.client/'sink165.sfc').resolve()),
                        '--timeout=60','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true',
                        '--snes.disableFrameSkipping=true'],cwd=out,stdout=log,stderr=subprocess.STDOUT,
                       env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                       creationflags=subprocess.CREATE_NO_WINDOW,check=True,timeout=90)
    r=json.loads((out/'result.json').read_text())
    assert r['passed'] and r['commits']==2 and r['last_status']==1
    for g in (905,906):
        assert (out/f'frame-{g}.rgb').read_bytes()==(args.trace/f'frame-{g}.rgb').read_bytes()
    return dict(commits=r['commits'],status=r['last_status'],restored_map_bytes=16384)


def run(args):
    labels=json.loads((args.client/'labels.json').read_text())
    args.out=args.out.resolve()
    args.out.mkdir(parents=True,exist_ok=False)
    rows=[]
    for kind in ('cold','identity','checksum','trailing','short','retained','stop'):
        rows.append(exercise(args,906 if kind=='cold' else args.generation,kind,
                    edit_packet_case=lambda s:inject(s,labels,kind),reject_status=228 if kind=='stop' else 224))
    (args.out/'result.json').write_text(json.dumps(dict(guards=rows,restart=recover(args)),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('trace','client','out','mesen'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--generation',type=int,default=951)
    run(p.parse_args())
