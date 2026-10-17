# SPDX-License-Identifier: MIT
"""225/226 identical plans, banks and full planner output, including column-zero exceptions."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_fast226 import ROOT,BASE,sha,once,planner
from test_nes_scroll225 import host_source


def host():
    s=host_source()
    s=once(s,'static bool write_slot(void *ctx,unsigned bank,const struct nes_plan191 *q){','''static FILE *trace226;
extern unsigned long long fine_calls226,fine_scans226;
static void snapshot226(void){
 struct nes_resident211 copy=cache;copy.write=NULL;copy.ctx=NULL;
 assert(fwrite(&candidate,1,sizeof candidate,trace226)==sizeof candidate);
 assert(fwrite(&copy,1,sizeof copy,trace226)==sizeof copy);
 assert(fwrite(banks,1,sizeof banks,trace226)==sizeof banks);
}
static bool write_slot(void *ctx,unsigned bank,const struct nes_plan191 *q){
 assert(fwrite(q,1,sizeof *q,trace226)==sizeof *q);''')
    s=once(s,' assert(cache.prepared);verify_bank();cost225();',' assert(cache.prepared);verify_bank();cost225();snapshot226();')
    s=once(s,'static bool empty_writer(','''static void exceptions226(void){
 for(unsigned column=0;column<33;column++)for(unsigned row=0;row<8;row++)for(unsigned mode=0;mode<2;mode++){
  reset();source(0,1000+column*16+row*2+mode);
  unsigned y=16+row;
  r.counts[3]=1;r.exceptions[0]=(9u<<19)|((y*33+column)<<6)|(((row+mode)&7)<<3)|((row+2)&7);
  run_frame(7);r.generation++;run_frame(7);r.generation++;run_frame(7);
 }
 /* Maximum exception list, ordinary destination rows, mixed physical tags. */
 reset();source(0,5000);r.counts[3]=128;
 for(unsigned i=0;i<128;i++){unsigned y=16+i/33,x=i%33;
  r.exceptions[i]=(9u<<19)|((y*33+x)<<6)|((y&7)<<3)|((y+1)&7);
 }
 run_frame(9);r.generation++;run_frame(9);
}
static bool empty_writer(''')
    s=once(s,'int main(void){','int main(void){\n trace226=fopen("trace.bin","wb");assert(trace226);')
    s=once(s,' adversarial225();faults();',' adversarial225();exceptions226();faults();')
    s=once(s,' return 0;\n}', ''' assert(!fclose(trace226));
 printf("WORK226 fine_calls=%lu fine_exception_scans=%lu\\n",(unsigned long)fine_calls226,(unsigned long)fine_scans226);
 return 0;
}''')
    return s


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
    src=BASE/'probes/nes-scroll225/arm01/src';fixture=BASE/'probes/nes-scroll225/test02/candidate'
    gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
    env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    results={};pins={}
    for kind in ['baseline','candidate','negative_col0','negative_all']:
        out=d/kind;out.mkdir()
        for f in fixture.iterdir():
            if f.suffix not in ['.c','.h','.inc'] or f.name=='host.c':continue
            source=src/f.name if (src/f.name).exists() else f
            shutil.copyfile(source,out/f.name);pins[str(source.relative_to(BASE))]=sha(source)
        raw=(src/'nes_planner211.c').read_text()
        if kind!='baseline':raw=planner(raw)
        if kind=='negative_col0':raw=once(raw,'if(exceptional&1)exceptional=UINT64_C(0x1ffffffff);','/* negative: omit destination-column broadcast */')
        if kind=='negative_all':raw=once(raw,'if((exceptional>>x)&1){','if(0){')
        (out/'nes_planner211.c').write_text(raw,encoding='utf8',newline='\n')
        prof=once(raw,'static unsigned fine(', 'unsigned long long fine_calls226,fine_scans226;\nstatic unsigned fine(')
        prof=once(prof,'bool low){\n for(', 'bool low){\n fine_calls226++;\n for(')
        prof=once(prof,'  uint32_t v=s->exceptions[i];if(', '  fine_scans226++;uint32_t v=s->exceptions[i];if(')
        (out/'planner_profile.c').write_text(prof,encoding='utf8',newline='\n')
        (out/'host.c').write_text(host(),encoding='utf8',newline='\n')
        files=['host.c','reference203.c','planner_profile.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c']
        for name,args in [('build',[gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe']),('run',[out/'host.exe'])]:
            with (out/(name+'.log')).open('wb') as log:
                q=subprocess.run(list(map(str,args)),cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW)
            text=(out/(name+'.log')).read_text(errors='replace')
            if kind.startswith('negative') and name=='run':
                assert q.returncode!=0,'Negative missed';results[kind]=dict(rejected=True,output=text);break
            assert q.returncode==0,text[-5000:]
        if kind in ['baseline','candidate']:results[kind]=dict(output=text,trace_sha256=sha(out/'trace.bin'),planner_sha256=sha(out/'nes_planner211.c'))
        print(kind+' '+text[-800:],flush=True)
    assert (d/'baseline/trace.bin').read_bytes()==(d/'candidate/trace.bin').read_bytes()
    r=dict(passed=True,results=results,trace_bytes=(d/'candidate/trace.bin').stat().st_size,inputs=pins,
        scope=__doc__,physical=False,timing_measured=False,
        public_sources={n:sha(ROOT/n) for n in ['tools/nes_fast226.py','tools/test_nes_fast226.py']})
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
