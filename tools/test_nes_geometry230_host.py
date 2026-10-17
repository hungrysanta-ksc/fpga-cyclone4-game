# SPDX-License-Identifier: MIT
"""Actual227 C receiver/planner/sink on actual RTL records from observed-game replay.

The186 reference converter independently checks normal BG pixels, OBJ planar
bytes, palette and raw rows. ACK and tile fetch callbacks remain host models.
No physical timing or actual65816 execution is claimed by this test.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, subprocess
from build_nes_game164 import palette
from run_nes_scroll229 import ROM_SHA

ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent

HOST=r'''
static void dump230(unsigned frame){
 char name[80];snprintf(name,sizeof name,"frame%u.metadata",frame);
 FILE *f=fopen(name,"wb");assert(f);
 assert(fwrite(candidate.map,1,4096,f)==4096);
 assert(fwrite(candidate.cgram,1,512,f)==512);
 assert(fwrite(candidate.oam,1,544,f)==544);
 uint8_t bundle[3418]={0};memcpy(bundle,candidate.hdma,candidate.hdma_size);
 assert(candidate.patch_count);
 memcpy(bundle+1121,candidate.patch.chr,2048);
 memcpy(bundle+3169,candidate.patch.mode[0],81);
 memcpy(bundle+3250,candidate.patch.mode[1],81);
 memcpy(bundle+3331,candidate.patch.enable,81);
 for(unsigned i=0;i<3;i++){bundle[3412+i*2]=(uint8_t)candidate.patch.size[i];bundle[3413+i*2]=(uint8_t)(candidate.patch.size[i]>>8);}
 assert(fwrite(bundle,1,sizeof bundle,f)==sizeof bundle);fclose(f);
}
static void receive230(const char *dir,unsigned frame){
 char name[1024];snprintf(name,sizeof name,"%s/frame%u.wire",dir,frame);
 FILE *f=fopen(name,"r");assert(f);nes_native165_reset(&input);
 unsigned hi,mid,lo,token=0;input_bytes=0;input_blocks=0;unsigned block=0;
 static const unsigned widths[]={2,1,7,4,7,1,2,8};
 while(fscanf(f,"%8x%8x%8x",&hi,&mid,&lo)==3){
  unsigned k=hi>>29,gen=(hi>>13)&65535,index=hi&8191;
  unsigned n=k==0&&(index&4096)?8:widths[k];uint64_t value=((uint64_t)mid<<32)|lo;
  uint8_t p[12];unsigned tag=(k<<13)|index;p[0]=tag>>8;p[1]=tag;p[2]=gen>>8;p[3]=gen;
  for(unsigned j=0;j<n;j++)p[4+j]=(uint8_t)(value>>(8*(n-1-j)));
  if(k==7&&index==3){assert(input.state==NES_NATIVE165_COMPLETE);input.state=NES_NATIVE165_PREPARED;}
  assert(nes_native165_packet(&input,(uint16_t)token,p,n+4));token++;input_bytes+=n+4;
  if(block+n+4>248){input_blocks++;block=0;}block+=n+4;
 }
 fclose(f);if(block)input_blocks++;
 assert(input.state==NES_NATIVE165_COMMITTED);
 memset(&r,0,sizeof r);
 memcpy(r.maps,input.maps,sizeof r.maps);memcpy(r.rows,input.rows,sizeof r.rows);
 memcpy(r.objects,input.objects,sizeof r.objects);memcpy(r.exceptions,input.exceptions,sizeof r.exceptions);
 memcpy(r.raster,input.raster,sizeof r.raster);memcpy(r.palette,input.palette,sizeof r.palette);
 memcpy(r.raw_pixels,input.raw_pixels,sizeof r.raw_pixels);memcpy(r.counts,input.counts,sizeof r.counts);
 r.generation=input.generation;r.ntiles=input.ntiles;r.patch_count=input.patch_count;r.state=input.state;
 for(unsigned i=0;i<r.ntiles;i++){r.tiles[i].tag=input.tiles[i].tag;r.tiles[i].kind=input.tiles[i].kind;
  assert(r.tiles[i].tag<8192);memcpy(r.tiles[i].data,rom_chr+r.tiles[i].tag*16,16);}
 snprintf(name,sizeof name,"frame%u.geometry",frame);f=fopen(name,"wb");assert(f);
 /* Canonical, little-endian fixture fields; no struct padding or pointers.
  * Raw rows are separate because the receiver's required-bitmap aliases them.
  * Production source delta must resend raw rows after bitmap enumeration. */
#define FIELD(x) assert(fwrite(r.x,1,sizeof r.x,f)==sizeof r.x)
 FIELD(maps);FIELD(rows);FIELD(objects);FIELD(exceptions);FIELD(raster);FIELD(palette);FIELD(counts);
#undef FIELD
 assert(fwrite(&r.patch_count,1,1,f)==1);fclose(f);
 snprintf(name,sizeof name,"frame%u.raw",frame);f=fopen(name,"wb");assert(f);
 assert(fwrite(r.raw_pixels,1,r.patch_count*256u,f)==r.patch_count*256u);fclose(f);
}
int main(int argc,char **argv){
 assert(argc==5);FILE *f=fopen(argv[2],"rb");assert(f);
 assert(fseek(f,16+262144,SEEK_SET)==0);assert(fread(rom_chr,1,sizeof rom_chr,f)==sizeof rom_chr);fclose(f);
 f=fopen("palette.bin","rb");assert(f);assert(fread(lut,1,sizeof lut,f)==sizeof lut);fclose(f);
 FILE *csv=fopen("cost.csv","w");assert(csv);
 fprintf(csv,"frame,generation,groups,objects,patches,ingress_payload,ingress_blocks,metadata_spi,tile_bytes,plans,map_vram_bytes,pixel_checks\n");
 reset();
 for(unsigned frame=(unsigned)atoi(argv[3]);frame<=(unsigned)atoi(argv[4]);frame++){
  receive230(argv[1],frame);
  unsigned oldwire=wire225,oldnew=newbytes,oldcalls=calls,oldmap=mapbytes,oldchecked=checked;
  char name[80];snprintf(name,sizeof name,"frame%u.packets",frame);packet_trace=fopen(name,"wb");assert(packet_trace);
  run_frame(1);
  fclose(packet_trace);packet_trace=NULL;dump230(frame);
  fprintf(csv,"%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\n",frame,r.generation,r.counts[0]/33,r.counts[2],r.patch_count,input_bytes,input_blocks,wire225-oldwire,newbytes-oldnew,calls-oldcalls,mapbytes-oldmap,checked-oldchecked);
 }
 fclose(csv);printf("PASS GEOMETRY230 C frames=%u reference_checks=%u metadata_spi=%u tile_bytes=%u\n",frames,checked,wire225,newbytes);
 return 0;
}
'''


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    for n in ('rtl','rom','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--first',type=int,default=905);p.add_argument('--last',type=int,default=975)
    a=p.parse_args();assert sha(a.rom)==ROM_SHA;d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
    rtl=json.loads((a.rtl/'result.json').read_text());assert rtl['passed']
    assert rtl['first']<=a.first<=a.last<=rtl['last']
    fixture=BASE/'probes/nes-scroll225/test02/candidate';production=BASE/'probes/nes-repeat227/arm01/src'
    pins={}
    for f in fixture.iterdir():
        if f.suffix not in ['.c','.h','.inc'] or f.name=='host.c':continue
        src=production/f.name if (production/f.name).exists() else f
        pins[str(src.relative_to(BASE))]=sha(src);shutil.copyfile(src,d/src.name)
    old=fixture/'host.c';pins[str(old.relative_to(BASE))]=sha(old);s=old.read_text()
    s=s[:s.index('static void compatibility(')]
    start=s.index('#include "scene203.inc"');end=s.index('static void convert_input(',start);s=s[:start]+s[end:]
    s=s.replace('#include <string.h>','#include <string.h>\n#include <stdlib.h>\nstatic unsigned input_bytes,input_blocks;\nstatic uint8_t rom_chr[131072];')
    s=s.replace('static unsigned packets225,', 'static FILE *packet_trace;\nstatic unsigned packets225,')
    s=s.replace('(void)ctx;packets225++;wire225+=n+3;', '(void)ctx;packets225++;wire225+=n+3;\n uint8_t length[2]={(uint8_t)n,(uint8_t)(n>>8)};assert(packet_trace);\n assert(fwrite(length,1,2,packet_trace)==2);assert(fwrite(p,1,n,packet_trace)==n);')
    (d/'host.c').write_text(s+HOST,encoding='utf-8',newline='\n');(d/'palette.bin').write_bytes(palette())
    gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
    env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    files=['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c']
    for label,args in [('build',[gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe']),('run',[d/'host.exe',a.rtl.resolve(),a.rom.resolve(),a.first,a.last])]:
        with (d/(label+'.log')).open('wb') as log:
            q=subprocess.run(list(map(str,args)),cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        text=(d/(label+'.log')).read_text(errors='replace');assert q.returncode==0,text[-5000:]
    result=dict(passed=True,scope=__doc__,first=a.first,last=a.last,pins=pins,script_sha256=sha(Path(__file__)),
                rtl_result_sha256=sha(a.rtl/'result.json'),cost_sha256=sha(d/'cost.csv'),host_sha256=sha(d/'host.c'),output=text,
                evidence_files={f.name:sha(f) for f in sorted(d.glob('frame*')) if f.is_file()},
                physical=False,actual_snes_execution=False,source_read_timing=False)
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(text)


if __name__=='__main__':main()
