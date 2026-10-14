# SPDX-License-Identifier: MIT
"""Deployed batched converter: mask validation, padding reuse, unchanged payload."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_game147 import ROOT,sha
from nes_clip178 import converter,header,replace

def main():
    p=argparse.ArgumentParser()
    for n in ['prior','video','out','gcc']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();a.out.mkdir()
    names=['nes_native165.c','nes_native165.h','nes_native_video165.c','nes_native_video165.h','nes_trace166.c','nes_trace166.h']
    prep=json.loads((a.prior/'preparation-boundary177.json').read_bytes())
    pins=prep['copied']|prep['changed']|prep['added']
    for n in names:
        assert sha(a.prior/'src'/n)==pins['src/'+n],n
        shutil.copy2(a.prior/'src'/n,a.out/n)
    old={n:sha(a.out/n) for n in names}
    for n,fn in [('nes_native_video165.c',converter),('nes_native_video165.h',header)]:
        f=a.out/n;f.write_text(fn(f.read_text()),encoding='utf8',newline='\n')
    s=(ROOT/'tests/nes-functional/native_video165_host.c').read_text()
    s=replace(s,'widths[]={2,1,7,3,7,1,2,8}', 'widths[]={2,1,7,4,7,1,2,8}')
    s=replace(s,'n==(kind?32u:16u)', 'n>0&&n<=240&&n%(kind?32u:16u)==0&&slot+n/(kind?32u:16u)<=(kind?128u:1024u)')
    s=s.replace('fail_call=4','fail_call=1').replace('calls==4','calls==1')
    anchor='printf("PASS VIDEO165 generation='
    at=s.index(anchor)
    s=s[:at]+'''assert(sizeof(plan)==15888); /*178 mask occupies existing alignment byte. */
 for(unsigned mask=0;mask<256;mask++){
  for(unsigned y=0;y<224;y++)scene.raster[y]=(scene.raster[y]&~((uint64_t)255<<36))|((uint64_t)mask<<36);
  calls=0;bool ok=nes_native_video165_build(&scene,palette,&plan,stage,NULL);
  assert(ok==(mask==0x18||mask==0x1e));
  if(ok)assert(plan.valid&&plan.display_mask==mask);
  else assert(!plan.valid&&plan.error==3&&calls==0);
 }
 for(unsigned y=0;y<224;y++)scene.raster[y]=(scene.raster[y]&~((uint64_t)255<<36))|((uint64_t)0x1e<<36);
 scene.raster[112]=(scene.raster[112]&~((uint64_t)255<<36))|((uint64_t)0x18<<36);
 calls=0;assert(!nes_native_video165_build(&scene,palette,&plan,stage,NULL)&&plan.error==3&&calls==0);
 scene.raster[112]=(scene.raster[112]&~((uint64_t)255<<36))|((uint64_t)0x1e<<36);
 assert(nes_native_video165_build(&scene,palette,&plan,stage,NULL)&&plan.display_mask==0x1e);
 '''+s[at:]
    (a.out/'host.c').write_text(s,encoding='utf8',newline='\n')
    env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
    def run(args,label,cwd):
        with (a.out/(label+'.log')).open('wb') as f:
            r=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
        text=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0,text[-3000:]
        return text
    run([a.gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-I','.','nes_native165.c','nes_native_video165.c','nes_trace166.c','host.c','-o','host.exe'],'compile',a.out)
    results=[]
    for frame in [24,25]:
        d=a.out/f'frame{frame}';d.mkdir();v=a.video/f'frame{frame}'
        log=run([a.out/'host.exe',v/'records.hex',v/'palette.bin'],f'frame{frame}',d)
        files=['bg.bin','obj.bin','map.bin','oam.bin','cgram.bin','hdma.bin','summary.txt']
        for n in files:assert (d/n).read_bytes()==(v/n).read_bytes(),(frame,n)
        results.append(dict(frame=frame,log=log.strip(),payload_equal=files))
    r=dict(passed=True,cases=results,uniform_masks_per_scene=256,mixed_mask_rejected_before_staging=True,plan_bytes=15888,
           prior_sources=old,candidate_sources={n:sha(a.out/n) for n in names},
           public_sources={n:sha(ROOT/n) for n in ['tools/nes_clip178.py','tools/test_nes_clip178_converter.py','tests/nes-functional/native_video165_host.c']},
           scope='Host compiled deployed batched C with sealed old game fixtures. No full ARM stack/link or new scene pixel proof.')
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS CLIP178 CONVERTER masks=512 size=15888')

if __name__=='__main__':main()
