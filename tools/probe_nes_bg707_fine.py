"""Check fine-Y preview/wrap against the unchanged703 address generator.

All fine values, copy masks, render/PPUDATA/copy combinations; compares actual
post-clock scroll registers, including simultaneous copy and increment.
"""
import argparse,json,shutil
from pathlib import Path
from nes_game147 import sha

def prepare(base,fixture,out):
    m=json.loads((fixture/'inputs.json').read_text())
    out.mkdir(parents=True,exist_ok=False)
    for n in m['sources']:
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(fixture/n,p)
    old=(base/'rtl/ppu.sv').read_text().split('module VramAddressGen (',1)[1].split('endmodule',1)[0]
    old='module ReferenceVramAddressGen ('+old+'endmodule\n'
    ports=".clk(clk),.clear(1'b0),.ce(1'b1),.reset(1'b0),.is_rendering(render),.ain(3'd0),.din(8'd0),.read(1'b0),.write(1'b0),.is_pre_render(1'b1),.trigger_2007(trigger),.cycle(dot),.SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),.SaveStateBus_wren(1'b0),.SaveStateBus_rst(1'b0)"
    tb='''module game147_tb;
reg clk=0,render=0,trigger=0;reg [8:0] dot=0;wire [2:0] preview;
integer f,t,k,r,c,n=0;reg [2:0] captured;
'''+f'VramAddressGen dut({ports},.native_fine_next(preview));\nReferenceVramAddressGen refgen({ports});\n'+'''
initial begin
for(f=0;f<8;f++)for(t=0;t<8;t++)for(k=0;k<6;k++)for(r=0;r<2;r++)for(c=0;c<4;c++)begin
 clk=0;render=r;trigger=c&1;
 case(k) 0:dot=228;1:dot=230;2:dot=255;3:dot=279;4:dot=303;5:dot=335;endcase
 dut.vram_v=(f<<12)|15'h0bbf;refgen.vram_v=(f<<12)|15'h0bbf;
 dut.vram_t=(t<<12)|15'h0421;refgen.vram_t=(t<<12)|15'h0421;
 dut.write_shift=(c&2);refgen.write_shift=(c&2);
 dut.ppu_incr=1;refgen.ppu_incr=1;
 dut.ppu_address_latch=0;refgen.ppu_address_latch=0;
 dut.vram_x=0;refgen.vram_x=0;
 #10;captured=preview;clk=1;#10;
 if(dut.vram_v!==refgen.vram_v || dut.vram_t!==refgen.vram_t)
  $fatal(1,"707 changed scroll f=%0d t=%0d k=%0d r=%0d c=%0d",f,t,k,r,c);
 if(render && captured!==dut.vram_v[14:12])
  $fatal(1,"707 preview mismatch f=%0d t=%0d k=%0d c=%0d",f,t,k,c);
 n++;
end
$display("DONE698 FINE707 cases=%0d reference_equivalent=1 preview_render=1",n);$finish;
end
endmodule
'''
    (out/'game147_tb.sv').write_text(old+tb,encoding='utf8',newline='\n')
    m.update(stage=707,scope=__doc__,reference_sha256=sha(base/'rtl/ppu.sv'))
    m['sources']['game147_tb.sv']=sha(out/'game147_tb.sv')
    (out/'inputs.json').write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','fixture','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.fixture,a.out)
