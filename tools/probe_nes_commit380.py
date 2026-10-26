# SPDX-License-Identifier: MIT
"""Actual65816 commit guards:STOP while waiting/before unblank/before or after ACK."""
import argparse,inspect,json,os,subprocess
from pathlib import Path
import probe_nes_display266 as prior
from nes_delta231 import ROOT,sha,once

def rom(d):
 s=inspect.getsource(prior.rom)
 s=once(s,'def rom(d):', '''def rom(d):
 def guard380(label):
  c.absolute(0xad,0x6001);c.emit(0x29,0xc0);c.branch(0xf0,'safe380_'+label);c.jump('abort380');c.label('safe380_'+label)
'''.rstrip())
 s=once(s,' c.store(0x420c,0);c.absolute(0xad,0x1000);', " guard380('apply');c.store(0x420c,0);c.absolute(0xad,0x1000);")
 s=once(s,'c.store(0x2100,15)', "guard380('unblank');c.store(0x2100,15)")
 s=once(s,' for i in range(4):c.absolute(0xad,0x6048+i);', " guard380('ack')\n for i in range(4):c.absolute(0xad,0x6048+i);")
 s=once(s,' c.store(0x6058,0x5a)', " c.store(0x6058,0x5a);guard380('post')")
 s=once(s,"c.label('done');c.branch(0x80,'done');data=c.finish()", """c.label('done');c.branch(0x80,'done')
 c.label('abort380');c.store(0x420c,0);c.store(0x2100,0x80);c.store(0x606f,0xee);c.label('halt380');c.branch(0x80,'halt380');data=c.finish()""")
 ns=dict(prior.__dict__);exec(compile(s,'commit380-generator','exec'),ns);return ns['rom'](d)

LUA=r'''
local out=assert(io.open(OUT..'/events.csv','w'));local reads=0;local status=0;local ack=false;local ackscan=-1;local regs={};local bankwrites=0
local function note(op,a,v)local s=emu.getState();out:write(string.format('%d,%d,%d,%d,%d\n',op,a,v or 0,s.masterClock,s['ppu.scanline']));out:flush()end
emu.addMemoryCallback(function(a,v)note(0,a,1);return 1 end,emu.callbackType.read,0x6054)
emu.addMemoryCallback(function(a,v)local b=VIEW[a-0x6070+1];assert(b);reads=reads+1;note(0,a,b);return b end,emu.callbackType.read,0x6070,0x607b)
emu.addMemoryCallback(function(a,v)status=status+1;local b=(STOP>0 and (OLD or status>=STOP)) and 0x80 or 0;note(0,a,b);return b end,emu.callbackType.read,0x6001)
emu.addMemoryCallback(function(a,v)local b=52+a-0x6048;note(0,a,b);return b end,emu.callbackType.read,0x6048,0x604b)
local function write(a,v)note(1,a,v);regs[a]=v;if reads==12 and a~=0x2100 and a~=0x420c then bankwrites=bankwrites+1 end end
emu.addMemoryCallback(write,emu.callbackType.write,0x2100,0x212f)
emu.addMemoryCallback(write,emu.callbackType.write,0x4310,0x4334)
emu.addMemoryCallback(write,emu.callbackType.write,0x420c)
emu.addMemoryCallback(function(a,v)note(1,a,v);if a==0x6058 then ack=true;ackscan=emu.getState()['ppu.scanline'];assert(v==0x5a and reads==12 and ackscan>=225)end end,emu.callbackType.write,0x604c,0x6058)
emu.addMemoryCallback(function(a,v)
 assert(reads==12);local abort=not OLD and STOP>0
 if abort then assert(v==0xee and regs[0x2100]==0x80 and regs[0x420c]==0 and ack==(STOP==4));if STOP==1 then assert(bankwrites==0)end
 else assert(v==0xa5 and ack)end
 local f=assert(io.open(OUT..'/cpu-result.json','w'));f:write(string.format('{"completed":true,"abort":%s,"status_reads":%d,"ACK_attempted":%s,"ACK_scanline":%d,"post_view_PPU_writes":%d,"force_blank":%s}',tostring(abort),status,tostring(ack),ackscan,bankwrites,tostring(regs[0x2100]==0x80)));f:close();out:close();emu.stop(0)
end,emu.callbackType.write,0x606f)
-- Zero terminators are explicit CPU-control fixtures,not uploadedHDMA proof.
for _,a in ipairs({0x16500,0x17161,0x17203,0x1e500,0x1f1b2,0x1f203})do emu.write(a,0,emu.memType.snesWorkRam)end
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);results=[]
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 cases=[('old-stop',0,1,True),('normal0',0,0,False),('normal1',1,0,False)]+[(f'stop{i}',0,i,False) for i in range(1,5)]
 for name,bank,stop,old in cases:
  case=d/name;case.mkdir();body=prior.rom(case) if old else rom(case)
  view=bytes.fromhex((ROOT.parent/f'probes/nes-joint266/cpu0{bank+1}/expected-display.hex').read_text())
  script='local OUT='+json.dumps(case.as_posix())+'\nlocal VIEW={'+','.join(map(str,view))+'}\nlocal STOP='+str(stop)+'\nlocal OLD='+str(old).lower()+'\n'+LUA
  (case/'capture.lua').write_text(script,newline='\n')
  with (case/'mesen.log').open('wb') as log:
   r=subprocess.run(['C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe','--testRunner',str(case/'capture.lua'),str(case/'display.sfc'),'--timeout=20','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(case/'mesen.log').read_text(errors='replace')[-2000:]
  result=json.loads((case/'cpu-result.json').read_text());result.update(name=name,ROM=sha(case/'display.sfc'),events=sha(case/'events.csv'),body_bytes=body);results.append(result)
 assert results[0]['status_reads']==0 and results[0]['ACK_attempted'] and results[0]['post_view_PPU_writes']>0
 report=dict(passed=True,old_kernel_STOP_safe=False,cases=results,selected_for_whole_schedule=False,scope='Actual65816 paired old/new mockedfault tests;precommit abort forces blank/disablesHDMA and withholdsACK. STOPafterACK is postcommit invalidation. No fullresidentCPU/recovery/fullpixel proof.',source={str(ROOT/'tools/probe_nes_commit380.py'):sha(ROOT/'tools/probe_nes_commit380.py')})
 (d/'result.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(report))
if __name__=='__main__':main()
