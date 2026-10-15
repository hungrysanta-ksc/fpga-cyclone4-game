# SPDX-License-Identifier: MIT
"""Packed1813 -> real C converter -> DATA5 sender, differential lifetime test.

ACKs are mocked here. Actual65816 evidence is reused only for identical DATA5
sender/client bytes, not reported as a new full-system hardware run.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
from nes_clip178 import replace
from nes_paired181 import video,receiver,sink
from build_nes_game164 import palette


def host():
    s=(ROOT/'tests/nes-functional/consume181_host.c').read_text()
    s=replace(s,'0x1811','0x1813');s=replace(s,'0x1812','0x1815')
    s=replace(s,'p[0]==2&&p[1]==5','(p[0]==2||p[0]==4||p[0]==5)&&p[1]==5')
    s=replace(s,'else if(p[0]==2){','else if(p[0]==2||p[0]==4||p[0]==5){')
    s=replace(s,'unsigned k=p[1],at=get16(p+10),size=get16(p+12);',
                'unsigned k=p[1],at=get16(p+10),size=p[0]==2?get16(p+12):get16(p+14);')
    s=replace(s,'memcpy(staged[k]+at,p+16,size);lengths[k]+=size;',
                'for(unsigned j=0;j<size;j++){staged[k][at+j]=p[16+(p[0]==2?j:j%2)];}lengths[k]+=size;')
    s=replace(s,'for(unsigned y=0;y<224;y++)assert(packet(1,y,y%8));', '''for(unsigned y=0;y<224;y+=8){
  uint64_t v=0;for(unsigned j=0;j<8;j++)v=(v<<8)|((y+j)%8);
  assert(packet(7,0x1907,v));
 }''')
    s=replace(s,'for(unsigned i=0;i<32;i++)assert(packet(5,i,i==17?0x16:(unsigned[]){15,1,33,48}[i%4]));', '''for(unsigned i=0;i<32;i+=8){
  uint64_t v=0;for(unsigned j=0;j<8;j++)v=(v<<8)|((i+j)==17?0x16:(unsigned[]){15,1,33,48}[(i+j)%4]);
  assert(packet(7,0x1d07,v));
 }''')
    s=replace(s,'for(unsigned s=0;s<patches;s++)for(unsigned x=0;x<256;x++)assert(packet(6,s*256+x,color(rows[s],x)));', '''for(unsigned at=0;at<patches*256;){
  unsigned n=patches*256-at;if(n>10)n=10;uint64_t v=0;
  for(unsigned j=0;j<n;j++){unsigned i=at+j;v=(v<<6)|color(rows[i/256],i%256);}
  assert(packet(7,0x1000+at,((uint64_t)n<<60)|v));at+=n;
 }''')
    s=replace(s,'static uint8_t staged[6][16384],old_bg[16384],old_obj[4096];','static uint8_t staged[6][16384];')
    s=re.sub(r'^extern bool legacy_build[^\n]*\n','',s,flags=re.M)
    s=re.sub(r'^static bool old_stage[^\n]*\n','',s,flags=re.M)
    start=s.index(' if(!patches){');end=s.index(' }else{',start)
    s=s[:start]+' dump("plan.bin",&P,sizeof(P));\n if(patches){'+s[end+8:]
    s=replace(s,' scene.state=NES_NATIVE165_COMPLETE;', ''' /* Reuse must not suppress high-rank/last-row overlap detection. Each
  * trial starts with a fresh build, and the same output workspace is dirty. */
 uint64_t saved=scene.objects[0];unsigned count=scene.counts[2];
 scene.counts[2]=2;scene.objects[1]=scene.objects[0];
 assert(!build()&&P.error==10&&!P.valid);checks++;
 scene.objects[0]=scene.objects[1]=5|(UINT64_C(215)<<13)|(UINT64_C(80)<<22)|(UINT64_C(128)<<38)|(UINT64_C(7)<<46);
 assert(!build()&&P.error==10&&!P.valid);checks++;
 scene.objects[0]=saved;scene.counts[2]=count;assert(build());checks++;
 scene.state=NES_NATIVE165_COMPLETE;''')
    return s


def main():
    p=argparse.ArgumentParser()
    for n in ('out','gcc','arm'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    sources={};env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
    def run(args,cwd,name):
        with (cwd/name).open('wb') as f:r=subprocess.run(list(map(str,args)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode==0,(cwd/name).read_text(errors='replace')
    results=[]
    for variant in ('reference','reuse'):
        d=a.out/variant;d.mkdir()
        for n in ('nes_native165.h','nes_native_video165.h','nes_native_sink165.h','nes_trace166.h','nes_trace166.c','nes_sink_trace168.h','nes_sink_trace168.c'):
            shutil.copy2(a.arm/'src'/n,d/n);sources['arm/'+n]=sha(d/n)
        for name,public,transform in [('nes_native165.c','nes_native181.c',receiver),('nes_native_sink165.c','nes_native_sink181.c',sink),
                                      ('nes_native_video165.c','nes_native_video181.c',video if variant=='reuse' else str)]:
            (d/name).write_text(transform((ROOT/'src/nes/firmware'/public).read_text()),encoding='utf8',newline='\n')
            if variant=='reuse':assert (d/name).read_bytes()==(a.arm/'src'/name).read_bytes(),name
        (d/'host.c').write_text(host(),encoding='utf8',newline='\n')
        run([a.gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','nes_native165.c','nes_native_video165.c','nes_native_sink165.c','nes_trace166.c','nes_sink_trace168.c','host.c','-o','host.exe'],d,'gcc.log')
        for count,phase in ((0,0),(1,0),(7,0),(7,1),(7,2)):
            case=d/f'rows{count}-phase{phase}';case.mkdir();(case/'palette.bin').write_bytes(palette())
            run([d/'host.exe',count,phase,case/'palette.bin'],case,'host.log')
            if variant=='reuse':
                ref=a.out/'reference'/case.name;compared={}
                for f in ref.glob('*.bin'):
                    x=f.read_bytes();y=(case/f.name).read_bytes()
                    # Only the expired key bytes differ for non-raw plans;
                    # all fields used by seal/upload and every packet match.
                    offset=448 if count==0 and f.name=='plan.bin' else 0
                    assert x[offset:]==y[offset:],(case.name,f.name)
                    compared[f.name]=dict(bytes=len(y),ignored_expired_key_bytes=offset,sha256=sha(case/f.name))
                log=(case/'host.log').read_text();checks=int(re.search(r'checks=(\d+)',log)[1])
                results.append(dict(case=case.name,checks=checks,compared=compared));print(log.strip(),flush=True)
    result=dict(passed=True,cases=results,checks=sum(c['checks'] for c in results),
        public_sources={n:sha(ROOT/n) for n in ('tools/nes_paired181.py','tools/test_nes_paired181.py','tests/nes-functional/consume181_host.c')},
        inputs=sources,generated={f.relative_to(a.out).as_posix():sha(f) for f in a.out.rglob('*') if f.suffix in ('.c','.h')},
        scope=__doc__,new_snes_run=False,physical=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':main()
