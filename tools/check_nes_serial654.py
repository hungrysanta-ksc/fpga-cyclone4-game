"""Qualify the shared serializer and streamed request/response CRCs."""
import argparse
import binascii
from pathlib import Path
from nes_raw506 import once
from check_nes_direct653 import bench as direct_bench
from check_nes_sender652 import prepare
from nes_direct653 import encode,map_block

def bench(s):
    s=direct_bench(s)
    s=once(s,"||dut.encoding))","||(dut.encoding&&!dut.raw_format)))")
    needle='  $fclose(out);$display("PASS652");'
    return once(s,needle,"""  if($test$plusargs("GUARDS"))begin
   // Invalid prefix/argument/complement/CRC/tail may never generate PREPARED.
   for(i=0;i<6;i++)begin
    reset=1;repeat(8)@(negedge clk);reset=0;repeat(8)@(negedge clk);
    request(8'hd3,956,1);
    case(i)
     0:spi_tx[1]=1;1:spi_tx[4]=3;2:spi_tx[5]^=1;
     3:spi_tx[6]^=1;4:spi_tx[7]^=1;5:;
    endcase
    if(i<=2)begin spi_tx[6]=0;for(j=0;j<6;j++)spi_tx[6]=c8(spi_tx[6],spi_tx[j]);end
    transfer(i==5?7:8);
    if(!fault || av || dut.token)$fatal(1,"bad control accepted");
   end
   // A reset while the shared shifter is emitting a raw fallback record
   // must discard both byte and credit ownership. No partially emitted
   // header or high cell byte is allowed into a later transaction.
   reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
   for(j=0;j<99;j++)scene[j]=15'h5411 ^ (j*113);
   groups=3;generation=957;owned=1;wait(dut.raw_format && dut.encoding && dut.position==5);
   reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
   request(8'hd0,0,0);transfer(8);status_check;
   if(rx[2][0] || {rx[3],rx[4],rx[5],rx[6]}!=0 || dut.read_seen || dut.encoding)$fatal(1,"raw STOP");
  end
"""+needle)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("board","out","data","bin"):p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--guards",action="store_true");a=p.parse_args()
    prepare(a,encoder=encode,codec="nes_geometry_sender653.sv",bench=bench)
    if a.guards:
        rows=(a.out/"blocks.txt").read_text().splitlines()
        cells=[(0x5411^(j*113))&32767 for j in range(99)]
        assert len(rows)==2
        for i,row in enumerate(rows):
            wire=bytes.fromhex(row.split()[1]);at=i*80
            assert wire[12 if i==0 else 0:-2]==map_block(cells[at:99 if i else 80],at,956)
            assert binascii.crc_hqx(wire[:-2],65535)==int.from_bytes(wire[-2:],"big")
