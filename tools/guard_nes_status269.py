# SPDX-License-Identifier: MIT
"""Actual output owner: reset, short STOP, stale ACK and invalidation rearm."""
from pathlib import Path
import argparse,json,os,re,shutil
from nes_delta231 import BASE,sha
from nes_joint269 import sources
from probe_nes_joint266 import run
from map_nes_joint269 import rom_patch,top_patch
from nes_delta231 import once

TB=r'''
`timescale 1ns/1ps
module status269_tb;
 reg host_clk=0,nes_clk=0;always #5.952381 host_clk=~host_clk;always #22.727 nes_clk=~nes_clk;
 reg reset=1,cancel=0,read_n=1,write_n=1;reg [23:0] address=0;reg [7:0] data_in=0;
 wire [7:0] data_out;wire bus_valid,fault;integer checks=0;
 nes_output260 dut(@PORTS@);
 task read_status(input [7:0] expected);
 begin address=24'h006001;read_n=0;#100;if(!bus_valid||data_out!==expected)$fatal(1,"status got %h expected %h",data_out,expected);read_n=1;#100;checks++;end endtask
 task writebyte(input [23:0] a,input [7:0] v);
 begin @(negedge host_clk);address=a;data_in=v;write_n=0;repeat(12)@(negedge host_clk);write_n=1;repeat(12)@(negedge host_clk);end endtask
 task blocked;
 begin
  address=24'h006000;read_n=0;#100;if(bus_valid)$fatal(1,"dirty ordinary read");read_n=1;
  writebyte(24'h00601c,8'ha5);writebyte(24'h006050,8'ha5);writebyte(24'h006058,8'h5a);
  if(fault||dut.queue.retired||dut.final_send||dut.map_receipt)$fatal(1,"stale completion consumed");checks++;
 end endtask
 initial begin
  #100;read_status(8'hc0);reset=0;repeat(30)@(negedge host_clk);
  read_status(8'h40);blocked();writebyte(24'h006006,8'ha4);read_status(8'h40);
  writebyte(24'h006006,8'ha5);read_status(0);
  // Short pulse between host rising edges must not disappear.
  @(negedge host_clk);#1;cancel=1;#1;cancel=0;repeat(20)@(negedge host_clk);
  read_status(8'h40);blocked();writebyte(24'h006006,8'ha5);read_status(0);
  cancel=1;read_status(8'hc0);writebyte(24'h006006,8'ha5);read_status(8'hc0);
  cancel=0;repeat(30)@(negedge host_clk);read_status(8'h40);
  writebyte(24'h006006,8'ha5);read_status(0);
  $display("PASS STATUS269 checks=%0d short_STOP/stale_ACK/rearm",checks);$finish;
 end
 initial begin #100000;$fatal(1,"status timeout");end
endmodule
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--cpu',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
 src=sources();s=src['nes_mux260.sv'];header=s[s.index('(\n input wire'):s.index('\n);')];direction=None;ports=[]
 named={'nes_clk','host_clk','reset','cancel','address','read_n','write_n','data_in','data_out','bus_valid','fault'}
 for item in header[1:].split(','):
  if 'input wire' in item:direction='in'
  elif 'output wire' in item:direction='out'
  name=re.findall(r'\b\w+\b',item)[-1]
  if name in named:ports.append(f'.{name}({name})')
  elif direction=='in':ports.append(f".{name}({'1' if name=='SPI_SS' else chr(39)+'0'})")
 names=['nes_mux260.sv','nes_queue260.sv','nes_tile_producer260.sv','nes_bulk_aperture188.sv','nes_domain_reset124.sv','nes_native_mailbox206.sv']
 for n in names:
  text=src[n] if n in src else (BASE/'probes/nes-joint268/joint-reuse01'/n).read_text()
  (d/n).write_text(text,encoding='utf-8',newline='\n')
 old=BASE/'probes/nes-joint268/board01'
 for n,s in rom_patch({n:(old/n).read_text() for n in ['nes_sink_bus165.sv','nes_sink_bridge165.sv']}).items():
  names.append(n);(d/n).write_text(s,encoding='utf-8',newline='\n')
 cpu=json.loads((a.cpu/'result.json').read_text());image=(a.cpu/'ordinary.sfc').read_bytes();assert cpu['passed']
 (d/'sink-program.hex').write_text((image[:0xfc0]+image[0x7fc0:0x8000]).hex(' ')+'\n')
 top=top_patch((old/'fxpak_nes_screen137_top.sv').read_text());mux=top[top.index(' wire stop_read269='):top.index(' assign SNES_DATABUS_DIR=')]
 extra='''
 reg power_reset=0,host_locked=1;wire core_reset=reset||cancel;
 wire [23:0] SNES_ADDR_IN=address;wire SNES_READ_IN=read_n,SNES_WRITE_IN=write_n;
 wire SNES_ROMSEL_IN=!address[15];wire [7:0] sink_data204;wire [7:0] bus_data=data_out;
 wire sink_oe204,sink_dir204;wire bus_oe_n=!bus_valid;wire bus_dir=bus_valid;
 wire consumer_oe,consumer_dir;wire [7:0] consumer_data;wire pad_commit;wire [15:0] pad_buttons;
 nes_sink_bridge165 #(.KEEP_ROM(1)) rom(.clk(host_clk),.raw_reset(core_reset),.active(!core_reset),.stop(cancel),
 .SPI_SS(1'b1),.SPI_SCK(1'b0),.SPI_MOSI(1'b0),.spi_selected(),.spi_miso(),.fault(),
 .address(address),.read_n(read_n),.write_n(write_n),.romsel_n(SNES_ROMSEL_IN),.data_in(data_in),
 .data_out(sink_data204),.oe_n(sink_oe204),.dir(sink_dir204),.pad_commit(pad_commit),.pad_buttons(pad_buttons));
'''+mux+'''
 task read_rom(input [23:0] a,input [7:0] expected);
 begin address=a;read_n=0;#200;if(consumer_oe||!consumer_dir||consumer_data!==expected)$fatal(1,"STOP program ROM %h",a);
 host_locked=0;#1;if(!consumer_oe)$fatal(1,"clock loss did not gate IO");host_locked=1;
 power_reset=1;#1;if(!consumer_oe)$fatal(1,"power reset did not gate IO");power_reset=0;
 read_n=1;#100;checks++;end endtask
'''
 text=TB.replace('@PORTS@',','.join(ports));text=once(text,' task read_status',extra+'\n task read_status')
 text=once(text,'if(!bus_valid||data_out!==expected)', 'if(consumer_oe||!consumer_dir||consumer_data!==expected||!bus_valid||data_out!==expected)')
 text=once(text,'#100;read_status(8\'hc0);', f"#100;read_rom(24'h008000,8'h78);read_rom(24'h{cpu['zero_source']:06x},0);read_status(8'hc0);")
 text=once(text,'cancel=1;read_status(8\'hc0);', "cancel=1;read_rom(24'h008000,8'h78);read_rom(24'h00fffc,0);read_status(8'hc0);")
 text=once(text,"writebyte(24'h006006,8'ha5);read_status(8'hc0);", """writebyte(24'h006006,8'ha5);read_status(8'hc0);
  writebyte(24'h006002,8'hab);writebyte(24'h006003,8'hcd);
  if(pad_commit||pad_buttons!=0)$fatal(1,"STOP pad write escaped reset");""")
 (d/'status269_tb.sv').write_text(text,encoding='utf-8',newline='\n');shutil.copyfile(__file__,d/Path(__file__).name)
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*names,'status269_tb.sv'],d,'vlog')
 log=run(a.questa_bin/'vsim.exe',['-c','work.status269_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim');assert 'PASS STATUS269' in log
 result=dict(passed=True,scope=__doc__,rtl_hashes={n:sha(d/n) for n in names},CPU_ROM_sha256=sha(a.cpu/'ordinary.sfc'),top_mux=mux,full_board_functional=False,log=[l for l in log.splitlines() if 'PASS ' in l]);(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['log'])


if __name__=='__main__':main()
