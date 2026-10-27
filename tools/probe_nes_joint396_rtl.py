# SPDX-License-Identifier: MIT
"""Twelve physicalSPI frames and inherited guards with396 storage."""
import inspect
import probe_nes_jobs394_rtl as old
from nes_delta231 import ROOT
from probe_nes_joint396_native import fixtures
s=inspect.getsource(old.main)
s=s.replace("'nes_bulk_aperture188.sv'","'nes_bulk_aperture188.sv','nes_stage396.sv','nes_check396.sv'")
s=s.replace("shutil.copyfile(ROOT/'tests/nes-jobs394/record_tb.sv',d/'record_tb.sv')", "(d/'record_tb.sv').write_text(test396(),newline='\\n')")
s=s.replace('from guard_nes_jobs394 import guards','from guard_nes_joint396 import guards')
def test396():
 s=(ROOT/'tests/nes-jobs394/record_tb.sv').read_text().replace('flow.tile_bytes','flow.aperture.used').replace('.tile_generation(generation)',".tile_generation(GUARD==18?generation+16'd1:generation)")
 s=s.replace('nes_output260 flow(',"""reg[4:0] footer_pause396=0;reg[31:0] paused_token396=0;
 always @(negedge host_clk)begin
  if(reset||cancel)begin footer_pause396=0;paused_token396=0;end
  else if(footer_pause396!=0)footer_pause396=footer_pause396-1'b1;
  else if(flow.state==flow.TAKE&&flow.chunk_token!=paused_token396)begin paused_token396=flow.chunk_token;footer_pause396=14;end
 end
 nes_output260 flow(.footer_request396(footer_pause396!=0),.footer_data396(8'd0),""")
 s=s.replace('if(GUARD==16&&flow.allocation!=1)','if((GUARD==16||GUARD==19)&&flow.allocation!=1)')
 s=s.replace('reg [7:0] before_ram[0:1023]', 'reg [7:0] before_meta396[0:1023];reg [7:0] before_ram[0:1023]')
 s=s.replace('before_queue[i]=flow.queue.buffer[i];','before_queue[i]=flow.queue.buffer[i];before_meta396[i]=flow.tile_link.memory[i];')
 s=s.replace('memory[i]!==before_ram[i]||', 'flow.tile_link.memory[i]!==before_meta396[i]||memory[i]!==before_ram[i]||')
 s=s.replace(' task transfer(input integer offset,n);begin',''' reg [7:0] rx396[0:258];reg [7:0] crc396;
 function automatic[7:0] c8396(input[7:0] old,input[7:0] v);reg[7:0] c;begin c=old^v;for(integer i=0;i<8;i++)c=c[7]?(c<<1)^8'h07:c<<1;c8396=c;end endfunction
 task transfer(input integer offset,n);begin''')
 s=s.replace('#190.476190476;sck=0;end', '#190.476190476;rx396[j]={rx396[j][6:0],miso};sck=0;end')
 s=s.replace('#2000;ss=1;#2000;\n end endtask', '''#2000;ss=1;#2000;
  if(n>=14)begin crc396=0;for(integer j=1;j<(packets[offset]==8'he0 ? 24:13);j++)crc396=c8396(crc396,rx396[j]);
   if(rx396[1]!==8'hfb||rx396[packets[offset]==8'he0 ? 24:13]!==crc396)$fatal(1,"physical response CRC396 command%h got%h expected%h version%h",packets[offset],rx396[packets[offset]==8'he0 ? 24:13],crc396,rx396[1]);end
 end endtask''')
 s=s.replace('$display("FRAME394', '''for(integer j=0;j<25;j++)packets[30000+j]=j==0?8'he0:8'd0;transfer(30000,25);
   $display("FRAME394''')
 return s
ns=dict(old.__dict__,fixtures=fixtures,test396=test396);exec(compile(s,'joint396-rtl', 'exec'),ns)
if __name__=='__main__':ns['main']()
