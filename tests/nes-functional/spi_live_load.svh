// SPDX-License-Identifier: MIT
// 055 stimulus only: accelerated digital SPI, not the STM32 callback waveform.
 reg SPI_SS=1,SPI_SCK=0,SPI_MOSI=0;
 wire spi_miso,spi_selected,spi_fault;wire [3:0] spi_error;
 reg [7:0] tx[0:7],rx[0:7];
 integer serial_frames=0,status_checks=0;
 function automatic [7:0] crc_byte(input [7:0] p,input [7:0] v);
  reg [7:0] c;begin c=p^v;repeat(8)c=c[7]?(c<<1)^8'h07:c<<1;crc_byte=c;end
 endfunction
 task automatic command(input [7:0] op,input [23:0] address,input [7:0] arg);
  reg [7:0] c;
  tx[0]=op;tx[1]=address[23:16];tx[2]=address[15:8];tx[3]=address[7:0];tx[4]=arg;tx[5]=~arg;
  c=0;for(integer j=0;j<6;j++)c=crc_byte(c,tx[j]);tx[6]=c;tx[7]=8'ha5;
  SPI_SCK=0;SPI_SS=0;#120;
  for(integer j=0;j<64;j++)begin
   SPI_MOSI=tx[j/8][7-j%8];#60;SPI_SCK=1;#60;rx[j/8][7-j%8]=spi_miso;SPI_SCK=0;
  end
  #120;SPI_SS=1;#240;serial_frames++;
 endtask
 task automatic status(input integer count,input [7:0] flags);
  command(8'h65,0,0);status_checks++;
  if(rx[1]!==8'h54 || rx[2]!==flags || rx[3]!==0 ||
     {rx[4],rx[5],rx[6]}!==count[23:0] || rx[7]!==0)
   $fatal(1,"SPI status expected count=%0d flags=%0d received=%h %h %h %h %h %h %h",count,flags,rx[1],rx[2],rx[3],rx[4],rx[5],rx[6],rx[7]);
 endtask
 always @(posedge mem_clk)if(!boot_reset && (spi_fault || boot_fault))
  $fatal(1,"SPI/BOOT fault=%0d/%0d bytes=%0d",spi_error,boot_error,loaded_bytes);
 initial begin
  integer total;
  wait(!boot_reset);repeat(4)@(negedge mem_clk);
  total=65536+(chr_32k?32768:16384);command(8'h60,0,{7'd0,chr_32k});status(0,1);
  for(integer b=0;b<total;b++)begin
   if(!load_ready)$fatal(1,"SPI byte not ready %0d",b);
   command(8'h61,b,b<65536?prg[b]:chr[b-65536]);
   if(loaded_bytes!==b+1 || loaded || run_enable)$fatal(1,"SPI byte commit %0d",b);
   // A full buffer refuses further DATA before END marks it loaded.
   if((b+1)%16384==0)begin status(b+1,b+1==total?0:1);$display("SPI PROGRESS bytes=%0d time=%0t",b+1,$time);end
  end
  if(memory.writes!=total)$fatal(1,"SPI pin write count");
  for(integer b=0;b<65536;b++)if(memory.prg[b]!==prg[b])$fatal(1,"SPI PRG mismatch %0d",b);
  for(integer b=0;b<total-65536;b++)if(memory.chr[b]!==chr[b])$fatal(1,"SPI CHR mismatch %0d",b);
  command(8'h62,total,0);status(total,2);
  if(!loaded || run_enable)$fatal(1,"SPI END handshake");
  command(8'h63,total,0);status(total,6);
  if(!run_enable)$fatal(1,"SPI START handshake");
  $display("SPI BOOT bytes=%0d pin_writes=%0d run=%0d frames=%0d status_checks=%0d",loaded_bytes,memory.writes,run_enable,serial_frames,status_checks);
 end
