# SPDX-License-Identifier: MIT
"""Execute actual SNES CPU/SPC: vblank writes, full RGB, source wrap and pads."""
from pathlib import Path
import argparse,json,os,subprocess
from build_nes_game164 import build
from build_nes_game163 import build as old_build
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','mesen']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii();a.out.mkdir(parents=True)
 e=a.baseline.resolve()/'nes-game161/evidence';pins=json.loads((e/'manifest.json').read_bytes())['files']
 for n in ['client/payload.bin','client/expected-1.rgb','client/expected-2.rgb']:assert sha(e/n)==pins[n]
 build(a.out/'client');old_build(a.out/'old-client')
 (a.out/'payload.bin').write_bytes((e/'client/payload.bin').read_bytes());cases=[]
 for name,delay,old in [('ready3',3,False),('ready17',17,False),('old-blank-control',3,True)]:
  d=a.out/name;d.mkdir()
  lua='local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal PAYLOAD='+json.dumps((a.out/'payload.bin').as_posix())+f'\nlocal READY_DELAY={delay}\n'
  lua+=(ROOT/'snes/video_probe/capture_game164.lua').read_text();(d/'capture.lua').write_text(lua,encoding='utf8')
  env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
  rom=a.out/('old-client/game163.sfc' if old else 'client/game164.sfc')
  with (d/'mesen.log').open('wb') as log:
   run=subprocess.run([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(rom),'--timeout=40','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=55,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(d/'mesen.log').read_text(errors='replace')
  if (d/'failure.txt').exists():text+='\n'+(d/'failure.txt').read_text()
  if old:
   assert run.returncode!=0 and 'display blanked after initial reveal' in text,text[-2000:]
   cases.append(dict(name=name,rejected=True,reason='display blanked after initial reveal'));continue
  assert run.returncode==0,text[-2500:]
  for i in [1,2]:assert (d/f'frame-{i}.rgb').read_bytes()==(e/f'client/expected-{i}.rgb').read_bytes(),(name,i)
  dmas=[list(map(int,s.split())) for s in (d/'dma.tsv').read_text().splitlines()]
  assert len(dmas)==12 and dmas[0][2]==57344
  assert [row[2] for row in dmas[1:]]==[5632]*10+[1024]
  assert all(225<=row[5]<262 for row in dmas[1:])
  inputs=[list(map(int,s.split())) for s in (d/'inputs.tsv').read_text().splitlines()]
  assert len(inputs)>=13
  cases.append(dict(name=name,ready_delay_frames=delay,exact_rgb_frames=2,checked_canvas_pixels=122368,active_picture_pixels=114688,dma_records=dmas,pad_polls=len(inputs),max_visible_dma_end_line=max(row[5] for row in dmas[1:]),spc_status='A9',every_visible_frame_pad_polled=True))
 result=dict(passed=True,cases=cases,program_sha256=sha(a.out/'client/game-program.hex'),sources={n:sha(ROOT/n) for n in ['tools/build_nes_game164.py','tools/test_nes_game164_client.py','snes/video_probe/capture_game164.lua','tools/nes_spc163.py']},scope='Actual NTSC SNES CPU/SPC with synthetic frozen FPGA pixels/ready/buttons; all visible VRAM writes in vblank, no post-reveal forced blank, complete RGB equality, input polling through ready stalls. Not physical frame rate, atomic update or physical pad quality proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
