# SPDX-License-Identifier: MIT
"""Common progress CRC/ownership plus snapshot-to-IRQ race and reset guards."""
import inspect
import guard_nes_spi270 as base
import guard_nes_spi282 as prior
from nes_delta231 import once


def testbench():
    s=prior.testbench()
    s=s.replace('transfer(9,0);check_status(9,8\'hf9)', 'transfer(12,0);check_status(12,8\'hfa)')
    s=s.replace('transfer(20,0);check_status(20,8\'hd7)', 'transfer(12,0);check_status(12,8\'hfa)')
    s=s.replace('for(integer n=8;n<=10;n=n+2)', 'for(integer n=11;n<=13;n=n+2)')
    s=s.replace('transfer(9,1)', 'transfer(12,1)')
    s=once(s,' nes_spi270 common(', ' wire irq284,mode284;reg planidle284=1;\n nes_spi270 common(.progress_irq284(irq284),.progress_mode284(mode284),')
    s=s.replace('.plan_idle(1\'b1)', '.plan_idle(planidle284)')
    s=once(s,'  $display("PASS SPI282', '''  clear();progress=128'h0102030405060708090a0b0c0d0e0f10;
  tx[0]=8'he2;transfer(12,0);check_status(12,8'hfa);
  if($isunknown({irq284,mode284})||irq284||!mode284)$fatal(1,"initial IRQ baseline");checks++;
  @(negedge clk);progress[120]=~progress[120];#1;
  if(!irq284)$fatal(1,"phase change missed");checks++;
  repeat(200)@(negedge clk);if(!irq284)$fatal(1,"notification not held");checks++;
  tx[0]=8'he2;transfer(12,0);if(irq284)$fatal(1,"snapshot did not rearm");checks++;
  planidle284=0;#1;if(!irq284)$fatal(1,"plan bank change missed");checks++;
  tx[0]=8'he2;transfer(12,0);if(irq284)$fatal(1,"plan rearm");checks++;
  planidle284=1;#1;if(!irq284)$fatal(1,"plan ready missed");checks++;
  tx[0]=8'he2;mutate=1;transfer(12,0);mutate=0;
  check_status(12,8'hfa);if(!irq284)$fatal(1,"change during snapshot lost");checks++;
  tx[0]=8'he0;transfer(24,0);if(irq284)$fatal(1,"identity view cannot arm");checks++;
  tx[0]=8'he2;transfer(12,0);reset=1;#1;
  if(irq284||mode284)$fatal(1,"reset left stale notification");checks++;reset=0;
  clear();packet();transfer(19,0);
  if(irq284)$fatal(1,"own accepted count woke IRQ");checks++;
  @(negedge clk);retire=1;@(negedge clk);retire=0;#1;
  if(!irq284)$fatal(1,"retirement missed");checks++;
  clear();tx[0]=8'he2;transfer(11,0);
  if(!qf||!irq284)$fatal(1,"output fault did not wake");checks++;
  prefix(8'hd4,0,0,0);transfer(8,0);
  if(irq284||mode284)$fatal(1,"source D4 did not restore pin ownership");checks++;
  clear();tx[0]=8'he2;transfer(12,0);
  prefix(8'hd5,0,0,0);transfer(8,0);
  if(irq284||mode284)$fatal(1,"source D5 did not restore pin ownership");checks++;
  $display("PASS SPI282''')
    return s.replace('PASS SPI282','PASS SPI284')


def main():
    ns=dict(base.__dict__);ns.update(TB=testbench(),__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(base.main).replace('PASS SPI270','PASS SPI284'),'spi284-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
