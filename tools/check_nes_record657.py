"""Run the board record width and verify cancellation before the first header."""
import argparse
from pathlib import Path

from check_nes_stream656 import check_rows, directed
from check_nes_serial654 import bench as ordinary
from check_nes_sender652 import prepare
from nes_direct653 import encode
from nes_raw506 import once


def bench(source, guards, split, count, direct, audit):
    source=directed(source,False,False) if guards else ordinary(source)
    if not count:
        source=once(source,"[95:0] data,record_data","[79:0] data,record_data")
        source=once(source,".WIDTH(96)) records",".WIDTH(80)) records")
    if split:
        source=once(once(once(source,"[79:0] data,record_data","[41:0] data,record_data"),".WIDTH(80)) records",".WIDTH(42)) records"),".tx_data(record_data)",".segment(record_data)")
    if direct:
        source=once(source,".WIDTH(80)) records",".WIDTH(80),.EXTERNAL_PAYLOAD(1)) records")
        source=once(source," reg [7:0] rx", """ reg [63:0] launched;
 always @(posedge nes)if(!reset && tx && tr)launched<=record_data[63:0];
 always @(negedge nes)if(!reset && records.request!=records.ack_sync[1] && launched!==record_data[63:0])
  $fatal(1,"source payload changed before return");
 reg [7:0] rx""")
    if audit:
        assert count and not guards
        source=once(source," reg [7:0] rx",""" integer launched_fd,accepted_fd;
 initial begin launched_fd=$fopen("launch.txt","w");accepted_fd=$fopen("accept.txt","w");end
 always @(posedge nes)if(!reset && tx && tr)$fwrite(launched_fd,"%0t %024x\\n",$time,record_data);
 always @(posedge clk)if(!reset && valid && ready)$fwrite(accepted_fd,"%0t %024x\\n",$time,data);
 reg [7:0] rx""")
    if not guards:
        return source
    if direct:
        source=once(source,"always #5.952 clk=~clk;", "reg host_running=1;always #5.952 if(host_running)clk=~clk;")
        source=once(source,'  $fclose(out);',"""  // Pause the destination before launch, revoke the lease while REQ is held.
  reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
  @(negedge clk);host_running=0;
  @(negedge nes);generation=16'hb34f;owned=1;wait(records.request!=records.ack_sync[1]);
  @(negedge nes);owned=0;wait(release_frame);repeat(12)begin
   @(negedge nes);if(!src.cancel_pending || !records.request)$fatal(1,"lost pending ownership");
  end
  host_running=1;wait(dut.available);request(8'hd0,0,0);transfer(8);status_check;
  if({rx[5],rx[6]}!==24)$fatal(1,"lost header or cancel");
  spi_tx[0]=8'hd1;transfer(27);
  if({rx[1],rx[2],rx[3],rx[4]}!==32'he000b34f ||
     {rx[13],rx[14],rx[15],rx[16]}!==32'he002b34f || rx[24]!==1)$fatal(1,"paused capture order");
  crc=16'hffff;for(j=1;j<=24;j++)crc=c16(crc,rx[j]);
  if({rx[25],rx[26]}!==crc)$fatal(1,"paused capture CRC");
  $fclose(out);""")
    if split:
        source=once(source,'  $fclose(out);',"""  // Revoke after the first fragment is launched. Only ABORT can become visible.
  reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
  @(negedge nes);generation=16'hb42c;owned=1;wait(src.suffix);@(negedge nes);owned=0;
  wait(dut.available);request(8'hd0,0,0);transfer(8);status_check;
  if({rx[5],rx[6]}!==12)$fatal(1,"partial header visible");
  spi_tx[0]=8'hd1;transfer(15);
  if({rx[1],rx[2],rx[3],rx[4]}!==32'he002b42c || rx[12]!==1)$fatal(1,"cancelled prefix identity");
  crc=16'hffff;for(j=1;j<=12;j++)crc=c16(crc,rx[j]);
  if({rx[13],rx[14]}!==crc)$fatal(1,"cancelled prefix CRC");
  $fclose(out);""")
    return once(source,'  $fclose(out);',"""  // A rejected lease may send ABORT before the host sees its header.
  reset=1;owned=0;repeat(12)@(negedge nes);reset=0;repeat(12)@(negedge nes);
  generation=16'hca71;owned=1;wait(src.state==src.HEADER);@(negedge nes);owned=0;
  wait(dut.available);request(8'hd0,0,0);transfer(8);status_check;
  if({rx[5],rx[6]}!==16'd12)$fatal(1,"abort before header length");
  spi_tx[0]=8'hd1;transfer(15);
  if({rx[1],rx[2],rx[3],rx[4]}!==32'he002ca71 || rx[12]!==1)
   $fatal(1,"abort before header identity");
  crc=16'hffff;for(j=1;j<=12;j++)crc=c16(crc,rx[j]);
  if({rx[13],rx[14]}!==crc)$fatal(1,"abort before header CRC");
  $fclose(out);""")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("out","board","data","bin"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--guards",action="store_true")
    mode=p.add_mutually_exclusive_group()
    mode.add_argument("--split",action="store_true")
    mode.add_argument("--count",action="store_true")
    mode.add_argument("--direct",action="store_true")
    p.add_argument("--audit",action="store_true")
    a=p.parse_args()
    prepare(a,encoder=encode,codec="nes_geometry_sender653.sv",bench=lambda s:bench(s,a.guards,a.split,a.count,a.direct,a.audit))
    if a.guards:check_rows((a.out/"blocks.txt").read_text().splitlines())
