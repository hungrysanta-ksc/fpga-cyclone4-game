# SPDX-License-Identifier: MIT
"""041 diagnostic: same040 behavior; latch exact frontend predicates pre-update."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys
from nes_h1_spi import replace,sha
from nes_h1_release import frontend as release_frontend
from nes_h1_fault import boundary as fault_boundary,source as fault_source,session as fault_session
ROOT=Path(__file__).resolve().parents[1]

def frontend():
 s=release_frontend()
 s=replace(s,' output reg [3:0] frontend_error',' output reg [127:0] frontend_snapshot,\n output reg [3:0] frontend_error')
 monitor="""
 // Read-only instrumentation. Counts are pre-edge samples in host_clk cycles,
 // saturating at255; they are not analog pulse measurements.
 reg sampled_read_n;
 reg [7:0] low_count,high_count,last_low_count,last_high_count;
 wire [7:0] causes={1'b0,
  (pending==2 && !local_pending && !(payload_pending ? data_valid : reg_rvalid)),
  (!rd_sync[1] && rd_previous && raw_read && is_payload(addr_sync) && !romsel_n &&
   !(frontend_error==0 && ready && addr_sync[11:0]==position)),
  (!read_n && !write_n),
  ((pending!=0 || output_valid) && is_payload(read_address) && !read_n && romsel_n),
  (pending!=0 && !write_n),
  (pending!=0 && read_n),
  ((pending!=0 || output_valid) && !read_n && snes_addr!=read_address)};
 always @(posedge host_clk or posedge reset) begin
  if(reset)begin
   frontend_snapshot<=0;sampled_read_n<=1;
   low_count<=0;high_count<=0;last_low_count<=0;last_high_count<=0;
  end else begin
   sampled_read_n<=read_n;
   if(read_n)begin
    low_count<=0;
    if(!sampled_read_n)begin last_low_count<=low_count;high_count<=1;end
    else if(high_count!=255)high_count<=high_count+1'b1;
   end else begin
    high_count<=0;
    if(sampled_read_n)begin last_high_count<=high_count;low_count<=1;end
    else if(low_count!=255)low_count<=low_count+1'b1;
   end
   if(frontend_snapshot[7:0]==0 && causes!=0)
    frontend_snapshot<={8'h41,last_high_count,high_count,last_low_count,low_count,
     4'b0,position,read_address,snes_addr,
     ready,busy,fault,reg_rvalid,data_valid,romsel_n,read_n,write_n,
     output_valid,payload_pending,local_pending,rd_previous,rd_sync,pending,causes};
  end
 end
"""
 return replace(s,' always @(posedge host_clk or posedge reset) begin',monitor+'\n always @(posedge host_clk or posedge reset) begin')

def transport():
 s=(ROOT/'src/nes/nes_transport.sv').read_text()
 return replace(s,' output wire [3:0] bus_error,frontend_error',' output wire [127:0] frontend_snapshot,\n output wire [3:0] bus_error,frontend_error')
def pattern():
 s=(ROOT/'src/nes/nes_h1_pattern.sv').read_text()
 return replace(s,' output wire [3:0] bus_error,frontend_error,',' output wire [127:0] frontend_snapshot,\n output wire [3:0] bus_error,frontend_error,')
def boundary():
 s=fault_boundary()
 s=replace(s,"command==8'hf1 ?8'h39:","command==8'hf1 ?8'h41:")
 s=replace(s,' reg [31:0] run_cycles=0;',' wire [127:0] frontend_snapshot;\n reg [31:0] run_cycles=0;')
 s=replace(s,"  8'd0;",''.join("  command==8'h%02x ?frontend_snapshot[%d:%d]:\n"%(0xd0+i,i*8+7,i*8) for i in range(16))+"  8'd0;")
 s=replace(s,'  .bus_error(bus_error),.frontend_error(frontend_error),','  .frontend_snapshot(frontend_snapshot),\n  .bus_error(bus_error),.frontend_error(frontend_error),')
 return s

def session():return replace(fault_session(),'if(id!=0x39)','if(id!=0x41)')
def source():
 s=fault_source().replace('NES-H1-FAULT-039','NES-H1-EDGE-041').replace('nes-h1-last-039.txt','nes-h1-last-041.txt')
 s=s.replace('detail[14]','detail[30]').replace('hex[29]','hex[61]').replace('i<14','i<30').replace('hex[28]','hex[60]')
 return replace(s,'(i<3?0xf0+i:0xf5+i-3)','(i<3?0xf0+i:i<14?0xf5+i-3:0xd0+i-14)')

def materialize(out):
 for n,fn in [('nes_snes_frontend',frontend),('nes_transport',transport),('nes_h1_pattern',pattern),('nes_h1_board_bus',boundary)]:
  (out/(n+'.sv')).write_text(fn())

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True);a=p.parse_args()
 subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'tools/prepare_nes_h1_firmware.py'),'--out',str(a.out),'--upstream',str(a.upstream)],check=True)
 (a.out/'src/nes_h1_stm32.c').write_text(source(),newline='\n');(a.out/'src/nes_h1_session.c').write_text(session(),newline='\n')
 (a.out/'edge-preparation.json').write_text(json.dumps({'candidate':'NES-H1-EDGE-041','protocol_hex':'41','files':{n:sha(a.out/'src'/n) for n in ('nes_h1_stm32.c','nes_h1_session.c')}},indent=2))
if __name__=='__main__':main()
