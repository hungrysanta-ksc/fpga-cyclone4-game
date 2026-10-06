# SPDX-License-Identifier: MIT
"""048 structural primary-OAM banking; original held HDL stays in private generated files."""
from pathlib import Path
import argparse,difflib,json,re,shutil,subprocess,sys,os
import nes_ncr1_live as live
import nes_ncr1_live_resource as resource
ROOT=live.ROOT
original_prepare=live.prepare
CANDIDATE='NES-R1-OAM-BANKED-048'

def bank_ppu(text):
 start=text.index('module OAMEval(');end=text.index('endmodule',start)+len('endmodule');old=text[start:end];s=old
 assert s.count('reg [7:0] oam[256];')==1
 s=s.replace('reg [7:0] oam[256];','\n'.join('reg [7:0] oam_bank'+str(i)+'[0:31];' for i in range(8)))
 ss='if (Savestate_OAMWrEn) oam[Savestate_OAMAddr] <= Savestate_OAMWriteData;';assert s.count(ss)==1;s=s.replace(ss,'// Primary OAM writes are factored into independent byte lanes below.')
 cp=re.compile(r"\s*oam\[\{oam_row_cur, 3'b([01]{3})\}\] <= oam\[\{oam_row_last, 3'b\1\}\];")
 s,n=cp.subn('',s);assert n==8,n
 wr="oam[oam_read_addr] <= (is_attr_byte) ? (oam_din & 8'hE3) : oam_din;";assert s.count(wr)==1;s=s.replace(wr,'// Primary byte write handled by the bank writer.')
 # Remaining occurrences are reads. Balanced brackets retain slices inside addresses.
 pos=0
 while True:
  a=s.find('oam[',pos)
  if a<0:break
  depth=1;b=a+4
  while depth:
   if s[b]=='[':depth+=1
   elif s[b]==']':depth-=1
   b+=1
  expr=s[a+4:b-1];replacement='oam_read('+expr+')';s=s[:a]+replacement+s[b:];pos=a+len(replacement)
 decl="""
// Original048 structural mapping: addr[2:0] is a lane, addr[7:3] a row.
// Three original write sources keep their source-order priority per byte.
function automatic [7:0] oam_read(input [7:0] address);
 case(address[2:0])
"""+'\n'.join(f" 3'd{i}:oam_read=oam_bank{i}[address[7:3]];" for i in range(8))+"\n default:oam_read=8'hxx;\n endcase\nendfunction\n"
 writers=''
 for i in range(8):
  writers+=f"""
always @(posedge clk)begin
 if(Savestate_OAMWrEn && Savestate_OAMAddr[2:0]==3'd{i})
  oam_bank{i}[Savestate_OAMAddr[7:3]]<=Savestate_OAMWriteData;
 if(!reset && ce)begin
  if(((~old_rendering && rendering) || corrupting_write) && ~PAL &&
     ((old_using_secondary != using_secondary) || corrupting_write))
   oam_bank{i}[oam_row_cur]<=oam_bank{i}[oam_row_last];
  if(oam_data_write && !rendering && oam_read_addr[2:0]==3'd{i})
   oam_bank{i}[oam_read_addr[7:3]]<=is_attr_byte ? (oam_din & 8'hE3) : oam_din;
 end
end
"""
 # Declare function after bank declarations, before procedural calls.
 anchor='reg [1:0] eval_count;';assert s.count(anchor)==1;s=s.replace(anchor,anchor+'\n'+decl)
 s=s.replace('endmodule',writers+'\nendmodule')
 assert 'oam[' not in s
 return text[:start]+s+text[end:]

def prepare(out):
 sources=original_prepare(out);p=out/'rtl/ppu.sv';old=p.read_text();new=bank_ppu(old);live.put(p,new)
 live.put(out/'oam-banking.diff',''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='047/rtl/ppu.sv',tofile='048/rtl/ppu.sv')))
 sources['rtl/ppu.sv']=live.sha(p);sources['oam-banking.diff']=live.sha(out/'oam-banking.diff');return sources

def equivalent(a):
 out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir()
 ref=ROOT/'analysis/local-ncr1-live-047/rtl/rtl/ppu.sv';old=ref.read_text();new=bank_ppu(old)
 def extract(text,name):
  m=re.search(r'(?ms)^module OAMEval\(.*?^endmodule',text);assert m
  return text[:text.index('import regs_savestates::*;')]+'import regs_savestates::*;\n'+m[0].replace('module OAMEval(', 'module '+name+'(',1)+'\n'
 live.put(out/'oam_reference.sv',extract(old,'oam_reference'));live.put(out/'oam_banked.sv',extract(new,'oam_banked'))
 for n in ('rtl/regs_savestates.sv','rtl/bus_savestates.vhd','COPYING'):
  src=ROOT/'analysis/local-ncr1-live-047/rtl'/n;shutil.copy2(src,out/Path(n).name)
 shutil.copy2(ROOT/'tests/nes-functional/oam_banked_tb.sv',out/'oam_banked_tb.sv')
 sources={p.name:live.sha(p) for p in out.iterdir() if p.is_file()}
 for tool,args,name in [('vlib',['work'],'vlib'),('vcom',['-2008','bus_savestates.vhd'],'vcom'),('vlog',['-sv','-mfcu','regs_savestates.sv','oam_reference.sv','oam_banked.sv','oam_banked_tb.sv'],'vlog'),('vsim',['-c','oam_banked_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation')]:
  with (out/(name+'.log')).open('wb') as f:cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  assert cp.returncode==0,name
 log=(out/'simulation.log').read_text(errors='replace');m=re.search(r'PASS OAM BANKING cycles=(\d+) row_copies=(\d+) cpu_writes=(\d+) ss_writes=(\d+) collisions=(\d+)',log)
 assert m and not re.search(r'\*\* (?:Fatal|Error):',log),'Inspect raw simulation.log'
 counts=list(map(int,m.groups()));assert counts[0]>100000 and min(counts[1:])>0,counts
 x={'candidate':CANDIDATE,'passed':True,'sources':sources,'cycles':counts[0],'row_copies':counts[1],'cpu_writes':counts[2],'ss_writes':counts[3],'write_collisions':counts[4],'scope':'Differential every-edge outputs, primary256bytes, secondary64bytes and evaluator state, directed+random NTSC/PAL inputs; simulation equivalence, not formal exhaustive proof'}
 live.put(out/'result.json',json.dumps(x,indent=2)+'\n');print(json.dumps(x,indent=2))

def main():
 mode=sys.argv.pop(1)
 if mode=='equivalence':
  p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
  assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''));equivalent(a);return
 out=Path(sys.argv[sys.argv.index('--out')+1]);live.prepare=prepare;resource.prepare=prepare
 if mode=='resource':resource.main()
 elif mode=='live':live.main()
 else:raise ValueError(mode)
 p=out/'result.json';m=json.loads(p.read_text());m['reference_candidate']=m['candidate'];m['candidate']=CANDIDATE;m['driver_sha256']=live.sha(Path(__file__));live.put(p,json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
