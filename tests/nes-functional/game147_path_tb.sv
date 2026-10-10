// SPDX-License-Identifier: MIT
// Boundary coverage uses explicit test-only count deposits, not a full load.
`timescale 1ns/1ps
module game147_path_tb;
 reg clk=0,mem_clk=0,reset=1,read_reset=1;
 always #23.280423 clk=~clk;always #2.9761905 mem_clk=~mem_clk;
 reg check_enable=0,check_request=0;reg [18:0] check_address=0;
 wire check_ready,check_response,check_fault;wire [18:0] check_response_address;wire [7:0] check_data;
 reg load_begin=0,load_chr32=0,load_valid=0,load_end=0,start=0,stop=0;reg [7:0] load_data=8'h5a;
 wire load_ready,loaded,run_enable,boot_fault,rom_chr32;wire [3:0] boot_error;wire [18:0] loaded_bytes;
 reg rom_request=0;reg [21:0] rom_address=0;wire rom_ready,rom_response,rom_error;
 wire [21:0] rom_response_address,psram_address;wire [7:0] rom_data;
 wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble;wire [15:0] psram_data;
 nes_rom_boot boot(.*);
 assign #70 psram_data=!psram_oe?16'h1234:16'hzzzz;
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;wire spi_miso,spi_selected;
 reg [18:0] status_count=0;reg status_loaded=0;
 wire spi_fault;wire [3:0] spi_error;wire ctrl_begin,ctrl_chr,ctrl_valid,ctrl_end,ctrl_start,ctrl_stop;
 wire ctrl_check_enable,ctrl_request;wire [18:0] ctrl_address;wire [7:0] ctrl_data;
 reg ctrl_response=0;reg [18:0] ctrl_response_address=0;reg [7:0] ctrl_response_data=8'ha6;
 nes_rom_spi_check control(.mem_clk(mem_clk),.reset(reset),.SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
 .spi_miso(spi_miso),.spi_selected(spi_selected),.load_ready(1'b1),.loaded(status_loaded),.run_enable(1'b0),
 .boot_fault(1'b0),.boot_error(4'd0),.loaded_bytes(status_count),.load_begin(ctrl_begin),.load_chr32(ctrl_chr),
 .load_valid(ctrl_valid),.load_end(ctrl_end),.start(ctrl_start),.stop(ctrl_stop),.load_data(ctrl_data),
 .fault(spi_fault),.error_code(spi_error),.check_enable(ctrl_check_enable),.check_request(ctrl_request),
 .check_address(ctrl_address),.check_ready(1'b1),.check_response(ctrl_response),
 .check_response_address(ctrl_response_address),.check_data(ctrl_response_data),.check_fault(1'b0));
 integer checks=0,writes=0,reads=0,negative=0,starts=0,begins=0;
 reg [24:0] cache_cpu=0;reg [21:0] cache_ppu=0;
 reg cache_cpu_early=0,cache_ppu_early=0,cache_reply=0;reg [21:0] cache_reply_address=0;reg [7:0] cache_reply_data=0;
 wire cache_request,cache_cpu_valid,cache_ppu_valid,cache_fault;wire [21:0] cache_address;wire [7:0] cache_cpu_data,cache_ppu_data;
 nes_rom_early cache(.clk(clk),.reset(reset),.cpu_address_valid(cache_cpu_early),.ppu_address_valid(cache_ppu_early),
 .cpumem_addr(cache_cpu),.cpumem_read(1'b0),.cpu_sample(1'b0),.ppumem_addr(cache_ppu),.ppumem_read(1'b0),.ppu_sample(1'b0),
 .cpu_data(cache_cpu_data),.ppu_data(cache_ppu_data),.cpu_valid(cache_cpu_valid),.ppu_valid(cache_ppu_valid),
 .rom_ready(1'b1),.rom_request(cache_request),.rom_address(cache_address),.rom_response(cache_reply),.rom_error(1'b0),
 .rom_response_address(cache_reply_address),.rom_data(cache_reply_data),.fault_trigger(),.fault_context(),.fault(cache_fault),.error_code());
 function automatic [7:0] cache_value(input [21:0] a);return a[7:0]^a[15:8]^{2'b0,a[21:16]};endfunction
 always @(posedge clk)begin
  if(reset)cache_reply<=0;
  else begin
   cache_reply<=cache_request;
   if(cache_request)begin cache_reply_address<=cache_address;cache_reply_data<=cache_value(cache_address);end
  end
 end
 task automatic cache_read(input bit ppu,input [21:0] address);
  @(negedge clk);cache_cpu_early=0;cache_ppu_early=0;
  if(ppu)cache_ppu=address;else cache_cpu={3'd0,address};
  #1;ck(ppu?!cache_ppu_valid:!cache_cpu_valid);
  if(ppu)cache_ppu_early=1;else cache_cpu_early=1;
  if(ppu)wait(cache_ppu_valid);else wait(cache_cpu_valid);
  ck(!cache_fault && (ppu?cache_ppu_data:cache_cpu_data)===cache_value(address));
  repeat(3)@(negedge clk);cache_cpu_early=0;cache_ppu_early=0;
 endtask
 always @(posedge mem_clk)begin if(ctrl_start)starts++;if(ctrl_begin)begins++;end
 task automatic ck(input bit value);checks++;if(!value)$fatal(1,"PATH147 check=%0d count=%h boot=%h spi=%h",checks,loaded_bytes,boot_error,spi_error);endtask
 task automatic fresh;
  @(negedge mem_clk);reset=1;load_begin=0;load_valid=0;load_end=0;start=0;stop=0;check_enable=0;check_request=0;status_loaded=0;status_count=0;ctrl_response=0;
  SPI_SS=1;SPI_SCK=0;#200;reset=0;#200;
 endtask
 function automatic [21:0] physical(input [18:0] n);physical=n<19'h40000 ? {3'd0,n} : 22'h200000+(n-19'h40000);endfunction
 task automatic write_boundary(input [18:0] n);
  reg [21:0] a;realtime t;
  fresh();@(negedge mem_clk);load_begin=1;@(negedge mem_clk);load_begin=0;ck(load_ready);
  boot.loader.loaded_bytes=n;a=physical(n);
  load_valid=1;@(negedge mem_clk);load_valid=0;
  wait(!psram_we);t=$realtime;
  ck({psram_address[19:0],psram_1ce,!psram_ble}===a);
  ck(psram_data===16'h5a5a && psram_oe && (!psram_1ce ^ !psram_2ce));
  wait(psram_we);ck($realtime-t>=375.0);wait(loaded_bytes==n+1);ck(!boot_fault);writes++;
 endtask
 task automatic read_boundary(input [18:0] n);
  fresh();@(negedge mem_clk);load_begin=1;@(negedge mem_clk);load_begin=0;
  boot.loader.loaded_bytes=19'h60000;load_end=1;@(negedge mem_clk);load_end=0;ck(loaded);
  check_enable=1;wait(check_ready);@(negedge mem_clk);check_address=n;check_request=1;
  @(negedge mem_clk);check_request=0;wait(!psram_oe);
  ck({psram_address[19:0],psram_1ce,n[0]}===physical(n));
  wait(check_response);ck(check_response_address===n && check_data===(n[0]?8'h34:8'h12));reads++;
 endtask
 reg [7:0] tx[0:7],rx[0:7];
 function automatic [7:0] crc_byte(input [7:0] p,input [7:0] v);
  reg [7:0] c;c=p^v;repeat(8)c=c[7]?(c<<1)^8'h07:c<<1;return c;
 endfunction
 task automatic command(input [7:0] op,input [23:0] offset,input [7:0] arg);
  reg [7:0] c;
  tx[0]=op;tx[1]=offset[23:16];tx[2]=offset[15:8];tx[3]=offset[7:0];tx[4]=arg;tx[5]=~arg;
  c=0;for(integer k=0;k<6;k++)c=crc_byte(c,tx[k]);tx[6]=c;tx[7]=8'ha5;
  SPI_SS=0;#120;
  for(integer j=0;j<64;j++)begin SPI_MOSI=tx[j/8][7-j%8];#60;SPI_SCK=1;#60;rx[j/8][7-j%8]=spi_miso;SPI_SCK=0;end
  #120;SPI_SS=1;#240;
 endtask
 task automatic ack_boundary(input [18:0] n);
  fresh();status_loaded=1;status_count=19'h60000;
  command(8'h66,0,0);ck(!spi_fault && ctrl_check_enable);
  @(negedge mem_clk);control.check_next=n;#100;
  command(8'h67,{5'd0,n},0);ck(!spi_fault);
  @(negedge mem_clk);ctrl_response_address=n;ctrl_response=1;@(negedge mem_clk);ctrl_response=0;
  command(8'h68,{5'd0,n},8'ha6);ck(!spi_fault && ctrl_address===n+19'd1);
  command(8'h6a,0,0);ck(rx[1]==8'h5f && {rx[4],rx[5],rx[6]}=={5'd0,n+19'd1});
 endtask
 initial begin
  fresh();cache_read(0,22'h001234);cache_read(0,22'h011234);cache_read(0,22'h031234);
  cache_read(1,22'h200123);cache_read(1,22'h208123);cache_read(1,22'h210123);cache_read(1,22'h218123);
  write_boundary(0);write_boundary(19'hffff);write_boundary(19'h10000);write_boundary(19'h1ffff);
  write_boundary(19'h20000);write_boundary(19'h3ffff);write_boundary(19'h40000);write_boundary(19'h5ffff);
  read_boundary(0);read_boundary(19'hffff);read_boundary(19'h10000);read_boundary(19'h3ffff);
  read_boundary(19'h40000);read_boundary(19'h5ffff);
  // Out-of-range CHECK and early END remain fail-closed.
  @(negedge mem_clk);check_address=19'h60000;check_request=1;@(negedge mem_clk);check_request=0;ck(check_fault);negative++;
  fresh();@(negedge mem_clk);load_begin=1;@(negedge mem_clk);load_begin=0;load_end=1;
  @(negedge mem_clk);load_end=0;ck(boot_fault && boot_error==2);negative++;
  // Old80/96KiB BEGIN cannot accidentally select this fixed384KiB decoder.
  fresh();command(8'h60,0,0);ck(spi_fault && spi_error==3);negative++;
  fresh();command(8'h60,0,1);ck(spi_fault && spi_error==3);negative++;
  fresh();command(8'h60,0,2);ck(!spi_fault && begins==1);
  status_count=19'h60000;command(8'h65,0,0);ck(rx[1]==8'h5f && {rx[4],rx[5],rx[6]}==24'h060000);
  ack_boundary(19'hffff);ack_boundary(19'h1ffff);ack_boundary(19'h3ffff);ack_boundary(19'h5ffff);
  command(8'h69,24'h60000,0);ck(!spi_fault && control.verified);
  command(8'h63,24'h60000,0);ck(!spi_fault && starts==1);
  fresh();status_loaded=1;status_count=19'h60000;command(8'h63,24'h60000,0);ck(spi_fault && spi_error==8);negative++;
  fresh();status_count=19'h40000;command(8'h61,24'h000000,0);ck(spi_fault && spi_error==5);negative++;
  $display("PASS PATH147 checks=%0d writes=%0d reads=%0d negative=%0d",checks,writes,reads,negative);$finish;
 end
 initial begin #10000000;$fatal(1,"PATH147 watchdog");end
endmodule
