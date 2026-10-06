# SPDX-License-Identifier: MIT
"""047 actual bound PPU/encoder/producer/transport joint area probe; virtual external ROM/IO."""
from pathlib import Path
import argparse,json,subprocess,re
from nes_ncr1_live import prepare,put,sha,ROOT,FILES

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--quartus-bin',type=Path,required=True);a=p.parse_args();out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir()
 sources=prepare(out)
 tb=(out/'ncr1_live_tb.sv').read_text();body=tb[tb.index(' wire frame_start'):tb.index(' reg [7:0] prg')]
 body=body.replace('reg chr_32k;','wire chr_32k=ext_chr_32k;')
 body=body.replace(' reg [23:0] snes_addr=0;reg read_n=1,write_n=1,romsel_n=1;reg [7:0] snes_data_in=0;', ' wire [23:0] snes_addr=ext_snes_addr;wire read_n=ext_read_n,write_n=ext_write_n,romsel_n=ext_romsel_n;wire [7:0] snes_data_in=ext_snes_data_in;')
 body=body.replace('reg [7:0] cpumem_din=0,ppumem_din=0;', 'wire [7:0] cpumem_din,ppumem_din;')
 body=body.replace('reg [4:0] joypad1_data=0,joypad2_data=0;', 'wire [4:0] joypad1_data=ext_joypad1,joypad2_data=ext_joypad2;')
 body=body.replace('wire immutable_chr=1;','wire immutable_chr=ext_immutable_chr;')
 body=re.sub(r' integer frames_started=.*?;\n','',body)
 body=body.replace('reg test_arm=0;initial begin #60000000;test_arm=1;end', '').replace('wire arm=test_arm && frames_started<4;', 'wire arm=ext_arm;')
 ins={'clk':'','host_clk':'','reset':'','reset_epoch':'[15:0]','arm':'','immutable_chr':'','chr_32k':'','snes_addr':'[23:0]','read_n':'','write_n':'','romsel_n':'','snes_data_in':'[7:0]','cpumem_din':'[7:0]','ppumem_din':'[7:0]','joypad1':'[4:0]','joypad2':'[4:0]'}
 outs={'cpumem_addr':'[24:0]','ppumem_addr':'[21:0]','cpumem_read':'','cpumem_write':'','ppumem_read':'','ppumem_write':'','cpumem_dout':'[7:0]','ppumem_dout':'[7:0]','sample':'[15:0]','color':'[5:0]','emphasis':'[2:0]','cycle':'[8:0]','scanline':'[8:0]','joypad_clock':'[1:0]','joypad_out':'[2:0]','hsync':'','vsync':'','hblank':'','vblank':'','bus_data':'[7:0]','databus_oe_n':'','databus_dir':'','ready':'','busy':'','fault':'','encoder_fault':'','producer_fault':'','tap_fault':'','tap_error':'[7:0]','published':'[15:0]'}
 header=[f'input wire {w} ext_{n}' for n,w in ins.items()]+[f'output wire {w} out_{n}' for n,w in outs.items()]
 aliases='wire queue_clk=ext_clk,clk=ext_clk,host_clk=ext_host_clk,reset=ext_reset,reset_nes=ext_reset,cold_reset=ext_reset;\nwire [15:0] reset_epoch=ext_reset_epoch;\n'
 ram="""
wire cpu_ram_sel=cpumem_addr[24:11]==14'h700;
wire prg_ram_sel=cpumem_addr[24:13]==12'h1e0;
wire ciram_sel=ppumem_addr[21:11]==11'h740;
wire [7:0] cpu_q,prg_q,nt_q;
assign cpumem_din=cpu_ram_sel ? cpu_q : prg_ram_sel ? prg_q : ext_cpumem_din;
assign ppumem_din=ciram_sel ? nt_q : ext_ppumem_din;
nes_resource_ram #(.AW(11)) cpu_ram(clk,cpumem_write && cpu_ram_sel,cpumem_addr[10:0],cpumem_dout,cpu_q);
nes_resource_ram #(.AW(13)) prg_ram(clk,cpumem_write && prg_ram_sel,cpumem_addr[12:0],cpumem_dout,prg_q);
nes_resource_ram #(.AW(11)) ciram(clk,ppumem_write && ciram_sel,ppumem_addr[10:0],ppumem_dout,nt_q);
"""
 put(out/'nes_live_joint.sv','// Original047 joint resource wrapper; RAM service is resource-only.\nmodule nes_live_joint(\n'+',\n'.join(header)+'\n);\n'+aliases+body+ram+'\n'.join('assign out_'+n+'='+n+';' for n in outs)+'\nendmodule\n')
 put(out/'live.qpf','PROJECT_REVISION = "live"\n')
 put(out/'live.sdc','create_clock -name nes -period 46.560846 [get_ports ext_clk]\ncreate_clock -name host -period 11.904762 [get_ports ext_host_clk]\nderive_clock_uncertainty\n')
 qsf=[v for v in (out/'probe.qsf').read_text().splitlines() if not any(s in v for s in ['TOP_LEVEL_ENTITY','SDC_FILE','VIRTUAL_PIN'])]
 qsf+=['set_global_assignment -name TOP_LEVEL_ENTITY nes_live_joint','set_global_assignment -name SDC_FILE live.sdc']
 qsf+=['set_global_assignment -name SYSTEMVERILOG_FILE '+n+'.sv' for n in FILES+['nes_live_joint']]
 qsf+=['set_instance_assignment -name VIRTUAL_PIN ON -to ext_'+n for n in ins if n not in ('clk','host_clk')]
 qsf+=['set_instance_assignment -name VIRTUAL_PIN ON -to out_'+n for n in outs]
 put(out/'live.qsf','\n'.join(qsf)+'\n')
 sources.update({n:sha(out/n) for n in ['nes_live_joint.sv','nes_resource.sv','live.qsf','live.qpf','live.sdc']})
 m={'candidate':'NES-R2-NCR1-LIVE-047','sources':sources,'phases':{},'scope':'Joint014 core with12KiB localRAM and actual exported PPU binding +047tap +046encoder +045producer +044transport. Area probe only: virtual ROM/IO, uninitialized resource RAM, no board PLL/controller/loader, no STA or hardware signoff.'}
 for phase in ('map','fit'):
  with (out/(phase+'.log')).open('wb') as f:cp=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'live'],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=900)
  m['phases'][phase]=cp.returncode;put(out/'result.json',json.dumps(m,indent=2)+'\n');print(phase,cp.returncode,flush=True)
  if cp.returncode:break
 print((out/'output_files/live.fit.summary').read_text(errors='replace') if (out/'output_files/live.fit.summary').exists() else 'Inspect raw logs')
if __name__=='__main__':main()
