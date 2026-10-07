# SPDX-License-Identifier: MIT
"""063 captured062 C samples through unchanged061 board pins, at nominal delays."""
from pathlib import Path
import argparse,json,os,re,shutil,sys,time
from nes_board_diagnostic import materialize
from nes_menu_diagnostic import source
from nes_spi_boot import ROOT,sha,put,run

def preflight():
 s=(ROOT/'tests/nes-functional/board_session_tb.sv').read_text()
 assert s.index('fxpak_nes_diagnostic_top dut(')<s.index('task automatic frame;')
 assert 'always #62.5 board8=~board8;' in s
 # Catch the byte-write versus word-read contract confusion before a long run.
 reader=(ROOT/'src/nes/nes_rom_physical.sv').read_text()
 assert "assign psram_bhe=1'b0;" in reader and "assign psram_ble=1'b0;" in reader
 assert "if(psram_bhe!==1'b0||psram_ble!==1'b0)" in s

def main():
 p=argparse.ArgumentParser()
 for n in ['out','host-run','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--case',choices=['fine_x','banks32'],default='fine_x');p.add_argument('--limit-frames',type=int,default=0)
 p.add_argument('--mask-link',type=int,choices=[0,1],default=1)
 p.add_argument('--park-legacy',type=int,choices=[0,1],default=0)
 a=p.parse_args();preflight();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 host=a.host_run.resolve();h=json.loads((host/'result.json').read_text());assert h['candidate']=='NES-BOARD-SESSION-063' and h['host_pass']
 for n,v in h['sources'].items():assert sha(host/n)==v,n
 assert (host/'nes_h1_stm32.c').read_text()==source()
 assert sha(host/(a.case+'.trace'))==h['traces'][a.case]
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);shutil.copy2(__file__,out/'executed-driver.py')
 files=materialize(out)
 # A force on an input net can collapse back onto the shared PLL net. Give
 # ONLY the reset-held H1 ports separate simulation expressions instead.
 boundary=out/'nes_h1_spi_boot.sv';production_boundary=boundary.read_text()
 shutil.copy2(boundary,out/'production-nes_h1_spi_boot.sv')
 old='.queue_clk(clock84),.host_clk(clock84),.reset(reset)'
 assert production_boundary.count(old)==1
 put(boundary,production_boundary.replace(old,'.queue_clk(clock84 && board_session_tb.link_clocks),.host_clk(clock84 && board_session_tb.link_clocks),.reset(reset)'))
 put(out/'pll_model.sv',"`timescale 1ns/1ps\nmodule gbc_bus_pll0(input areset,inclk0,output reg c0=0,output wire locked);reg enable=1;always begin wait(enable);#5.952381;if(enable||c0)c0=~c0;end assign locked=1'b0;endmodule\n")
 model=(ROOT/'tests/nes-functional/rom_boot_model.sv').read_text().replace('assign #25','assign #(70,70,35)').replace('<35.70','<350')
 put(out/'rom_boot_model.sv',model);shutil.copy2(ROOT/'tests/nes-functional/board_session_tb.sv',out/'board_session_tb.sv')
 files+=['pll_model.sv','rom_boot_model.sv','board_session_tb.sv']
 run([sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',out/'h1'],out,'fixture')
 for n in ['h1-pattern.hex','h1-program.hex']:shutil.copy2(out/'h1/build'/n,out/n)
 payload=(host/a.case/'mmc3.nes').read_bytes()[16:];total=len(payload);assert total==(81920 if a.case=='fine_x' else 98304)
 put(out/'expected.hex',''.join(f'{b:02x}\n' for b in payload));shutil.copy2(host/(a.case+'.trace'),out/'session.trace')
 for tool,args in [('vlib',['work']),('vlog',['-sv',*files])]:
  log=run([a.questa_bin/(tool+'.exe'),*args],out,tool);assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
 started=time.monotonic()
 log=run([a.questa_bin/'vsim.exe','-c','-voptargs=-O5','board_session_tb','+TOTAL='+str(total),'+LIMIT_FRAMES='+str(a.limit_frames),'+MASK_LINK='+str(a.mask_link),'+PARK_LEGACY='+str(a.park_legacy),
  '-do','onerror {quit -code 1}; run -all; quit -f'],out,'simulation',18000)
 assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
 marker=re.search(r'PASS SESSION (?:FULL|PREFIX)[^\r\n]*',log);assert marker
 r=dict(candidate='NES-BOARD-SESSION-063',case=a.case,full_session=not a.limit_frames,limit_frames=a.limit_frames,mask_link=a.mask_link,
  park_legacy=a.park_legacy,vopt='-O5',marker=marker[0],wall_seconds=time.monotonic()-started,sources={n:sha(out/n) for n in files},host_result_sha256=sha(host/'result.json'),
  trace_sha256=sha(out/'session.trace'),fixture_sha256=h['fixtures'][a.case],driver_sha256=sha(out/'executed-driver.py'),
  production_boundary_sha256=sha(out/'production-nes_h1_spi_boot.sv'),
  simulation_only_transform='separate reset-held H1 port clocks; optional legacy84MHz park after CF/F0/F1; loader SPI and PSRAM8MHz always free-running',
  memory_clock_mhz=8,SPI_delay_us=2,hardware_execution=False,analog_PLL=False,read_model_ns=70,write_pulse_min_ns=350)
 put(out/'result.json',json.dumps(r,indent=2)+'\n');print(marker[0],flush=True)

if __name__=='__main__':main()
