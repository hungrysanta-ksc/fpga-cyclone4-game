# SPDX-License-Identifier: MIT
"""First-fault-only observation on frozen138; no reader/core timing changes."""
from pathlib import Path
import argparse,json,shutil,subprocess,re
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

def edit(root,name,old,new):
 p=root/name;p.write_text(once(p.read_text(encoding='utf8'),old,new),encoding='utf8',newline='\n')

def arm_delta(s):
 for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','nes_h1_stm32.c','nes_run136.inc','nes_cf86_session094.c','nes_cf86_session094.h']:
  p=s/n;p.write_text(p.read_text(encoding='utf8').replace('138','139'),encoding='utf8',newline='\n')
 for n in ['nes_h1_stm32.c','nes_rom_verify.c','nes_run136.inc']:
  p=s/n;t=p.read_text(encoding='utf8');t=re.sub(r'\b0x5a\b','0x5b',t);t=re.sub(r'\b0xd5\b','0xd6',t);p.write_text(t,encoding='utf8',newline='\n')
 edit(s,'nes_menu_diagnostic.c','board_expected_hex=5a','board_expected_hex=5b')
 edit(s,'nes_run136.h','uint32_t first,last,stopped;','uint32_t first,last,stopped,context_hi,context_lo;\n uint8_t first_error,stop_error,context_valid;')
 shutil.copy2(ROOT/'src/nes/firmware/nes_fault139.inc',s/'nes_run136.inc')
 edit(s,'nes_menu_diagnostic.c','run_rom_error=%u\\n",','run_rom_error=%u\\nrun_first_error=%u\\nrun_stop_error=%u\\nfault_context_valid=%u\\nfault_context_hi=%08lx\\nfault_context_lo=%08lx\\n",')
 edit(s,'nes_menu_diagnostic.c','nes_run136.flags,nes_run136.rom_error);','nes_run136.flags,nes_run136.rom_error,nes_run136.first_error,nes_run136.stop_error,nes_run136.context_valid,(unsigned long)nes_run136.context_hi,(unsigned long)nes_run136.context_lo);')

def fit_delta(o):
 p=o/'nes_rom_spi.sv';s=p.read_text();assert s.count("8'h5a")==2;p.write_text(s.replace("8'h5a","8'h5b"))
 # Expose the pre-edge context; no new register or control in the ROM service.
 edit(o,'nes_rom_service.sv','output reg fault,output reg [3:0] error_code','output wire fault_trigger,output wire [63:0] fault_context,\n output reg fault,output reg [3:0] error_code')
 edit(o,'nes_rom_service.sv',' always @(posedge clk or posedge reset)begin',''' //139 Parallel observation only. Capture on the SAME edge that sets fault.
 assign fault_trigger=!reset && !fault && (
  (rom_response && (!busy || rom_response_address!=pending_address || rom_error)) ||
  (busy && !rom_response && age==255) ||
  (ppu_sample && ppu_rom && !ppu_valid) || (cpu_sample && cpu_rom && !cpu_valid));
 assign fault_context={1'b0,busy,pending_ppu,rom_ready,rom_response,cpu_sample,ppu_sample,cpu_valid,ppu_valid,age,pending_address,cpumem_addr};
 always @(posedge clk or posedge reset)begin''')
 edit(o,'nes_live_joint.sv','output wire out_rom_fault,','output wire out_fault_trigger,output wire [63:0] out_fault_context,\noutput wire out_rom_fault,')
 edit(o,'nes_live_joint.sv','nes_rom_early rom_service(','nes_rom_early rom_service(\n.fault_trigger(out_fault_trigger),.fault_context(out_fault_context),')
 edit(o,'fxpak_nes_screen137_top.sv','wire core_reset,cpu_sample,rom_fault;','wire core_reset,cpu_sample,rom_fault,fault_trigger;wire [63:0] fault_context;')
 edit(o,'fxpak_nes_screen137_top.sv','.out_rom_fault(rom_fault),','.out_fault_trigger(fault_trigger),.out_fault_context(fault_context),\n  .out_rom_fault(rom_fault),')
 edit(o,'fxpak_nes_screen137_top.sv','.core_reset(core_reset),.cpu_sample(cpu_sample),','.fault_trigger(fault_trigger),.fault_context(fault_context),\n  .core_reset(core_reset),.cpu_sample(cpu_sample),')
 p=o/'nes_run_observer134.sv';s=p.read_text().replace("8'hd5","8'hd6")
 s=once(s,'input wire [3:0] rom_error,','input wire [3:0] rom_error,\n input wire fault_trigger,input wire [63:0] fault_context,')
 s=once(s,'reg [55:0] snapshot;','reg [55:0] snapshot;\n reg context_valid;reg [63:0] first_context;')
 s=once(s,"command==8'h70","(command==8'h70 || command==8'h71 || command==8'h72)")
 s=once(s,'samples<=0;sticky_fault<=0;first_error<=0;','samples<=0;sticky_fault<=0;first_error<=0;context_valid<=0;first_context<=0;')
 s=once(s,'if(cpu_sample && !core_reset','if(fault_trigger && !context_valid)begin context_valid<=1;first_context<=fault_context;end\n   if(cpu_sample && !core_reset')
 s=once(s,"snapshot<={8'hd6,6'd0,sticky_fault,core_reset,4'd0,first_error,samples};",'''case(incoming)
        8'h71:snapshot<={8'hd6,7'd0,context_valid,first_context[63:24]};
        8'h72:snapshot<={8'hd6,7'd0,context_valid,first_context[23:0],4'd0,first_error,8'd1};
        default:snapshot<={8'hd6,6'd0,sticky_fault,core_reset,4'd0,first_error,samples};
       endcase''')
 p.write_text(s,encoding='utf8',newline='\n')

def prepare(base,out,kind):
 assert not out.exists();e=base/'nes-display138/evidence';m=json.loads((ROOT/'analysis/display138-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files']
 prefix={'fit':'fit01/','arm':'arm02/','host':'host07/'}[kind];copied={}
 for n,h in pins.items():
  if not n.startswith(prefix):continue
  rel=n[len(prefix):];p=Path(rel)
  if kind=='fit' and (rel.startswith(('db/','incremental_db/','output_files/')) or p.suffix not in ['.sv','.v','.vhd','.hex','.sdc','.qsf','.qpf']):continue
  if kind=='arm' and (any(x.startswith(('obj-','.dep-')) for x in p.parts) or p.suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or p.name in ['.ARG_VERSION','executed-builder.ps1']):continue
  if kind=='host' and p.suffix not in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:continue
  assert sha(e/n)==h,n;d=out/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,d);copied[rel]=h
 if kind=='fit':fit_delta(out)
 else:
  arm_delta(out/'src' if kind=='arm' else out)
  if kind=='arm':(out/'src/VERSION').write_text('RELEASE_VERSION = "NES-SCREEN139"\n')
 (out/'preparation139.json').write_text(json.dumps(dict(copied=copied,changed={n:sha(out/n) for n,h in copied.items() if sha(out/n)!=h}),indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--kind',choices=['arm','fit','host'],required=True);p.add_argument('--quartus-bin',type=Path)
 a=p.parse_args();prepare(a.baseline,a.out,a.kind)
 if a.quartus_bin:
  for phase in ['map','fit','sta']:
   with (a.out/(phase+'.log')).open('wb') as f:r=subprocess.run([str(a.quartus_bin/f'quartus_{phase}.exe'),'board'],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=900)
   print(phase,r.returncode,flush=True);assert r.returncode==0
