# SPDX-License-Identifier: MIT
# Real Mesen CPU/PPU execution with an explicitly simulated cartridge MMIO device.
from pathlib import Path
import argparse,hashlib,json,os,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(probe,rtl,out,mode):
 frames=[list(map(int,s.split())) for s in (out/'frames.tsv').read_text().splitlines()]
 pages=[f[3] for f in frames]
 assert pages==([0,1,2,3,1,2,3] if mode=='normal' else [0,4]),pages
 for idx,frame,clock,page,error,w,h in frames:
  expected=bytes(7*256*3)+(probe/f'expected-{page}.rgb').read_bytes()+bytes(8*256*3)
  actual=(out/f'frame-{idx:03}.rgb').read_bytes()
  assert (w,h,len(actual))==(256,239,len(expected))
  assert actual==expected,(mode,page,sum(a!=b for a,b in zip(actual,expected)))
 rows=[s.split() for s in (out/'trace.tsv').read_text().splitlines()]
 d=[[int(x) for x in row[1:]] for row in rows if row[0]=='D']
 model=list(map(int,(out/'model.tsv').read_text().split()))
 tx=[]
 if mode=='normal':
  assert model==[6,12288,0],model
  assert [f[1]-frames[1][1] for f in frames[1:]]==[0,60,120,180,240,300]
  assert bytes(row[1] for row in d)==rtl.read_bytes()[:12288]
  for i in range(6):
   packet=d[i*2048:(i+1)*2048]
   assert [row[0] for row in packet]==list(range(0x408000,0x408800))
   assert all(225<=row[4]<=261 for row in packet)
   gaps=[b[2]-a[2] for a,b in zip(packet,packet[1:])]
   assert set(gaps)<={8,48} and 8 in gaps,set(gaps)
   stalls=0
   for before,after in zip(packet,packet[1:]):
    if after[2]-before[2]==48:
     assert before[4]==after[4] and 524<=before[5]<=538 and after[5]==before[5]+48
     stalls+=1
   tx.append({'sequence':i+1,'first_read_master_clock':packet[0][2],'last_read_master_clock':packet[-1][2],'read_interval_master_clocks':sorted(set(gaps)),'refresh_stalls':stalls})
  # DMA programming must really use bank40 incrementing mode1, VRAM2118/2119,2048 bytes.
  setup=[[int(x) for x in row[1:]] for row in rows if row[0]=='A']
  streams=[row for row in setup if row[0]==64]
  assert len(streams)==6 and all(row[:5]==[64,32768,2048,1,24] for row in streams)
  starts=[[int(x) for x in row[1:]] for row in rows if row[:3]==['S','8166','1']]
  ends=[[int(x) for x in row[1:]] for row in rows if row[:3]==['S','8166','3']]
  assert len(starts)==len(ends)==6
  for txrow,start,end in zip(tx,starts,ends):
   assert 225<=start[4]<=end[4]<=261
   margin=(262-start[4])*1364-4-start[5]-(end[2]-start[2]);assert margin>0
   txrow.update(duration_master_clocks=end[2]-start[2],margin_master_clocks=margin)
 else:
  assert model==[0,0,1 if mode=='absent' else 2],model
  assert not d
 result={'candidate':'NES-H1-PATTERN-033','mode':mode,'passed':True,'pages':pages,'frames':len(frames),'exact_pixels':len(frames)*256*239,'transactions':tx,'model_counts':model,'scope':'Real SNES CPU/PPU DMA with Lua MMIO model fed actual RTL bytes; not co-simulation or physical FPGA timing','auditor_sha256':sha(__file__)}
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
def main():
 p=argparse.ArgumentParser()
 for n in ('probe','rtl-bytes','out','mesen'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mode',choices=['normal','absent','bad_length'],default='normal');p.add_argument('--audit-only',action='store_true')
 a=p.parse_args();probe=a.probe.resolve();rtl=a.rtl_bytes.resolve();out=a.out.resolve();exe=a.mesen.resolve()
 if a.audit_only:print(json.dumps(audit(probe,rtl,out,a.mode),indent=2));return
 assert str(out).isascii() and not out.exists();out.mkdir()
 source=Path(__file__).resolve().parents[1]/'snes/video_probe/capture_h1_pattern.lua'
 prefix='local OUT_DIR='+json.dumps(out.as_posix())+'\nlocal RTL_BYTES='+json.dumps(rtl.as_posix())+'\nlocal MODE='+json.dumps(a.mode)+'\n'
 (out/'capture.lua').write_text(prefix+source.read_text(),encoding='utf-8',newline='\n')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (out/'mesen.log').open('wb') as log:
  cp=subprocess.run([str(exe),'--testRunner',str(out/'capture.lua'),str(probe/'nes-h1-pattern-033.sfc'),'--timeout=30','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
 meta={'exit_code':cp.returncode,'rom_sha256':sha(probe/'nes-h1-pattern-033.sfc'),'rtl_bytes_sha256':sha(rtl),'observer_sha256':sha(source),'runner_sha256':sha(__file__),'mesen_sha256':sha(exe),'mode':a.mode}
 (out/'capture.json').write_text(json.dumps(meta,indent=2)+'\n')
 assert cp.returncode==0,'Inspect raw mesen.log'
 print(json.dumps(audit(probe,rtl,out,a.mode),indent=2))
if __name__=='__main__':main()
