# SPDX-License-Identifier: MIT
"""Measure the unchanged actual26665816 display kernel,including4212 polling."""
import argparse,csv,json,os,shutil,subprocess
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from probe_nes_display266 import rom

LUA=r'''
local out=assert(io.open(OUT..'/events.csv','w'))
local function note(op,a,v)
 local s=emu.getState();out:write(string.format('%d,%d,%d,%d,%d\n',op,a,v or 0,s.masterClock,s['ppu.scanline']));out:flush()
end
local reads=0
emu.addMemoryCallback(function(a,v)note(0,a,1);return 1 end,emu.callbackType.read,0x6054)
emu.addMemoryCallback(function(a,v)local b=VIEW[a-0x6070+1];assert(b);note(0,a,b);reads=reads+1;return b end,emu.callbackType.read,0x6070,0x607b)
emu.addMemoryCallback(function(a,v)note(0,a,0x34+a-0x6048);return 0x34+a-0x6048 end,emu.callbackType.read,0x6048,0x604b)
emu.addMemoryCallback(function(a,v)note(0,a,v)end,emu.callbackType.read,0x4212)
local function write(a,v)note(1,a,v)end
emu.addMemoryCallback(write,emu.callbackType.write,0x2100,0x2133)
emu.addMemoryCallback(write,emu.callbackType.write,0x4310,0x4334)
emu.addMemoryCallback(write,emu.callbackType.write,0x420c)
emu.addMemoryCallback(function(a,v)
 note(1,a,v)
 if a==0x6058 then assert(reads==12 and v==0x5a and emu.getState()['ppu.scanline']>=225);out:close();emu.stop(0)end
end,emu.callbackType.write,0x604c,0x6058)
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet';results=[]
 for bank in (0,1):
  case=d/f'bank{bank}';case.mkdir();body=rom(case);ref=BASE/f'probes/nes-joint266/cpu0{bank+1}'
  assert sha(case/'display.sfc')==sha(ref/'display.sfc')
  view=bytes.fromhex((ref/'expected-display.hex').read_text());assert len(view)==12 and view[:3]==bytes([bank,24,2])
  (case/'capture.lua').write_text('local OUT='+json.dumps(case.as_posix())+'\nlocal VIEW={'+','.join(map(str,view))+'}\n'+LUA,newline='\n')
  with (case/'mesen.log').open('wb') as log:
   r=subprocess.run(['C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe','--testRunner',str(case/'capture.lua'),str(case/'display.sfc'),'--timeout=20','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=case,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(case/'mesen.log').read_text(errors='replace')
  events=[list(map(int,x)) for x in csv.reader((case/'events.csv').read_text().splitlines())]
  views=[x for x in events if x[0]==0 and 0x6070<=x[1]<=0x607b];assert len(views)==12
  poll=next(x for x in events if x[1]==0x4212);ack=events[-1];assert ack[1:3]==[0x6058,90]
  results.append(dict(bank=bank,ROM=sha(case/'display.sfc'),events=sha(case/'events.csv'),head_first_master=next(x[3] for x in events if x[1]==0x6054),
   first_view_master=views[0][3],last_view_master=views[-1][3],first_4212_master=poll[3],post_view_to_first_4212_clocks=poll[3]-views[-1][3],ack_master=ack[3],ack_scanline=ack[4],body=body))
 result=dict(passed=True,cases=results,scope='Actual unchanged415B266display kernel with mocked12Bview/ready/token;records4212poll and PPU writes. No RTL/DMA/HDMA upload or fullCPU proof.',source={str(ROOT/'tools/probe_nes_kernel378.py'):sha(ROOT/'tools/probe_nes_kernel378.py'),str(ROOT/'tools/probe_nes_display266.py'):sha(ROOT/'tools/probe_nes_display266.py')})
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result))
if __name__=='__main__':main()
