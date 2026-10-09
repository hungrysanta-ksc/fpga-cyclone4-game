# SPDX-License-Identifier: MIT
"""Actual128 boot/reader response ownership, cancel across all read phases."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_command128 import ROOT,sha,put,materialize
def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin','baseline']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists() and str(o).isascii();o.mkdir()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 materialize(o,a.baseline)
 f=ROOT/'tests/nes-functional/loader127_tb.sv';s=f.read_text()
 # Both80/96KiB geometries exercise the restructured loader state decoding.
 s=s.replace('   check_enable=0;repeat(5)@(negedge mem_clk);', '''   // Cancellation includes every SETUP/ACTIVE/HOLD/RELEASE/response position.
   for(integer phase=0;phase<24;phase++)begin
    wait(check_ready);@(negedge mem_clk);check_address=17;check_request=1;
    @(negedge mem_clk);check_request=0;repeat(phase)@(negedge mem_clk);
    check_enable=0;#0.001;
    ck(!check_response&&psram_we&&psram_oe,"CANCEL128 immediate response/pin release");
    repeat(6)@(negedge mem_clk);ck(!check_response,"CANCEL128 no stale response");
    check_enable=1;check_byte(17);
   end
   $display("PASS128 BOOT cancellations=24");
   check_enable=0;repeat(5)@(negedge mem_clk);''')
 s=s.replace('  $display("PASS127 LOADER', '''  // Reconstitute the legal READY state after the preceding real80/96KiB loads.
  // Only these misuse cases seed internal state; normal load/reads above do not.
  for(integer bad=0;bad<6;bad++)begin
   fresh();dut.loader.state=4;dut.loader.loaded_bytes=81920;dut.loader.chr32=0;
   check_enable=1;wait(check_ready);@(negedge mem_clk);before_writes=ram.writes;
   case(bad)
    0:load_begin=1;
    1:load_valid=1;
    2:load_end=1;
    3:start=1;
    4:begin check_address=17;check_request=1;@(negedge mem_clk);check_address=19;end
    5:begin check_enable=0;check_request=1;end
   endcase
   @(negedge mem_clk);load_begin=0;load_valid=0;load_end=0;start=0;check_request=0;
   #0.001;ck(check_fault&&!run_enable&&psram_we&&psram_oe,"OWN128 misuse no external owner");
   check_enable=0;
   // BEGIN misuse left the internal loader in RECEIVE, but the fault latch must
   // still suppress DATA. A second BEGIN here would mask a missing latch gate.
   load_valid=1;@(negedge mem_clk);load_valid=0;repeat(150)@(negedge mem_clk);
   ck(ram.writes==before_writes,"OWN128 direct post-fault DATA blocked");
   load_begin=1;@(negedge mem_clk);load_begin=0;
   repeat(3)begin load_valid=1;@(negedge mem_clk);end
   load_valid=0;repeat(150)@(negedge mem_clk);
   ck(ram.writes==before_writes&&!run_enable&&psram_we&&psram_oe,"OWN128 sticky latch blocks later writes");
  end
  $display("PASS128 OWN misuse_ready_fixtures=6");
  $display("PASS127 LOADER''')
 put(o/f.name,s)
 f=ROOT/'tests/nes-functional/rom_boot_model.sv';put(o/f.name,f.read_text().replace('assign #25','assign #70').replace('<35.70','<375.0'))
 for n in ['nes_command128.py','nes_command128_boot.py']:shutil.copy2(ROOT/'tools'/n,o/('executed-'+n))
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=log,stderr=subprocess.STDOUT,timeout=600)
  assert r.returncode==0,label
 run('vlib',['work'],'vlib');run('vlog',['-sv','nes_rom_loader.sv','nes_rom_boot.sv','nes_rom_physical.sv','rom_boot_model.sv','loader127_tb.sv'],'compile')
 run('vsim',['-c','loader127_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'boot')
 log=(o/'boot.log').read_text(errors='replace');assert 'PASS128 BOOT cancellations=24' in log and 'PASS128 OWN misuse_ready_fixtures=6' in log and 'PASS127 LOADER' in log and '** Fatal:' not in log
 original=(o/'nes_rom_boot.sv').read_text();needle='.load_valid(load_valid && !check_failed)';assert needle in original
 put(o/'negative-latch.sv',original.replace(needle,'.load_valid(load_valid)'))
 run('vlog',['-sv','negative-latch.sv'],'negative-latch-compile')
 run('vsim',['-c','loader127_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'negative-latch')
 log=(o/'negative-latch.log').read_text(errors='replace');assert '** Fatal: LOADER127 OWN128 direct post-fault DATA blocked' in log
 put(o/'boot128.json',json.dumps(dict(passed=True,cancellations=24,misuse_ready_fixtures=6,missing_latch_rejected=True,sources={p.name:sha(p) for p in o.iterdir() if p.suffix in ['.sv','.py']}),indent=2)+'\n');print('PASS128 boot ownership/cancellation + missing latch rejection')
if __name__=='__main__':main()
