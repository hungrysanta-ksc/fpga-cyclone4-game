# SPDX-License-Identifier: MIT
"""Actual231 in-place C receiver + dirty planner/sink on pinned230 frames.

Host encoder, source transfer verification and display ACK are fixtures.
No FPGA delta producer, production SPI binding or actual65816 execution.
"""
from pathlib import Path
import argparse,json,os,struct,subprocess
from nes_delta231 import materialize,sha,ROOT,BASE,once
from analyze_nes_geometry230 import spans
from run_nes_scroll229 import ROM_SHA

REPLAY=r'''
static struct nes_source231 source_delta;
static struct nes_native165 source_input;
static unsigned delta_input_bytes;
static void replay231(const char *dir,unsigned frame){
 char name[1024];snprintf(name,sizeof name,"%s/frame%u.delta",dir,frame);FILE *f=fopen(name,"rb");assert(f);
 uint8_t header[4];assert(fread(header,1,4,f)==4);unsigned n=word(header),bytes=word(header+2);
 bool full=source_delta.serial==0;unsigned serial=source_delta.serial+1;
 nes_native165_consumed(&source_input);
 assert(nes_source231_begin(&source_delta,&source_input,1,full?0:source_delta.serial,serial,input.generation,full,n,bytes));
 delta_input_bytes=28;
 for(unsigned i=0;i<n;i++){
  uint8_t h[3],b[240];assert(fread(h,1,3,f)==3);unsigned count=h[2];assert(count<=240);
  if(count){assert(fread(b,1,count,f)==count);assert(nes_source231_write(&source_delta,&source_input,i,word(h),b,count));delta_input_bytes+=count+3;}
  else{int kind=fgetc(f);if(kind==1){assert(fread(b,1,9,f)==9);uint64_t mask=0;for(unsigned j=0;j<8;j++)mask|=(uint64_t)b[j+1]<<(8*j);
    assert(nes_source231_raster(&source_delta,&source_input,i,word(h),b[0],mask));delta_input_bytes+=13;
   }else{assert(kind==2&&fread(b,1,3,f)==3);assert(nes_source231_shift(&source_delta,&source_input,i,word(h),b[0]==1?1:-1,(uint16_t)word(b+1)));delta_input_bytes+=7;}}
 }
 assert(fgetc(f)==EOF);fclose(f);assert(nes_source231_geometry(&source_delta,&source_input));
 for(unsigned at=0;at<input.patch_count*256u;){unsigned n=input.patch_count*256u-at;if(n>240)n=240;
  assert(nes_source231_raw(&source_delta,&source_input,at,input.raw_pixels+at,n));at+=n;delta_input_bytes+=n+3;
 }
 assert(nes_source231_end(&source_delta,&source_input));
#define SAME(x) assert(!memcmp(source_input.x,input.x,sizeof input.x))
 SAME(maps);SAME(rows);SAME(objects);SAME(exceptions);SAME(raster);SAME(palette);SAME(counts);
#undef SAME
 assert(source_input.ntiles==input.ntiles&&source_input.patch_count==input.patch_count);
 for(unsigned i=0;i<input.ntiles;i++)assert(source_input.tiles[i].tag==input.tiles[i].tag&&source_input.tiles[i].kind==input.tiles[i].kind);
 assert(!memcmp(source_input.raw_pixels,input.raw_pixels,input.patch_count*256u));
 source_input.state=NES_NATIVE165_PREPARED;
 uint8_t commit[12]={0xe0,3,(uint8_t)(input.generation>>8),(uint8_t)input.generation};
 assert(nes_native165_packet(&source_input,0,commit,12));assert(source_input.state==NES_NATIVE165_COMMITTED);
 input=source_input;
}
'''

SOURCE_FAULTS=r'''
static void source_faults231(void){
 unsigned cases=0;
 for(unsigned which=0;which<18;which++){
  struct nes_source231 d=source_delta;struct nes_native165 s=source_input;nes_native165_consumed(&s);
  unsigned serial=d.serial+1,gen=(unsigned)(s.generation+1)&65535;uint8_t one=0;
  bool ok;
  if(which<4){ok=nes_source231_begin(&d,&s,which==1?2:1,which==0?d.serial-1:d.serial,which==2?serial+1:which==3?UINT32_MAX:serial,(uint16_t)gen,false,0,0);}
  else if(which==13){nes_source231_reset(&d);nes_native165_reset(&s);assert(nes_source231_begin(&d,&s,1,0,1,(uint16_t)gen,true,1,1));assert(nes_source231_write(&d,&s,0,0,&one,1));ok=nes_source231_geometry(&d,&s);}
  else{
   unsigned spans=which==8?2:(which==6||which==7||which==9||which>=14)?1:0;
   unsigned bytes=which==8?2:(which==16?8:which==15?66:spans);
   assert(nes_source231_begin(&d,&s,1,d.serial,serial,(uint16_t)gen,false,spans,bytes));
   switch(which){
    case 4:ok=nes_source231_begin(&d,&s,1,d.serial,serial,(uint16_t)gen,false,0,0);break;
    case 5:ok=nes_source231_raw(&d,&s,0,&one,1);break;
    case 6:ok=nes_source231_write(&d,&s,1,0,&one,1);break;
    case 7:ok=nes_source231_write(&d,&s,0,5741,&one,1);break;
    case 8:assert(nes_source231_write(&d,&s,0,0,&one,1));ok=nes_source231_write(&d,&s,1,0,&one,1);break;
    case 9:ok=nes_source231_geometry(&d,&s);break;
    case 10:assert(nes_source231_geometry(&d,&s));ok=nes_source231_end(&d,&s);break;
    case 11:assert(nes_source231_geometry(&d,&s));one=64;ok=nes_source231_raw(&d,&s,0,&one,1);break;
    case 12:assert(nes_source231_geometry(&d,&s));ok=nes_source231_raw(&d,&s,1,&one,1);break;
    case 14:one=64;assert(nes_source231_write(&d,&s,0,5664,&one,1));ok=nes_source231_geometry(&d,&s);break;
    case 15:ok=nes_source231_shift(&d,&s,0,2,1,0);break;
    case 16:ok=nes_source231_raster(&d,&s,0,3873,1,1);break;
    default:ok=nes_source231_write(&d,&s,0,UINT32_MAX,&one,1);break;
   }
  }
  assert(!ok&&d.fault&&!d.valid&&!d.open&&s.state==NES_NATIVE165_FAILED);
  assert(!nes_source231_begin(&d,&s,1,0,1,1,true,1,1));cases++;
 }
 /* Identical geometry is a valid zero-span update. Raw must still be sent
  * after required-tag enumeration has invalidated the shared union. */
 struct nes_source231 d=source_delta;struct nes_native165 s=source_input;d.generation=s.generation=UINT16_MAX;nes_native165_consumed(&s);
 assert(nes_source231_begin(&d,&s,1,d.serial,d.serial+1,0,false,0,0));assert(nes_source231_geometry(&d,&s));
 for(unsigned at=0;at<source_input.patch_count*256u;){unsigned n=source_input.patch_count*256u-at;if(n>240)n=240;assert(nes_source231_raw(&d,&s,at,source_input.raw_pixels+at,n));at+=n;}
 assert(nes_source231_end(&d,&s)&&s.state==NES_NATIVE165_COMPLETE&&s.generation==0);
 printf("SOURCE231 faults=%u zero_delta_and_generation_wrap=PASS\n",cases);
}
'''


def encode(old,new,cold):
    if cold:return [(i,len(new[i:i+240]),struct.pack('<HB',i,len(new[i:i+240]))+new[i:i+240]) for i in range(0,len(new),240)]
    ops=[]
    def literal(a,b):
        for off,data in spans(old[a:b],new[a:b]):ops.append((a+off,len(data),struct.pack('<HB',a+off,len(data))+data))
    for at in range(0,2112,66):
        a,b=old[at:at+66],new[at:at+66]
        if a==b:continue
        if a[2:]==b[:-2]:ops.append((at,66,struct.pack('<HBBB',at,0,2,1)+b[-2:]))
        elif a[:-2]==b[2:]:ops.append((at,66,struct.pack('<HBBB',at,0,2,255)+b[:2]))
        else:literal(at,at+66)
    literal(2112,3872)
    y=0
    while y<224:
        at=3872+y*8;mask=int.from_bytes(old[at:at+8],'little')^int.from_bytes(new[at:at+8],'little')
        if not mask:y+=1;continue
        end=y+1
        while end<224:
            off=3872+end*8
            if (int.from_bytes(old[off:off+8],'little')^int.from_bytes(new[off:off+8],'little'))!=mask:break
            end+=1
        lit=spans(old[at:3872+end*8],new[at:3872+end*8])
        if sum(3+len(b) for _,b in lit)<13:literal(at,3872+end*8)
        else:ops.append((at,(end-y)*8,struct.pack('<HBBBQ',at,0,1,end-y,mask)))
        y=end
    literal(5664,5741)
    assert ops==sorted(ops)
    return ops


def main():
    p=argparse.ArgumentParser()
    for n in ('out','rom'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert sha(a.rom)==ROM_SHA;d=a.out.resolve();pins=materialize(d)
    baseline=BASE/'probes/nes-geometry230/host06';rtl=BASE/'probes/nes-geometry230/rtl02'
    old=bytes(5741)
    for f in range(905,976):
        new=(baseline/f'frame{f}.geometry').read_bytes()
        ops=encode(old,new,f==905)
        data=struct.pack('<HH',len(ops),sum(n for _,n,_ in ops))+b''.join(b for _,_,b in ops)
        (d/f'frame{f}.delta').write_bytes(data);old=new
    s=(baseline/'host.c').read_text()
    s=once(s,'#include "nes_resident211.h"','#include "nes_delta231.h"\nstatic struct nes_dirty231 dirty;')
    s=once(s,'static unsigned newbytes,','static FILE *plan_trace;\nstatic unsigned newbytes,')
    s=once(s,'newbytes+=unit;return true;','assert(plan_trace);fprintf(plan_trace,"%u,%u,%u\\n",kind,q->slot,unit);newbytes+=unit;return true;')
    s=once(s,'nes_native_video211_plan(&input,lut,&candidate,&cache)','nes_native_video231_plan(&input,lut,&candidate,&cache,&dirty)')
    s=once(s,'struct nes_resident211 c=cache;struct nes_native_sink165 sink;', 'struct nes_resident211 c=cache;struct nes_dirty231 dc=dirty;struct nes_native_sink165 sink;')
    s=once(s,'nes_sink212_seal(&sink,&candidate,&c)','nes_sink231_seal(&sink,&candidate,&c,&dc)')
    s=once(s,'assert(nes_resident211_commit(&cache,cache.serial,r.generation,cache.target,true));',
        'assert(nes_resident211_commit(&cache,cache.serial,r.generation,cache.target,true));assert(nes_dirty231_commit(&dirty,cache.serial,r.generation,cache.target,true));')
    s=once(s,'nes_resident211_reset(&cache);','nes_resident211_reset(&cache);nes_dirty231_reset(&dirty);')
    at=s.index('int main(');s=s[:at]+REPLAY+SOURCE_FAULTS+s[at:]
    s=once(s,'assert(argc==5);','assert(argc==6);')
    s=once(s,'receive230(argv[1],frame);','receive230(argv[1],frame);replay231(argv[5],frame);')
    s=once(s,'run_frame(1);\n  fclose(packet_trace);', 'snprintf(name,sizeof name,"frame%u.plans",frame);plan_trace=fopen(name,"w");assert(plan_trace);\n  run_frame(1);fclose(plan_trace);plan_trace=NULL;\n  fclose(packet_trace);')
    s=once(s,'map_vram_bytes,pixel_checks\\n','map_vram_bytes,pixel_checks,source_delta_payload\\n')
    s=once(s,'"%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\\n"','"%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\\n"')
    s=once(s,'mapbytes-oldmap,checked-oldchecked);','mapbytes-oldmap,checked-oldchecked,delta_input_bytes);')
    s=s.replace('PASS GEOMETRY230 C','PASS DELTA231 C')
    s=once(s,'fclose(csv);printf(', 'fclose(csv);source_faults231();printf("STATE231 source=%u dirty=%u video=%u input=%u\\n",(unsigned)sizeof source_delta,(unsigned)sizeof dirty,(unsigned)sizeof candidate,(unsigned)sizeof input);printf(')
    (d/'host.c').write_text(s,encoding='utf-8',newline='\n');(d/'palette.bin').write_bytes((baseline/'palette.bin').read_bytes())
    gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
    env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
    files=['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c','nes_delta231.c']
    for label,args in [('build',[gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe']),('run',[d/'host.exe',rtl,a.rom.resolve(),905,975,d])]:
        with (d/(label+'.log')).open('wb') as log:
            q=subprocess.run(list(map(str,args)),cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        text=(d/(label+'.log')).read_text(errors='replace');assert q.returncode==0,text[-6000:]
    result=dict(passed=True,scope=__doc__,pins=pins,script_sha256=sha(Path(__file__)),host_sha256=sha(d/'host.c'),cost_sha256=sha(d/'cost.csv'),
                output=text,first=905,last=975,physical=False,actual_snes_execution=False,
                evidence_files={f.name:sha(f) for f in sorted(d.glob('frame*')) if f.is_file()})
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(text)


if __name__=='__main__':main()
