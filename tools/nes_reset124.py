# SPDX-License-Identifier: MIT
"""Exact, diagnostic-only transformations of pinned123/122 inputs.

Historical product modules remain immutable. Generated variants share the same
module names and are used only in the fresh124 test/fit directory.
"""
from pathlib import Path
import difflib,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,s):p.write_text(s,encoding='utf-8',newline='\n')
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a))
 return s.replace(a,b)
def reader(s):
 s=replace(s,'wire sr=reset || source_reset[1],mr=reset || memory_reset[1];','wire sr=source_reset[1],mr=memory_reset[1];')
 for clk,r,name in [('mem_clk','mr','request_sync'),('clk','sr','ack_sync')]:
  s=replace(s,f'always @(posedge {clk} or posedge reset)\n  if(reset){name}<=0;else if({r}){name}<=0;',f'always @(posedge {clk} or posedge {r})\n  if({r}){name}<=0;')
 for clk,r,body in [('clk','sr','request_toggle<=0;ack_seen<=0;source_busy<=0;address_hold<=0;'),('mem_clk','mr','state<=IDLE;reading_active<=0;remaining<=0;ack_toggle<=0;data_hold<=0;check_response<=0;psram_address<=0;chip<=0;lane<=0;')]:
  s=replace(s,f'always @(posedge {clk} or posedge reset)begin\n  if(reset)begin {body}end\n  else if({r})begin {body}end',f'always @(posedge {clk} or posedge {r})begin\n  if({r})begin {body}end')
 return s
def bridge(s):
 s=replace(s,'assign cmd_ready=!reset && h_up','assign cmd_ready=h_up')
 s=replace(s,'assign p_accept=!reset && q_up','assign p_accept=q_up')
 s=replace(s,'assign p_error=(!reset && q_up)','assign p_error=q_up')
 for clk,up in [('queue_clk','q_up'),('host_clk','h_up')]:
  s=replace(s,f'always @(posedge {clk} or posedge reset) begin\n  if(reset) begin',f'always @(posedge {clk} or negedge {up}) begin\n  if(!{up}) begin')
 return s
def transport(s):
 s=replace(s,' nes_packet_cdc_ram bridge(.*);',' wire host_reset124;\n nes_domain_reset124 host_release(.clk(host_clk),.raw_reset(reset),.reset(host_reset124));\n nes_packet_cdc_ram bridge(.*);')
 for n in ['nes_host_stage stage','nes_snes_frontend frontend']:
  s=replace(s,n+'(.*);',n+'(.reset(host_reset124),.*);')
 return s
def top(s):
 s=replace(s,'wire reset_request=boot_reset || !run_enable;', 'wire raw_stop=boot_reset || !run_enable;wire reset_request;\n nes_domain_reset124 init_release(.clk(clk),.raw_reset(raw_stop),.reset(reset_request));')
 s=replace(s,'wire memory_ready;wire reset=reset_request || !memory_ready,reset_nes=reset,cold_reset=reset;', 'wire memory_ready;wire common_reset=raw_stop || !memory_ready;wire reset;\n nes_domain_reset124 core_release(.clk(clk),.raw_reset(common_reset),.reset(reset));\n wire reset_nes=reset,cold_reset=reset;')
 s=replace(s,'nes_transport transport(.*);','nes_transport transport(.reset(common_reset),.*);')
 s=replace(s,'.clk(clk),.mem_clk(mem_clk),.reset(reset),','.clk(clk),.mem_clk(mem_clk),.reset(common_reset),')
 return s
def testbench(s):
 s=replace(s,'wire memory_ready;wire reset=reset_request || !memory_ready;', 'wire memory_ready;wire common_reset=reset_request || !memory_ready;wire reset,init_reset124;\n nes_domain_reset124 init_release(.clk(queue_clk),.raw_reset(reset_request),.reset(init_reset124));\n nes_domain_reset124 core_release(.clk(queue_clk),.raw_reset(common_reset),.reset(reset));')
 s=replace(s,'.reset(reset_request)', '.reset(init_reset124)')
 s=replace(s,'nes_transport transport(.*);','nes_transport transport(.reset(common_reset),.*);')
 s=replace(s,'.clk(clk),.mem_clk(mem_clk),.reset(reset),','.clk(clk),.mem_clk(mem_clk),.reset(common_reset),')
 return s
def materialize(o,mode):
 edits={'nes_rom_physical.sv':reader,'nes_packet_cdc_ram.sv':bridge,'nes_transport.sv':transport}
 if mode=='fit':edits['nes_live_joint.sv']=top
 if mode=='core':edits['ncr1_live_tb.sv']=testbench
 if mode=='unit':edits={'nes_rom_physical.sv':reader}
 records={}
 for n,fn in edits.items():
  p=o/n;old=p.read_text();before=sha(p);new=fn(old);put(p,new)
  put(o/(n+'.reset124.diff'),''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='baseline/'+n,tofile='124/'+n)))
  records[n]={'before':before,'after':sha(p)}
 shutil.copy2(ROOT/'src/nes/diagnostic/nes_domain_reset124.sv',o/'nes_domain_reset124.sv')
 shutil.copy2(__file__,o/'executed-reset124.py')
 put(o/'reset124-transform.json',json.dumps(records,indent=2)+'\n')
