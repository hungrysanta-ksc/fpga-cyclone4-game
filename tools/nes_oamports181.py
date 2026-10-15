# SPDX-License-Identifier: MIT
"""Preserve OAM cycle contract; expose byte-enable words to RAM inference."""
from pathlib import Path
import argparse,json,re,shutil
from nes_game147 import sha

def packed(s):
 for port in ['main','copy','extra','repeat','state']:
  old=f'reg [63:0] primary_ss_{port}[0:31],primary_run_{port}[0:31];'
  assert s.count(old)==1
  s=s.replace(old,f'reg [7:0][7:0] primary_ss_{port}[0:31],primary_run_{port}[0:31];')
  for writer,addr in [('ss','Savestate_OAMAddr[7:3]'),('run','oam_write_row')]:
   old=f'primary_{writer}_{port}[{addr}][wb_{port}*8+:8]'
   assert s.count(old)==1;s=s.replace(old,f'primary_{writer}_{port}[{addr}][wb_{port}]')
 for i in range(8):
  for writer in ['ss','run']:
   old=f'primary_{writer}_main[observed_row][{i*8}+:8]'
   assert s.count(old)==1;s=s.replace(old,f'primary_{writer}_main[observed_row][{i}]')
 return s

def primitive(s):
 # Keep the asynchronous debug/observation backing arrays. They are unconsumed
 # and prune in this board; they are not the source of any internal read data.
 for port,addr in {'main':'oam_read_addr[7:3]','copy':'oam_row_last','extra':'oam_addr_ex[5:1]',
                   'repeat':'oam_addr[7:3]','state':'Savestate_OAMAddr[7:3]'}.items():
  old=f'reg [63:0] primary_ss_q_{port},primary_run_q_{port};'
  assert s.count(old)==1;s=s.replace(old,f'wire [63:0] primary_ss_q_{port},primary_run_q_{port};')
  for writer in ['ss','run']:
   old=f' primary_{writer}_q_{port}<=primary_{writer}_{port}[{addr}];\n'
   assert s.count(old)==1;s=s.replace(old,'')
  inst=''
  for writer,wa,data in [('ss','Savestate_OAMAddr[7:3]',"{4{Savestate_OAMWriteData}}"),('run','oam_write_row',None)]:
   for half in range(2):
    mask=f'primary_{writer}_mask[{half*4}+:4]'
    din=data or f'primary_run_data[{half*32}+:32]'
    inst+=f'''
altsyncram #(.operation_mode("DUAL_PORT"),.intended_device_family("Cyclone IV E"),
 .ram_block_type("M9K"),.width_a(32),.widthad_a(5),.numwords_a(32),
 .width_b(32),.widthad_b(5),.numwords_b(32),.width_byteena_a(4),.byte_size(8),
 .address_reg_b("CLOCK1"),.outdata_reg_b("UNREGISTERED"),
 .read_during_write_mode_mixed_ports("DONT_CARE"),.power_up_uninitialized("TRUE"))
 primary_{writer}_{port}_word{half}(.clock0(clk),.clock1(~clk),
 .clocken0(1'b1),.clocken1(1'b1),.clocken2(1'b1),.clocken3(1'b1),
 .aclr0(1'b0),.aclr1(1'b0),.addressstall_a(1'b0),.addressstall_b(1'b0),
 .address_a({wa}),.data_a({din}),.wren_a(|{mask}),.byteena_a({mask}),
 .address_b({addr}),.data_b(32'b0),.wren_b(1'b0),.byteena_b(1'b1),
 .rden_a(1'b1),.rden_b(1'b1),.q_a(),.q_b(primary_{writer}_q_{port}[{half*32}+:32]),.eccstatus());
'''
  anchor=f'genvar rb_{port};';assert s.count(anchor)==1;s=s.replace(anchor,inst+'\n'+anchor)
 return s

def prepare(prior,out,mode='packed'):
 assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
 m=json.loads((prior/'preparation.json').read_bytes());pins=m['sources']
 for n,h in pins.items():
  assert sha(prior/n)==h,n;p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(prior/n,p)
 p=out/'rtl/ppu.sv';p.write_text((packed if mode=='packed' else primitive)(p.read_text()),encoding='utf8',newline='\n')
 changed=[n for n in pins if sha(out/n)!=pins[n]];assert changed==['rtl/ppu.sv']
 m.update(baseline_oamports_sources=pins,sources={n:sha(out/n) for n in pins},changed=changed,
  oamports_generator_sha256=sha(Path(__file__)),oamports_mode=mode,adopted=False,hardware=False)
 (out/'preparation.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf8');return m
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['prior','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mode',choices=['packed','primitive'],default='packed')
 a=p.parse_args();prepare(a.prior,a.out,a.mode)
