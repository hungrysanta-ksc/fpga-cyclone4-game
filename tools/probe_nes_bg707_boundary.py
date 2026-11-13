"""Selected core: sweep background render restart against CPU read phase.

193:230, low address61 and physical21e161 are measured705 fields. Other
history (2001 write, tile16, fineY1) is a sensitivity fixture, not a captured
instruction trace. Real PPU enable pipeline, mapper, ROM service and reader.
"""
import argparse,json
from pathlib import Path
import probe_nes_bonus698_boundary as prior

def prepare(board,rom,out,phase,dot=230):
    prior.prepare(board,rom,out,phase)
    p=out/'game147_tb.sv';s=p.read_text();s=s[:s.index(' reg [8:0] dot698')]
    fixture=(prior.base.ROOT/'tests/nes-functional/game160_transition_tb.sv').read_text()
    body=fixture[fixture.index(' reg [8:0] dot160'):]
    body=body.replace('integer step160,', 'integer scenario,phase707,offset707,first707;reg [63:0] context707,ppu707;\n integer step160,')
    body=body.replace('target160=336,latch160=0',f'target160={dot},latch160=97')
    a=body.index('  unused155=');b=body.index('  $readmemh',a)
    body=body[:a]+body[b:]
    body=body.replace("bg_name_table=8'h07", "bg_name_table=8'h16").replace("vram=15'h0b00", "vram=15'h1000")
    body=body.replace("wr160(16'h8001,8'h5c)", "wr160(16'h8001,8'h78)")
    body=body.replace("wr160(16'h8001,8'h5e)", "wr160(16'h8001,8'h7a)")
    body=body.replace('  repeat(8)@(negedge clk);reset_request=0;', '''  for(scenario=0;scenario<36;scenario++)begin
  phase707=scenario%12;offset707=scenario/12;
  @(negedge clk);reset_request=1;ce160=0;ppu_write160=0;dot160=223;cpuaddr160=0;div160=12;
  failed160=0;checked160=0;first707=-1;context707=0;ppu707=0;
  repeat(8)@(negedge clk);reset_request=0;''')
    body=body.replace('ppu_write160=dot160==target160-4;', 'ppu_write160=dot160==target160-4-offset707;')
    body=body.replace('step160>=20', 'step160>=12+phase707').replace('(step160-20)', '(step160-12-phase707)')
    body=body.replace('if(fault_trigger)failed160=1;', '''if(fault_trigger&&!failed160)begin failed160=1;first707=step160;context707=fault_context;ppu707=ppu_fault_state154;end''')
    body=body.replace('   if(step160==31 && (ppumem_addr!==(22\'h217000 | latch160) || !tap_ce || !ppumem_read))$fatal(1,"transition boundary mismatch");','')
    a=body.index('  if(control155');b=body.index(' initial begin #100000000',a)
    body=body[:a]+'''  $display("CASE707 scenario=%0d cpu_phase=%0d write_offset=%0d failed=%0d error=%0d checked=%0d first=%0d context=%h ppu=%h",scenario,phase707,offset707,failed160,rom_error_code,checked160,first707,context707,ppu707);
  @(negedge clk);reset_request=1;ce160=0;ppu_write160=0;cpuaddr160=0;
  #0.001;if(rom_request||rom_response||rom_cpu_valid||rom_ppu_valid||!psram_oe)$fatal(1,"707 STOP not immediate");
  repeat(16)@(negedge clk);
  if(rom_request||rom_response||rom_cpu_valid||rom_ppu_valid||!psram_oe)$fatal(1,"707 stale reply after STOP");
  end
  $display("DONE698 background boundary sweep");$finish;
 end
'''+body[b:]
    p.write_text(s+body,encoding='utf8',newline='\n')
    m=json.loads((out/'inputs.json').read_text());m.update(stage=707,scope=__doc__,target_dot=dot)
    m['sources']['game147_tb.sv']=prior.base.sha(p)
    (out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','rom','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--phase',type=float,default=3.5)
    p.add_argument('--dot',type=int,default=230)
    a=p.parse_args();prepare(a.board,a.rom,a.out,a.phase,a.dot)
