# SPDX-License-Identifier: MIT
"""Actual SNES CPU/SPC boot plus focused port-failure injection and video reuse."""
from pathlib import Path
import argparse,json,os,subprocess
from build_nes_game163 import build
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','mesen']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 e=a.baseline.resolve()/'nes-game161/evidence';pins=json.loads((e/'manifest.json').read_bytes())['files']
 for n in ['client/payload.bin','client/expected-1.rgb','client/expected-2.rgb']:
  assert sha(e/n)==pins[n]
 build(a.out/'client');cases=[]
 (a.out/'payload.bin').write_bytes((e/'client/payload.bin').read_bytes())
 for mode,expected in [(0,0xa9),(1,0xe1),(2,0xe2),(3,0xe3),(4,0xe4),(5,0xe5)]:
  d=a.out/f'case{mode}';d.mkdir()
  lua='local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal PAYLOAD='+json.dumps((a.out/'payload.bin').as_posix())+f'\nlocal MODE={mode}\n'
  lua+='''
local phase,status,lastwrite=0,nil,0
local audio=assert(io.open(OUT_DIR..'/audio.tsv','w'))
emu.addMemoryCallback(function(a,v)
 if a==0x2142 and phase==2 then phase=3 end
 if a==0x2140 then
  lastwrite=v
  if v==0xcc then phase=1 elseif phase==1 then phase=2 end
 end
end,emu.callbackType.write,0x2140,0x2143)
emu.addMemoryCallback(function(a,v)
 if MODE==1 then return 0 end
 if MODE==2 and phase==1 and a==0x2140 then return 0 end
 if MODE==3 and phase==2 and a==0x2140 then return lastwrite~255 end
 if MODE==4 and phase==3 and a==0x2140 then return 0 end
 if MODE==5 and phase==3 and a==0x2141 then return 0x60 end
end,emu.callbackType.read,0x2140,0x2141)
emu.addMemoryCallback(function(a,v)
 assert(status==nil,'status must be written exactly once');status=v
 audio:write(v..' '..emu.getState().frameCount..' '..emu.getState().masterClock..'\\n');audio:flush()
end,emu.callbackType.write,0x7001,0x7001)
'''
  lua+=(ROOT/'snes/video_probe/capture_game161.lua').read_text().replace("if s.frameCount>120", "if s.frameCount>240")
  (d/'capture.lua').write_text(lua,encoding='utf8')
  env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
  with (d/'mesen.log').open('wb') as log:
   run=subprocess.run([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(a.out/'client/game163.sfc'),'--timeout=90','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=110,creationflags=subprocess.CREATE_NO_WINDOW)
  assert run.returncode==0,(mode,(d/'mesen.log').read_text(errors='replace')[-1800:])
  status,frame,tick=map(int,(d/'audio.tsv').read_text().split());assert status==expected,(mode,status,expected)
  for i in [1,2]:assert (d/f'frame-{i}.rgb').read_bytes()==(e/f'client/expected-{i}.rgb').read_bytes(),(mode,i)
  inputs=[list(map(int,s.split())) for s in (d/'inputs.tsv').read_text().splitlines()];assert len(inputs)==14
  cases.append(dict(mode=mode,status_hex=f'{status:02X}',frame=frame,master_clock=tick,exact_rgb_frames=2,pad_polls=14))
 result=dict(passed=True,cases=cases,program_sha256=sha(a.out/'client/game-program.hex'),sources={n:sha(ROOT/n) for n in ['tools/nes_spc163.py','tools/build_nes_game163.py','tools/test_nes_game163_client.py','src/renderer/base/g9_snes_io.py','snes/video_probe/capture_game161.lua']},scope='Actual SNES CPU and SPC for positive boot; five injected port failures; two prior exact RGB frames/pad polls each. Not physical DAC/analog sound or warm reset proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
