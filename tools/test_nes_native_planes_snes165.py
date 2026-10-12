# SPDX-License-Identifier: MIT
"""Reproduce two formerly rejected game frames in the actual SNES model."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
from nes_native_planes165 import PlaneConsumer,decode,reference_planes_rgb
from test_nes_native_commands165 import build,ROOT
from nes_game147 import sha

def main():
 p=argparse.ArgumentParser()
 for n in ['stream','planes','out','mesen']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 assert json.loads((a.planes/'result.json').read_bytes())['passed']
 selected=[12,15];raw=bytes(int(v,16) for v in (a.stream/'chr.hex').read_text().split())
 tiles={t:raw[t*16:t*16+16] for t in range(8192)};allrows={}
 for line in (a.stream/'rows.tsv').read_text().splitlines():
  g,y,x,m,v=line.split();v=int(v,16);allrows[int(g),int(y)]=(int(x),int(m,16),tuple((v>>(i*6))&63 for i in range(32)))
 consumer=PlaneConsumer();plans=[];expected=[]
 for g in selected:
  info,words=decode(a.planes/f'frame-{g}-mode-0.dump');assert info['valid']
  rows=[allrows[g,y] for y in range(224)];plan=consumer.prepare(words,rows,tiles)
  consumer.commit(plan);plans.append(plan)
  expected.append(bytes(7*256*3)+reference_planes_rgb(words,rows,tiles)+bytes(8*256*3))
 sizes=build(plans,a.out)
 script='local OUT_DIR='+json.dumps(a.out.as_posix())+'\n'+(ROOT/'snes/video_probe/capture_native_commands165.lua').read_text()
 (a.out/'capture.lua').write_text(script,encoding='utf8')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (a.out/'mesen.log').open('wb') as f:
  r=subprocess.run([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.out/'native.sfc'),'--timeout=40',
   '--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],
   env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(a.out/'mesen.log').read_text(errors='replace')[-3000:]
 frames=[]
 for i,(plan,gold) in enumerate(zip(plans,expected),1):
  actual=(a.out/f'frame-{i}.rgb').read_bytes();(a.out/f'expected-{i}.rgb').write_bytes(gold)
  assert actual==gold,(i,len(actual),sum(x!=y for x,y in zip(actual,gold)))
  frames.append(dict(generation=selected[i-1],payload=plan['payload'],charged=plan['charged'],commands=len(plan['writes']),
   derived_patterns=plan['derived_patterns'],rgb_sha256=hashlib.sha256(actual).hexdigest()))
 trace=[list(map(int,l.split())) for l in (a.out/'trace.tsv').read_text().splitlines()]
 commit=next(r for r in trace if r[0]==0x7000 and r[1]==2);assert commit[3]>=225
 result=dict(passed=True,frames=frames,pixels=114688,update_commit_scanline=commit[3],**sizes,
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_native_planes165.py','tools/test_nes_native_planes_snes165.py',
   'tools/nes_native_commands165.py','tools/test_nes_native_commands165.py','snes/video_probe/capture_native_commands165.lua']},
  scope='Two formerly rejected real-game boot frames through PC derived patterns and actual SNES CPU/DMA/PPU. Complete CHR from PC ROM. No live hardware fill/host/first-level/FPS proof.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
