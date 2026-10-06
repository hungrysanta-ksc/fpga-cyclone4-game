# SPDX-License-Identifier: MIT
"""037 logical bus phase/turnaround regression; no physical delay signoff."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_h1_spi import fixed_boundary,replace,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser()
 for n in ('out','build','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir()
 files=['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport','nes_h1_pattern_producer','nes_h1_pattern','nes_h1_board_bus']
 for n in files:shutil.copy2(ROOT/'src/nes'/(n+'.sv'),out/(n+'.sv'))
 (out/'nes_h1_board_bus.sv').write_text(fixed_boundary())
 for n in ('h1-pattern.hex','h1-program.hex','program-full.hex'):shutil.copy2(a.build/n,out/n)
 tb=(ROOT/'tests/nes-functional/h1_board_tb.sv').read_text()
 tb=replace(tb,'reg [7:0] snes_data_in=0;',"""reg [7:0] host_data=0;
 wire [7:0] snes_data_in;
 integer phase=0,profile=0;
 real setup_ns=20,low_ns=180,hold_ns=20,gap_ns=100,receive_ns=0;
 // FPGA input disappears when the external receiver is disabled.
 // Delays are deliberately chosen model inputs, not measured board values.
 assign #(receive_ns) snes_data_in=(!SNES_DATABUS_OE && !SNES_DATABUS_DIR && !SNES_WRITE_IN)?host_data:8'hzz;""")
 tb=replace(tb,' wire SNES_DATABUS_OE,SNES_DATABUS_DIR,run_active,diagnostic_fault;', ' wire run_active,diagnostic_fault;')
 tb=replace(tb,'reg [7:0] host_data=0;', 'wire SNES_DATABUS_OE,SNES_DATABUS_DIR;\n reg [7:0] host_data=0;')
 tb=replace(tb,'   rx[b]=spi_miso;#2000;SPI_SCK=0;','   #2000;rx[b]=spi_miso;SPI_SCK=0;')
 start=tb.index(' task automatic wr(');end=tb.index(' task automatic acquire(',start)
 tb=tb[:start]+""" task automatic wr(input integer a,input integer value);
  SNES_ADDR_IN=a;host_data=~value;SNES_ROMSEL_IN=1;#(setup_ns);SNES_WRITE_IN=0;
  #(low_ns-60);host_data=value;#60;
  if(SNES_DATABUS_OE || SNES_DATABUS_DIR)$fatal(1,"write direction");
  SNES_WRITE_IN=1;#(hold_ns);SNES_ADDR_IN=24'h123456;host_data=8'hxx;#(gap_ns);
 endtask
 task automatic rd(input integer a,input integer want,input integer select,input integer kind=0);
  SNES_ADDR_IN=a;SNES_ROMSEL_IN=select;#(setup_ns);SNES_READ_IN=0;#(low_ns-1);
  if(SNES_DATABUS_OE || !SNES_DATABUS_DIR || snes_data_out!==want[7:0])$fatal(1,"read%h got%h wanted%h",a,snes_data_out,want);
  #1;
  if(kind==1)romreads++;
  if(kind==2)payloadreads++;
  SNES_READ_IN=1;#0.001;if(!SNES_DATABUS_OE || SNES_DATABUS_DIR)$fatal(1,"read release");
  #(hold_ns);SNES_ADDR_IN=24'habcd00;#(gap_ns);
 endtask
"""+tb[end:]
 tb=replace(tb,'  log=$fopen',"""  if(!$value$plusargs("PHASE=%d",phase))$fatal(1,"phase missing");
  if(!$value$plusargs("PROFILE=%d",profile))$fatal(1,"profile missing");
  if(profile==1)begin setup_ns=0;low_ns=120;hold_ns=0;gap_ns=48;receive_ns=15;end
  #(phase);
  log=$fopen""")
 tb=replace(tb,'for(integer i=0;i<65536;i++)rd', 'for(integer i=0;i<512;i++)rd')
 tb=replace(tb,'  $display("PASS NES H1 BOARD', '  $display("PASS PHASE phase=%0d profile=%0d",phase,profile);\n  $display("PASS NES H1 BOARD')
 (out/'h1_board_tb.sv').write_text(tb)
 def run(tool,args,label):
  with (out/(label+'.log')).open('wb') as f:
   cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  return cp.returncode
 assert run('vlib',['work'],'vlib')==0
 assert run('vlog',['-sv',*[n+'.sv' for n in files],'h1_board_tb.sv'],'compile')==0
 results=[]
 for profile in range(2):
  for phase in range(12):
   label=f'p{profile}-phase{phase:02d}'
   code=run('vsim',['-c','h1_board_tb',f'+PHASE={phase}',f'+PROFILE={profile}','-do','onerror {quit -code 1}; run -all; quit -f'],label)
   log=(out/(label+'.log')).read_text(errors='replace')
   ok=code==0 and not re.search(r'\*\* (?:Fatal|Error):',log) and 'PASS NES H1 BOARD checks=6 rombytes=512 payloadbytes=8192' in log
   results.append(dict(profile=profile,phase_ns=phase,passed=ok,exit_code=code))
   (out/'result.json').write_text(json.dumps(dict(candidate='NES-H1-BRINGUP-037',runs=results,compiled_boundary_sha256=sha(out/'nes_h1_board_bus.sv'),passed=all(x['passed'] for x in results)),indent=2))
   if not ok:raise RuntimeError(label+' failed: inspect raw log')
 print('PASS bus sweep:24 phase/profile combinations;12288 ROM bytes;196608 payload bytes')
if __name__=='__main__':main()
