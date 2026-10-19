# SPDX-License-Identifier: MIT
"""Remove the retained legacy E0/E1 endpoint, preserving local program ROM/pad.

One Lite whole-board MAP. The separate bus guard does not qualify full board
CDC/IO/STA or link the complete65816 program.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_delta231 import BASE,sha,once
from probe_nes_joint266 import run


def patch():
 old=BASE/'probes/nes-joint267/board02'
 s=(old/'nes_sink_bridge165.sv').read_text();start=s.index(' nes_sink_spi165 endpoint(');end=s.index(' wire bus_oe,bus_dir;',start)
 s=s[:start]+''' // The new output queue owns E0/E1, packet CRC, ACK and faults.
 assign spi_selected=1'b0;assign spi_miso=1'b0;assign fault=1'b0;
 assign ready=1'b0;assign length=9'd0;assign pd=8'd0;
'''+s[end:]
 s=once(s,' nes_sink_bus165 bus(', ' nes_sink_bus165 #(.ROM_ONLY(1)) bus(')
 t=(old/'nes_sink_bus165.sv').read_text()
 t=once(t,'module nes_sink_bus165(', 'module nes_sink_bus165 #(parameter ROM_ONLY=0)(')
 t=once(t,' wire control=local_bank&&', " wire control=ROM_ONLY?(local_bank&&(address[15:0]==16'h6002||address[15:0]==16'h6003)):local_bank&&")
 t=once(t,'assign dir=read_active&&(control||rom_select||packet_select);', 'assign dir=read_active&&(ROM_ONLY?rom_select:(control||rom_select||packet_select));')
 return {'nes_sink_bridge165.sv':s,'nes_sink_bus165.sv':t}


TB=r'''
`timescale 1ns/1ps
module cleanup268_tb;
 reg clk=0;always #5.952381 clk=~clk;
 reg reset=1,active=1,ss=1,sck=0,mosi=0,rd=1,wr=1,romsel=1;
 reg [23:0] addr=0;reg [7:0] din=0;
 wire sel,miso,fault,oe,dir,pad;wire [7:0] dout;wire [15:0] buttons;
 integer checks=0,pads=0;
 nes_sink_bridge165 dut(.clk(clk),.raw_reset(reset),.active(active),.stop(1'b0),
 .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.spi_selected(sel),.spi_miso(miso),
 .address(addr),.read_n(rd),.write_n(wr),.romsel_n(romsel),.data_in(din),.data_out(dout),.oe_n(oe),.dir(dir),
 .pad_commit(pad),.pad_buttons(buttons),.fault(fault));
 always @(posedge clk)begin
  if(sel||miso||fault)$fatal(1,"legacy SPI endpoint still drives");
  if(pad)pads++;
 end
 task readcheck(input [23:0] a,input selected,input [7:0] value);
 begin
  @(negedge clk);addr=a;rd=0;romsel=a[15]?0:1;repeat(12)@(negedge clk);
  if(selected)begin if(oe||!dir||dout!==value)$fatal(1,"ROM %h got %h",a,dout);end
  else if(!oe||dir)$fatal(1,"legacy packet/control read still drives %h",a);
  rd=1;repeat(5)@(negedge clk);checks++;
 end endtask
 task writebyte(input [23:0] a,input [7:0] value);
 begin @(negedge clk);addr=a;din=value;wr=0;repeat(12)@(negedge clk);wr=1;repeat(12)@(negedge clk);end
 endtask
 reg [7:0] command;
 initial begin
  repeat(8)@(negedge clk);reset=0;repeat(20)@(negedge clk);
  readcheck(24'h008000,1,8'h78);readcheck(24'h@ZERO@,1,0);
  readcheck(24'h00ff00,1,8'hff);readcheck(24'h00fffc,1,0);readcheck(24'h00fffd,1,8'h80);
  readcheck(24'h006000,0,0);readcheck(24'h006001,0,0);readcheck(24'h006004,0,0);
  readcheck(24'h006010,0,0);readcheck(24'h400000,0,0);readcheck(24'h4000ff,0,0);
  writebyte(24'h006002,8'hab);writebyte(24'h006003,8'hcd);
  if(buttons!==16'hcdab||pads!=1)$fatal(1,"pad preservation");
  writebyte(24'h00601c,8'ha5);if(pads!=1)$fatal(1,"ACK aliases pad");
  for(integer c=0;c<2;c++)begin
   command=c?8'he1:8'he0;ss=0;
   for(integer i=7;i>=0;i--)begin mosi=command[i];repeat(8)@(negedge clk);sck=1;repeat(8)@(negedge clk);sck=0;end
   ss=1;repeat(20)@(negedge clk);
  end
  active=0;readcheck(24'h008000,0,0);
  $display("PASS ROMPAD268 checks=%0d pad=%0d no_legacy_E0_E1",checks,pads);$finish;
 end
endmodule
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--guard',action='store_true');p.add_argument('--cpu',type=Path);p.add_argument('--questa-bin',type=Path);a=p.parse_args()
 d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True);old=BASE/'probes/nes-joint267/board02';pins={}
 if a.guard:
  assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
  r=json.loads((a.cpu/'result.json').read_text());assert r['passed'] and r['existing165_ROM_decode']
  rom=(a.cpu/'ordinary.sfc').read_bytes();image=rom[:0xfc0]+rom[0x7fc0:0x8000];assert len(image)==4096
  (d/'sink-program.hex').write_text(image.hex(' ')+'\n')
  shutil.copyfile(old/'nes_domain_reset124.sv',d/'nes_domain_reset124.sv')
  (d/'cleanup268_tb.sv').write_text(TB.replace('@ZERO@',f'{r["zero_source"]:06x}'),encoding='utf-8',newline='\n')
  pins['CPU_result']=sha(a.cpu/'result.json');pins['CPU_ROM']=sha(a.cpu/'ordinary.sfc')
 else:
  for f in old.rglob('*'):
   rel=f.relative_to(old)
   if any(x in ('work','db','incremental_db','output_files') for x in rel.parts):continue
   if f.is_file() and f.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
    target=d/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target);pins[rel.as_posix()]=sha(f)
 for name,s in patch().items():(d/name).write_text(s,encoding='utf-8',newline='\n')
 shutil.copyfile(Path(__file__),d/Path(__file__).name)
 r=dict(scope=__doc__,input_hashes=pins,changed_hashes={n:sha(d/n) for n in patch()},script_sha256=sha(Path(__file__)),full_board_functional=False,FIT=False,STA=False)
 if a.guard:
  names=['nes_sink_bridge165.sv','nes_sink_bus165.sv','nes_domain_reset124.sv','cleanup268_tb.sv']
  run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*names],d,'vlog')
  log=run(a.questa_bin/'vsim.exe',['-c','work.cleanup268_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim')
  assert 'PASS ROMPAD268' in log;r.update(passed=True,guard=True,log=[x for x in log.splitlines() if 'PASS ' in x])
 else:
  with (d/'map.log').open('wb') as log:
   cp=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
  summary=(d/'output_files/board.map.summary').read_text();raw=(d/'map.log').read_text(errors='replace');undriven=re.findall(r'Warning \(10034\):[^\r\n]+',raw)
  r.update(passed=cp.returncode==0 and not undriven,guard=False,summary=summary,Quartus='Lite25.1std',undriven_outputs=undriven,returncode=cp.returncode)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k in ('passed','guard','summary','log')}));assert r['passed']


if __name__=='__main__':main()
