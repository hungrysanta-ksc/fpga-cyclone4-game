# SPDX-License-Identifier: MIT
"""Residual CRC/transaction length boundary after removing duplicate registers."""
import inspect
import guard_nes_spi270 as old
from nes_delta231 import once

TB=once(old.TB,'  $display("PASS SPI270 checks=%0d",checks);$finish;',r'''
  for(integer n=0;n<=257;n++)begin
   if(n==0||n==15||n==16||n==255||n==256||n==257)begin
    clear();tx[0]=8'he1;c=crc16(16'hffff,8'he1);
    for(integer j=1;j<=n;j++)begin tx[j]=(j*17)^8'ha9;c=crc16(c,tx[j]);end
    tx[n+1]=c[15:8];tx[n+2]=c[7:0];transfer(n+3,0);
    if(n<16||n>256)begin if(!qf||queue.accepted)$fatal(1,"bad residual length %0d",n);end
    else begin
     if(qf||queue.accepted!=1||queue.packet_length!=n)$fatal(1,"valid residual length %0d",n);
     for(integer j=0;j<n;j++)if(queue.buffer[j]!==tx[j+1])$fatal(1,"payload overwritten by CRC %0d/%0d",n,j);
    end
    checks++;
   end
  end
  for(integer byte275=0;byte275<19;byte275++)begin
   for(integer bit275=0;bit275<8;bit275++)begin
    if(byte275!=0)begin
     clear();packet();tx[byte275]^=1<<bit275;transfer(19,0);
     if(!qf||queue.accepted)$fatal(1,"single-bit CRC corruption published");checks++;
    end
   end
  end
  $display("PASS SPI270 checks=%0d",checks);$display("PASS CRC275");$finish;''')
TB=TB.replace('#5000000;','#30000000;')

def main():
 ns=dict(old.__dict__);ns.update(TB=TB,__file__=__file__,__doc__=__doc__)
 exec(compile(inspect.getsource(old.main),'spi275-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
