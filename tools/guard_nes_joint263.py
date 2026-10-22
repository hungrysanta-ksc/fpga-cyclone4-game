# SPDX-License-Identifier: MIT
"""Real bridge negative edges, cancellation and frozen shared RAM."""
import argparse,json,os,shutil
from pathlib import Path
from probe_nes_joint263 import prepare,run
from nes_delta231 import sha,once,ROOT

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src,pins,stats=prepare(d,905);s=(d/'joint263_tb.sv').read_text()
 s=once(s,'module joint263_tb;', 'module joint263_tb;parameter GNEG=0;integer streams_guard263=0;')
 s=s.replace('&& !NEG','&&!NEG').replace('&&!NEG)', '&&!NEG&&!GNEG)').replace('&&!NEG&&!PRENEG)', '&&!NEG&&!PRENEG&&!GNEG)')
 s=once(s,'  for(integer i=0;i<count263;i++)begin', '''
  if(GNEG==1)begin wr261(24'h006060,0);wr261(24'h006063,8'ha5);wait(1'b0);end
  if(GNEG==2||GNEG==7)begin
   wr261(24'h006060,0);wr261(24'h006061,0);wr261(24'h006062,GNEG==2?8'h9c:8'h88);wr261(24'h006063,8'ha5);
   if(GNEG==7)wr261(24'h006063,8'ha5);wait(1'b0);
  end
  for(integer i=0;i<count263;i++)begin''')
 s=once(s,'   word263=call263(3,i,0);', '''   word263=call263(3,i,0);
   if(GNEG==5&&word263[21:18]==3)word263=word263^1;
   if(GNEG==6&&word263[21:18]==5)word263=word263^1;''')
 s=once(s,'    token261(token263);wr261', '    token261(token263+(GNEG==8));wr261')
 s=once(s,'endmodule', '''
 always @(posedge clk)if(dut.stream_valid&&stream_ready)streams_guard263++;
 initial begin : cancel_bridge263
  if(GNEG==3||GNEG==4)begin
   wait(streams_guard263==8);@(negedge clk);disable bus263;
   bus_read=1;bus_write=1;repeat(8)@(negedge host_clk);
   if(GNEG==3)test_abort=1;else begin token261(dut.flow.last_map_token);wr261(24'h006058,8'h5a);end
  end
 end
 initial begin : guard_result263
 reg [7:0] frozen[0:1023];
 if(GNEG)begin
  wait(source_fault);disable bus263;repeat(4)@(negedge clk);
  if(v_sealed||lease_valid||staged||rack||flow_retired)$fatal(1,"postfault completion");
  for(integer i=0;i<1024;i++)frozen[i]=dut.core.memory[i];
  repeat(256)@(negedge clk);
  for(integer i=0;i<1024;i++)if(frozen[i]!==dut.core.memory[i])$fatal(1,"postfault RAM write");
  $display("PASS BRIDGE263 GNEG=%0d fault=%0d streams=%0d",GNEG,source_fault,streams_guard263);$finish;
 end
 end
endmodule''')
 (d/'joint263_tb.sv').write_text(s,encoding='utf-8',newline='\n')
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',['-O2','-std=c99','-Wall','-Wextra','-Werror','-shared','nes_producer263.c','-o','producer263.dll'],d,'native')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint263_tb.sv'],d,'vlog');guards=[]
 for i in range(1,9):
  log=run(a.questa_bin/'vsim.exe',['-c','-sv_lib','producer263','work.joint263_tb',f'-gGNEG={i}','+LAST=905','-do','onerror {quit -code 1};run -all;quit -f'],d,f'guard{i}',300)
  assert f'PASS BRIDGE263 GNEG={i}' in log;guards.append(i)
 r=dict(passed=True,guards=guards,rtl_hashes={n:sha(d/n) for n in src},TB_sha256=sha(d/'joint263_tb.sv'),scope=__doc__)
 shutil.copyfile(__file__,d/'guard_nes_joint263.py');(d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(r))

if __name__=='__main__':main()
