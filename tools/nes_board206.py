# SPDX-License-Identifier: MIT
"""206 domain-local cancel gates; paired with205 tile stream. No CDC waivers."""
from pathlib import Path
import argparse,json,shutil
from nes_board204 import ROOT,BASE,sha,replace

def transform(name,s):
 if name=='nes_native_mailbox165.sv':
  s=replace(s,'module nes_native_mailbox165 #','module nes_native_mailbox206 #')
  s=replace(s,'!reset&&sr[1]','sr[1]');s=replace(s,'!reset&&dr[1]','dr[1]')
 elif name=='nes_plan_batch201.sv':
  s=replace(s,'module nes_plan_batch201(','module nes_plan_batch206(')
  s=s.replace('nes_native_mailbox165 #','nes_native_mailbox206 #')
  s=replace(s,'reg hf,nf;wire cancel=raw||hf||nf;assign fault=hf||nf||source_fault;',
   '''reg hf,nf;wire cancel=raw||hf||nf;assign fault=hf||nf||source_fault;
 // Internal faults remain latched under the base resets hr/nr. Cancellation
 // gates use separate local releases, so they cannot erase their own cause.
 wire hc,nc;
 nes_domain_reset124 hcancel(.clk(host_clk),.raw_reset(cancel),.reset(hc));
 nes_domain_reset124 ncancel(.clk(nes_clk),.raw_reset(cancel),.reset(nc));''')
  # Classify each data gate by owning domain; raw cancel ends at reset pins.
  for a,b in [('pending&&!cancel','pending&&!hc'),('retire_pending&&!cancel','retire_pending&&!hc'),
              ('wire retire_ack=!cancel','wire retire_ack=!nc'),('!hr&&!cancel','!hr&&!hc'),
              ('!nr&&!cancel','!nr&&!nc')]:s=s.replace(a,b)
  assert s.count('else if(!cancel)')==2
  s=s.replace('else if(!cancel)','else if(!hc)',1).replace('else if(!cancel)','else if(!nc)',1)
 elif name=='nes_tile_bulk193.sv':
  s=replace(s,'module nes_tile_bulk193(','module nes_tile_bulk206(')
  s=replace(s,'nes_native_mailbox165 #','nes_native_mailbox206 #')
  s=replace(s,'wire cancel=common_reset||source_fault||source_failed||host_failed;',
   '''wire cancel=common_reset||source_failed||host_failed;
 wire sc,hc;
 nes_domain_reset124 scancel(.clk(nes_clk),.raw_reset(cancel),.reset(sc));
 nes_domain_reset124 hcancel(.clk(host_clk),.raw_reset(cancel),.reset(hc));''')
  s=s.replace('sending&&!cancel','sending&&!sc').replace('!sr&&!cancel','!sr&&!sc')
  s=s.replace('else if(!cancel)','else if(!sc)',1)
  s=s.replace('!cancel','!hc')
  s=replace(s,'.clk(host_clk),.reset(reset),.active(active),.stop(stop||fault)',
                '.clk(host_clk),.reset(hr),.active(1\'b1),.stop(hc)')
 elif name=='nes_direct204.sv':
  s=replace(s,'module nes_direct204(','module nes_direct206(')
  s=replace(s,'reg hf,nf;', '''reg hf,nf;
 wire hr,nr,hc,nc;
 nes_domain_reset124 hrelease(.clk(host_clk),.raw_reset(reset),.reset(hr));
 nes_domain_reset124 nrelease(.clk(nes_clk),.raw_reset(reset),.reset(nr));''')
  s=replace(s,'posedge host_clk or posedge reset','posedge host_clk or posedge hr')
  s=replace(s,'if(reset)begin hf','if(hr)begin hf')
  s=replace(s,'posedge nes_clk or posedge reset','posedge nes_clk or posedge nr')
  s=replace(s,'if(reset)begin nf','if(nr)begin nf')
  s=replace(s,'wire cancel=hf||nf;', '''wire cancel=hf||nf;
 nes_domain_reset124 hcancel(.clk(host_clk),.raw_reset(reset||cancel),.reset(hc));
 nes_domain_reset124 ncancel(.clk(nes_clk),.raw_reset(reset||cancel),.reset(nc));''')
  s=replace(s,'endpoint(.clk(host_clk),.reset(reset)','endpoint(.clk(host_clk),.reset(hr)')
  s=replace(s,".enable(1'b1),.stop(1'b0),.source_fault(cancel)",".enable(1'b1),.stop(1'b0),.source_fault(hf)")
  # SPI source fault is sticky hf, not hc (hc includes startup reset hold).
  s=replace(s,'nes_plan_batch201 transport','nes_plan_batch206 transport')
  s=replace(s,'source(.clk(nes_clk),.reset(reset),.stop(cancel)','source(.clk(nes_clk),.reset(nr),.stop(nc)')
  s=replace(s,'nes_tile_bulk193 bulk','nes_tile_bulk206 bulk')
  s=replace(s,"control(.clk(host_clk),.reset(reset),.active(1'b1),.stop(cancel)","control(.clk(host_clk),.reset(hr),.active(1'b1),.stop(hc)")
  s=replace(s,'assign oe_n=reset||cancel||','assign oe_n=hr||hc||')
 elif name=='nes_rom_loader.sv':
  # Use the counter's existing clear/update enable, not another priority mux.
  s=replace(s,'reg count_complete;', '(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION ON; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) reg count_complete;')
  s=replace(s,'''  else if(active_reset)count_complete<=0;
  else if(!fault)begin
   if(count_stop || count_begin)count_complete<=0;
   else if(count_advance)count_complete<=loaded_bytes==total-1'b1;
  end''', '''  else if(count_update)begin
   if(count_clear)count_complete<=0;
   else count_complete<=loaded_bytes==total-1'b1;
  end''')
 else: raise ValueError(name)
 return s

MODULES={'nes_native_mailbox165.sv':'nes_native_mailbox206.sv','nes_plan_batch201.sv':'nes_plan_batch206.sv',
 'nes_tile_bulk193.sv':'nes_tile_bulk206.sv','nes_direct204.sv':'nes_direct206.sv','nes_rom_loader.sv':'nes_rom_loader.sv'}
def prepare(out):
 out=out.resolve();out.mkdir(parents=True,exist_ok=False)
 old=BASE/'probes/nes-board205/source01';p=json.loads((old/'preparation205.json').read_bytes())
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n;(out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 for n,new in MODULES.items():
  (out/new).write_text(transform(n,(old/n).read_text()),encoding='utf8',newline='\n')
 f=out/'nes_live_joint.sv';f.write_text(replace(f.read_text(),'nes_direct204 direct_path','nes_direct206 direct_path'),encoding='utf8',newline='\n')
 f=out/'board.qsf';s=f.read_text()
 for n,new in MODULES.items():
  if n=='nes_native_mailbox165.sv':
   # Existing geometry/ACK channels still instantiate165; only new direct
   # plan/tile channels use206. Keep both definitions in the whole board.
   s+='\nset_global_assignment -name SYSTEMVERILOG_FILE '+new+'\n'
  elif n!=new:s=replace(s,'SYSTEMVERILOG_FILE '+n,'SYSTEMVERILOG_FILE '+new)
 f.write_text(s,encoding='utf8',newline='\n')
 names=list(dict.fromkeys(list(p['sources'])+list(MODULES.values())))
 result=dict(sources={n:sha(out/n) for n in names},baseline=p['sources'],public_sources={'tools/nes_board206.py':sha(Path(__file__))},
  changed=[n for n in p['sources'] if sha(out/n)!=p['sources'][n]],old_constraints_unchanged=True,no_package=True,adopted=False)
 (out/'preparation206.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(files=len(names),changed=result['changed'])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
