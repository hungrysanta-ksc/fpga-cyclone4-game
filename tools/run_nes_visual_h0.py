# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,os,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(probe,out):
 meta=json.loads((out/'capture.json').read_text())
 assert meta['exit_code']==0 and meta['rom_sha256']==sha(probe/'nes-h0-visual-030.sfc')
 frames=[list(map(int,s.split())) for s in (out/'frames.tsv').read_text().splitlines()]
 assert len(frames)==7 and [f[3] for f in frames]==[1,1,2,2,3,3,1],frames
 assert [f[1]-frames[0][1] for f in frames]==[0,30,60,90,120,150,180],frames
 comparisons=[]
 for idx,ef,clock,page,age,w,h in frames:
  actual=(out/f'frame-{idx:03}.rgb').read_bytes();expected=(probe/f'expected-{page}.rgb').read_bytes()
  expected=bytes(7*256*3)+expected+bytes(8*256*3)
  assert (w,h,len(actual))==(256,239,len(expected))
  bad=sum(actual[i:i+3]!=expected[i:i+3] for i in range(0,len(actual),3))
  comparisons.append({'page':page,'age':age,'emulator_frame':ef,'different_pixels':bad})
  assert bad==0,(idx,bad)
 rows=[list(map(int,s.split())) for s in (out/'trace.tsv').read_text().splitlines()]
 starts=[v for v in rows if v[0]==0x1fe6 and v[1]==1]
 ends=[v for v in rows if v[0]==0x1fe6 and v[1]==3]
 assert len(starts)==len(ends)==4
 tx=[]
 for start,end in zip(starts,ends):
  assert 225<=start[4]<=261 and 225<=end[4]<=261
  dmas=[v for v in rows if v[0]==0x420b and start[2]<v[2]<end[2]]
  assert len(dmas)==1 and dmas[0][-2:]==[24,2048]
  assert all(225<=v[4]<=261 for v in dmas)
  margin=(262-start[4])*1364-4-start[5]-(end[2]-start[2]);assert margin>0
  tx.append({'page':end[6],'duration_master_clocks':end[2]-start[2],'margin_master_clocks':margin})
 startup=[v[-2:] for v in rows if v[0]==0x420b and v[2]<starts[0][2]]
 assert startup==[[34,512],[24,14336],[24,14336],[24,14336]],startup
 brightness=[v[1] for v in rows if v[0]==0x2100];assert brightness==[128,15,15,15,15]
 result={'candidate':'NES-H0-VISUAL-030','passed':True,'frames':comparisons,'exact_pixels':7*256*239,'active_pixels':7*256*224,'capture_padding_rows':[7,8],'page_commits':tx,'hardware_verified':False,'scope':'Readable standalone224-line SNES diagnostic; no NES/FPGA transport claim','capture':meta,'auditor_sha256':sha(__file__)}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))

def main():
 p=argparse.ArgumentParser()
 for n in ('probe','out','mesen'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--audit-only',action='store_true')
 a=p.parse_args();probe=a.probe.resolve();out=a.out.resolve();exe=a.mesen.resolve()
 if a.audit_only:
  audit(probe,out);return
 assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
 source=Path(__file__).resolve().parents[1]/'snes/video_probe/capture_visual_h0.lua'
 (out/'capture.lua').write_text('local OUT_DIR='+json.dumps(out.as_posix())+'\n'+source.read_text(),encoding='utf-8',newline='\n')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (out/'mesen.log').open('wb') as log:
  run=subprocess.run([str(exe),'--testRunner',str(out/'capture.lua'),str(probe/'nes-h0-visual-030.sfc'),'--timeout=30','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
 meta={'exit_code':run.returncode,'rom_sha256':sha(probe/'nes-h0-visual-030.sfc'),'observer_sha256':sha(source),'runner_sha256':sha(__file__),'mesen_sha256':sha(exe)}
 (out/'capture.json').write_text(json.dumps(meta,indent=2)+'\n')
 assert run.returncode==0,'See raw mesen.log'
 audit(probe,out)
if __name__=='__main__':main()
