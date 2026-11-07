"""Exercise ties, the 32-cell cap, overlap and tail references on the board SPI."""
import argparse
import binascii
from pathlib import Path
from check_nes_sender652 import prepare
from check_nes_serial654 import bench as serializer_bench
from nes_direct653 import encode,map_block
from nes_raw506 import once

def bench(s,mode):
    s=serializer_bench(s)
    pair=mode!="walk"
    address_test="""if(dut.current_word!==scene[cell_at] ||
        dut.reference_word!==scene[cell_at-dut.codec.distance])$fatal(1,"paired cell data");""" if pair else """
      if(dut.read_byte!==(dut.codec.address[0]?scene[cell_at][15:8]:scene[cell_at][7:0]))$fatal(1,"walk target");
    end
    if(!reset && dut.active && dut.codec.state==dut.codec.CMP_B)begin
      cell_at=dut.cell_base+dut.codec.index+dut.codec.length-dut.codec.distance;
      if(dut.codec.address[7:1]!==7'(cell_at-dut.cell_base) ||
         dut.read_byte!==(dut.codec.address[0]?scene[cell_at][15:8]:scene[cell_at][7:0]))$fatal(1,"walk reference");"""
    s=once(s," integer file_in,", """ integer cell_at;
 always @(posedge clk)begin
    if(!reset && dut.active && dut.codec.state==dut.codec.CMP_A)begin
      cell_at=dut.cell_base+dut.codec.index+dut.codec.length;
      if(dut.codec.distance>dut.codec.index || dut.codec.length>=32 ||
         dut.codec.index+dut.codec.length>=dut.cells ||
         dut.codec.address[7:1]!==7'(cell_at-dut.cell_base))$fatal(1,"match bounds");
      """+address_test+"""
    end
 end
 integer file_in,""")
    if mode=="mask":s=s.replace("dut.codec.length","dut.codec.best")
    return once(s,'  $fclose(out);$display("PASS652");',"""  for(r=0;r<5;r++)begin
   reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
   for(j=0;j<99;j++)begin
    case(r)
     0:n=1;1:n=2;2:n=4;3:n=33;default:n=7;
    endcase
    scene[j]=r==4 && (j==31 || j==32 || j==78) ? 15'h7123 : (j%n)*257+17;
   end
   groups=3;patches=0;objects=0;exceptions=0;palettes=1;generation=960+r;owned=1;
   for(i=0;i<2;i++)begin
    wait(dut.available);@(negedge clk);request(8'hd0,0,0);transfer(8);status_check;
    length={rx[5],rx[6]};spi_tx[0]=8'hd1;transfer(length+3);
    $fwrite(out,"MATCH ");for(j=1;j<=length+2;j++)$fwrite(out,"%02x",rx[j]);$fwrite(out,"\\n");
    request(8'hd2,i,0);transfer(8);status_check;
   end
  end
  // Kill a multi-cell match between address issue and result use. Restart
  // with a disjoint map so stale lane/length or RAM data cannot pass.
  reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
  for(j=0;j<99;j++)scene[j]=17+(j%4)*257;
  generation=980;owned=1;wait(dut.active && dut.codec.state==dut.codec.CMP_A &&
                              dut.codec.PROGRESS==3);
  @(negedge clk);reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
  request(8'hd0,0,0);transfer(8);status_check;
  if(rx[2][0] || {rx[3],rx[4],rx[5],rx[6]}!=0)$fatal(1,"search STOP");
  for(j=0;j<99;j++)scene[j]=15'h4411^(j*113);
  generation=981;owned=1;wait(dut.available);@(negedge clk);
  request(8'hd0,0,0);transfer(8);status_check;
  length={rx[5],rx[6]};spi_tx[0]=8'hd1;transfer(length+3);
  $fwrite(out,"COLD ");for(j=1;j<=length+2;j++)$fwrite(out,"%02x",rx[j]);$fwrite(out,"\\n");
  $fclose(out);$display("PASS652");""".replace("dut.codec.PROGRESS","dut.codec.best" if mode=="mask" else "dut.codec.length"))

def profile_bench(s):
    s=serializer_bench(s)
    s=once(s," integer file_in,", """ integer prof,probes=0,second_reads=0,search_steps=0;
 always @(posedge clk)if(!reset && dut.active)begin
    if(dut.codec.state==dut.codec.CMP_A)probes=probes+1;
    if(dut.codec.state==dut.codec.CMP_B)second_reads=second_reads+1;
    if(dut.codec.state==dut.codec.SEARCH)search_steps=search_steps+1;
 end
 integer file_in,""")
    s=once(s,'  file_in=$fopen','  prof=$fopen("search.txt","w");file_in=$fopen')
    return once(s,'    $fwrite(out,"%0d %0d', '''    $fdisplay(prof,"%0d %0d %0d %0d %0d",g,i,probes,second_reads,search_steps);
    probes=0;second_reads=0;search_steps=0;
    $fwrite(out,"%0d %0d''')


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("board","out","data","bin"):p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--mode",choices=("base","walk","pair","mask"),required=True)
    p.add_argument("--profile",action="store_true")
    a=p.parse_args();a.guards=not a.profile
    if a.profile:
        prepare(a,encoder=encode,codec="nes_geometry_sender653.sv",bench=profile_bench,generations=(955,))
        raise SystemExit(0)
    assert a.mode!="base"
    prepare(a,encoder=encode,codec="nes_geometry_sender653.sv",bench=lambda s:bench(s,a.mode))
    rows=(a.out/"blocks.txt").read_text().splitlines()
    assert len(rows)==13
    for ident,period in enumerate((1,2,4,33,7)):
        cells=[0x7123 if ident==4 and i in (31,32,78) else (i%period)*257+17 for i in range(99)]
        for i in range(2):
            label,packet=rows[2+2*ident+i].split()
            wire=bytes.fromhex(packet)
            assert label=="MATCH" and wire[0 if i else 12:-2]==map_block(cells[80:] if i else cells[:80],80*i,960+ident)
            assert binascii.crc_hqx(wire[:-2],65535)==int.from_bytes(wire[-2:],"big")
    tag,packet=rows[-1].split();wire=bytes.fromhex(packet)
    assert tag=="COLD" and wire[12:-2]==map_block([0x4411^(i*113) for i in range(80)],0,981)
    assert binascii.crc_hqx(wire[:-2],65535)==int.from_bytes(wire[-2:],"big")
