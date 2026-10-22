# SPDX-License-Identifier: MIT
"""Actual source FSM raw2->0->2->1->2, bad query, STOP and bounded capacity."""
from pathlib import Path
import argparse,binascii,json,shutil
from nes_delta231 import sha
from probe_nes_joint261 import run
from probe_nes_decode280 import records,chunks,encode280,ARM

TB=r'''
`timescale 1ns/1ps
module raw280_tb;
 parameter NEG=0;
 reg clk=0;always #22.727 clk=~clk;
 reg reset=1,abort_source=0,start=0,response=0;reg [63:0] data=0;
 reg [31:0] serial=1;reg [15:0] gen=65535;reg [2:0] raw=2;
 wire ready,query,rv,bv,phase,done;wire [2:0] kind;wire [12:0] qi;
 wire [7:0] rl,bd;wire [9:0] addr;wire we;wire [7:0] value;
 reg [7:0] ram[0:1023];reg [7:0] q;wire [3:0] fault;
 reg accept=0,ack=0;integer fd,frame=0,cycles=0,writes=0;
 nes_core257 dut(
 .clk(clk),.reset(reset),.abort_source(abort_source),.start(start),.start_ready(ready),
 .frame_owned(1'b1),.geometry_valid(1'b1),.frame_generation(gen),
 .content_epoch(32'd1),.frame_serial(serial),.patch_count(raw),
 .display_lease(1'b1),.display_generation(gen),.display_epoch(32'd1),
 .row_count(8'd224),.object_count(8'd0),.exception_count(8'd0),.group_count(6'd1),.palette_count(6'd1),
 .query(query),.query_kind(kind),.query_index(qi),.raw_response(response),.raw_hit(1'b1),.raw_data(data),
 .record_valid(rv),.record_ready(1'b1),.record_length(rl),.byte_valid(bv),.byte_ready(accept),.byte_data(bd),
 .ack_valid(ack),.ack_accept(1'b1),.ack_generation(gen),.v_display_ack(phase),
 .transport_crc_pending(1'b0),.transport_empty(1'b1),.transport_crc(16'd0),.transport_byte(8'd0),
 .ram_a_q(q),.ram_b_q(8'd0),.ram_a_addr(addr),.ram_a_we(we),.ram_a_w(value),
 .output_phase(phase),.done(done),.fault(fault));
 always @(posedge clk)begin
  q<=ram[addr];if(we)begin ram[addr]<=value;writes++;end
  cycles++;
  response<=query;data<=0;
  if(query)case(kind)
   0:data<=qi;
   1:data<=qi[7:0];
   4:if(qi>=224-raw)data<=64'h0002000000000000|((64'(qi)-(224-raw))<<50);
     else data<=64'h0000018000000000|{59'd0,qi[4:0]};
   5:data<=qi[5:0];
   7:data<=NEG==1?64'd64:({58'd0,qi[5:0]}^((qi==3)?{63'd0,serial[0]}:64'd0));
   default:;
  endcase
  if(!reset&&dut.mask_pending278&&dut.a_we)$fatal(1,"fixed port conflict");
  if(!reset&&dut.base_we&&dut.base_addr>=4910)$fatal(1,"base bounds");
  if(!NEG&&fault)$fatal(1,"raw transition fault %0d",fault);
  if(rv)$fwrite(fd,"%0d ",rl);
  if(bv&&accept)begin
   $fwrite(fd,"%02x",bd);
   if(dut.rec_i+1==rl)$fwrite(fd,"\n");
  end
 end
 always @(negedge clk)begin accept=cycles%5!=0;ack=dut.state==dut.WAITACK;end
 initial begin
  repeat(5)@(negedge clk);reset=0;
  if(NEG==3)raw=3;
  for(frame=1;frame<=(NEG?1:5);frame++)begin
   wait(ready);fd=$fopen($sformatf("raw%0d.records",frame),"w");
   @(negedge clk);start=1;@(negedge clk);start=0;
   if(NEG==2)begin wait(dut.raw_mode&&dut.state==dut.FSTORE);@(negedge clk);abort_source=1;end
   if(NEG)begin
    wait(fault);repeat(4)@(negedge clk);
    begin integer saved;saved=writes;repeat(30)@(negedge clk);
     if(writes!=saved||we||dut.base_valid||bv||rv)$fatal(1,"fault did not freeze source");end
    $fclose(fd);$display("PASS RAW280 NEG=%0d",NEG);$finish;
   end
   wait(done);wait(ready);@(negedge clk);$fclose(fd);
   serial++;gen++;
   case(frame)1:raw=0;2:raw=2;3:raw=1;4:raw=2;endcase
  end
  $display("PASS RAW280 transitions=5");$finish;
 end
 initial begin #100000000;$fatal(1,"raw timeout");end
endmodule
'''


def geometry(count):
    out=bytearray()
    for i in range(1056):out+=(i if i<33 else 0).to_bytes(2,'little')
    out+=bytes(range(224))+bytes(1024+512)
    for i in range(224):out+=((1024+((i-(224-count))<<11)) if i>=224-count else i&31).to_bytes(2,'little')
    out+=b'\x18'+bytes(range(32))+bytes(32)
    for v in [33,224,0,0,224,32]:out+=v.to_bytes(2,'little')
    out+=bytes([count]);assert len(out)==4398
    return bytes(out)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--arm',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--questa-bin',type=Path,required=True);a=ap.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    shutil.copyfile(a.source/'nes_core257.sv',d/'nes_core257.sv');(d/'raw280_tb.sv').write_text(TB)
    run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv','nes_core257.sv','raw280_tb.sv'],d,'vlog')
    for neg in range(4):
        log=run(a.questa_bin/'vsim.exe',['-c','work.raw280_tb',f'-gNEG={neg}','-do','onerror {quit -code 1};run -all;quit -f'],d,f'neg{neg}')
        assert 'PASS RAW280' in log
        if neg==0:
            arm=ARM(a.arm/'decoder.elf',None);arm.call('reset280',[])
            old=bytes(4398);prev=None
            for serial,count in enumerate([2,0,2,1,2],1):
                g=geometry(count);raw=bytes((i%64)^((serial&1) if i==3 else 0) for i in range(count*256))
                rr=records(d/f'raw{serial}.records')
                assert rr==encode280(old,g,raw,prev,serial,(65534+serial)&65535),serial
                for b in chunks(rr):
                    arm.uc.mem_write(0x20018000,b)
                    assert arm.call('block280',[0x20010000,0x20018000,len(b),binascii.crc_hqx(b,65535)])==1
                assert arm.call('complete280',[])==1
                assert bytes(arm.uc.mem_read(0x20010000,4398+len(raw)))==g+raw
                shutil.copyfile(d/f'raw{serial}.records',d/f'transition{serial}.records')
                old=g;prev=raw
    r=dict(passed=True,transitions=[2,0,2,1,2],generation_wrap=True,guards=['raw high bits','STOP raw FSTORE','raw>2 reject'],
        RTL_sha256=sha(d/'nes_core257.sv'),ARM_sha256=sha(a.arm/'decoder.elf'),TB_sha256=sha(d/'raw280_tb.sv'),scope=__doc__)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))


if __name__=='__main__':main()
