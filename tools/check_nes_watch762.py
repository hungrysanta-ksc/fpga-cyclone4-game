# SPDX-License-Identifier: MIT
"""Generate a pin-level test from 753-family transfers, including the real E1 packet CRC."""
import argparse
import csv
import json
from pathlib import Path
from nes_raw506 import once

CORE = """ reg [7:0] stimulus[0:1535];
 task send_record(input int length);
  reg [15:0] crc;
  crc=16'hffff;
  for(int i=0;i<=16+length;i++)crc=c16(crc,tx[i]);
  tx[17+length]=crc[15:8];tx[18+length]=crc[7:0];
  transfer(19+length);publish();
  if(fault)$fatal(1,"packet admission");
 endtask
 task load_page(input int bank,input int startoff);
  prepare(0,1);head[12]=12;
  for(int i=0;i<16;i++)tx[i+1]=head[i];
  for(int i=0;i<12;i++)tx[17+i]=0;
  tx[19]=bank;send_record(12);
  for(int k=0;k<8;k++)begin
   prepare(k+1,2);head[10]=startoff+192*k;head[11]=(startoff+192*k)>>8;head[12]=192;
   for(int i=0;i<16;i++)tx[i+1]=head[i];
   for(int i=0;i<192;i++)tx[17+i]=stimulus[192*k+i];
   send_record(192);
  end
 endtask
 task arm(input int src);
  write_byte('h6006,src);write_byte('h6007,src>>8);
 endtask
 task result(input bit good);
  address='h6006;rn=0;wn=1;#100;
  if(oe||!dir||dout!==(good?8'h80:8'h00))$fatal(1,"result %x expected %d",dout,good);
  rn=1;#150;
 endtask
 task exercise(input int bank,input int src,input int mode);
  restart();load_page(bank,src&4095);arm(src);
  for(int i=0;i<1536;i++)begin
   if(mode==4&&i==1535)break;
   address='h7f0000+src+i+(mode==6&&i==1535);
   pp='h18+(i&1)+(mode==3&&i==1535);rn=0;wn=1;
   din=~stimulus[i];#26;pw=0;#25;
   if(!listen||dir||!oe)$fatal(1,"receiver direction");
   din=stimulus[i]^(mode==1&&i==1535);#75;
   if(i==1535&&dut.pass762)$fatal(1,"premature pass");
   if(i==1535&&mode==2)begin stop=1;#1;if(dut.pass762||listen)$fatal(1,"STOP");end
   pw=1;rn=1;din='h5a;#140;
  end
  if(mode==5)begin
   address='h7f0000+src+1536;pp='h18;rn=0;pw=0;#100;pw=1;rn=1;#100;
  end
  if(mode!=4)result(mode==0);
  prepare(9,3);transfer(19);publish();
  if(mode==0)begin
   if(fault||dut.endpoint.retired!=10)$fatal(1,"final ACK");
  end else if(dut.endpoint.retired!=9)$fatal(1,"invalid final ACK");
 endtask
"""
def prepare(trace,packets,board,out):
    out.mkdir(parents=True,exist_ok=False)
    src=Path('tests/nes-functional/progress680_tb.sv').read_text()
    src=once(src,'module progress680_tb;', 'module watch762_tb;')
    src=once(src,' nes_sink_bridge165 dut(', ' reg [7:0] pp=0;reg pw=1;wire listen;\n nes_sink_bridge165 dut(.periph_addr(pp),.pawr_n(pw),.receive762(listen),')
    src=src[:src.index(' initial begin')]+CORE
    tests=[' initial begin #(PHASE);']
    for g in (952,957):
        # The CPU pin log is decoded independently against original E1s.
        rows=list(csv.DictReader((trace/'wire762.csv').open()))
        beats=[r for r in rows if int(r['g'])==g and r['event']=='write']
        if len(beats)!=1536:
            continue
        start=int(beats[0]['source']);ref={}
        for _,_,h,_ in map(json.loads,packets.read_text().splitlines()):
            b=bytes.fromhex(h)
            if int.from_bytes(b[8:10],'little')==g and b[:2]==bytes((2,2)):
                ref.update(enumerate(b[16:],int.from_bytes(b[10:12],'little')))
        data=bytes(ref[start%4096+i] for i in range(1536))
        for i,r in enumerate(beats):
            assert (int(r['source']),int(r['port']),int(r['byte']))==(start+i,0x2118+i%2,data[i])
        (out/f'map{g}.hex').write_text(data.hex('\n')+'\n')
        tests.append(f' $readmemh("map{g}.hex",stimulus);')
        for mode in (range(7) if g==957 else [0]):
            tests.append(f' exercise({start>>15},{start},{mode});')
    assert any('exercise(0' in s for s in tests),'957 transfer missing'
    src+='\n'.join(tests)+'\n $display("PASS762 phase=%0f",PHASE);$finish;end\nendmodule\n'
    (out/'watch762_tb.sv').write_text(src)
    import shutil
    for n in ('sink-program.hex','nes_domain_reset124.sv','nes_sink_bus165.sv','nes_sink_spi165.sv',
              'nes_sink_bridge165.sv','nes_map_watch762.sv'):
        shutil.copyfile(board/n,out/n)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('trace','packets','board','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    prepare(a.trace,a.packets,a.board,a.out)
