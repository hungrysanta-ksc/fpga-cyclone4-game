# SPDX-License-Identifier: MIT
"""Directed raw0 final RAM job through public validator ports; no CPU timing."""
import argparse,binascii,json,shutil,struct
from pathlib import Path
from probe_nes_refill267 import run
from nes_delta231 import sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out;d.mkdir(parents=True,exist_ok=False);shutil.copyfile(a.source/'nes_validator278.sv',d/'nes_validator278.sv')
    h=bytearray(32);h[:4]=b'H2\x02\x00';struct.pack_into('<IIHH',h,4,1,1,1,1);h[19]=0x18
    struct.pack_into('<H',h,22,binascii.crc_hqx(b'\0',65535));struct.pack_into('<H',h,24,1)
    struct.pack_into('<H',h,30,binascii.crc_hqx(h[:30],65535))
    display=struct.pack('<12H',16,0,4096,512,544,1,0,0,0x1060,0x18,0x2472,0)
    def hexfile(name,b):(d/name).write_text(''.join(f'{v:02x}\n' for v in b),newline='\n')
    hexfile('context.hex',h);hexfile('display.hex',display)
    tb=r'''
module final332_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,abort_source=0,grant=0,ack=0,beg=0,range_valid=0,map_range=0,descriptor=0,finish=0,all_consumed=1;
 reg [11:0] first=0,count=0;reg context_valid=0;reg [7:0] context_data=0;
 reg h_start=0,h_valid=0;reg [7:0] h_data=0;reg display_request=0,display_response_ready=0;
 wire ready,sealed,initialized,context_ready,h_ready,display_ready,display_valid;
 wire [3:0] fault;wire [9:0] address;wire we;wire [7:0] value,display_data;wire [8:0] expected_address;
 reg [7:0] memory[0:1023],expected[0:511],context_bytes[0:31],display_bytes[0:23];reg [7:0] q=0,eq=0;
 integer checks=0,mode=0,done=0;reg [7:0] wanted;
 always @(posedge clk)begin
  q<=memory[address];eq<=expected[expected_address];if(we)memory[address]<=value;
  if(reset)checks<=0;
  else if(dut.state==dut.E_CAPTURE332)begin
   if(expected_address!==(checks<24?448+checks:checks<190?256+checks-24:checks-190))$fatal(1,"expected address/count");
   checks<=checks+1;
  end
 end
 nes_validator278 dut(.expected_data332(eq),.expected_addr332(expected_address),
 .exec_start298(1'b0),.exec_kind298(2'd0),.exec_op298(4'd0),.exec_length298(9'd0),.exec_data298(8'd0),.exec_busy298(),.exec_done298(),.exec_addr298(),
 .manifest_at282(),.manifest_started282(),.crc_reset287(1'b0),.v_descriptor287(descriptor),.clk(clk),.reset(reset),.abort_source(abort_source),
 .grant278(grant),.grant_epoch278(32'd1),.grant_serial278(32'd1),.grant_generation278(16'd1),.grant_raw278(3'd0),.host_ack278(ack),
 .crc_done278(),.crc_index278(),.init278(initialized),.ram_q(q),.ram_addr(address),.ram_we(we),.ram_w(value),
 .display_write(1'b0),.display_request(display_request),.display_request_ready(display_ready),.display_response_valid(display_valid),.display_response_ready(display_response_ready),.display_response(display_data),
 .v_begin_valid(beg),.v_target_bank(1'b0),.v_raw_count(3'd0),.v_range_valid(range_valid),.v_map_range(map_range),.v_first(first),.v_count(count),
 .v_check_valid(1'b0),.v_check_value(8'd0),.v_finish_valid(finish),.v_all_consumed(all_consumed),.v_ready(ready),.v_sealed(sealed),
 .h_start(h_start),.h_kind(2'd1),.h_index(4'd0),.h_valid(h_valid),.h_data(h_data),.h_ready(h_ready),
 .context_valid(context_valid),.context_data(context_data),.context_ready(context_ready),.fault(fault));
 task mark(input integer f,input integer n,input bit m,input bit end_mode);
  begin wait(ready);@(negedge clk);first=f;count=n;map_range=m;descriptor=end_mode;range_valid=1;
   @(negedge clk);range_valid=0;wait(ready);@(negedge clk);if(fault)$fatal(1,"range fault");end
 endtask
 initial begin
  $readmemh("context.hex",context_bytes);$readmemh("display.hex",display_bytes);
  for(mode=0;mode<7;mode++)begin
   reset=1;ack=0;all_consumed=1;repeat(3)@(negedge clk);reset=0;wait(initialized);@(negedge clk);
   for(integer i=0;i<512;i++)expected[i]=0;
   for(integer i=0;i<256;i++)expected[i]=255;
   for(integer i=144;i<148;i++)expected[256+i]=255;
   for(integer i=0;i<24;i++)expected[448+i]=display_bytes[i];
   if(mode==1)expected[0]=0;
   grant=1;@(negedge clk);grant=0;wait(context_ready);@(negedge clk);
   for(integer i=0;i<32;i++)begin context_valid=1;context_data=context_bytes[i]^((mode==2&&i==30)?1:0);@(negedge clk);end
   context_valid=0;beg=1;@(negedge clk);beg=0;wait(ready);@(negedge clk);
   h_start=1;@(negedge clk);h_start=0;wait(h_ready);@(negedge clk);h_valid=1;
   @(negedge clk);h_valid=0;wait(ready);
   if(mode!=5)mark(1152,1184,0,1);
   for(integer i=0;i<(mode==6?2016:2048);i+=32)mark(i,32,1,0);
   @(negedge clk);all_consumed=mode!=4;finish=1;@(negedge clk);finish=0;
   wait(sealed||fault);@(negedge clk);
   if(mode==0||mode==3)begin
    if(fault||checks!=446)$fatal(1,"valid scan completion");
    for(integer i=0;i<(mode==3?11:12);i++)begin
     wait(display_ready);@(negedge clk);display_request=1;@(negedge clk);display_request=0;
     wait(display_valid);@(negedge clk);
     case(i)
      0:wanted=0;1:wanted=8'h18;2:wanted=0;3:wanted=1;4:wanted=0;5:wanted=0;6:wanted=0;7:wanted=0;default:wanted=0;
     endcase
     if(display_data!==wanted)$fatal(1,"raw0 display view");
     display_response_ready=1;@(negedge clk);display_response_ready=0;
    end
    wait(dut.state==dut.V_WAITDISPLAY);@(negedge clk);ack=1;@(negedge clk);ack=0;@(negedge clk);
    if(mode==0)begin if(fault||sealed||dut.active)$fatal(1,"final ack");end
    else if(fault!=7||sealed)$fatal(1,"short display read accepted");
   end else if(fault!=(mode==2?7:3)||sealed)$fatal(1,"expected independent fault");
   $display("PASS FINAL332 raw0 case=%0d reads=%0d fault=%0d",mode,checks,fault);done++;
  end
  if(done!=7)$fatal(1,"case count");$finish;
 end
 initial begin #1000000;$fatal(1,"timeout final332");end
endmodule
'''
    (d/'final332_tb.sv').write_text(tb,newline='\n')
    qbin=Path('C:/altera_standard/25.1std/questa_fse/win64')
    run(qbin/'vlib.exe',['work'],d,'vlib');run(qbin/'vlog.exe',['-sv','nes_validator278.sv','final332_tb.sv'],d,'vlog')
    raw=run(qbin/'vsim.exe',['-c','work.final332_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',60)
    assert raw.count('PASS FINAL332 raw0 case=')==7
    out=dict(passed=True,cases=7,RTL_sha256=sha(d/'nes_validator278.sv'),tb_sha256=sha(d/'final332_tb.sv'),log_sha256=sha(d/'vsim.log'),script_sha256=sha(Path(__file__)),scope=__doc__)
    (d/'result.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n');print('PASS raw0 final RAM job 7 cases')


if __name__=='__main__':main()
