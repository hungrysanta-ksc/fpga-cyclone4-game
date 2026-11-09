"""Exact-ROM natural startup, selected703B core/reader and focused BG request trace."""
import argparse,json
from pathlib import Path
import probe_nes_bonus698 as base

def prepare(board,rom,out,phase,frames):
    m=base.prepare(board,rom,out)
    p=out/'game147_tb.sv';s=p.read_text()
    s=s.replace('initial begin #3.5;',f'initial begin #{phase};')
    s=s.replace('if(frame==350&&!cheated)','if(1\'b0&&!cheated)')
    s=s.replace('(frame>=30&&frame<34)||(frame>=90&&frame<96)',"(1'b0)")
    s=s.replace('(frame>=360&&frame<366)||(frame>=550&&frame<556)',"(1'b0)")
    marker='  if(fault_trigger)begin'
    s=s.replace(marker,'''  if(scanline==193 && cycle>=210 && cycle<=240)
   $display("BG707 tick=%0d frame=%0d line=%0d dot=%0d ce=%b cpu=%h/%b/%h div=%0d re=%b name=%h vram=%h latch=%h chr=%h hint=%b/%h need=%b/%b req=%b/%h response=%b/%h busy=%b age=%0d cache=%b/%h/%b/%h context=%h ppu=%h",
    ticks,frame,scanline,cycle,tap_ce,dut.core.cpu_addr_full,dut.core.cpu_rnw,dut.core.cpu_dout,dut.core.div_cpu,
    dut.core.ppu.re_sr,dut.core.ppu.bg_name_table,dut.core.ppu.vram,dut.core.ppu.vram_a_byte,ppumem_addr,
    rom_service.ppu_prefetch_valid,game148_hint_physical,rom_service.cpu_need,rom_service.ppu_need,
    rom_request,rom_address,rom_response,rom_response_address,rom_service.busy,rom_service.age,
    rom_service.ppu_cached,rom_service.ppu_tag,rom_service.ppu_previous_cached,rom_service.ppu_previous_tag,fault_context,ppu_fault_state154);
'''+marker)
    p.write_text(s,encoding='utf8',newline='\n')
    m.update(stage=707,frames=frames,memory_phase_ns=phase,intervention=None,pad='none',scope=__doc__)
    m['sources']['game147_tb.sv']=base.sha(p)
    (out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','rom','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--phase',type=float,default=3.5);p.add_argument('--frames',type=int,default=20)
    a=p.parse_args();prepare(a.board,a.rom,a.out,a.phase,a.frames)
