// SPDX-License-Identifier: MIT
// Uses the054 SPI tasks without changing frozen054 expectations/evidence.
 integer geometry_checks=0;
 task automatic geometry(input bit expected);
  #1;geometry_checks++;
  if(rom_chr32!==expected)$fatal(1,"Geometry check%0d expected%0d got%b",geometry_checks,expected,rom_chr32);
 endtask
 initial begin
  fresh();geometry(0);
  command(8'h60,0,1);geometry(1);check(load_ready&&!run_enable);
  // Protocol accepts the BEGIN frame, loader rejects it while receiving.
  // Its argument latch changes to0; the accepted configuration MUST stay1.
  command(8'h60,0,0);geometry(1);check(boot_fault&&boot_error==1&&!run_enable);
  fresh();command(8'h60,0,0);geometry(0);
  frame(8'h60,0,1);tx[6]^=1;transfer(64);geometry(0);protocol_failure(2);
  fresh();command(8'h60,0,1);geometry(1);
  command(8'h61,0,8'h55);geometry(1);check(loaded_bytes==1);
  command(8'h64,1,0);geometry(1);check(!loaded&&!run_enable&&loaded_bytes==0);
  command(8'h60,0,0);geometry(0);check(load_ready);
  command(8'h64,0,0);command(8'h60,0,1);geometry(1);
  fresh();frame(8'h60,0,1);transfer(63);geometry(0);protocol_failure(1);
  fresh();frame(8'h60,0,1);tx[7]=0;transfer(64);geometry(0);protocol_failure(2);
  fresh();command(8'h60,0,2);geometry(0);protocol_failure(3);
  fresh();command(8'h60,1,1);geometry(0);protocol_failure(5);
  $display("PASS SPI GEOMETRY checks=%0d negative_cases=%0d",geometry_checks,negative_cases);
  spi_done=1;
 end
