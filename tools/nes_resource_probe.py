# Latest validated MMC3 resource envelope. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,json,hashlib,shutil,re,subprocess,difflib
from nes_functional import VHDL,SV
T65='884a7c84128a9936690f1a73a14036b7742aed646a78209471a769071edfa692'
WRAPPER='13b471adbf0f3a751023f94b88e95eaf9511c6bfa7dccbbe43c3f5ebe159e07f'
ADAPTER='c9a014df2f7fbb22d576c004abcb9ba12d62c0b208dc16a68f4b26364c4b387e'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('validated-rtl','out','quartus-bin'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--local-ram',action='store_true');a=p.parse_args();src=a.validated_rtl.resolve();out=a.out.resolve();assert str(out).isascii();m=json.loads((src/'build.json').read_text());assert m['diagnostic_passed'] and m['mapper']==4
 assert m['upstream_commit']=='49a0a662e244469ca77b2155746a066df704ffae'
 for e in m['sources']:assert sha(src/e['path'])==e['compiled_sha256'],e['path']
 for f,h in [('rtl/t65/T65.vhd',T65),('nes_probe.sv',WRAPPER),('cart_nrom.sv',ADAPTER)]:assert sha(src/f)==h,f
 out.mkdir(parents=True,exist_ok=False)
 for f in VHDL+SV+['COPYING','cart_nrom.sv','nes_probe.sv']:
  d=out/f;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src/f,d)
 shutil.copyfile(src/'build.json',out/'validated-build.json')
 # The64/16KiB diagnostic fixture cuts are not a game-size contract.
 p=out/'cart_nrom.sv';old=p.read_text();new=old.replace("prg_ain[15] ? {9'd0,mp[15:0]} : {3'd0,mp}","{3'd0,mp}").replace("{8'd0,mc[13:0]}","mc")
 assert new!=old and 'mp[15:0]' not in new and 'mc[13:0]' not in new;p.write_text(new,encoding='utf-8',newline='\n')
 (out/'resource-adapter.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='validated009-adapter',tofile='full-address-resource-adapter')),encoding='utf-8')
 p=out/'nes_probe.sv';old=p.read_text();new=old.replace("21'h00ffff","21'h1fffff").replace("20'h03fff","20'hfffff");p.write_text(new,encoding='utf-8',newline='\n')
 ports=re.findall(r'\b(input|output)\s+wire\s+(signed\s+)?(\[[^\]]+\]\s*)?(\w+)',new.split('module nes_probe(',1)[1].split(');',1)[0])
 top='nes_probe'
 if a.local_ram:
  top='nes_resource'
  header=',\n'.join(f'{d} wire {sg}{w}{n}' for d,sg,w,n in ports)
  conn=',\n'.join('.'+n+'('+({'cpumem_din':'cpu_data','ppumem_din':'ppu_data'}.get(n,n))+')' for _,_,_,n in ports)
  body="""
wire cpu_ram_sel=cpumem_addr[24:11]==14'h700;
wire prg_ram_sel=cpumem_addr[24:13]==12'h1e0;
wire ciram_sel=ppumem_addr[21:11]==11'h740;
wire [7:0] cpu_q,prg_q,nt_q;
wire [7:0] cpu_data=cpu_ram_sel ? cpu_q : prg_ram_sel ? prg_q : cpumem_din;
wire [7:0] ppu_data=ciram_sel ? nt_q : ppumem_din;
nes_resource_ram #(.AW(11)) cpu_ram(clk,cpumem_write && cpu_ram_sel,cpumem_addr[10:0],cpumem_dout,cpu_q);
nes_resource_ram #(.AW(13)) prg_ram(clk,cpumem_write && prg_ram_sel,cpumem_addr[12:0],cpumem_dout,prg_q);
nes_resource_ram #(.AW(11)) ciram(clk,ppumem_write && ciram_sel,ppumem_addr[10:0],ppumem_dout,nt_q);
"""
  ram="""
// Resource-only synchronous read-old-data RAM; no reset clear, initialization, loader or CDC.
module nes_resource_ram #(parameter AW=11)(input clk,input we,input [AW-1:0] addr,input [7:0] din,output reg [7:0] q);
(* ramstyle="M9K" *) reg [7:0] mem[0:(1<<AW)-1];
always @(posedge clk)begin
 if(we)mem[addr]<=din;
 q<=mem[addr];
end
endmodule
"""
  (out/'nes_resource.sv').write_text('// SPDX-License-Identifier: MIT\nmodule nes_resource(\n'+header+'\n);\n'+body+'\nnes_probe core('+conn+');\nendmodule\n'+ram,encoding='utf-8',newline='\n')
 (out/'probe.qpf').write_text('PROJECT_REVISION = "probe"\n')
 (out/'probe.sdc').write_text('create_clock -name nes_master -period 46.560846 [get_ports clk]\nderive_clock_uncertainty\n')
 qsf='\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY '+top,'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files','set_global_assignment -name NUM_PARALLEL_PROCESSORS 4','set_global_assignment -name SEED 1','set_global_assignment -name VHDL_INPUT_VERSION VHDL_2008','set_global_assignment -name SDC_FILE probe.sdc','set_global_assignment -name STRATIX_DEVICE_IO_STANDARD "3.3-V LVTTL"'])+'\n'
 for f in VHDL:qsf+='set_global_assignment -name VHDL_FILE '+f+'\n'
 for f in SV+['cart_nrom.sv','nes_probe.sv']+(['nes_resource.sv'] if a.local_ram else []):qsf+='set_global_assignment -name SYSTEMVERILOG_FILE '+f+'\n'
 for _,_,_,n in ports:
  if n!='clk':qsf+='set_instance_assignment -name VIRTUAL_PIN ON -to '+n+'\n'
 (out/'probe.qsf').write_text(qsf,encoding='utf-8')
 result=dict(candidate='NES-R1-RESOURCE-018',implementation_candidate='NES-P2-RDY-014',upstream_commit=m['upstream_commit'],local_ram=a.local_ram,hardware_eligible=False,driver_sha256=sha(Path(__file__)),validated_build_sha256=sha(src/'build.json'),sources={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()},scope='Standard MMC3, full mapper address bits; latest validated core. Optional2KiBCPU+2KiBCIRAM+8KiBPRGRAM in M9K. Virtual external ROM and IO. No board IO/PSRAM/SRAM controller/CDC/packet encoder/SNES interface/loader/initialization. New adapter/RAM wrapper not functionally validated.',phases={})
 for phase in ('map','fit','sta'):
  with (out/(phase+'.log')).open('wb') as log:r=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'probe'],cwd=out,stdout=log,stderr=subprocess.STDOUT)
  result['phases'][phase]=r.returncode;(out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(phase,r.returncode,flush=True)
  if r.returncode:raise SystemExit('Inspect raw '+str(out/(phase+'.log')))
 print('Resource probe finished; inspect fit/STA/removed logic and exclusions.',flush=True)
if __name__=='__main__':main()