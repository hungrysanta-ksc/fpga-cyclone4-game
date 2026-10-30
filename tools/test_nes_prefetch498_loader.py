# SPDX-License-Identifier: MIT
"""498 actual RTL truth table of the only changed loader next-state bit.
Includes blocked commands, STOP/fault drain, terminal and mixed SETUP/WRITE.
Not a new full PSRAM/physical-loader trial.
"""
import argparse,json,subprocess
from pathlib import Path
from nes_status495 import sha
TB=r'''
module loader498;
 reg clk=0,reset=0,lb=0,le=0,start=0,stop=0,blocked=0,f=0,t=0;
 reg[15:0] p=0;integer i;
 nes_rom_loader_ref a(.mem_clk(clk),.reset(reset),.load_begin(lb),.load_chr32(1'b0),.load_valid(1'b0),.load_end(le),.start(start),.stop(stop),.load_data(8'd0),.commands_blocked(blocked));
 nes_rom_loader b(.mem_clk(clk),.reset(reset),.load_begin(lb),.load_chr32(1'b0),.load_valid(1'b0),.load_end(le),.start(start),.stop(stop),.load_data(8'd0),.commands_blocked(blocked));
 initial begin
 force a.phase=p;force b.phase=p;force a.fault=f;force b.fault=f;force a.terminal=t;force b.terminal=t;
 for(i=0;i<512;i=i+1)begin
 p=0;p[7]=i[0];p[2]=i[1];f=i[2];t=i[3];stop=i[4];blocked=i[5];lb=i[6];le=i[7];start=i[8];#1;
 if(a.to_write!==b.to_write)$fatal(1,"loader mismatch row %0d",i);
 end
 $display("PASS LOADER498 512 exact next-state rows");$finish;
 end
endmodule
'''
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['base','board','bin','out']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(exist_ok=False)
 old=(a.base/'nes_rom_loader.sv').read_text();new=(a.board/'nes_rom_loader.sv').read_text()
 (a.out/'old.sv').write_text(old.replace('module nes_rom_loader ','module nes_rom_loader_ref '))
 (a.out/'tb.sv').write_text(TB)
 def run(name,args):
  with (a.out/(name+'.log')).open('wb') as f:r=subprocess.run([str(a.bin/(args[0]+'.exe')),*args[1:]],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=90)
  return r.returncode,(a.out/(name+'.log')).read_text(errors='replace')
 code,log=run('lib',['vlib','work']);assert code==0,log
 for tag,src in [('normal',new),('mutant',new.replace('commands_blocked ? write_blocked : write_unblocked','write_unblocked'))]:
  (a.out/'new.sv').write_text(src)
  code,log=run(tag+'-compile',['vlog','-sv','old.sv','new.sv','tb.sv']);assert code==0 and '** Error' not in log,log[-1500:]
  code,log=run(tag,['vsim','-c','loader498','-do','onerror {quit -code 1}; run -all; quit -f'])
  if tag=='normal':assert code==0 and 'PASS LOADER498' in log and '** Fatal' not in log,log[-1500:]
  else:assert '** Fatal' in log and 'loader mismatch row' in log,log[-1500:]
 result={'passed':True,'rows':512,'mutant_rejected':True,'scope':__doc__,'baseline_SHA256':sha(a.base/'nes_rom_loader.sv'),'candidate_SHA256':sha(a.board/'nes_rom_loader.sv')}
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
