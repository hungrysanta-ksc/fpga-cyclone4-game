# SPDX-License-Identifier: MIT
"""Audited one-pass model -> actual C234 -> unchanged231 output/reference.

Consumer ACK is modeled; actual65816 evidence is reused only when output
packets match the sealed231 run exactly. No production ingress or FPS proof.
"""
from pathlib import Path
import argparse,csv,json,os,random,struct,subprocess
from nes_delta231 import BASE,ROOT,sha,once
from nes_source234 import materialize
from nes_stream234 import Memory,records,encode,crc
from test_nes_delta231 import encode as oracle,REPLAY as OLD_REPLAY,SOURCE_FAULTS
from run_nes_scroll229 import ROM_SHA

REPLAY = r'''
static struct nes_source234 source_delta;
static struct nes_native165 source_input;
static unsigned delta_input_bytes;
static unsigned read234(FILE *f,uint8_t *b){
 int lo=fgetc(f);if(lo==EOF)return 0;int hi=fgetc(f);assert(hi!=EOF);
 unsigned n=(unsigned)lo+((unsigned)hi<<8);assert(n&&n<=243&&fread(b,1,n,f)==n);return n;
}
static void replay231(const char *dir,unsigned frame){
 char name[1024];snprintf(name,sizeof name,"%s/frame%u.stream",dir,frame);FILE *f=fopen(name,"rb");assert(f);
 uint8_t b[243];unsigned n;delta_input_bytes=0;
 nes_native165_consumed(&source_input);
 while((n=read234(f,b))!=0){assert(nes_source234_packet(&source_delta,&source_input,b,n));delta_input_bytes+=n;}
 fclose(f);assert(source_input.state==NES_NATIVE165_COMPLETE&&!source_delta.open&&source_delta.valid);
''' + OLD_REPLAY[OLD_REPLAY.index('#define SAME'):]

FAULTS = r'''
static uint8_t fault_packet234[256][243];static unsigned fault_size234[256],fault_count234;
static struct nes_source234 prior234;static struct nes_native165 prior_input234;
static void source_faults234(const char *dir){
 char name[1024];snprintf(name,sizeof name,"%s/frame905.stream",dir);FILE *f=fopen(name,"rb");assert(f);
 uint8_t b[243];unsigned n,cases=0;nes_source234_reset(&prior234);nes_native165_reset(&prior_input234);
 while((n=read234(f,b)))assert(nes_source234_packet(&prior234,&prior_input234,b,n));fclose(f);
 assert(prior_input234.state==NES_NATIVE165_COMPLETE);prior_input234.state=NES_NATIVE165_COMMITTED;nes_native165_consumed(&prior_input234);
 snprintf(name,sizeof name,"%s/frame906.stream",dir);f=fopen(name,"rb");assert(f);
 while((n=read234(f,b))){assert(fault_count234<256);memcpy(fault_packet234[fault_count234],b,n);fault_size234[fault_count234++]=n;}fclose(f);
 for(unsigned cut=0;cut<fault_count234;cut++){
  /* Each missing/duplicated complete record, every shortened record and
   * every one-bit byte corruption; always start from the same admitted base. */
  for(unsigned mode=0;mode<4;mode++)for(unsigned at=0;at<(mode>=2?fault_size234[cut]:1);at++){
   struct nes_source234 d=prior234;struct nes_native165 s=prior_input234;bool ok=true;
   for(unsigned i=0;i<fault_count234&&ok;i++){
    n=fault_size234[i];memcpy(b,fault_packet234[i],n);
    if(i==cut){if(mode==0)continue;if(mode==2)n=at;if(mode==3)b[at]^=1;}
    ok=nes_source234_packet(&d,&s,b,n);
    if(i==cut&&mode==1&&ok)ok=nes_source234_packet(&d,&s,b,n);
   }
   /* Missing final marker is detected by transport deadline/common STOP,
    * not by pretending the record parser can infer missing future bytes. */
   assert(!ok||d.open);if(ok)nes_source234_abort(&d,&s);
   assert(d.fault&&!d.valid&&!d.open&&s.state==NES_NATIVE165_FAILED);
   assert(!nes_source234_packet(&d,&s,fault_packet234[0],fault_size234[0]));cases++;
  }
  struct nes_source234 d=prior234;struct nes_native165 s=prior_input234;
  for(unsigned i=0;i<cut;i++)assert(nes_source234_packet(&d,&s,fault_packet234[i],fault_size234[i]));
  nes_source234_abort(&d,&s);assert(d.fault&&!d.valid&&!d.open);cases++;
 }
 /* Counts must be checked independently of the transcript CRC. */
 for(unsigned which=0;which<2;which++){
  struct nes_source234 d=prior234;struct nes_native165 s=prior_input234;bool found=false;
  for(unsigned i=0;i<fault_count234;i++){
   n=fault_size234[i];memcpy(b,fault_packet234[i],n);
   if(n==10&&b[0]==255&&b[1]==255&&b[3]==3){
    b[4+2*which]^=1;uint16_t c=d.crc;
    for(unsigned j=0;j<8;j++){c^=(uint16_t)b[j]<<8;for(unsigned k=0;k<8;k++)c=(uint16_t)((c<<1)^((c&0x8000)?0x1021:0));}
    b[8]=(uint8_t)c;b[9]=(uint8_t)(c>>8);assert(!nes_source234_packet(&d,&s,b,n));found=true;break;
   }
   assert(nes_source234_packet(&d,&s,b,n));
  }
  assert(found&&d.fault&&!d.valid);cases++;
 }
 /* Common-reset cold replay, then a zero-change generation-wrap stream. */
 for(unsigned round=0;round<2;round++){
  struct nes_source234 d={0};struct nes_native165 s;nes_native165_reset(&s);
  for(unsigned frame=0;frame<2;frame++){
   snprintf(name,sizeof name,"%s/%s",dir,frame?"wrap.stream":"coldwrap.stream");f=fopen(name,"rb");assert(f);
   while((n=read234(f,b)))assert(nes_source234_packet(&d,&s,b,n));fclose(f);
   assert(d.valid&&!d.open&&s.state==NES_NATIVE165_COMPLETE&&s.generation==(frame?0:65535));
   s.state=NES_NATIVE165_COMMITTED;nes_native165_consumed(&s);
  }
  assert(s.generation==0&&d.serial==2);cases++;
 }
 printf("SOURCE234 faults_and_restart=%u source_bytes=%u PASS\n",cases,(unsigned)sizeof source_delta);
}
'''


def model_tests():
    rng=random.Random(234);checks=0
    # Full noise, sparse changes, repeated masks and both row-shift directions.
    for case in range(400):
        old=bytes(rng.randrange(256) for _ in range(5741));new=bytearray(old)
        if case%4==0:
            for _ in range(300):new[rng.randrange(5741)]=rng.randrange(256)
        elif case%4==1:
            mask=rng.getrandbits(64)
            for y in range(224):
                at=3872+y*8;m=mask if y%17 else 1
                new[at:at+8]=(int.from_bytes(old[at:at+8],'little')^m).to_bytes(8,'little')
        elif case%4==2:
            for at in range(0,2112,66):
                new[at:at+66]=(old[at+2:at+66]+b'\x01\x00') if case%8==2 else (b'\x01\x00'+old[at:at+64])
        else:new[:]=bytes(rng.randrange(256) for _ in range(5741))
        for cold in (False,True):
            m=Memory(old,bytes(new));out=[];records(m,cold,lambda *r:out.append(r))
            assert out==oracle(old,bytes(new),cold),(case,cold)
            assert m.reads==m.queries==5741 and m.cursor==5741 and m.base==new
            checks+=1
    return checks


def save_stream(p,packets):
    p.write_bytes(b''.join(struct.pack('<H',len(b))+b for b in packets))


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);a=p.parse_args()
    assert sha(a.rom)==ROM_SHA;d=a.out.resolve();pins=materialize(d)
    oldrun=BASE/'probes/nes-delta231/test07';baseline=BASE/'probes/nes-geometry230/host06';rtl=BASE/'probes/nes-geometry230/rtl02'
    sealed=json.loads((oldrun/'result.json').read_text());assert sha(oldrun/'host.c')==sealed['host_sha256']
    old=bytes(5741);stats=[]
    for row in csv.DictReader((oldrun/'cost.csv').open()):
        f=int(row['frame']);new=(oldrun/f'frame{f}.geometry').read_bytes();raw=(oldrun/f'frame{f}.raw').read_bytes()
        for ext in ('geometry','raw'):
            name=f'frame{f}.{ext}';assert sha(oldrun/name)==sealed['evidence_files'][name]
        packets,mem=encode(old,new,raw,f-904,int(row['generation']))
        save_stream(d/f'frame{f}.stream',packets)
        # Compare only geometry records before its terminal, independent oracle.
        cut=next(i for i,b in enumerate(packets) if len(b)==10 and b[:4]==b'\xff\xff\0\3')
        assert packets[1:cut]==[b for _,_,b in oracle(old,new,f==905)]
        stats.append(dict(frame=f,wire_bytes=sum(map(len,packets)),lengths=list(map(len,packets)),**mem));old=new
    first=(oldrun/'frame905.geometry').read_bytes();raw=(oldrun/'frame905.raw').read_bytes()
    coldwrap,_=encode(bytes(5741),first,raw,1,65535);save_stream(d/'coldwrap.stream',coldwrap)
    wrap,_=encode(first,first,raw,2,0);save_stream(d/'wrap.stream',wrap)
    s=(oldrun/'host.c').read_text();s=once(s,'#include "nes_delta231.h"','#include "nes_delta231.h"\n#include "nes_source234.h"')
    s=once(s,OLD_REPLAY,REPLAY);s=once(s,SOURCE_FAULTS,FAULTS)
    s=once(s,'source_faults231();','source_faults234(argv[5]);')
    s=s.replace('STATE231 source=','STATE234 source=').replace('PASS DELTA231 C','PASS SOURCE234 C')
    (d/'host.c').write_text(s,encoding='utf-8',newline='\n');(d/'palette.bin').write_bytes((baseline/'palette.bin').read_bytes())
    gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    files=['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c','nes_delta231.c']
    for label,args in [('build',[gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe']),('run',[d/'host.exe',rtl,a.rom.resolve(),905,975,d])]:
        with (d/(label+'.log')).open('wb') as log:q=subprocess.run(list(map(str,args)),cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        text=(d/(label+'.log')).read_text(errors='replace');assert q.returncode==0,text[-6000:]
    matches=0
    for f in range(905,976):
        for ext in ('geometry','raw','metadata','packets','plans'):
            n=f'frame{f}.{ext}';assert sha(oldrun/n)==sealed['evidence_files'][n]
            assert (d/n).read_bytes()==(oldrun/n).read_bytes(),n;matches+=1
    result=dict(passed=True,scope=__doc__,model_cases=model_tests(),frames=71,exact_output_files=matches,output=text,
                source_state_host_bytes=32,scratch_capacity_model_bytes=635,full_runtime=False,rtl=False,physical=False,
                pins=pins,host_sha256=sha(d/'host.c'),script_sha256=sha(Path(__file__)),stats=stats,
                sources={n:sha(ROOT/'tools'/n) for n in ('nes_source234.py','nes_stream234.py','test_nes_source234.py')})
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(text);print('model800 and output355 exact PASS')


if __name__=='__main__':main()
