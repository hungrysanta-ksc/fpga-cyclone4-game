# SPDX-License-Identifier: MIT
"""051 causal live-address early ROM requests; retain050 scheduling failure."""
from pathlib import Path
import json,sys,shutil
import nes_rom_service as base
import nes_ncr1_live as live
original_prepare=base.prepare
ROOT=live.ROOT
CANDIDATE='NES-R1-ROM-EARLY-051'
baseline=False
TRACE="""
 // Test-only bounded ring: pre-edge request/response/demand state at the decision.
 reg [191:0] rom_history[0:15];integer rom_history_index=0;
 always @(posedge clk)if(!reset)begin
  rom_history[rom_history_index]<={59'd0,bg_tick,cpumem_addr,ppumem_addr,
    cpumem_read,ppumem_read,rom_cpu_sample,tap_ce,rom_cpu_valid,rom_ppu_valid,
    rom_request,rom_ready,rom_response,rom_error,rom_address,rom_response_address};
  rom_history_index<=(rom_history_index+1)%16;
 end
"""
def prepare(out):
 sources=original_prepare(out)
 if not baseline:
  shutil.copy2(ROOT/'src/nes/nes_rom_early.sv',out/'nes_rom_service.sv')
  p=out/'rtl/ppu.sv';s=live.expose(p.read_text(),'PPU','output wire rom_ppu_address_valid','assign rom_ppu_address_valid=ALE && !vram_w;');live.put(p,s)
  p=out/'rtl/nes.v';s=live.expose(p.read_text(),'NES','output wire rom_cpu_address_valid,rom_ppu_address_valid','assign rom_cpu_address_valid=prg_addr[15] && prg_allow;')
  s=s.replace('PPU ppu(', 'PPU ppu(\n.rom_ppu_address_valid(rom_ppu_address_valid),');live.put(p,s)
  p=out/'nes_probe.sv';s=live.expose(p.read_text(),'nes_probe','output wire rom_cpu_address_valid,rom_ppu_address_valid')
  s=s.replace('NES core(', 'NES core(\n.rom_cpu_address_valid(rom_cpu_address_valid),.rom_ppu_address_valid(rom_ppu_address_valid),');live.put(p,s)
 p=out/'ncr1_live_tb.sv';s=p.read_text();s=s.replace(' integer i,pixels=0,fetches=0;',TRACE+'\n integer i,pixels=0,fetches=0;',1)
 needle='if(rom_fault)$fatal(1,"ROM DEADLINE/PROTOCOL error=%0d tick=%0d cpu=%h ppu=%h",rom_error_code,bg_tick,cpumem_addr,ppumem_addr);'
 assert s.count(needle)==1
 s=s.replace(needle,'if(rom_fault)begin\n for(integer h=0;h<16;h++)$display("ROM HISTORY %048h",rom_history[(rom_history_index+h)%16]);\n '+needle[len('if(rom_fault)'):]+'\n end')
 live.put(p,s)
 for n in ('rtl/ppu.sv','rtl/nes.v','nes_probe.sv','nes_rom_service.sv','ncr1_live_tb.sv'):sources[n]=live.sha(out/n)
 return sources
def main():
 global baseline
 mode=sys.argv[1];baseline=mode=='baseline'
 if baseline:sys.argv[1]='negative'
 else:
  base.DECL='wire rom_cpu_address_valid,rom_ppu_address_valid;\n'+base.DECL
  base.ROM=base.ROM.replace('nes_rom_service rom_service(', 'nes_rom_early rom_service(\n.cpu_address_valid(rom_cpu_address_valid),.ppu_address_valid(rom_ppu_address_valid),')
 base.prepare=prepare
 out=Path(sys.argv[sys.argv.index('--out')+1]);base.main()
 p=out/'result.json';m=json.loads(p.read_text());m.update(candidate=CANDIDATE,early_reads=not baseline,driver_sha256=live.sha(Path(__file__)),scope='Causal current-address early requests; synchronous latency backend only, no physical PSRAM or CDC. Baseline mode retains050 read-strobe scheduling.')
 live.put(p,json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
