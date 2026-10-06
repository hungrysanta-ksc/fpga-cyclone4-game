# SPDX-License-Identifier: MIT
'052 actual core ->051 early reads -> bundled CDC and read-only PSRAM pins.'
from pathlib import Path
import json,sys,shutil,re
import nes_rom_early as early
import nes_ncr1_live as live
import nes_ncr1_live_resource as resource
ROOT=live.ROOT
prepare_early=early.prepare
read_clocks=3
phase_ps=0
PINS='wire [21:0] psram_address;wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;wire [15:0] psram_data;'
def bridge():
 return 'nes_rom_physical #(.READ_CYCLES('+str(read_clocks)+')) physical(.clk(clk),.mem_clk(mem_clk),.reset(reset),\n'+',\n'.join('.'+n+'('+n+')' for n in ['rom_request','rom_address','rom_ready','rom_response','rom_error','rom_response_address','rom_data','psram_address','psram_1ce','psram_2ce','psram_oe','psram_we','psram_bhe','psram_ble','psram_data'])+');\n'
def prepare(out):
 sources=prepare_early(out)
 for n in ('nes_rom_physical.sv',):shutil.copy2(ROOT/'src/nes'/n,out/n)
 shutil.copy2(ROOT/'tests/nes-functional/rom_physical_model.sv',out/'rom_backend_model.sv')
 p=out/'ncr1_live_tb.sv';s=p.read_text()
 needle='rom_backend_model backend(.*);';assert s.count(needle)==1
 s=s.replace(needle,PINS+'\nreg mem_clk=0;initial begin #'+str(phase_ps/1000.0)+';forever #5.952381 mem_clk=~mem_clk;end\n'+bridge()+'rom_physical_model #(.FIXTURE(1)) memory(.*);\n'+'''
 integer physical_requests=0,physical_responses=0,physical_start=0,physical_min=1000,physical_max=0;
 always @(posedge clk)if(!reset)begin
  if(rom_response)begin
   physical_responses++;
   if(bg_tick-physical_start<physical_min)physical_min=bg_tick-physical_start;
   if(bg_tick-physical_start>physical_max)physical_max=bg_tick-physical_start;
  end
  if(rom_request)begin physical_requests++;physical_start=bg_tick;end
 end
''')
 s=s.replace('backend.accepted','physical_requests').replace('$display("ROM SERVICE requests=', '$display("PHYSICAL responses=%0d latency=%0d..%0d",physical_responses,physical_min,physical_max);\n  $display("ROM SERVICE requests=')
 live.put(p,s)
 for n in ('nes_rom_physical.sv','rom_backend_model.sv','ncr1_live_tb.sv'):sources[n]=live.sha(out/n)
 return sources

def main():
 global read_clocks,phase_ps
 if '--phase-ps' in sys.argv:
  i=sys.argv.index('--phase-ps');phase_ps=int(sys.argv[i+1]);del sys.argv[i:i+2]
 if '--delay' in sys.argv:read_clocks=int(sys.argv[sys.argv.index('--delay')+1])
 assert 1<=read_clocks<=16 and 0<=phase_ps<11905
 mode=sys.argv[1];out=Path(sys.argv[sys.argv.index('--out')+1])
 live.FILES.append('nes_rom_physical');early.prepare=prepare
 old_put=resource.put
 def pin_put(p,s):
  if p.name=='nes_live_joint.sv':
   a=s.index('input wire ext_rom_ready,');b=s.index('output wire [3:0] out_rom_error_code,',a)
   s=s[:a]+'''input wire ext_mem_clk,
input wire [15:0] ext_psram_data,
output wire [21:0] out_psram_address,
output wire out_psram_1ce,out_psram_2ce,out_psram_oe,out_psram_we,out_psram_bhe,out_psram_ble,
output wire out_rom_fault,
'''+s[b:]
   a=s.index('wire rom_ready=ext_rom_ready,');b=s.index('wire rom_cpu_address_valid',a)
   s=s[:a]+'''wire mem_clk=ext_mem_clk;
wire rom_ready,rom_response,rom_error;wire [21:0] rom_response_address;wire [7:0] rom_data;
'''+PINS+'\nassign psram_data=ext_psram_data;\n'+'\n'.join('assign out_'+n+'='+n+';' for n in ['psram_address','psram_1ce','psram_2ce','psram_oe','psram_we','psram_bhe','psram_ble','rom_fault','rom_error_code'])+'\n'+bridge()+s[b:]
  if p.name=='live.qsf':
   obsolete=['ext_rom_ready','ext_rom_response','ext_rom_error','ext_rom_response_address','ext_rom_data','out_rom_request','out_rom_address']
   s='\n'.join(x for x in s.splitlines() if not any(x.endswith('-to '+n) for n in obsolete))+'\n'
   s+='\n'.join('set_instance_assignment -name VIRTUAL_PIN ON -to '+n for n in ['ext_psram_data','out_psram_address','out_psram_1ce','out_psram_2ce','out_psram_oe','out_psram_we','out_psram_bhe','out_psram_ble'])+'\n'
  if p.name=='live.sdc':s+='create_clock -name memory -period 11.904762 [get_ports ext_mem_clk]\n# Area probe only. Board bundled-data constraints and physical STA remain required.\n'
  old_put(p,s)
 resource.put=pin_put;early.main()
 p=out/'result.json';m=json.loads(p.read_text());m.update(candidate='NES-R1-ROM-PHYSICAL-052',driver_sha256=live.sha(Path(__file__)),memory_read_clocks=read_clocks,memory_period_ns=11.904762,phase_ps=phase_ps,physical_access_model_ns=25,scope='Actual051 core with original052 read-only PSRAM pin controller and bundled toggle crossing. Pin model25ns is an assumption; virtual resource IO, no board PLL/loader/SD image or physical STA.')
 live.put(p,json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
