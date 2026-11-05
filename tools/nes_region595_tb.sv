// Behavioral leased collector and SPI pins. Commands come from the linked M4.
`timescale 1ns/1ps
module region595_tb;
 reg clk=0,host_clk=0,reset=1,enable=0,owned=0;
 always #22.727 clk=~clk;
 initial begin #3.5;forever #5.952 host_clk=~host_clk;end
 reg [31:0] epoch=1;reg [15:0] generation=0;
 reg [5:0] groups,palettes;reg [7:0] objects,exceptions;reg [2:0] patches;
 reg ss=1,sck=0,mosi=0,response=0;reg [63:0] data,pending;
 reg [63:0] values[0:16383];
 wire query,released,selected,miso,host_fault,packet_fault;wire [3:0] source_fault;
 wire [2:0] kind;wire [12:0] index;wire [15:0] qgen;
 integer delay=0,queries=0,repair_rows=0,leases=0;
 integer corrupt=0;reg injected=0;
 nes_region595 dut(.clk(clk),.host_clk(host_clk),.reset(reset),.enable(enable),.frame_owned(owned),.geometry_valid(1'b1),
  .generation(generation),.epoch(epoch),.groups(groups),.palettes(palettes),.objects(objects),.exceptions(exceptions),
  .rows(8'd224),.patches(patches),.query(query),.query_kind(kind),.query_index(index),.query_generation(qgen),
  .response(response),.hit(1'b1),.data(data),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(selected),.miso(miso),
  .release_frame(released),.source_fault(source_fault),.host_fault(host_fault),.packet_fault(packet_fault));
 always @(posedge clk)begin
  response<=0;
  if(reset)begin delay<=0;injected<=0;end
  else begin
   if(query)begin
    if(qgen!=generation||!owned||delay!=0)$fatal(1,"query ownership");
    pending<=values[kind*2048+index];queries<=queries+1;delay<=3+index%3;
    if(corrupt!=0&&!injected&&dut.phase==1&&index==5)begin pending<=values[index]^1;injected<=1;end
    if(dut.phase==1 && dut.repaired && index%33==0)repair_rows<=repair_rows+1;
   end
   if(delay>0)begin delay<=delay-1;if(delay==1)begin response<=1;data<=pending;end end
   if(released)begin owned<=0;leases<=leases+1;end
  end
 end
 integer command=0,go=0,n=0,frame_id=0,done=0;
 reg [2071:0] tx=0,rx=0;integer i,b,f,a0,a1,a2,a3,a4,a5,a6;string name;
 always @(go)begin
  case(command)
   1:begin
    name=$sformatf("frame%0d.values",frame_id);$readmemh(name,values);
    name=$sformatf("frame%0d.counts",frame_id);f=$fopen(name,"r");
    if($fscanf(f,"%d %d %d %d %d %d %d",a0,a1,a2,a3,a4,a5,a6)!=7)$fatal(1,"counts");$fclose(f);
    if(owned)$fatal(1,"leased");generation=frame_id;groups=a0/33;objects=a2;exceptions=a3;palettes=a5/32;patches=a6;
    owned=1;enable=1;
   end
   2:begin rx=0;#2000;ss=0;#2000;
    for(i=n-1;i>=0;i=i-1)for(b=7;b>=0;b=b-1)begin
     mosi=tx[8*i+b];#190.476;sck=1;rx[8*i+b]=selected?miso:0;#190.476;sck=0;
    end
    #2000;ss=1;#2000;
   end
   3:begin reset=1;enable=0;owned=0;#1000;if(query||selected)$fatal(1,"STOP");
    reset=0;#1000;if(dut.base_valid||dut.spi.sealed||dut.spi.read_seen||dut.action_toggle||dut.spi.token)$fatal(1,"STOP residue");
   end
   default:;
  endcase
  done=go;
 end
endmodule
