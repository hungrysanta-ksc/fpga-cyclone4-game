# SPDX-License-Identifier: MIT
"""Actual E1 MISO pre-admission/retirement/wrap snapshots and retained SPI guards."""
import inspect
import guard_nes_spi270 as old
from nes_delta231 import once

TB=once(old.TB,'  $display("PASS SPI270 checks=%0d",checks);$finish;',r'''
  clear();packet();transfer(19,0);check_status(9,8'hf9);
  if(queue.accepted!=1||{rx[3],rx[4]}!=0||{rx[5],rx[6]}!=0)$fatal(1,"E1 snapshot included current admission");checks++;
  packet();transfer(19,0);check_status(9,8'hf9);
  if(queue.accepted!=2||{rx[3],rx[4]}!=1||{rx[5],rx[6]}!=0)$fatal(1,"E1 queued snapshot");checks++;
  @(negedge clk);retire=1;@(negedge clk);retire=0;
  packet();transfer(19,0);check_status(9,8'hf9);
  if(queue.accepted!=3||{rx[3],rx[4]}!=2||{rx[5],rx[6]}!=1)$fatal(1,"E1 retirement snapshot");checks++;
  clear();queue.accepted=16'hffff;queue.retired=16'hffff;
  packet();transfer(19,0);check_status(9,8'hf9);
  if(queue.accepted!=0||{rx[3],rx[4]}!=16'hffff||{rx[5],rx[6]}!=16'hffff)$fatal(1,"E1 wrap snapshot");checks++;
  clear();packet();tx[18]^=1;transfer(19,0);check_status(9,8'hf9);
  if(!qf||queue.accepted!=0)$fatal(1,"valid pre-snapshot acknowledged bad packet");checks++;
  $display("PASS SPI270 checks=%0d",checks);$display("PASS E1_SNAPSHOT271");$finish;''')

def main():
 ns=dict(old.__dict__);ns.update(TB=TB,__file__=__file__,__doc__=__doc__)
 exec(compile(inspect.getsource(old.main),'spi271-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
