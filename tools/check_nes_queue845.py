"""Exercise the unchanged board queue with the palette heads actually preceding SEAL."""
import argparse
from pathlib import Path
from analyze_nes_section841 import folder, packets
from nes_dma845 import base
from check_nes_repeat833 import prepare as queue_fixture


def prepare(dest):
    queue_fixture(base.TEMP,dest)
    data=packets(folder(1,"844objdonefixed"))[-3:]
    assert [(b[0],b[1]) for b in data]==[(2,3),(4,3),(3,0)]
    (dest/"heads.hex").write_text("\n".join(b.ljust(256,b"\0").hex(" ") for b in data)+"\n")
    tb=dest/"repeat833_tb.sv"
    common=tb.read_text().split(" reg [7:0] heads")[0]
    tb.write_text(common+"""
 reg [7:0] bytes845[0:767];
 task submit845(input integer i);
  integer n;reg [15:0] crc;
  n=16+bytes845[256*i+12]+256*bytes845[256*i+13];tx[0]='he1;crc=c16('hffff,'he1);
  for(int b=0;b<n;b++)begin tx[b+1]=bytes845[256*i+b];crc=c16(crc,tx[b+1]);end
  tx[n+1]=crc[15:8];tx[n+2]=crc[7:0];transfer(n+3);
 endtask
 task ack845(input integer i,input bit bad);
  integer n;
  n=16+bytes845[256*i+12]+256*bytes845[256*i+13];
  for(int b=0;b<n;b++)begin
   address='h400000+b;#50;rn=0;#85;
   if(oe||!dir||dout!==bytes845[256*i+b])$fatal(1,"wrong queue head");
   rn=1;#65;
  end
  ack[0]=i==2?1:0;ack[1]=bytes845[256*i];for(int b=2;b<10;b++)ack[b]=bytes845[256*i+b];
  ack[10]='h65;ack[11]='h9a;if(bad)ack[8]^=1;
  publish();status();
 endtask
 initial begin
  $readmemh("heads.hex",bytes845);
  for(int failat=0;failat<4;failat++)begin
   restart();for(int i=0;i<3;i++)submit845(i);
   status();if(fault||{rx[3],rx[4]}!=3||{rx[5],rx[6]}!=0)$fatal(1,"queue before receipts");
   for(int i=0;i<3;i++)begin
    ack845(i,i==failat);
    if(i==failat)begin
     if(!fault||{rx[5],rx[6]}!=i||dut.endpoint.packet_ready)$fatal(1,"bad receipt released a head");
     break;
    end
    if(fault||{rx[5],rx[6]}!=i+1)$fatal(1,"lost checked retirement");
    if(i==2 && (!rx[2][1]||rx[7]!=1||rx[8]!=3))$fatal(1,"no final receipt");
   end
  end
  $display("PASS845 queued palette DATA and RLE then SEAL, three wrong identities blocked, final ACK checked");$finish;
 end
 initial begin #30000000;$fatal(1,"timeout");end
endmodule
""",newline="\n")
    job=dest/"job.ps1"
    job.write_text(job.read_text().replace("PASS833","PASS845"),newline="\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("dest",type=Path)
    prepare(p.parse_args().dest)
