# SPDX-License-Identifier: MIT
"""Actual expanded staging cancellation, consume and independent CRC faults."""
import inspect
import json,shutil
import guard_nes_owner319 as old
from nes_delta231 import once
old.CASES[11]='STOP during direct expected scan'
old.CASES.update({8:'STOP during expanded staging write',9:'premature expanded consume',10:'independent consumed-byte CRC corruption'})

def aperture_test(d):
 q=old.Path('C:/altera_standard/25.1std/questa_fse/win64');a=d/'aperture';a.mkdir()
 for n in ('nes_bulk_aperture188.sv','nes_domain_reset124.sv'):shutil.copyfile(d/n,a/n)
 tb=r'''
module aperture325_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,active=1,stop=0,wide325=0,beg=0,bv=0,seal=0,consume=0;
 reg [11:0] length=0;reg [31:0] token=0,ctoken=0;reg [7:0] byte_in=0;
 reg [23:0] address=0;reg read_n=1;wire br,pr,cr,pe,ce,oe;wire [7:0] data;wire [11:0] size;wire [31:0] published;
 nes_bulk_aperture188 #(.ALLOW_SHORT_SEAL(1)) dut(.clk(clk),.reset(reset),.active(active),.stop(stop),.wide325(wide325),
 .begin_valid(beg),.begin_length(length),.begin_token(token),.begin_ready(br),.byte_valid(bv),.byte_data(byte_in),.byte_ready(pr),.seal(seal),.cancel(1'b0),.producer_error(pe),
 .chunk_ready(cr),.chunk_length(size),.chunk_token(published),.consume(consume),.consume_token(ctoken),.consume_error(ce),
 .address(address),.read_n(read_n),.write_n(1'b1),.data_out(data),.oe_n(oe),.dir());
 task fill(input integer n,input integer id);
  begin wait(br);@(negedge clk);length=n;token=id;beg=1;@(negedge clk);beg=0;
   for(integer i=0;i<n;i++)begin if(!pr)$fatal(1,"write readiness");byte_in=(i*17+id)&255;bv=1;@(negedge clk);end
   bv=0;seal=1;@(negedge clk);seal=0;end
 endtask
 task read_all(input integer n,input integer id);
  begin wait(cr);if(size!=n||published!=id)$fatal(1,"published identity");
   for(integer i=0;i<n;i++)begin address=24'h400800+i;read_n=0;repeat(8)@(negedge clk);
    if(oe||data!==((i*17+id)&255))$fatal(1,"expanded address %0d value %0d",i,data);
    read_n=1;@(negedge clk);end
  end
 endtask
 task retire(input integer id);
  begin ctoken=id;consume=1;@(negedge clk);consume=0;@(negedge clk);end
 endtask
 initial begin
  repeat(5)@(negedge clk);reset=0;repeat(5)@(negedge clk);
  fill(32,1);fill(32,2);read_all(32,1);retire(1);read_all(32,2);retire(2);
  if(cr)$fatal(1,"old tile chunk live");wide325=1;
  fill(3418,3);read_all(3418,3);
  ctoken=99;consume=1;@(negedge clk);consume=0;if(!ce||!cr)$fatal(1,"wrong token accepted");@(negedge clk);retire(3);
  wait(br);length=3418;token=4;beg=1;@(negedge clk);beg=0;bv=1;byte_in=123;repeat(7)@(negedge clk);
  stop=1;repeat(8)@(negedge clk);if(cr||br||pr)$fatal(1,"STOP exposes stage");bv=0;stop=0;repeat(8)@(negedge clk);
  if(cr)$fatal(1,"partial expansion survived STOP");
  $display("PASS APERTURE325 tile_pingpong wide3418 wrong_token STOP");$finish;
 end
endmodule
'''
 (a/'aperture325_tb.sv').write_text(tb,newline='\n')
 old.run(q/'vlib.exe',['work'],a,'vlib')
 old.run(q/'vlog.exe',['-sv','nes_domain_reset124.sv','nes_bulk_aperture188.sv','aperture325_tb.sv'],a,'vlog')
 raw=old.run(q/'vsim.exe',['-c','work.aperture325_tb','-do','run -all;quit -f'],a,'vsim',60)
 assert 'PASS APERTURE325' in raw
 (a/'result.json').write_text(json.dumps(dict(passed=True,RTL_sha256=old.sha(a/'nes_bulk_aperture188.sv'),tb_sha256=old.sha(a/'aperture325_tb.sv'),log_sha256=old.sha(a/'vsim.log')))+'\n')

def main():
 s=inspect.getsource(old.main).replace("default='1,2,3,4,5,6,7'","default='1,2,3,4,5,6,7,8,9,10'")
 s=s.replace("'.cfg','.palette','.expected'","'.cfg','.palette','.expected','.lens','.desc'").replace('probe_nes_owner319.py','probe_nes_joint327.py')
 s=once(s,'reg [7:0] frozen319[0:1023];reg [7:0] queue319[0:1023];','reg [7:0] frozen319[0:1023];reg [7:0] queue319[0:1023];reg [7:0] stage325[0:4095];reg [7:0] corrupt325;')
 s=once(s,'  repeat(256)@(negedge host_clk);','  for(integer j=0;j<4096;j++)stage325[j]=dut.flow.shared_ram.aperture.storage[j];\n  repeat(256)@(negedge host_clk);\n  for(integer j=0;j<4096;j++)if(stage325[j]!==dut.flow.shared_ram.aperture.storage[j])$fatal(1,"staging write after STOP325");')
 s=once(s,"    s=once(s,'endmodule',", "    s=once(s,'if(reset||!active263||source_fault)released312<=0;', 'if(reset||!active263||source_fault||injected319)released312<=0;')\n    s=once(s,'endmodule',")
 s=once(s,'  else $fatal(1,"unknown guard319");','''  else if(NEG319==8)wait(dut.flow.state==dut.flow.EXPAND325&&dut.flow.expanded325==7);
  else if(NEG319==9)wait(dut.flow.state==dut.flow.DMA&&dut.flow.data_command278&&dut.flow.chunk_length>4);
  else if(NEG319==10)wait(dut.flow.tap_byte278&&dut.flow.ordinary_hash_ready);
  else $fatal(1,"unknown guard319");''')
 s=s.replace('if(NEG319<=4||NEG319==7)begin','if(NEG319<=4||NEG319==7||NEG319==8)begin')
 s=once(s,'  else force dut.flow.held=0;', '''  else if(NEG319==9)begin disable bus263;bus_read=1;bus_write=1;token261(dut.flow.chunk_token);wr261(24'h006059,8'ha5);end
  else if(NEG319==10)begin
   corrupt325=dut.flow.tap_value278^8'hff;force dut.flow.tap_value278=corrupt325;
   @(negedge host_clk);release dut.flow.tap_value278;
  end else force dut.flow.held=0;''')
 # CRC is rejected at seal, not immediately at a valid byte transfer.
 s=once(s,'begin #100000;$fatal(1,"missing expected fault319");end', 'begin #(NEG319==10?200000000:100000);$fatal(1,"missing expected fault319");end')
 s=s.replace('dut.flow.state==dut.flow.MISSUE313&&dut.flow.header[0]==3&&dut.flow.manifest_byte313==190','dut.core.validator.state==dut.core.validator.E_CAPTURE327&&dut.expected_addr327==190')
 s=s.replace('else force dut.flow.held=0;', 'else force dut.expected_data327=0;')
 s=s.replace('  else $fatal(1,"unknown guard319");','  else if(NEG319==11)wait(dut.core.validator.state==dut.core.validator.E_CAPTURE327&&dut.expected_addr327==200);\n  else $fatal(1,"unknown guard319");')
 s=s.replace('if(NEG319<=4||NEG319==7||NEG319==8)begin','if(NEG319<=4||NEG319==7||NEG319==8||NEG319==11)begin')
 ns=dict(old.__dict__);exec(compile(s,'guards325','exec'),ns);ns['main']()
 import sys
 aperture_test(old.Path(sys.argv[sys.argv.index('--out')+1]))

if __name__=='__main__':main()
