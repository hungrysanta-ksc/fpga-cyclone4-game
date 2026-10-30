# SPDX-License-Identifier: MIT
"""502 bounded row ownership; same PPU/native equivalence and retained guards."""
import argparse,json,shutil
from pathlib import Path
import test_nes_capture501_equivalence as eq
base=eq.base
ROOT=base.ROOT

def prepare(a):
 if a.guards:eq.candidate.prepare(a)
 else:eq.prepare(a)
 m=json.loads((a.out/'inputs.json').read_text())
 for n in ['nes_native_planes165.sv','nes_native_frame201.sv']:
  shutil.copy2(ROOT/'src/fpga/nes_capture502'/n,a.out/n);m['sources'][n]=base.sha(a.out/n)
 # Preserve actual retained rows for downstream serializer/CPU experiments.
 p=a.out/'capture500_tb.sv';s=p.read_text();s=s.replace('  $display("RESULT500',"""  if(guard==0)begin
   fd=$fopen({stimulus,".raw502.txt"},"w");
   for(integer i=0;i<patches;i++)begin
    $fwrite(fd,"%0d ",patch_row[i]);
    for(integer x=0;x<256;x++)$fwrite(fd,"%02h",capture.pixels.rows.pixels[i*256+x]);
    $fwrite(fd,"\\n");
   end
   $fclose(fd);
  end
  $display("RESULT500""");p.write_text(s,encoding='utf8',newline='\n')
 if getattr(a,'boundary',False):
  m['cases']=[]
  for name,off,on in [('visible-end',[193,254],[193,258]),('hblank-start',[193,257],[193,300]),('prefetch-first',[193,320],[193,324]),('prefetch-last',[193,338],[194,0]),('line-zero',[193,340],[194,4])]:
   events=[off+[1,0],on+[1,24]];c=dict(name=name,frame=None,delay=0,address_writes=False,events=events);m['cases'].append(c)
   (a.out/(name+'.txt')).write_text(''.join(' '.join(map(str,r))+'\n' for r in events),newline='\n')
  events=[[193,8,1,0],[194,4,1,24],[200,8,1,0],[201,4,1,24]]
  m['cases'].append(dict(name='four-raw-rows',frame=None,delay=0,address_writes=False,events=events))
  (a.out/'four-raw-rows.txt').write_text(''.join(' '.join(map(str,r))+'\n'for r in events),newline='\n')
 m['testbench_SHA256']=base.sha(p);(a.out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('mode',choices=['prepare','run'])
 for n in ['board','reference','out','questa-bin']:p.add_argument('--'+n,type=Path)
 p.add_argument('--focus');p.add_argument('--edges',action='store_true');p.add_argument('--guards',action='store_true');p.add_argument('--guard-list');p.add_argument('--boundary',action='store_true')
 a=p.parse_args();a.phase_sweep=True
 if a.mode=='prepare':prepare(a)
 else:
  m=json.loads((a.out/'inputs.json').read_text())
  if 'planes501_reference.sv' in m['sources']:base.FILES.append('planes501_reference.sv')
  eq.candidate.run(a)
