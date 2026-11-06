"""Same physical source/host wiring in the benchmark and in the full project."""
import argparse
import binascii
from pathlib import Path
from nes_raw506 import once
from nes_direct653 import encode,map_block
from check_nes_serial654 import bench as serial_bench
from check_nes_search655 import bench as walk_bench
from check_nes_sender652 import prepare


def bind(s,fused):
    if not fused:return s
    s=once(s," nes_native_mailbox165 #(.WIDTH(96)) records("," wire wr656;wire [95:0] next656;\n nes_native_mailbox165 #(.WIDTH(96),.SHARE_WORD(1)) records(")
    s=once(s,"record_data,valid,ready,data);","record_data,valid,ready,data,wr656,next656);")
    s=once(s,"pv,pr,prepared);","pv,pr,prepared,1'b0,17'b0);")
    return once(s,"data,av,ar,aa,ag,fault);","""data,av,ar,aa,ag,fault,wr656,next656);
 reg stalled;reg [95:0] pending;
 always @(posedge clk)begin
  if(!reset && wr656 && (records.capture || valid || ready))$fatal(1,"capture/serializer collision");
  if(!reset && stalled && (!valid || data!==pending))$fatal(1,"pending word changed");
  stalled<=!reset && valid && !ready;pending<=data;
 end""")


def directed(s,fused,header):
    s=walk_bench(s,"walk")
    s=once(s,"dut.codec.state==dut.codec.CMP_B)begin","!dut.codec.wait_read && dut.codec.state==dut.codec.CMP_B)begin")
    needle='  $fclose(out);$display("PASS652");'
    wrapped=once(s,needle,"""  for(r=0;r<4;r++)begin
   reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
   for(j=0;j<99;j++)scene[j]=(r==2)?(15'h5331 ^ (j*113)):(19+(j%4)*257);
   groups=3;patches=0;objects=0;exceptions=0;palettes=1;generation=990+r;owned=1;
   case(r)
    0:wait(dut.codec.state==dut.codec.HEADER && dut.codec.index==5);
    1:wait(dut.codec.state==dut.codec.STREAM && !dut.codec.raw && dut.codec.write_en);
    2:wait(dut.codec.state==dut.codec.RAW_WAIT && dut.encoding && dut.position==6);
    3:wait(dut.codec.state==dut.codec.CRC_SCAN && !dut.codec.address[8] && dut.codec.address[7:0]==11);
   endcase
   @(negedge clk);reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
   request(8'hd0,0,0);transfer(8);status_check;
   if(rx[2][0] || {rx[3],rx[4],rx[5],rx[6]}!=0 || dut.read_seen || dut.encoding)
    $fatal(1,"partial work survived STOP");
  end
  for(j=0;j<99;j++)scene[j]=15'h4421 ^ (j*127);
  generation=999;owned=1;wait(dut.available);@(negedge clk);
  request(8'hd0,0,0);transfer(8);status_check;
  length={rx[5],rx[6]};spi_tx[0]=8'hd1;transfer(length+3);
  $fwrite(out,"RESTART ");for(j=1;j<=length+2;j++)$fwrite(out,"%02x",rx[j]);$fwrite(out,"\\n");
"""+needle)
    if header:wrapped=once(wrapped,"dut.codec.state==dut.codec.HEADER && dut.codec.index==5","dut.emitting_header && dut.position==6")
    return bind(wrapped,fused)


def check_rows(rows):
    assert len(rows)==14
    for i,row in enumerate(rows):
        tag,packet=row.split();wire=bytes.fromhex(packet)
        assert binascii.crc_hqx(wire[:-2],65535)==int.from_bytes(wire[-2:],"big")
        if i<2:
            cells=[0x5411^(j*113) for j in range(99)];generation=956;at=80*i;expected="RAW"
        elif i<12:
            k=(i-2)//2;period=(1,2,4,33,7)[k]
            cells=[0x7123 if k==4 and j in (31,32,78) else (j%period)*257+17 for j in range(99)]
            generation=960+k;at=80*(i%2);expected="MATCH"
        else:
            generation=981 if i==12 else 999;at=0;expected="COLD" if i==12 else "RESTART"
            cells=[(0x4411^(j*113)) if i==12 else (0x4421^(j*127)) for j in range(80)]
        assert tag==expected and wire[0 if at else 12:-2]==map_block(cells[at:at+80],at,generation)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("board","out","data","bin"):p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--fused",action="store_true");p.add_argument("--header",action="store_true");p.add_argument("--directed",action="store_true")
    a=p.parse_args();a.guards=a.directed
    prepare(a,encoder=encode,codec="nes_geometry_sender653.sv",
            bench=lambda s:directed(s,a.fused,a.header) if a.directed else bind(serial_bench(s),a.fused))
    if a.directed:check_rows((a.out/"blocks.txt").read_text().splitlines())
