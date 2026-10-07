# SPDX-License-Identifier: MIT
"""Replay062 candidate-aware C GPIO through061 physical top with a conservative pin model."""
from pathlib import Path
import argparse, json, os, re, shutil, sys
from nes_board_diagnostic import materialize
from nes_spi_boot import ROOT, run, sha, put
from nes_rom_geometry import replace
from nes_menu_diagnostic import source


def preflight():
    s=testbench()
    assert s.index('wire [3:0] boot_error,')<s.index('task automatic command(')
    assert s.index('fxpak_nes_diagnostic_top dut(')<s.index('task automatic prepare;')


def testbench():
    s=(ROOT/'tests/nes-functional/sd_readback_wave_tb.sv').read_text()
    s=replace(s,'reg nes_clk=0,clock84=0,nes_reset=1,locked=0,read_reset=0;',
      'reg nes_clk=0,clock_enable=1,nes_reset=1,locked=0,read_reset=0; wire clock84;')
    s=replace(s,'always #23.280423 nes_clk=~nes_clk;', 'always #62.5 if(clock_enable)nes_clk=~nes_clk;')
    s=replace(s,'always #5.952381 clock84=~clock84;', 'assign clock84=dut.clock84;')
    s=replace(s,"nes_h1_spi_boot dut(.*,.SNES_ADDR_IN(24'd0),.SNES_READ_IN(1'b1),.SNES_WRITE_IN(1'b1),.SNES_ROMSEL_IN(1'b1),.snes_data_in(8'd0));", '''
 wire [7:0] snes_bus,ram_bus;wire mcu_ready,rom_zz,ram_oe,ram_we,snes_irq;
 fxpak_nes_diagnostic_top dut(.CLKIN(nes_clk),.SNES_CIC_CLK(1'b0),
 .SNES_ADDR_IN(24'd0),.SNES_READ_IN(1'b1),.SNES_WRITE_IN(1'b1),.SNES_ROMSEL_IN(1'b1),
 .SNES_CPU_CLK_IN(1'b0),.SNES_REFRESH(1'b0),.SNES_SYSCLK(1'b0),.SNES_PA_IN(8'd0),.SNES_PARD_IN(1'b1),.SNES_PAWR_IN(1'b1),
 .SNES_DATA(snes_bus),.SNES_IRQ(snes_irq),.SNES_DATABUS_OE(SNES_DATABUS_OE),.SNES_DATABUS_DIR(SNES_DATABUS_DIR),
 .SPI_MOSI(SPI_MOSI),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MISO(spi_miso),.MCU_RDY(mcu_ready),
 .ROM_ADDR(psram_address),.ROM_1CE(psram_1ce),.ROM_2CE(psram_2ce),.ROM_ZZ(rom_zz),
 .ROM_OE(psram_oe),.ROM_WE(psram_we),.ROM_BHE(psram_bhe),.ROM_BLE(psram_ble),.ROM_DATA(psram_data),
 .RAM_ADDR(),.RAM_OE(ram_oe),.RAM_WE(ram_we),.RAM_DATA(ram_bus),.DAC_MCLK(),.DAC_LRCK(),.DAC_SDOUT());
 assign load_ready=dut.boundary.load_ready;assign loaded=dut.boundary.loaded;
 assign loaded_bytes=dut.boundary.loaded_bytes;assign nes_run_enable=dut.boundary.nes_run_enable;
 assign spi_fault=dut.boundary.spi_fault;assign spi_error=dut.boundary.spi_error;
 assign boot_fault=dut.boundary.boot_fault;assign boot_error=dut.boundary.boot_error;
 assign run_active=dut.run_active;assign spi_drive=dut.spi_drive;
 initial force dut.locked=locked;
''')
    s=s.replace('dut.loader.', 'dut.boundary.loader.')
    s=s.replace('@(negedge clock84)', '@(negedge nes_clk)')
    s=replace(s,"#500;locked=1;nes_reset=0;#500;", "#500;locked=1;nes_reset=0;#2000;\n  legacy_query(8'hcf,8'h61);")
    s=replace(s,'#100;locked=1;SPI_SS=1;#1000;', '#100;locked=1;SPI_SS=1;#2000;')
    insertion='''
  // Parser refuses START even if its verification bit is fault-injected high.
  force dut.boundary.loader.control.verified=1'b1;
  command(8'h63,24'd0,8'd0);
  release dut.boundary.loader.control.verified;
  if(!spi_fault||spi_error!=8||nes_run_enable)$fatal(1,"061 START rejection missing");
  locked=0;#100;locked=1;#2000;
  // A control-wire fault cannot bypass the second, hardwired barrier.
  force dut.boundary.loader.boot.loader.state=3'd4;
  #1;release dut.boundary.loader.boot.loader.state;
  force dut.boundary.loader.start=1'b1;
  repeat(4)@(negedge nes_clk);
  if(dut.boundary.loader.boot.start!==1'b0||nes_run_enable)$fatal(1,"061 START disconnect missing");
  release dut.boundary.loader.start;
  locked=0;#100;locked=1;#2000;
  // Abort a write on raw lock loss with both clocks stopped. This intentionally
  // truncates the write and invalidates the image; it is NOT a valid RAM write.
  force dut.boundary.loader.boot.load_begin=tb_begin;
  force dut.boundary.loader.boot.load_valid=tb_valid;
  force dut.boundary.loader.boot.load_data=8'ha7;
  @(negedge nes_clk);tb_begin=1;@(negedge nes_clk);tb_begin=0;tb_valid=1;
  @(negedge psram_we);#100;clock_enable=0;dut.pll.enable=0;locked=0;#1;
  if(!psram_1ce||!psram_2ce||!psram_we||!psram_oe||!psram_bhe||!psram_ble||
     psram_data!==16'hzzzz||mcu_ready||spi_drive||!SNES_DATABUS_OE||snes_bus!==8'hzz)
     $fatal(1,"061 stopped-clock reset pins");
  #1000;tb_valid=0;release dut.boundary.loader.boot.load_begin;
  release dut.boundary.loader.boot.load_valid;release dut.boundary.loader.boot.load_data;
  clock_enable=1;dut.pll.enable=1;locked=1;#2000;
  if(loaded||loaded_bytes||spi_fault||boot_fault||!mcu_ready||!rom_zz||!ram_oe||!ram_we||ram_bus!==8'hzz||snes_irq)
     $fatal(1,"061 recovery/peripheral idle");
  legacy_query(8'hcf,8'h61);legacy_query(8'hf0,8'ha5);legacy_query(8'hf1,8'h44);
'''
    s=replace(s,'  $display("PASS SD GPIO',insertion+'  $display("PASS BOARD GPIO')
    s=s.replace('pll_loss=1 no_RUN=1','pll_loss_idle_and_write=1 start_barriers=2 no_RUN=1')
    s=s.replace('check_mode?4:6','check_mode?8:11')
    s=replace(s,' initial begin #600000000.0;', ' initial begin #900000000.0;')
    task='''
 function automatic [7:0] crc_byte(input [7:0] p,input [7:0] v);
  reg [7:0] c;begin c=p^v;repeat(8)c=c[7]?(c<<1)^8'h07:c<<1;crc_byte=c;end
 endfunction
 task automatic command(input [7:0] op,input [23:0] address,input [7:0] arg);
  reg [7:0] tx[8];reg [7:0] c;
  tx[0]=op;tx[1]=address[23:16];tx[2]=address[15:8];tx[3]=address[7:0];tx[4]=arg;tx[5]=~arg;c=0;
  for(integer j=0;j<6;j++)c=crc_byte(c,tx[j]);tx[6]=c;tx[7]=8'ha5;
  SPI_SCK=0;SPI_SS=0;#2000;
  for(integer j=0;j<64;j++)begin SPI_MOSI=tx[j/8][7-j%8];#2000;SPI_SCK=1;#2000;SPI_SCK=0;end
  #2000;SPI_SS=1;#2000;
 endtask
'''
    s=replace(s,' task automatic prepare;',task+' task automatic prepare;')
    return s


def main():
    p=argparse.ArgumentParser()
    for n in ['out','host-run','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--mutation',choices=['fast-memory','allow-start','connected-start'])
    a=p.parse_args();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
    host=a.host_run.resolve();r=json.loads((host/'result.json').read_text());assert r['host_model_pass'] and r['candidate']=='NES-MENU-DIAGNOSTIC-062'
    assert (host/'nes_h1_stm32.c').read_text()==source()
    for n,h in r['files'].items():assert sha(host/n)==h,n
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);shutil.copy2(__file__,out/'executed-driver.py')
    shutil.copy2(ROOT/'tools/nes_board_diagnostic.py',out/'executed-materializer.py')
    files=materialize(out)
    if a.mutation=='fast-memory':
        path=out/'nes_h1_spi_boot.sv';put(path,replace(path.read_text(),'.mem_clk(nes_clk)', '.mem_clk(clock84)'))
    if a.mutation=='allow-start':
        path=out/'nes_rom_spi.sv';put(path,replace(path.read_text(),"8'h63:fail(8); // 061 diagnostic never permits RUN", "8'h63:if(!verified)fail(8);else start<=1;"))
    if a.mutation=='connected-start':
        path=out/'nes_spi_boot.sv';put(path,replace(path.read_text(),".start(1'b0)",'.start(start)'))
    # This stub checks digital shell wiring/reset only, not analog PLL behavior.
    put(out/'pll_model.sv',"`timescale 1ns/1ps\nmodule gbc_bus_pll0(input areset,inclk0,output reg c0=0,output wire locked);reg enable=1;always #5.952381 if(enable)c0=~c0;assign locked=1'b0;endmodule\n")
    model=(ROOT/'tests/nes-functional/rom_boot_model.sv').read_text().replace('assign #25','assign #(70,70,35)').replace('<35.70','<350')
    put(out/'rom_boot_model.sv',model);put(out/'sd_readback_wave_tb.sv',testbench())
    files+=['pll_model.sv','rom_boot_model.sv','sd_readback_wave_tb.sv']
    run([sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',out/'h1'],out,'fixture')
    for tool,args in [('vlib',['work']),('vlog',['-sv',*files])]:
        log=run([a.questa_bin/(tool+'.exe'),*args],out,tool);assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
    cases=[];rom=(host/'banks32/mmc3.nes').read_bytes();assert sha(host/'banks32/mmc3.nes')==r['fixtures']['banks32']
    for mode,wave,key in [('load','load-waveform.txt','load_waveform_sha256'),('check','waveform.txt','waveform_sha256')]:
        c=out/mode;c.mkdir();assert sha(host/wave)==r[key];shutil.copy2(host/wave,c/'waveform.txt')
        for n in ['h1-pattern.hex','h1-program.hex']:shutil.copy2(out/'h1/build'/n,c/n)
        put(c/'expected.hex',''.join(f'{b:02x}\n' for b in rom[16:]))
        put(c/'modelsim.ini','[Library]\nwork = '+(out/'work').as_posix()+'\nothers = '+(a.questa_bin.parent/'modelsim.ini').as_posix()+'\n')
        try:
            log=run([a.questa_bin/'vsim.exe','-c','-ini','modelsim.ini','sd_readback_wave_tb','+CHECK='+str(int(mode=='check')),'-do','onerror {quit -code 1}; run -all; quit -f'],c,'simulation',1800)
        except RuntimeError:
            if not a.mutation:raise
            log=(c/'simulation.log').read_text(errors='replace')
        if a.mutation:
            # Questa may finish a $fatal with exit0 under run-all/quit-f.
            # Require the causal assertion in the raw transcript either way.
            expected={'fast-memory':'WRITE pulse too short','allow-start':'061 START rejection missing',
                      'connected-start':'Unexpected RUN'}[a.mutation]
            assert '** Fatal:' in log and expected in log,log[-2000:]
            put(out/'result.json',json.dumps(dict(candidate='NES-MENU-DIAGNOSTIC-062',mutation=a.mutation,
              expected_failure=True,assertion=expected,sources={n:sha(out/n) for n in files},
              driver_sha256=sha(out/'executed-driver.py'),materializer_sha256=sha(out/'executed-materializer.py')),indent=2)+'\n')
            print('EXPECTED FAILURE '+a.mutation+': '+expected,flush=True);return
        assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
        marker=re.search(r'PASS BOARD GPIO[^\r\n]*',log);assert marker
        cases.append(dict(mode=mode,marker=marker[0],waveform_sha256=sha(c/'waveform.txt')));print(marker[0],flush=True)
    assert not a.mutation,'Mutation unexpectedly passed'
    put(out/'result.json',json.dumps(dict(candidate='NES-MENU-DIAGNOSTIC-062',cases=cases,
      read_model_ns=70,write_pulse_min_ns=350,output_disable_model_ns=35,
      sources={n:sha(out/n) for n in files},host_result_sha256=sha(host/'result.json'),
      analog_pll=False,hardware_execution=False,driver_sha256=sha(out/'executed-driver.py'),
      materializer_sha256=sha(out/'executed-materializer.py')),indent=2)+'\n')

if __name__=='__main__':main()
