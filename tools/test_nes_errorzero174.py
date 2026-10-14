# SPDX-License-Identifier: MIT
"""Same-edge priority/reset/hold differential and legal SPI replay."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_errorzero174 import transform
from test_nes_rawstage167 import bench as rawbench,connected

def bench():
 s=rawbench().split('integer captures=0')[0]
 s+='''integer count=0;
initial begin
 for(integer held=0;held<17;held++)for(integer bits=0;bits<2048;bits++)for(integer code=0;code<16;code++)begin
  mem_clk=0;reset=1;#1;mem_clk=1;#1;mem_clk=0;reset=0;
  check_fault=bits[0];boot_fault=bits[1];check_response=bits[2];
  check_response_address=bits[5]?19'h12344:19'h12345;
'''
 for d in ['dut','refdut']:
  s+=f'''  {d}.check_enable=bits[3];{d}.check_busy=bits[4];{d}.ss_sync=bits[6]?0:3;{d}.ss_previous=1;
  {d}.sampled=bits[7];{d}.captured=bits[8];{d}.pending=bits[9];{d}.commit_inc=bits[10];
  {d}.decoded_error=code;{d}.check_request_tag=19'h12345;{d}.pending_command=4'ha;
  {d}.fault=held!=0;{d}.error_code=held?held-1:0;
'''
 s+='''  #1;mem_clk=1;#1;
'''
 for n in ['fault','error_code','check_enable','check_busy','check_done','verified','load_begin','load_valid','load_end','start','stop','check_request','check_next']:
  s+=f'  if(dut.{n}!==refdut.{n})$fatal(1,"ERRORZERO174 {n} held=%0d bits=%h code=%h",held,bits,code);\n'
 s+='''  if(!dut.fault && dut.error_code!=0)$fatal(1,"ERRORZERO174 invariant");
  mem_clk=0;#1;count++;
 end
 // Asynchronous reset also clears an already latched code without a clock.
 reset=1;#1;
 if(dut.fault || dut.error_code || refdut.fault || refdut.error_code)$fatal(1,"ERRORZERO174 async reset");
 $display("PASS ERRORZERO174 states=%0d",count);$finish;
end
endmodule
'''
 return s

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 a.out.mkdir(parents=True,exist_ok=False)
 names=['nes_rom_spi.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']
 for n in names:(a.out/n).write_bytes((a.candidate/n).read_bytes())
 old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.candidate/'nes_rom_spi.sv').read_text();assert new==transform(old)
 (a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1))
 (a.out/'bench.sv').write_text(bench())
 wire=connected();needle="boot.loader.phase=16'h10;";assert wire.count(needle)==1
 wire=wire.replace(needle,needle+"boot.loader.reject_state=4'b1100;")
 (a.out/'connected.sv').write_text(wire)
 def run(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=240)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert '** Fatal: ERRORZERO174' in log and 'PASS ERRORZERO174' not in log,label
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-2500:])
  return log
 run('vlib',['work'],'vlib');run('vlog',['-sv',*names,'reference.sv','bench.sv','connected.sv'],'compile')
 args=['-c','check165_tb','-do','onerror {quit -code 1}; run -all; quit -f']
 log=run('vsim',args,'priority');assert 'PASS ERRORZERO174 states=557056' in log
 log=run('vsim',['-c','tag165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'connected')
 assert 'wire_bits=14016' in log and 'acks=7 corruptions=19 cancels=72 overlaps=2' in log
 for label,needle,wrong in [('priority',"error_hard?4'd9:error_response?4'd7:","error_response?4'd7:error_hard?4'd9:"),('hold','else if(!fault)error_code<=','else error_code<=')]:
  assert new.count(needle)==1;(a.out/(label+'-wrong.sv')).write_text(new.replace(needle,wrong))
  run('vlog',['-sv',label+'-wrong.sv'],label+'-wrong-compile');run('vsim',args,label+'-wrong',True)
 r=dict(passed=True,states=557056,negatives=['priority','hold'],summary=re.search(r'PASS TAG165[^\r\n]+',log)[0],wire_bits=14016,
  sources={n:sha(a.out/n) for n in [*names,'reference.sv','bench.sv','connected.sv']},reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),
  invariant='reset-reachable !fault => error_code==0; fault holds any seeded 4-bit code',scope=__doc__,
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_errorzero174.py','tools/test_nes_errorzero174.py','tools/test_nes_rawstage167.py','tools/test_nes_commitstage167.py','tools/test_nes_commandpulse165.py','tools/test_nes_commandstage165.py','tools/test_nes_check165.py','tests/nes-functional/tag165_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n');print('PASS ERRORZERO174 557056 states/2 negatives/'+r['summary'])
if __name__=='__main__':main()
