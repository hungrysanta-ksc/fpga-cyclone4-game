# SPDX-License-Identifier: MIT
#053 actual ROM bytes reach uninitialized pin RAM only through loader writes.
from pathlib import Path
import sys,json,shutil
import nes_rom_physical as physical
import nes_ncr1_live as live
import nes_ncr1_live_resource as resource
ROOT=live.ROOT
prepare_physical=physical.prepare
CONTROLS='wire load_ready,loaded,boot_fault;wire [3:0] boot_error;wire [16:0] loaded_bytes;'
NAMES=['load_begin','load_chr32','load_valid','load_end','start','stop','load_data','load_ready','loaded','run_enable','boot_fault','boot_error','loaded_bytes','rom_request','rom_address','rom_ready','rom_response','rom_error','rom_response_address','rom_data','psram_address','psram_1ce','psram_2ce','psram_oe','psram_we','psram_bhe','psram_ble','psram_data']
def bridge():return 'nes_rom_boot physical(.clk(clk),.mem_clk(mem_clk),.reset(boot_reset),.read_reset(reset),\n'+',\n'.join('.'+n+'('+n+')' for n in NAMES)+');\n'
def prepare(out):
 sources=prepare_physical(out)
 for n in ('nes_rom_loader.sv','nes_rom_boot.sv'):shutil.copy2(ROOT/'src/nes'/n,out/n)
 shutil.copy2(ROOT/'tests/nes-functional/rom_boot_model.sv',out/'rom_backend_model.sv')
 p=out/'ncr1_live_tb.sv';s=p.read_text()
 s=s.replace('reg queue_clk=0,host_clk=0,reset_request=1;','reg queue_clk=0,host_clk=0,boot_reset=1;\nwire run_enable;wire reset_request=boot_reset || !run_enable;')
 s=s.replace('#20000;reset_request=0;','#20000;boot_reset=0;')
 s=s.replace('rom_physical_model #(.FIXTURE(1)) memory(.*);','rom_boot_model memory(.reset(boot_reset),.psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),.psram_oe(psram_oe),.psram_we(psram_we),.psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(psram_data));')
 needle='nes_rom_boot physical(';assert s.count(needle)==1
 s=s.replace(needle,CONTROLS+'\nreg load_begin=0,load_chr32=0,load_valid=0,load_end=0,start=0,stop=0;reg [7:0] load_data=0;\n'+needle)
 s=s.replace(' integer physical_requests=0,',"""
 always @(posedge mem_clk)if(!boot_reset && boot_fault)$fatal(1,"BOOT fault=%0d bytes=%0d",boot_error,loaded_bytes);
 initial begin
  integer total;
  wait(!boot_reset);repeat(4)@(negedge mem_clk);load_chr32=chr_32k;load_begin=1;
  @(negedge mem_clk);load_begin=0;total=65536+(chr_32k?32768:16384);
  for(integer b=0;b<total;b++)begin
   while(!load_ready)@(negedge mem_clk);
   load_data=b<65536?prg[b]:chr[b-65536];load_valid=1;
   @(negedge mem_clk);load_valid=0;
  end
  while(loaded_bytes!=total)@(negedge mem_clk);
  if(loaded || run_enable || memory.writes!=total)$fatal(1,"BOOT premature completion/count");
  for(integer b=0;b<65536;b++)if(memory.prg[b]!==prg[b])$fatal(1,"BOOT PRG mismatch %0d",b);
  for(integer b=0;b<total-65536;b++)if(memory.chr[b]!==chr[b])$fatal(1,"BOOT CHR mismatch %0d",b);
  load_end=1;@(negedge mem_clk);load_end=0;
  if(!loaded || run_enable)$fatal(1,"BOOT completion handshake");
  start=1;@(negedge mem_clk);start=0;
  $display("BOOT bytes=%0d pin_writes=%0d run=%0d",loaded_bytes,memory.writes,run_enable);
 end
 integer physical_requests=0,""")
 live.put(p,s)
 for n in ('nes_rom_loader.sv','nes_rom_boot.sv','rom_backend_model.sv','ncr1_live_tb.sv'):sources[n]=live.sha(out/n)
 return sources

def main():
 out=Path(sys.argv[sys.argv.index('--out')+1]);live.FILES.extend(['nes_rom_loader','nes_rom_boot']);physical.prepare=prepare;physical.bridge=bridge
 old_put=resource.put
 def boot_put(p,s):
  if p.name=='nes_live_joint.sv':
   s=s.replace('input wire ext_mem_clk,','input wire ext_load_begin,ext_load_chr32,ext_load_valid,ext_load_end,ext_start,ext_stop,\ninput wire [7:0] ext_load_data,\noutput wire out_load_ready,out_loaded,out_run_enable,out_boot_fault,\noutput wire [3:0] out_boot_error,\noutput wire [16:0] out_loaded_bytes,\ninput wire ext_mem_clk,')
   s=s.replace('input wire [15:0] ext_psram_data,','inout wire [15:0] ext_psram_data,')
   s=s.replace('reset_request=ext_reset;', 'boot_reset=ext_reset;wire run_enable;wire reset_request=boot_reset || !run_enable;')
   s=s.replace('wire [15:0] psram_data;','').replace('assign psram_data=ext_psram_data;','')
   s=s.replace('.psram_data(psram_data)', '.psram_data(ext_psram_data)')
   s=s.replace('wire mem_clk=ext_mem_clk;',CONTROLS+'\n'+'\n'.join('wire '+n+'=ext_'+n+';' for n in ['load_begin','load_chr32','load_valid','load_end','start','stop'])+'\nwire [7:0] load_data=ext_load_data;\n'+'\n'.join('assign out_'+n+'='+n+';' for n in ['load_ready','loaded','run_enable','boot_fault','boot_error','loaded_bytes'])+'\nwire mem_clk=ext_mem_clk;')
  if p.name=='live.qsf':
   s='\n'.join(x for x in s.splitlines() if not x.endswith('VIRTUAL_PIN ON -to ext_psram_data'))+'\n'
   s+='\n'.join('set_instance_assignment -name VIRTUAL_PIN ON -to '+n for n in ['ext_load_begin','ext_load_chr32','ext_load_valid','ext_load_end','ext_start','ext_stop','ext_load_data','out_load_ready','out_loaded','out_run_enable','out_boot_fault','out_boot_error','out_loaded_bytes'])+'\n'
  old_put(p,s)
 resource.put=boot_put;physical.main()
 p=out/'result.json';m=json.loads(p.read_text());m.update(candidate='NES-R1-ROM-BOOT-053',driver_sha256=live.sha(Path(__file__)),scope='Diagnostic ROM stream loader and exclusive load/run PSRAM pins; uninitialized pin model populated only by writes. Actual NES core after loading. No MCU SPI decoder, physical clock/board top or hardware image.')
 live.put(p,json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
