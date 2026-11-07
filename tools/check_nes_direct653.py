"""Exercise direct writes, original map fallback, D2 ownership and STOP."""
import argparse
import binascii
from pathlib import Path
from check_nes_sender652 import prepare
from nes_direct653 import encode,map_block


def bench(s):
    a=s.index("   // All BG cells");b=s.index("   reset=1;",a)
    s=s[:a]+"""   // Cold nonrepeating map, including a short final group.
   for(j=0;j<99;j++)scene[j]=15'h5411 ^ (j*113);
   groups=3;@(negedge nes);generation=956;owned=1;
   for(i=0;i<2;i++)begin
    wait(dut.available);@(negedge clk);
    if(!dut.codec.raw)$fatal(1,"expected original record fallback");
    request(8'hd0,0,0);transfer(8);status_check;
    length={rx[5],rx[6]};spi_tx[0]=8'hd1;transfer(length+3);
    $fwrite(out,"RAW ");for(j=1;j<=length+2;j++)$fwrite(out,"%02x",rx[j]);$fwrite(out,"\\n");
    request(8'hd2,i,0);transfer(8);status_check;
   end
"""+s[b:]
    # Break the immutable capture during an unsealed map. Leave the lease
    # disabled through the mailbox handshake; only E002 may terminate it.
    needle="   $readmemh(\"scene955.hex\",scene);g=954;groups=32;"
    return s.replace(needle, """   $readmemh("scene955.hex",scene);g=954;groups=32;
   @(negedge nes);generation=955;owned=1;wait(dut.cells==8 && !dut.sealed);
   @(negedge nes);owned=0;wait(dut.available);@(negedge clk);
   if(dut.cells || dut.compact)$fatal(1,"partial map masked ABORT");
   request(8'hd0,0,0);transfer(8);status_check;
   length={rx[5],rx[6]};spi_tx[0]=8'hd1;transfer(length+3);
   if(length!=24 || {rx[13],rx[14],rx[15],rx[16]}!==32'he00203bb)
    $fatal(1,"missing ABORT");
   crc=16'hffff;for(j=1;j<=length;j++)crc=c16(crc,rx[j]);
   if(crc!=={rx[length+1],rx[length+2]})$fatal(1,"ABORT CRC");
   reset=1;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);""")



if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("out","board","data","bin"):p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--guards",action="store_true");a=p.parse_args()
    prepare(a,encoder=encode,codec="nes_geometry_sender653.sv",bench=bench)
    if a.guards:
        cells=[(0x5411^(j*113))&32767 for j in range(99)]
        rows=(a.out/"blocks.txt").read_text().splitlines()
        assert len(rows)==2
        for i,row in enumerate(rows):
            _,wire=row.split();data=bytes.fromhex(wire);start=80*i
            assert data[12 if i==0 else 0:-2]==map_block(cells[start:80 if not i else 99],start,956)
            assert binascii.crc_hqx(data[:-2],65535)==int.from_bytes(data[-2:],"big")
