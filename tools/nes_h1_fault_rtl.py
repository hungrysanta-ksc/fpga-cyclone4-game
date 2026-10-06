# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_h1_spi import sha,replace
from nes_h1_fault import boundary as fixed_boundary
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser()
 for n in ('out','build','questa-bin','wave'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir()
 files=['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport','nes_h1_pattern_producer','nes_h1_pattern','nes_h1_board_bus']
 for n in files:shutil.copy2(ROOT/'src/nes'/(n+'.sv'),out/(n+'.sv'))
 (out/'nes_h1_board_bus.sv').write_text(fixed_boundary())
 for n in ('h1-pattern.hex','h1-program.hex','program-full.hex'):shutil.copy2(a.build/n,out/n)
 shutil.copy2(a.wave,out/'waveform.txt');(out/'h1_spi_wave_tb.sv').write_text((ROOT/'tests/nes-functional/h1_spi_wave_tb.sv').read_text().replace('samples!=224 || verified!=88','samples!=448 || verified!=200'))

 tb=(ROOT/'tests/nes-functional/h1_board_tb.sv').read_text()
 tb=replace(tb,"query(8'hf1,8'h34)","query(8'hf1,8'h39)")
 tb=replace(tb,'   rx[b]=spi_miso;#2000;SPI_SCK=0;', '   #2000;rx[b]=spi_miso;SPI_SCK=0;')
 tb=replace(tb,"  wr(24'h6000,2);while(dut.busy)#100;", "  rd(24'h6008,0,1);rd(24'h6009,8,1);rd(24'h6001,0,1);rd(24'h600a,0,1);\n  wr(24'h6000,2);while(dut.busy)#100;")
 tb=replace(tb,'for(integer seq=1;seq<=3;seq++)begin acquire(seq);consume(seq-1);end',"for(integer seq=1;seq<=3;seq++)begin acquire(seq);consume(seq-1);repeat(5)begin #1000000;query(8'hf2,3);query(8'hf5,0);end end")
 tasks="""
 reg [7:0] snapshot[0:10];
 task automatic snapshot_read;
  for(integer i=0;i<11;i++)begin
   SPI_SS=0;#2000;byte_io(8'hf5+i,ignored);byte_io(0,snapshot[i]);SPI_SS=1;#2000;
  end
 endtask
 task automatic snapshot_check(input [7:0] flags,input [7:0] errors,input [7:0] prod,input [23:0] addr);
  snapshot_read();
  if(snapshot[0]!==flags || snapshot[1]!==errors || snapshot[2]!==prod ||
     {snapshot[5],snapshot[4],snapshot[3]}!==addr ||
     {snapshot[9],snapshot[8],snapshot[7],snapshot[6]}==0)
   $fatal(1,"snapshot mismatch flags=%h errors=%h producer=%h addr=%h",snapshot[0],snapshot[1],snapshot[2],{snapshot[5],snapshot[4],snapshot[3]});
 endtask
"""
 tb=replace(tb,' initial begin\n  log=',tasks+'\n initial begin\n  log=')
 extra="""
  // Deliberately incomplete payload commit exercises the real stage error path.
  control(8'he8,8'ha5,8'h5a);while(dut.published<1)#100;acquire(1);rd(24'h408000,pattern[0],0);
  wr(24'h6000,2);query(8'hf2,7);
  snapshot_check(8'h87,8'h05,8'h10,24'h123456);
  wr(24'h6000,99);query(8'hf6,8'h05); // Preserve FIRST error, not later stage error8.
  pass("first_stage_fault_preserved_before_STOP");
  control(8'he9,8'ha5,8'h5a);query(8'hf5,0);
  control(8'he8,8'ha5,8'h5a);while(dut.published<1)#100;acquire(1);
  SNES_ADDR_IN=24'h408000;SNES_ROMSEL_IN=0;#20;SNES_READ_IN=0;#120;
  SNES_ADDR_IN=24'h408001;#100;SNES_READ_IN=1;#100;
  query(8'hf2,7);snapshot_check(8'h85,8'h10,0,24'h408001);
  pass("frontend_address_abort_snapshot");
  control(8'he9,8'ha5,8'h5a);query(8'hf5,0);
  SNES_ADDR_IN=24'h123456;SNES_ROMSEL_IN=1;
  control(8'he8,8'ha5,8'h5a);
  // Inject an otherwise unavailable queue response to test producer error routing.
  force dut.link.p_error=4;
  #1000;release dut.link.p_error;
  query(8'hf2,7);snapshot_check(8'hc3,0,8'h14,24'h123456);
  pass("injected_producer_response_error_snapshot");
  control(8'he9,8'ha5,8'h5a);query(8'hf5,0);query(8'hf2,2);
"""
 tb=replace(tb,'  $display("PASS NES H1 BOARD',extra+'\n  $display("PASS NES H1 BOARD')
 (out/'h1_board_tb.sv').write_text(tb)
 for label,tool,args in [('vlib','vlib',['work']),('compile','vlog',['-sv',*[n+'.sv' for n in files],'h1_spi_wave_tb.sv','h1_board_tb.sv']),('board','vsim',['-c','h1_board_tb','-do','onerror {quit -code 1}; run -all; quit -f']),('wave','vsim',['-c','h1_spi_wave_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (out/(label+'.log')).open('wb') as f:cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  assert cp.returncode==0,label
 log=(out/'board.log').read_text();assert 'PASS NES H1 BOARD checks=9 rombytes=65536 payloadbytes=8192' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 log=(out/'wave.log').read_text();assert 'PASS C SPI WAVE samples=448 verified=200 rows=1880' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 (out/'result.json').write_text(json.dumps({'candidate':'NES-H1-FAULT-039','passed':True,'samples':448,'verified_bits':200,'rows':1880,'waveform_sha256':sha(out/'waveform.txt'),'boundary_sha256':sha(out/'nes_h1_board_bus.sv')},indent=2))
 print('PASS039 SPI waveform and first-fault board9 cases')
if __name__=='__main__':main()
