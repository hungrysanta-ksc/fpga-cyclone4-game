"""Continue actual T65 through both CHR planes and following sprite; sample all CPU phases."""
import argparse,json
from pathlib import Path
import probe_nes_bonus702_cpu as prior
from nes_game147 import sha

def prepare(board,rom,out,phase,stop=False):
    prior.prepare(board,rom,out,phase)
    p=out/'game147_tb.sv';s=p.read_text()
    s=s.replace('scenario<8','scenario<12').replace('scenario%4','scenario%6').replace('scenario>=4','scenario>=6').replace('scenario<4','scenario<6')
    s=s.replace('if(step699>=79)break;','if(step699>=111)break;')
    # The physical701 snapshot has nametable address2300 at the next sprite.
    s=s.replace("force dut.core.ppu.vram=15'd0", "force dut.core.ppu.vram=15'h0300")
    s=s.replace('if(start699>=0)$display("MEM702', 'if(start699>=0)$display("MEM703')
    # Every consumed PRG byte is checked independently against the physical ROM.
    s=s.replace('    if(start699>=0)$display("MEM703', '''    if(rom_cpu_sample && !failed && cpumem_addr<25'h40000)
      if(!rom_cpu_valid || cpumem_din!==prg[cpumem_addr[17:0]])$fatal(1,"independent CPU ROM byte mismatch");
    if(start699>=0)$display("MEM703''')
    if stop:
        s=s.replace('    if(step699>=111)break;', '''    if(step699==49+3*(scenario%6))begin
      #0.001;reset_request=1;#0.001;
      if(rom_request||rom_response||rom_cpu_valid||rom_ppu_valid||!psram_oe)$fatal(1,"703 STOP not immediate");
      repeat(16)@(negedge clk);
      if(rom_request||rom_response||rom_cpu_valid||rom_ppu_valid||!psram_oe)$fatal(1,"703 stale reply after STOP");
      $display("STOP703 scenario=%0d step=%0d quiescent=1",scenario,step699);break;
    end''')
        s=s.replace('if(start699<0||first_raw<0||commit_tick<0)', 'if(start699<0||first_raw<0)')
    p.write_text(s,encoding='utf8',newline='\n')
    m=json.loads((out/'inputs.json').read_text());m['stage']=703;m['sources']['game147_tb.sv']=sha(p)
    m['scope']='T65 original IRQ code;6 alignments x2 sprite Y x memory phase; throughdot276 with independent PRG/CHR bytes and actual arbiter.'
    m['stop']=stop
    (out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','rom','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--phase',type=float,required=True)
    p.add_argument('--stop',action='store_true')
    a=p.parse_args();prepare(a.board,a.rom,a.out,a.phase,a.stop)
