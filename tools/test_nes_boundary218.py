# SPDX-License-Identifier: MIT
"""Same-edge SPI differential states, bit boundaries and real wire transactions."""
from pathlib import Path
import argparse,json,os,re,subprocess
from nes_game147 import ROOT,sha
from nes_boundary218 import transform
from test_nes_checkstate181 import STATE,bench as state_bench,connected

def bench():
 s=state_bench().replace('dut.check_busy=','dut.byte_last=0;dut.check_busy=',1)
 invariant='if(dut.byte_last !== (dut.bit_count==7))$fatal(1,"BOUNDARY218 invariant");'
 s=s.replace('mem_clk=0;#1;count++;',invariant+'\n mem_clk=0;#1;count++;')
 seed='\n'.join(f"dut.{n}='0;refdut.{n}='0;" for n in STATE)
 compare='\n'.join(f'if(dut.{n}!==refdut.{n})$fatal(1,"BOUNDARY218 mismatch {n} bits=%d bytes=%d flags=%h value=%h",bits,bytes,f,value);' for n in STATE)
 task='''integer boundaries=0;
task boundary(input [2:0] bits,input [3:0] bytes,input [3:0] f,input [7:0] value);
begin
'''+seed+'''
 reset=0;check_fault=0;boot_fault=0;check_response=0;
 dut.bit_count=bits;refdut.bit_count=bits;dut.byte_last=bits==7;
 dut.byte_count=bytes;refdut.byte_count=bytes;
 dut.shift=value>>1;refdut.shift=value>>1;
 dut.mosi_sync={value[0],value[0]};refdut.mosi_sync=dut.mosi_sync;
 dut.ss_sync=f[0]?3:0;refdut.ss_sync=dut.ss_sync;
 dut.sck_sync=f[1]?3:0;refdut.sck_sync=dut.sck_sync;
 dut.sck_previous=f[2];refdut.sck_previous=f[2];
 reset=f[3];
 #1;mem_clk=1;#1;
'''+compare+'\n'+invariant+'''
 mem_clk=0;#1;boundaries++;
end endtask
'''
 s=s.replace('initial begin\n',task+'initial begin\n',1)
 s=s.replace(' $display("PASS STATE181', ''' for(integer b=0;b<8;b++)for(integer n=0;n<16;n++)for(integer f=0;f<16;f++)for(integer v=0;v<256;v++)boundary(b,n,f,v);
 $display("PASS BOUNDARY218 boundaries=%0d",boundaries);
 $display("PASS STATE181''')
 return s

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','candidate','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 old=(a.baseline/'nes_rom_spi.sv').read_text();new=(a.candidate/'nes_rom_spi.sv').read_text();assert new==transform(old)
 a.out.mkdir();(a.out/'reference.sv').write_text(old.replace('module nes_rom_spi_check(','module baseline_check165(',1));(a.out/'candidate.sv').write_text(new)
 for n in ['nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv']:(a.out/n).write_bytes((a.candidate/n).read_bytes())
 (a.out/'state_tb.sv').write_text(bench());(a.out/'connected_tb.sv').write_text(connected())
 def run(tool,args,label,negative=False):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  log=(a.out/(label+'.log')).read_text(errors='replace')
  if negative:assert 'BOUNDARY218 invariant' in log or 'BOUNDARY218 mismatch' in log,(label,log[-3000:])
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),(label,log[-3000:])
  return log
 def sim(top):return ['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f']
 run('vlib',['work'],'vlib');run('vlog',['-sv','reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','state_tb.sv','connected_tb.sv'],'compile')
 log=run('vsim',sim('state181_tb'),'states');assert 'PASS STATE181 edges=1056768 followups=1024' in log and 'boundaries=524288' in log
 seq=run('vsim',sim('tag165_tb'),'connected');assert 'wire_bits=14016' in seq and 'acks=7 corruptions=19 cancels=72 overlaps=2' in seq
 for label,needle,replacement in [('early','byte_last<=bit_count==6','byte_last<=bit_count==5'),('ss','else if(ss_sync[1])byte_last<=0;','else if(ss_sync[1])byte_last<=1;')]:
  assert new.count(needle)==1;(a.out/('wrong-'+label+'.sv')).write_text(new.replace(needle,replacement))
  run('vlog',['-sv','wrong-'+label+'.sv'],label+'-compile');run('vsim',sim('state181_tb'),label+'-negative',True)
 r=dict(passed=True,same_edge=True,edges=1056768,followup_sequences=1024,bit_boundaries=524288,wire_bits=14016,negative_cases=['early byte boundary','SS boundary not cleared'],
  sequential_summary=re.search(r'PASS TAG165[^\r\n]+',seq)[0],source_sha256=sha(a.candidate/'nes_rom_spi.sv'),reference_sha256=sha(a.baseline/'nes_rom_spi.sv'),
  sources={n:sha(a.out/n) for n in ['reference.sv','candidate.sv','nes_rom_boot.sv','nes_rom_loader.sv','nes_rom_physical.sv','state_tb.sv','connected_tb.sv']},
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_boundary218.py','tools/test_nes_boundary218.py','tools/test_nes_checkstate181.py','tools/test_nes_rawstage167.py','tools/test_nes_commitstage167.py','tools/test_nes_commandpulse165.py','tools/test_nes_commandstage165.py','tools/test_nes_check165.py','tools/test_nes_counterpulse167.py','tests/nes-functional/tag165_tb.sv']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['sources','public_sources']}))
if __name__=='__main__':main()
