# SPDX-License-Identifier: MIT
"""Same ARM SPI driver/pins for source257 transport and output260 (259 ARM ABI).

Source bytes are prior255 N5 fixtures, producer record cuts are diagnostic243B.
No N5 receiver/planner or query/ROM arbiter timing is claimed by this replay.
"""
import inspect,json,sys,shutil
from pathlib import Path
import probe_nes_output260 as old
import probe_nes_arm260 as arm
from nes_delta231 import BASE,ROOT,once

EXTRA=r'''
 wire source_selected,source_miso,source_fault,host_fault,source_empty,source_ack;
 wire source_ready,source_byte_ready,crc_pending;wire [15:0] crc_previous;wire [7:0] crc_byte;
 reg source_record=0,source_byte=0;reg [7:0] source_length=0,source_data=0;
 function automatic [15:0] c16(input [15:0] c0,input [7:0] b);
  reg [15:0] c;begin c=c0^{b,8'd0};for(integer i=0;i<8;i++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end
 endfunction
 nes_transport257 ingress(.src_clk(nc),.host_clk(hc),.reset(reset),.abort_source(cancel),
 .crc_result(c16(crc_previous,crc_byte)),.crc_pending(crc_pending),.crc_previous(crc_previous),.crc_byte(crc_byte),
 .record_valid(source_record),.record_ready(source_ready),.record_length(source_length),.record_flush(1'b1),
 .byte_valid(source_byte),.byte_ready(source_byte_ready),.byte_data(source_data),
 .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(source_selected),.miso(source_miso),
 .ack_valid(source_ack),.ack_ready(1'b1),.ack_accept(),.ack_generation(),.source_fault(source_fault),.host_fault(host_fault),.source_empty(source_empty));
 assign miso=source_selected?source_miso:output_miso;
 always @(posedge hc)if(!reset)begin
  if(source_fault||host_fault)$fatal(1,"source transport fault");
  if(source_selected&&dut.queue.selected)$fatal(1,"shared SPI ownership collision");
 end
 reg [7:0] source_bytes[0:16383];integer source_size,source_at,source_n,source_fd,source_scan;
 initial begin
  source_fd=$fopen("source-size.txt","r");source_scan=$fscanf(source_fd,"%d",source_size);$fclose(source_fd);
  $readmemh("source.hex",source_bytes,0,source_size-1);wait(!reset);repeat(12)@(negedge nc);
  source_at=0;
  while(source_at<source_size)begin
   source_n=source_size-source_at;if(source_n>243)source_n=243;source_length=source_n;
   wait(source_ready);@(negedge nc);source_record=1;@(negedge nc);source_record=0;
   for(integer j=0;j<source_n;j++)begin
    wait(source_byte_ready);@(negedge nc);source_byte=1;source_data=source_bytes[source_at+j];@(negedge nc);source_byte=0;
   end
   source_at+=source_n;
  end
 end
'''

def testbench():
 s=(ROOT/'tests/nes-functional/output260_tb.sv').read_text()
 s=once(s,'wire miso;', 'wire miso,output_miso;')
 s=once(s,'.miso(miso),.address(address)', '.miso(output_miso),.address(address)')
 s=once(s,' integer ticks=0,',EXTRA+'\n integer ticks=0,')
 s=once(s,'reset=0;wait(ir);','reset=0;wait(source_ack);$fwrite(logfd,"input_done,%0d,0,0\\n",ticks);wait(ir);')
 return s

def build(d):
 shutil.copyfile(ROOT/'tools/nes_input259.c',d/'nes_input259.c')
 s=inspect.getsource(arm.build).replace("'nes_output260.c','stubs.s'","'nes_output260.c','nes_input259.c','stubs.s'")
 ns=dict(arm.__dict__);exec(compile(s,'bus259-build','exec'),ns);ns['build'](d)

def main():
 s=inspect.getsource(old.main)
 s=once(s,"shutil.copyfile(ROOT/'tests/nes-functional/output260_tb.sv',d/'output260_tb.sv');", "(d/'output260_tb.sv').write_text(testbench(),newline='\\n');")
 s=once(s,"src=sources()",'''source=bytearray()
 for line in (BASE/'probes/nes-joint255/test03/blocks.txt').read_text().splitlines():
  f,t,n,data=line.split()
  if int(f)==a.frame:source+=bytes.fromhex(data)
 assert source
 (d/'source.hex').write_text(source.hex(' '));(d/'source-size.txt').write_text(str(len(source)))
 fingerprint=2166136261
 for b in source:fingerprint=((fingerprint^b)*16777619)&0xffffffff
 src=sources()''')
 s=once(s,"ok=arm.call('frame259'", "input_before=arm.instructions;assert arm.call('read_source259',[len(source),gen,0,fingerprint])>0;input_instructions=arm.instructions-input_before\n   ok=arm.call('frame259'")
 s=once(s,"verify(packets,endpoint.packets)","verify(packets,[p for p in endpoint.packets if p[0]<=14])")
 s=once(s,"result=dict(passed=True,", "result=dict(source_bytes=len(source),input_ARM_instructions=input_instructions,shared_SPI_pins=True,source_query_timing_bound=False,passed=True,")
 ns=dict(old.__dict__);ns.update(testbench=testbench,build=build,__doc__=__doc__);exec(compile(s,'bus259-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
