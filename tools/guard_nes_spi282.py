# SPDX-License-Identifier: MIT
"""E1/E9 immutable command-start snapshots, independent CRC and admission."""
import inspect
import guard_nes_spi270 as base
import guard_nes_spi280 as prior
from nes_delta231 import once


def testbench():
    s=prior.testbench().replace('[106:0] link','[107:0] link')
    s=once(s,'  clear();@(negedge clk);queue.accepted', '''  clear();progress=128'h0102030405060708090a0b0c0d0e0f10;packet();mutate=1;transfer(19,0);mutate=0;
  check_status(12,8'hfa);
  if(rx[2]!=0||rx[3]!=0||rx[4]!=0||rx[5]!=0||rx[6]!=0||rx[7]!=1||
     rx[8]!=1||rx[9]!=0||rx[10]!=0||queue.accepted!=1)$fatal(1,"E1 start snapshot/acceptance");checks++;
  clear();@(negedge clk);queue.accepted''')
    s=once(s,'  transfer(520,0);if(pf', '''  transfer(520,0);check_status(12,8'hfa);
  if(rx[8]!=1||rx[9]!=0||rx[10]!=0||plan.accepted!=1)$fatal(1,"E9 start snapshot");checks++;
  if(pf''')
    return s.replace('PASS SPI280','PASS SPI282')


def main():
    ns=dict(base.__dict__);ns.update(TB=testbench(),__file__=__file__,__doc__=__doc__)
    exec(compile(inspect.getsource(base.main).replace('PASS SPI270','PASS SPI282'),'spi282-main','exec'),ns);ns['main']()


if __name__=='__main__':main()
