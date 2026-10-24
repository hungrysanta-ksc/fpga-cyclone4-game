# SPDX-License-Identifier: MIT
import guard_nes_spi307 as old
import json,sys
from pathlib import Path
from nes_delta231 import sha
from nes_delta231 import once
s=old.TB.replace('[109:0]','[112:0]').replace('[183:0]','[199:0]').replace("184'd0","200'd0")
s=once(s,'integer seals=0,commits=0;', '''reg [191:0] rec314=0;wire rv314;wire [4:0] ra314;wire [7:0] rb314;
 always @(posedge clk)if(rv314)rec314[ra314*8+:8]<=rb314;
 integer seals=0,commits=0;''')
s=once(s,'.progress_status(128\'d0),', '''.progress_status(128'd0),.frame_start312(1'b0),.frame_serial312(32'd1),.frame_generation312(16'd1),
 .record312(rec314),.load_enable312(1'b1),.record_valid312(rv314),.record_at312(ra314),.record_byte312(rb314),
 .consume_record312(1'b0),.expected_select313(1'b0),.expected_write313(1'b0),.expected_address313(9'd0),.expected_data313(8'd0),''')
s=once(s,"tx[0]='he1;for(integer j=1;j<17;j++)tx[j]=j;",'''tx[0]='he1;for(integer j=1;j<17;j++)tx[j]=0;
 tx[1]=2;tx[3]=queue.sequence312[7:0];tx[4]=queue.sequence312[15:8];tx[5]=1;tx[9]=1;''')
s=s.replace('j<4;j++','j<2;j++').replace('queue.used!=4','queue.used!=2').replace('queue.accepted!=4','queue.accepted!=2').replace('four credits','two credits').replace('fifth credit','third credit')
s=once(s,'if(seal)seals++;', '''if(seal)begin
   if(len!=3||plans!=1||crc!=c16(c16(c16(16'hffff,8'h83),8'd1),8'd0))$fatal(1,"shared seal fields lost across SS");
   seals++;
  end''')
s=once(s,' task e1(input integer bad);', ''' task ea;reg [7:0] h;begin
 tx[0]='hea;tx[1]=1;tx[2]=0;tx[3]=0;tx[4]=1;
 h=0;for(integer j=0;j<5;j++)h=c8(h,tx[j]);tx[5]=h;tx[6]='ha5;n=7;
 end endtask
 task e1(input integer bad);''')
s=once(s,' $display("PASS SPI307 13 boundary checks");', ''' fresh();e9(0);send(-1);ea();send(-1);
 if(pfault||bfault||ep.ended||ep.retiring||ep.accepted)$fatal(1,"EA lifetime");
 e9(0);send(-1);if(pfault||bfault||seals!=2||commits!=2)$fatal(1,"request field reuse after EA");
 $display("PASS SPI307 13 boundary checks");
 $display("PASS SPI314 shared seal lifetime and EA/reuse");''')
old.TB=s
if __name__=='__main__':
    old.main()
    d=Path(sys.argv[sys.argv.index('--out')+1])
    assert 'PASS SPI314' in (d/'vsim.log').read_text()
    r=json.loads((d/'result.json').read_text());r.update(checks=15,shared_seal_lifetime=True,EA_reuse=True,entry314_sha=sha(Path(__file__)))
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
