# SPDX-License-Identifier: MIT
"""Real exporter trace -> real receiver/RUN/planner/sink with reference pixels.

RTL query memory/ACK and C hardware SPI/source/ACK are fixtures; the recorded
exporter output bridges them. Not simultaneous board/C/SNES co-simulation.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_metadata203 import prepare,ROOT,BASE,sha,replace

BENCH=r'''
module metadata203_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,enable=0,owned=0,valid=1;reg [15:0] gen;
 reg [2:0] patches;reg [7:0] objects,exceptions;reg [5:0] groups,palettes;
 wire release_frame,query;wire [2:0] kind;wire [12:0] index;wire [15:0] qgen;
 reg response=0,hit=0;reg [63:0] data;reg [63:0] mem[0:16383];
 wire tv;reg ready=0;wire [95:0] td;reg ack=0;wire ar,busy;wire [3:0] error,state;
 integer clocks=0,scene,fd,cfg,rc,commits,stalls=0,total=0,fault=0,aborts=0;reg [95:0] held;reg pending=0;
 string name;
 nes_native_export203 #(.MAX_CYCLES(100000)) dut(
 .clk(clk),.reset(reset),.enable(enable),.frame_owned(owned),.geometry_valid(valid),.frame_generation(gen),
 .patch_count(patches),.row_count(8'd224),.object_count(objects),.exception_count(exceptions),.group_count(groups),.palette_count(palettes),
 .release_frame(release_frame),.query(query),.query_kind(kind),.query_index(index),.query_generation(qgen),
 .response(response),.hit(hit),.data(data),.tx_valid(tv),.tx_ready(ready),.tx_data(td),
 .ack_valid(ack),.ack_accept(fault!=3),.ack_generation(gen),.ack_ready(ar),.busy(busy),.error(error),.observe_state177(state));
 always @(posedge clk)begin
  clocks<=clocks+1;ready<=clocks%11<6;response<=query;hit<=query&&fault!=1;
  if(query)begin if(qgen!=gen)$fatal(1,"query generation");data<=mem[kind*2048+index];end
  ack<=0;
  if(reset)pending<=0;
  else begin
   if(pending && valid && (!tv||td!==held))$fatal(1,"held record changed");
   pending<=tv&&!ready;held<=td;if(tv&&!ready)stalls++;
   if(tv&&ready)begin
    if(td[95:93]==6)$fatal(1,"old CHR payload leaked");
    $fdisplay(fd,"%024h",td);total++;
    if(td[95:93]==7&&td[76:64]==1)ack<=1;
    if(td[95:93]==7&&td[76:64]==2)begin if(!fault)$fatal(1,"unexpected ABORT");aborts++;end
    if(td[95:93]==7&&td[76:64]==3)commits++;
   end
   if(release_frame)owned<=0;
  end
 end
 initial begin
  for(scene=0;scene<11;scene++)begin
   @(negedge clk);reset=1;enable=0;owned=0;commits=0;
   name=$sformatf("scene%0d.cfg",scene);cfg=$fopen(name,"r");if(!cfg)$fatal(1,"config");
   rc=$fscanf(cfg,"%d %d %d %d %d %d",gen,patches,objects,exceptions,groups,palettes);$fclose(cfg);if(rc!=6)$fatal(1,"config fields");
   name=$sformatf("scene%0d.mem",scene);$readmemh(name,mem);
   name=$sformatf("scene%0d.wire",scene);fd=$fopen(name,"w");
   repeat(3)@(negedge clk);reset=0;enable=1;owned=1;
   wait(commits==1);wait(!busy);@(negedge clk);enable=0;$fclose(fd);
   if(error)$fatal(1,"export error");
  end
  for(fault=1;fault<=3;fault++)begin
   @(negedge clk);reset=1;enable=0;owned=0;valid=1;commits=0;aborts=0;
   gen=10;patches=0;objects=0;exceptions=0;groups=1;palettes=1;$readmemh("scene0.mem",mem);
   name=$sformatf("fault%0d.wire",fault);fd=$fopen(name,"w");
   repeat(3)@(negedge clk);reset=0;enable=1;owned=1;
   if(fault==2)begin wait(state==2);@(negedge clk);valid=0;end
   wait(aborts==1);wait(!busy);@(negedge clk);enable=0;$fclose(fd);
   if(commits||error!=(fault==1?3:fault==2?1:6))$fatal(1,"fault termination");
  end
  if(!stalls)$fatal(1,"no backpressure");
  $display("PASS METADATA203 scenes=11 commits=11 faults=3 records=%0d stalls=%0d chr=0",total,stalls);$finish;
 end
 initial begin #2000000;$fatal(1,"watchdog");end
endmodule
'''

def materialize(out):
 prep=prepare(out);pins=prep['source_pins']
 def read(path):pins[path.relative_to(BASE).as_posix()]=sha(path);return path.read_text()
 # A distinct type retains original186 CHR bytes ONLY in the reference model.
 old=BASE/'probes/nes-paired186/arm01/src'
 h=read(old/'nes_native165.h');h=h[h.index('struct nes_native165_tile'):h.index('\nenum {')]
 h=h.replace('nes_native165_tile','nes_reference203_tile').replace('struct nes_native165 {','struct nes_reference203 {')
 (out/'reference203.h').write_text('#include <stdbool.h>\n#include <stdint.h>\n'+h,encoding='utf8')
 c=read(old/'nes_native_video165.c');c=c[:c.index('\nbool nes_native_video165_build(')]
 c=c.replace('struct nes_native165 *','struct nes_reference203 *').replace('nes_native_video185_build','reference203_build').replace('nes_native181_pixels','reference203_pixels')
 c=c.replace('#include "nes_native_video165.h"','''#include "nes_native_video165.h"
#include "reference203.h"
static const uint8_t *reference203_pixels(const struct nes_reference203 *s,unsigned slot){
 return s&&s->state==NES_NATIVE165_COMMITTED&&slot<s->patch_count?s->raw_pixels+slot*256:NULL;
}''')
 (out/'reference203.c').write_text(c,encoding='utf8')
 f=read(ROOT/'tests/nes-functional/plan191_host.c')
 stage=f[f.index('static bool stage('):f.index('static bool plan(')]
 scene=f[f.index('static void scene('):f.index('\nint main(')]
 prefix='''#include "nes_plan191.h"
#include "reference203.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct nes_reference203 r;
static struct nes_native_video165 ref;
static uint8_t bg[16384],obj[4096];static unsigned sizes[2];static uint16_t lut[64];
bool reference203_build(const struct nes_reference203 *,const uint16_t [64],struct nes_native_video165 *,bool,nes_native_video165_stage_fn,void *);
'''+stage+scene
 s=read(ROOT/'tests/nes-functional/runtime202_host.c');s=s[s.index('#include "nes_native_runtime165.h"'):]
 s=s.replace('nes_native_video185_build','reference203_build').replace('RUNTIME202','METADATA203')
 start=s.index('static void record(');end=s.index('static uint32_t ticks(',start)
 s=s[:start]+r'''
static unsigned current_scene;
static void ingress(void){
 char name[64];sprintf(name,"scene%u.wire",current_scene);FILE *f=fopen(name,"r");assert(f);
 nr=read_at=0;prepared=false;unsigned top,hi,lo;
 static const unsigned widths[]={2,1,7,4,7,1,2,8};
 while(fscanf(f,"%8x%8x%8x",&top,&hi,&lo)==3){
  uint64_t value=((uint64_t)hi<<32)|lo;
  unsigned k=top>>29,index=top&8191,gen=(top>>13)&65535,n=widths[k];assert(nr<2048&&gen==r.generation);
  unsigned tag=k*8192+index;uint8_t *b=records[nr];b[0]=(uint8_t)(tag>>8);b[1]=(uint8_t)tag;
  b[2]=(uint8_t)(gen>>8);b[3]=(uint8_t)gen;for(unsigned j=0;j<n;j++)b[4+j]=(uint8_t)(value>>(8*(n-1-j)));
  record_size[nr++]=(uint8_t)(4+n);if(k==7&&index==3)commit_at=nr-1;
 }fclose(f);assert(nr&&commit_at==nr-1);
}
static void fixtures(void){
 unsigned sequence[]={0,2,3,7,0,0,2,7,0,0,0};
 for(unsigned i=0;i<11;i++){
  scene(sequence[i]);r.generation=(uint16_t)(65533+i);
  if(i>=9){r.counts[0]=528;for(unsigned x=0;x<528;x++)r.maps[x]=(uint16_t)(x%(i==9?512:513));}
  char name[64];sprintf(name,"scene%u.cfg",i);FILE *f=fopen(name,"w");assert(f);
  fprintf(f,"%u %u %u %u %u %u\n",r.generation,r.patch_count,r.counts[2],r.counts[3],r.counts[0]/33,r.counts[5]/32);fclose(f);
  sprintf(name,"scene%u.mem",i);f=fopen(name,"w");assert(f);
  for(unsigned k=0;k<8;k++)for(unsigned x=0;x<2048;x++){
   uint64_t v=0;
   if(k<6&&x<r.counts[k])v=k==0?r.maps[x]:k==1?r.rows[x]:k==2?r.objects[x]:k==3?r.exceptions[x]:k==4?r.raster[x]:r.palette[x];
   if(k==7&&x<r.patch_count*256u)v=r.raw_pixels[x];
   fprintf(f,"%08x%08x\n",(unsigned)(v>>32),(unsigned)v);
  }fclose(f);
 }
}
static void faults(void){
 /* These edits target the actual RTL record trace, before PREPARED/COMMIT. */
 for(unsigned which=0;which<9;which++){
  current_scene=which<7?0:which+2;scene(0);r.generation=(uint16_t)(65533+current_scene);ingress();
  unsigned meta=0;for(unsigned i=0;i<nr;i++)if(records[i][0]==0xe0&&records[i][1]==4)meta=i;assert(meta);
  if(which==0)records[0][4]=0x18; /* incompatible header */
  if(which==1){records[1][0]=0xc0;records[1][1]=0;record_size[1]=6;} /* legacy CHR */
  if(which==2){memcpy(records[1],records[meta],12);record_size[1]=12;} /* early META_END */
  if(which==3)records[meta][11]=1; /* nonzero old CHR byte count */
  if(which==4)records[meta][3]^=1; /* generation */
  if(which==5){memcpy(records[meta+1],records[meta],12);record_size[meta+1]=12;} /* duplicate */
  if(which==6){records[1][0]=0xf0;records[1][1]=0;record_size[1]=12;memset(records[1]+4,0,8);records[1][4]=0xa0;} /* raw before metadata */
  nes_native165_reset(&received);bool ok=true;
  for(unsigned i=0;i<commit_at&&ok;i++)ok=nes_native165_packet(&received,(uint16_t)i,records[i],record_size[i]);
  if(which==7){assert(ok&&received.state==NES_NATIVE165_COMPLETE&&received.ntiles==512&&received.missing==0);
   for(unsigned t=0;t<512;t++)assert(received.tiles[t].tag==t&&received.tiles[t].kind==1);
  }else{assert(!ok&&received.state==NES_NATIVE165_FAILED);if(which==8)assert(received.error==34);
   assert(!nes_native181_pixels(&received,0));
  }
 }
 printf("PASS METADATA203 boundaries=9 receiver_bytes=%u tile_bytes=%u\n",(unsigned)sizeof received,(unsigned)sizeof received.tiles[0]);
 assert(sizeof received.tiles[0]==4&&sizeof received==sizeof(struct nes_reference203)-8192);
}
''' +s[end:]
 s=replace(s,'int main(void){','int main(int argc,char **argv){\n if(argc==2&&!strcmp(argv[1],"--fixtures")){fixtures();return 0;}')
 s=replace(s,'  build(sequence[i],(65533+i)&65535);','  current_scene=i;build(sequence[i],(65533+i)&65535);')
 s=replace(s,'  init();build(7,123);','  init();current_scene=3;build(7,0);r.generation=0;') # scene3 wraps to0
 s=replace(s,' return 0;\n}', ' faults();return 0;\n}')
 (out/'host203.c').write_text(prefix+'\n'+s,encoding='utf8',newline='\n')
 (out/'bench.sv').write_text(BENCH,encoding='utf8',newline='\n')
 return pins

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
 a.out=a.out.resolve();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';pins=materialize(a.out)
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
 env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 def run(args,name):
  with (a.out/(name+'.log')).open('wb') as log:
   r=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-6000:];return s
 sources=['host203.c','reference203.c','nes_native_runtime165.c','nes_native165.c','nes_trace166.c','nes_plan191.c','nes_plan_service200.c','nes_native_sink165.c','nes_sink_trace168.c','nes_sink_window184.c']
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-fstack-usage',*sources,'-o','host.exe'],'gcc')
 run([a.out/'host.exe','--fixtures'],'fixtures')
 for tool,args in [('vlib',['work']),('vlog',['-sv','nes_native_export203.sv','bench.sv']),('vsim',['-c','work.metadata203_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  rtl=run([a.questa_bin/(tool+'.exe'),*args],tool)
 host=run([a.out/'host.exe'],'host');assert 'frames=9 ' in host and host.count('PASS METADATA203 fault=')==6 and 'boundaries=9' in host
 assert 'scenes=11 commits=11' in rtl
 result=dict(passed=True,source_pins=pins,script_sha256=sha(Path(__file__)),frames=9,export_scenes=11,boundaries=9,runtime_faults=6,export_faults=3,
  host_summary=host.strip(),rtl_summary=[x for x in rtl.splitlines() if 'PASS METADATA203' in x],host_receiver_bytes=int(re.search(r'receiver_bytes=(\d+)',host)[1]),removed_chr_storage=8192,
  scope=__doc__,generated={n:sha(a.out/n) for n in ['host203.c','reference203.c','reference203.h','bench.sv']},
  full_board=False,rtl_c_trace_replay=True,rtl_c_simultaneous=False,actual_snes_cpu=False,physical=False,new_fit=False,new_package=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(host)
if __name__=='__main__':main()
