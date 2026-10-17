# SPDX-License-Identifier: MIT
"""Actual215 C + selected207 RTL with bounded host/ROM admission stalls.

Synthetic plans and modeled SNES consume, not a physical cause/FPS claim.
Never changes the deployed 1048576-cycle tile limit.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,time
from test_nes_join208 import prepare,ROOT,BASE,sha,replace

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
 p.add_argument('--cycles',type=int,required=True);p.add_argument('--slot-wait',action='store_true')
 p.add_argument('--expect-fault',action='store_true');p.add_argument('--candidate',action='store_true');a=p.parse_args();a.out=a.out.resolve()
 assert str(a.out).isascii() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 assert 0<=a.cycles<0x1000000
 pins,rtl=prepare(a.out);src=BASE/'probes/nes-plan215/arm01/src'
 if a.candidate:
  f=ROOT/'src/nes/rtl/nes_tile205.sv';shutil.copyfile(f,a.out/f.name);pins[str(f)]=sha(f)
 for f in [*src.glob('nes_*.h'),src/'nes_plan_service200.c']:
  shutil.copyfile(f,a.out/f.name);pins[str(f)]=sha(f)
 f=ROOT/'tests/nes-functional/plan215_host.c';pins[str(f)]=sha(f);s=f.read_text()
 s=replace(s,'#include "nes_plan_service200.h"','#include "nes_plan_service200.h"\n#include "nes_plan215.h"\n#include <stdlib.h>')
 s=replace(s,'static unsigned seq=1,frames,chunks,bytes,plans;',f'static unsigned seq=1,frames,chunks,bytes,plans;\nstatic unsigned waited;\n#define WAIT_CYCLES {a.cycles}u\n#define EXPECT_FAULT {int(a.expect_fault)}')
 marker='static unsigned le16('
 at=s.index(marker)
 s=s[:at]+'''static void checked(bool ok){
 if(ok)return;
 printf("TERMINAL error=%u sent=%u phase=%u reason=%u raw=",plan.error,plan.sent,nes_plan215.phase,nes_plan215.reason);
 for(unsigned i=0;i<20;i++)printf("%02x",nes_plan215.reply[i]);puts("");fflush(stdout);
 assert(EXPECT_FAULT&&plan.error==4&&plan.sent==1&&nes_plan215.reason==NES_PLAN215_FLAGS);
 static const uint8_t expected_fault[20]={0,0xd7,4,0x80,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0x7f};
 assert(!memcmp(nes_plan215.reply,expected_fault,20));
 rpc(6,0,NULL,0,NULL,0);rpc(9,0,NULL,0,NULL,0);
 puts("PASS WAIT216 expected fault; canceled and no exposed data");exit(0);
}
'''+s[at:]
 s=replace(s,'rpc(1,0,copy,n,rx,n);','rpc(1,0,copy,n,rx,n);\n if(copy[0]==0xe9&&!waited++){rpc(7,WAIT_CYCLES,NULL,0,NULL,0);}')
 s=replace(s,'assert(nes_plan200_emit(&plan,&q));','checked(nes_plan200_emit(&plan,&q));')
 s=replace(s,'assert(ok);','checked(ok);')
 start=s.index('static const unsigned counts[]=');end=s.index(';',start)
 s=s[:start]+'static const unsigned counts[]={29,0,15}'+s[end:]
 s=replace(s,'rpc(9,0,NULL,0,NULL,0);printf("PASS PLAN215','assert(!EXPECT_FAULT);rpc(9,0,NULL,0,NULL,0);printf("PASS WAIT216')
 (a.out/'host.c').write_text(s,encoding='utf8',newline='\n')
 s=(a.out/'join208_tb.sv').read_text()
 s=replace(s,'wire req,mready,mresponse,merror;','reg slot_allowed=1,slot_used=0;\n wire req,mready,mresponse,merror;')
 s=replace(s,".qualified_slot(1'b1)",'.qualified_slot(slot_allowed)')
 monitor='''
 integer first_fault=0;
 always @(negedge clk)if(!local_reset&&!first_fault&&
  (dut.source.tile_fault||dut.source.arbiter_fault||dut.source.denied||lease_fault||
   dut.spi_fault||dut.batch_fault||dut.bulk_fault||dut.consume_error||dut.command_error))begin
  first_fault=1;
  $display("FIRST216 time=%0t tile=%b arbiter=%b denied=%b lease=%b spi=%b batch=%b bulk=%b consume=%b command=%b cycles=%0d state=%0d index=%0d ready=%b slot=%b",
   $time,dut.source.tile_fault,dut.source.arbiter_fault,dut.source.denied,lease_fault,
   dut.spi_fault,dut.batch_fault,dut.bulk_fault,dut.consume_error,dut.command_error,
   dut.source.tile.cycles,dut.source.tile.state,dut.source.tile.index,dut.otready,slot_allowed);
  if(!dut.source.tile_fault||dut.source.tile.cycles!=1048577||
     dut.source.arbiter_fault||dut.source.denied||lease_fault||dut.spi_fault||
     dut.batch_fault||dut.bulk_fault||dut.consume_error||dut.command_error)
   $fatal(1,"unexpected first cause");
 end
 always @(posedge clk)if(!local_reset&&dut.source.tile.busy&&dut.source.tile.cycles==1048576)
  $display("LIMIT216 time=%0t state=%0d index=%0d out_ready=%b mem_ready=%b lease=%b",
   $time,dut.source.tile.state,dut.source.tile.index,dut.otready,dut.source.tile.mem_ready,dut.source.tile.lease_ok);
'''
 s=replace(s,' initial begin\n',monitor+' initial begin\n')
 # Admission disabled before sending the first E9, never during an owned read.
 if a.slot_wait:
  s=replace(s,'begin197();for(integer i=0;i<n;i++)begin',"if(join208_get(8)==8'he9&&!slot_used)begin slot_allowed=0;slot_used=1;end\n     begin197();for(integer i=0;i<n;i++)begin")
 s=replace(s,'    9:begin','''    7:begin
     repeat(a)@(negedge clk);slot_allowed=1;repeat(30)@(negedge host_clk);join208_reply(0);
    end
    9:begin''')
 s=replace(s,'$display("PASS JOIN208 RTL',f'if(first_fault!={int(a.expect_fault)})$fatal(1,"wrong first-fault count");\n     $display("PASS JOIN208 RTL')
 (a.out/'join208_tb.sv').write_text(s,encoding='utf8',newline='\n')
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');qb=Path('C:/altera_standard/25.1std/questa_fse/win64')
 env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
 def run(args,name):
  with (a.out/(name+'.log')).open('wb') as f:r=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(a.out/(name+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-O2','host.c','nes_plan_service200.c','-o','host.exe'],'gcc-host')
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-shared','join208_rpc.c','-o','join208_rpc.dll'],'gcc-rpc')
 run([qb/'vlib.exe','work'],'vlib');run([qb/'vlog.exe','-sv',*rtl,'join208_tb.sv'],'vlog')
 children=[];logs=[]
 try:
  for n,cmd in [('rtl',[qb/'vsim.exe','-c','-voptargs=+acc','-sv_lib','join208_rpc','work.join208_tb','-do','onerror {quit -code 1}; run -all; quit -f']),('host',[a.out/'host.exe'])]:
   f=(a.out/(n+'.log')).open('wb');logs.append(f);children.append(subprocess.Popen(list(map(str,cmd)),cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW))
  start=time.monotonic()
  while any(c.poll() is None for c in children):
   if any(c.poll() not in (None,0) for c in children) or time.monotonic()-start>600:break
   if '** Fatal:' in (a.out/'rtl.log').read_text(errors='replace'):break
   time.sleep(.1)
  codes=[c.poll() for c in children]
 finally:
  for c in children:
   if c.poll() is None:c.kill();c.wait()
  for f in logs:f.close()
 texts={n:(a.out/(n+'.log')).read_text(errors='replace') for n in ['rtl','host']}
 passed=codes==[0,0] and 'PASS WAIT216' in texts['host'] and 'PASS JOIN208 RTL' in texts['rtl']
 result=dict(passed=passed,codes=codes,cycles=a.cycles,slot_wait=a.slot_wait,expect_fault=a.expect_fault,candidate=a.candidate,
  source_pins=pins,public_sha=sha(Path(__file__)),scope=__doc__,physical=False,full_game=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result|{'source_pins':None}),flush=True)
 assert passed,{n:t[-4000:] for n,t in texts.items()}
if __name__=='__main__':main()
