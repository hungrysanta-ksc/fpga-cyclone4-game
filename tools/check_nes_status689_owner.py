"""Same-edge loader ownership and qualified bulk token/STOP regression."""
import argparse,json,subprocess
from pathlib import Path
from nes_raw506 import sha

LOADER=r'''
`timescale 1ns/1ps
module loader689_tb;
 parameter real PHASE=0;
 reg clk=0,run_clk=1,reset=1,ss=1,sck=0,mosi=0;
 always #2.976 if(run_clk)clk=~clk;
 wire [61:0] a,b;integer cycles=0;
 nes_rom_spi_check dut(.mem_clk(clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
 .spi_miso(a[0]),.spi_selected(a[1]),.load_ready(1'b1),.loaded(1'b1),.run_enable(1'b1),.boot_fault(1'b0),.boot_error(4'd0),.loaded_bytes(19'h60000),
 .load_begin(a[2]),.load_chr32(a[3]),.load_valid(a[4]),.load_end(a[5]),.start(a[6]),.stop(a[7]),.load_data(a[15:8]),.fault(a[16]),.error_code(a[20:17]),
 .check_enable(a[21]),.check_request(a[22]),.check_address(a[41:23]),.check_ready(1'b1),.check_response(1'b0),.check_fault(1'b0),.check_response_address(19'd0),.check_data(8'd0));
 assign a[61:42]=0;
 nes_rom_spi_check_reference refdut(.mem_clk(clk),.reset(reset),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),
 .spi_miso(b[0]),.spi_selected(b[1]),.load_ready(1'b1),.loaded(1'b1),.run_enable(1'b1),.boot_fault(1'b0),.boot_error(4'd0),.loaded_bytes(19'h60000),
 .load_begin(b[2]),.load_chr32(b[3]),.load_valid(b[4]),.load_end(b[5]),.start(b[6]),.stop(b[7]),.load_data(b[15:8]),.fault(b[16]),.error_code(b[20:17]),
 .check_enable(b[21]),.check_request(b[22]),.check_address(b[41:23]),.check_ready(1'b1),.check_response(1'b0),.check_fault(1'b0),.check_response_address(19'd0),.check_data(8'd0));
 assign b[61:42]=0;
 always @(negedge clk)if(!reset)begin if(a!==b)$fatal(1,"loader boundary mismatch");cycles++;end
 task byte_tx(input [7:0] x);
  for(int i=7;i>=0;i--)begin mosi=x[i];#190.476;sck=1;#190.476;sck=0;end
 endtask
 initial begin
  #(PHASE);
  for(int op=0;op<256;op++)begin
   reset=1;ss=1;#100;reset=0;#200;ss=0;#200;
   byte_tx(op);
   if(a[1]!==((op>>4)==6))$fatal(1,"opcode ownership");
   for(int n=0;n<10;n++)byte_tx(op+n*37);
   @(negedge clk);run_clk=0;ss=1;#1;if(a[1]||b[1])$fatal(1,"stopped clock SS release");
   #100;run_clk=1;#2200;
   // Abort each possible bit position of the next command.
   ss=0;for(int n=0;n<(op%8);n++)begin mosi=1;#190.476;sck=1;#190.476;sck=0;end
   ss=1;#2200;
  end
  $display("PASS689 OWNER loader opcodes=256 cycles=%0d phase=%0f",cycles,PHASE);$finish;
 end
 initial begin #30000000;$fatal(1,"loader timeout");end
endmodule
'''

BULK=r'''
`timescale 1ns/1ps
module bulk689_tb;
 parameter real PHASE=0;
 reg clk=0,run_clk=1,reset=1,active=1,stop=0,fault=0,ready=1;
 reg [31:0] token=32'h12345678;
 reg [23:0] address=0;reg rn=1,wn=1;reg [7:0] din=0;
 wire [7:0] data_a,data_b;wire oe_a,oe_b,dir_a,dir_b,consume_a,consume_b,err_a,err_b;
 wire [31:0] token_a,token_b;integer accepted=0,errors=0,cycles=0;
 always #5.952 if(run_clk)clk=~clk;
 nes_bulk_control194 dut(.clk(clk),.reset(reset),.active(active),.stop(stop),.fault(fault),
 .chunk_ready(ready),.chunk_kind(1'b0),.chunk_length(12'd1536),.chunk_slot(10'd4),.chunk_generation(16'd955),.chunk_token(token),
 .address(address),.read_n(rn),.write_n(wn),.data_in(din),.data_out(data_a),.oe_n(oe_a),.dir(dir_a),.consume(consume_a),.consume_token(token_a),.command_error(err_a));
 nes_bulk_control194_reference refdut(.clk(clk),.reset(reset),.active(active),.stop(stop),.fault(fault),
 .chunk_ready(ready),.chunk_kind(1'b0),.chunk_length(12'd1536),.chunk_slot(10'd4),.chunk_generation(16'd955),.chunk_token(token),
 .address(address),.read_n(rn),.write_n(wn),.data_in(din),.data_out(data_b),.oe_n(oe_b),.dir(dir_b),.consume(consume_b),.consume_token(token_b),.command_error(err_b));
 always @(negedge clk)if(!reset)begin
  if({data_a,oe_a,dir_a,consume_a,err_a}!=={data_b,oe_b,dir_b,consume_b,err_b})$fatal(1,"bulk boundary");cycles++;
 end
 always @(posedge clk)begin
  if(consume_a)begin
   if(!consume_b||token_a!==token_b||token_a!==token)$fatal(1,"qualified token");accepted++;
  end
  if(err_a)errors++;
 end
 task wr(input [23:0] a,input [7:0] v);
  @(negedge clk);address=a;din=v;rn=1;wn=0;repeat(12)@(negedge clk);wn=1;repeat(8)@(negedge clk);
 endtask
 task send(input [31:0] value,input integer n);
  for(int k=0;k<n;k++)wr('h604c+k,value>>(k*8));wr('h6050,'ha5);
 endtask
 initial begin
  #(PHASE);#200;reset=0;#200;
  for(int i=0;i<32;i++)begin
   token=32'h12345678+i*32'h1020304;
   send(token,3);send(token^32'h80000000,4);send(token,4);
  end
  if(accepted!=32||errors!=64)$fatal(1,"independent token counts");
  wr('h604c,token[7:0]);@(negedge clk);run_clk=0;address='h6040;rn=0;#50;stop=1;#1;
  if(!oe_a||!oe_b||consume_a)$fatal(1,"stopped host cancellation");
  #100;rn=1;run_clk=1;#100;stop=0;#200;
  send(token,3);send(token,4);if(accepted!=33||errors!=65)$fatal(1,"STOP partial survives");
  fault=1;#100;fault=0;#200;send(token,3);send(token,4);
  if(accepted!=34||errors!=66)$fatal(1,"fault restart");
  $display("PASS689 OWNER bulk accepted=%0d rejected=%0d cycles=%0d phase=%0f",accepted,errors,cycles,PHASE);$finish;
 end
 initial begin #3000000;$fatal(1,"bulk timeout");end
endmodule
'''

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','board','out','bin'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    names=('nes_rom_spi.sv','nes_bulk_control194.sv','nes_domain_reset124.sv')
    for n in names:(a.out/n).write_bytes((a.board/n).read_bytes())
    for n,module in [('nes_rom_spi.sv','nes_rom_spi_check'),('nes_bulk_control194.sv','nes_bulk_control194')]:
        (a.out/('reference_'+n)).write_text((a.base/n).read_text().replace('module '+module+'(','module '+module+'_reference('),newline='\n')
    (a.out/'owner689_tb.sv').write_text(LOADER+BULK,newline='\n')
    commands=[('vlib',['work']),('vlog',['-sv',*names,'reference_nes_rom_spi.sv','reference_nes_bulk_control194.sv','owner689_tb.sv'])]
    for top in ('loader689_tb','bulk689_tb'):
        for phase in (0,8):commands.append((top+str(phase),['-c',top,f'-gPHASE={phase}','-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0']))
    results=[]
    for tag,args in commands:
        tool=tag if tag in ('vlib','vlog') else 'vsim'
        with (a.out/(tag+'.log')).open('wb') as f:subprocess.run([a.bin/(tool+'.exe'),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=180)
        if tool=='vsim':
            lines=(a.out/(tag+'.log')).read_text().splitlines();line=next(l for l in lines if 'PASS689 OWNER' in l);results.append(line)
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,results=results,pins={n:sha(a.out/n) for n in names},reference={n:sha(a.base/n) for n in names},bench=sha(a.out/'owner689_tb.sv'),scope='Directed synchronous interfaces; invalid unqualified token value is intentionally not compared.'),indent=2)+'\n',newline='\n')
    print(json.dumps(results))
