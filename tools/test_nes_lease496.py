# SPDX-License-Identifier: MIT
"""496 actual lease201 regression: next capture exists but export waits for old retire."""
import argparse,hashlib,json,re,shutil,subprocess
from pathlib import Path
TB=r'''
module lease496_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,stop=0,cb=0,owned=0,valid=0,release_in=0,drained=0,retire=0;
 reg [15:0] gen=0,rgen=0;wire release_out,lease,permit,export_ok,waiting,fault;
 wire [15:0] saved;wire [31:0] epoch;
 nes_capture_lease201 d(clk,reset,stop,cb,owned,valid,gen,release_in,4'd0,1'b1,1'b1,1'b0,32'd7,drained,retire,rgen,release_out,lease,permit,export_ok,epoch,saved,waiting,fault);
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 initial begin
 tick;reset=0;cb=1;tick;cb=0;owned=1;valid=1;gen=1;release_in=1;tick;release_in=0;owned=0;valid=0;
 if(!lease||saved!=1||export_ok||fault)$fatal(1,"first lease");
 cb=1;tick;cb=0;owned=1;valid=1;gen=2;tick;
 if(export_ok||saved!=1||!waiting||fault)$fatal(1,"next export must wait for old display");
 drained=1;tick;if(!permit||export_ok)$fatal(1,"drained is not retired");
 rgen=1;retire=1;#1;if(release_out)$fatal(1,"retire releases next collector");tick;retire=0;
 if(!export_ok||waiting||fault)$fatal(1,"old retire did not enable next export");
 release_in=1;tick;release_in=0;
 if(!lease||saved!=2||export_ok||fault)$fatal(1,"new identity");
 rgen=1;retire=1;tick;retire=0;if(!fault||lease||export_ok)$fatal(1,"stale retirement accepted");
 stop=1;tick;if(lease||export_ok||waiting||fault)$fatal(1,"STOP cancellation");
 $display("PASS LEASE496 old identity, next capture/export, drain, stale retire, STOP");$finish;
 end
endmodule
'''
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['board','bin','out']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(exist_ok=False);src=a.board/'nes_capture_lease201.sv';s=src.read_text()
 joint=(a.board/'nes_live_joint.sv').read_text();assert '.enable(export_permitted204&&!direct_nes_fault204)' in joint
 (a.out/'tb.sv').write_text(TB);(a.out/'lease.sv').write_text(s)
 def run(name,args):
  with (a.out/(name+'.log')).open('wb')as f:r=subprocess.run([str(a.bin/(args[0]+'.exe')),*args[1:]],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=90)
  return r.returncode,(a.out/(name+'.log')).read_text(errors='replace')
 for name,args in [('lib',['vlib','work']),('compile',['vlog','-sv','lease.sv','tb.sv'])]:
  code,log=run(name,args);assert code==0 and '** Error' not in log,log[-2000:]
 code,log=run('normal',['vsim','-c','lease496_tb','-do','onerror {quit -code 1}; run -all; quit -f']);assert code==0 and 'PASS LEASE496' in log and '** Fatal'not in log
 needle='assign export_permitted=!reset&&!stop&&!fault&&!lost&&!waiting_display;';assert s.count(needle)==1
 (a.out/'lease.sv').write_text(s.replace(needle,'assign export_permitted=!reset&&!stop&&!fault&&!lost;'))
 code,log=run('negative_compile',['vlog','-sv','lease.sv','tb.sv']);assert code==0
 code,log=run('negative',['vsim','-c','lease496_tb','-do','onerror {quit -code 1}; run -all; quit -f']);assert '** Fatal' in log and 'first lease' in log
 r={'passed':True,'scope':__doc__,'early_export_mutant_rejected':True,'source_enable_bound_statically':True,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'joint_sha256':hashlib.sha256((a.board/'nes_live_joint.sv').read_bytes()).hexdigest(),'full_pipeline_simulation':False}
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
