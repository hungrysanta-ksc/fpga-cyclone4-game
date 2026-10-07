# SPDX-License-Identifier: MIT
"""070 frozen069 C full sessions through unchanged068 CF68 physical pins."""
from pathlib import Path
import argparse,json,os,re,shutil,sys,time
from nes_diag_safety import materialize
from nes_cf68_mcu import materialize as mcu_materialize
import tempfile
from nes_spi_boot import ROOT,sha,put,run

def preflight():
 s=(ROOT/'tests/nes-functional/cf68_session_tb.sv').read_text()
 assert 'module cf68_session_tb;' in s
 assert s.index('fxpak_nes_diagnostic_top dut(')<s.index('task automatic frame;')
 assert 'always #62.5 board8=~board8;' in s
 # Catch the byte-write versus word-read contract confusion before a long run.
 reader=(ROOT/'src/nes/diagnostic/nes_diag_safe_rom_physical.sv').read_text()
 assert "assign psram_bhe=1'b0;" in reader and "assign psram_ble=1'b0;" in reader
 assert "if(psram_bhe!==1'b0||psram_ble!==1'b0)" in s

def main():
 p=argparse.ArgumentParser()
 for n in ['out','host-run','questa-bin','fpga-evidence']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--case',choices=['fine_x','banks32'],default='fine_x');p.add_argument('--limit-frames',type=int,default=0)
 p.add_argument('--mask-link',type=int,choices=[0,1],default=1)
 p.add_argument('--park-legacy',type=int,choices=[0,1],default=0)
 p.add_argument('--mutation',choices=['response'])
 a=p.parse_args();preflight();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 host=a.host_run.resolve();h=json.loads((host/'result.json').read_text());assert h['candidate']=='NES-CF68-MCU-069' and h['session']
 for n,v in h['files'].items():assert sha(host/n)==v,n
 with tempfile.TemporaryDirectory() as d:
  mcu_materialize(Path(d));assert (host/'nes_h1_stm32.c').read_bytes()==(Path(d)/'nes_h1_stm32.c').read_bytes()
 mcu_meta=json.loads((ROOT/'analysis/cf68-mcu-verification.json').read_text())
 assert sha(host.parent/'manifest.json')==mcu_meta['manifest_sha256']
 fpga=a.fpga_evidence.resolve();meta=json.loads((ROOT/'analysis/diag-safety-verification.json').read_text())
 assert sha(fpga/'manifest.json')==meta['manifest_sha256']
 fit=json.loads((fpga/'fit/result.json').read_text())
 assert sha(host/(a.case+'.trace'))==h['traces'][a.case]
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);shutil.copy2(__file__,out/'executed-driver.py')
 files=materialize(out)
 production={n:sha(out/n) for n in files}
 for n,hsh in production.items():assert fit['sources'][n]==hsh,n
 shutil.copy2(ROOT/'tools/nes_diag_safety.py',out/'executed-materializer.py')
 shutil.copy2(ROOT/'tests/nes-functional/cf68_session_tb.sv',out/'executed-testbench.sv')
 # A force on an input net can collapse back onto the shared PLL net. Give
 # ONLY the reset-held H1 ports separate simulation expressions instead.
 boundary=out/'nes_h1_spi_boot.sv';production_boundary=boundary.read_text()
 shutil.copy2(boundary,out/'production-nes_h1_spi_boot.sv')
 old='.queue_clk(clock84),.host_clk(clock84),.reset(reset)'
 assert production_boundary.count(old)==1
 put(boundary,production_boundary.replace(old,'.queue_clk(clock84 && cf68_session_tb.link_clocks),.host_clk(clock84 && cf68_session_tb.link_clocks),.reset(reset)'))
 put(out/'pll_model.sv',"`timescale 1ns/1ps\nmodule gbc_bus_pll0(input areset,inclk0,output reg c0=0,output wire locked);reg enable=1;always begin wait(enable);#5.952381;if(enable||c0)c0=~c0;end assign locked=1'b0;endmodule\n")
 model=(ROOT/'tests/nes-functional/rom_boot_model.sv').read_text().replace('assign #25','assign #(70,70,35)').replace('<35.70','<350')
 put(out/'rom_boot_model.sv',model);shutil.copy2(ROOT/'tests/nes-functional/cf68_session_tb.sv',out/'cf68_session_tb.sv')
 files+=['pll_model.sv','rom_boot_model.sv','cf68_session_tb.sv']
 run([sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',out/'h1'],out,'fixture')
 for n in ['h1-pattern.hex','h1-program.hex']:shutil.copy2(out/'h1/build'/n,out/n)
 assert sha(host/a.case/'mmc3.nes')==h['fixtures'][a.case]
 payload=(host/a.case/'mmc3.nes').read_bytes()[16:];total=len(payload);assert total==(81920 if a.case=='fine_x' else 98304)
 put(out/'expected.hex',''.join(f'{b:02x}\n' for b in payload));shutil.copy2(host/(a.case+'.trace'),out/'session.trace')
 for tool,args in [('vlib',['work']),('vlog',['-sv',*files])]:
  log=run([a.questa_bin/(tool+'.exe'),*args],out,tool);assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
 if a.mutation:
  trace=out/'session.trace';rows=trace.read_text().splitlines();fields=rows[0].split()
  # Flip one C-consumed CF response bit; comparison must fail at that sample.
  fields[4]=f'{int(fields[4],16)^(1<<55):016x}';rows[0]=' '.join(fields)
  put(trace,'\n'.join(rows)+'\n')
 started=time.monotonic()
 try:
  log=run([a.questa_bin/'vsim.exe','-c','-voptargs=-O5','cf68_session_tb','+TOTAL='+str(total),'+LIMIT_FRAMES='+str(a.limit_frames),'+MASK_LINK='+str(a.mask_link),'+PARK_LEGACY='+str(a.park_legacy),
  '-do','onerror {quit -code 1}; run -all; quit -f'],out,'simulation',18000)
 except RuntimeError:
  if not a.mutation:raise
  log=(out/'simulation.log').read_text(errors='replace')
 if a.mutation:
  expected='070 MCU sample mismatch frame0 opcf bit8'
  assert '** Fatal:' in log and expected in log,log[-2000:]
  put(out/'result.json',json.dumps(dict(candidate='NES-CF68-SESSION-070',mutation=a.mutation,expected_failure=True,assertion=expected,driver_sha256=sha(out/'executed-driver.py'),production_sources=production),indent=2)+'\n')
  print('EXPECTED FAILURE '+expected,flush=True);return
 assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
 marker=re.search(r'PASS SESSION (?:FULL|PREFIX)[^\r\n]*',log);assert marker
 r=dict(production_sources=production,fpga_manifest_sha256=sha(fpga/'manifest.json'),mcu_manifest_sha256=sha(host.parent/'manifest.json'),startup_ready_wait=True,fpga_candidate='NES-DIAG-SAFETY-068',mcu_candidate='NES-CF68-MCU-069',candidate='NES-CF68-SESSION-070',case=a.case,full_session=not a.limit_frames,limit_frames=a.limit_frames,mask_link=a.mask_link,
  park_legacy=a.park_legacy,vopt='-O5',marker=marker[0],wall_seconds=time.monotonic()-started,sources={n:sha(out/n) for n in files},host_result_sha256=sha(host/'result.json'),
  trace_sha256=sha(out/'session.trace'),fixture_sha256=h['fixtures'][a.case],driver_sha256=sha(out/'executed-driver.py'),
  production_boundary_sha256=sha(out/'production-nes_h1_spi_boot.sv'),
  simulation_only_transform='separate reset-held H1 port clocks; optional legacy84MHz park after CF68/F0/F1; loader SPI and PSRAM8MHz always free-running',
  memory_clock_mhz=8,SPI_delay_us=2,hardware_execution=False,analog_PLL=False,read_model_ns=70,write_pulse_min_ns=350)
 put(out/'result.json',json.dumps(r,indent=2)+'\n');print(marker[0],flush=True)

if __name__=='__main__':main()
