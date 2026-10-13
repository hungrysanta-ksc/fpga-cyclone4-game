# SPDX-License-Identifier: MIT
"""Compare actual banked OAM before/after selection factoring, edge by edge."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 assert not a.out.exists() and str(a.out).isascii();a.out.mkdir(parents=True)
 prep=json.loads((a.prepared/'preparation.json').read_bytes())
 for n,h in prep['sources'].items():assert sha(a.prepared/n)==h,n
 for directory,name in [(a.baseline,'oam_reference'),(a.prepared,'oam_banked')]:
  s=(directory/'rtl/ppu.sv').read_text();m=re.search(r'(?ms)^module OAMEval\(.*?^endmodule',s);assert m
  (a.out/(name+'.sv')).write_text(s[:s.index('import regs_savestates::*;')]+'import regs_savestates::*;\n'+m[0].replace('module OAMEval(', 'module '+name+'(',1)+'\n')
 for n in ['regs_savestates.sv','bus_savestates.vhd']:shutil.copy2(a.prepared/'rtl'/n,a.out/n)
 s=(ROOT/'tests/nes-functional/oam_banked_tb.sv').read_text()
 s=s.replace('reference.oam[i]','reference.oam_read(i)')
 old='for(integer i=0;i<256;i++)if(reference.oam_read(i)!==candidate.oam_read(i))$fatal(1,"primary OAM mismatch cycle%0d addr%0d ref%h new%h",cycles_checked,i,reference.oam_read(i),candidate.oam_read(i));'
 assert old in s
 expr=lambda inst:','.join(f'{inst}.oam_bank{k}[i]' for k in range(8))
 s=s.replace(old,'for(integer i=0;i<32;i++)if({'+expr('reference')+'}!=={'+expr('candidate')+'})$fatal(1,"primary OAM mismatch row%0d edge%0d",i,cycles_checked);')
 s=s.replace('wire [7:0] ref_bus',"wire [7:0] native_oam_address=Savestate_OAMAddr;wire [7:0] ref_native,new_native;wire ref_write,new_write;\n wire [7:0] ref_bus")
 s=s.replace('reference(.oam_bus','reference(.native_oam_data(ref_native),.native_oam_write(ref_write),.oam_bus')
 s=s.replace('candidate(.oam_bus','candidate(.native_oam_data(new_native),.native_oam_write(new_write),.oam_bus')
 s=s.replace('if({ref_bus,','if({ref_native,ref_write,ref_bus,').replace('!=={new_bus,','!=={new_native,new_write,new_bus,')
 (a.out/'oam_banked_tb.sv').write_text(s)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  log=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),log[-3000:]
  return log
 run('vlib',['work'],'vlib');run('vcom',['-2008','bus_savestates.vhd'],'vcom')
 run('vlog',['-sv','-mfcu','regs_savestates.sv','oam_reference.sv','oam_banked.sv','oam_banked_tb.sv'],'vlog')
 log=run('vsim',['-c','oam_banked_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation')
 m=re.search(r'PASS OAM BANKING cycles=(\d+) row_copies=(\d+) cpu_writes=(\d+) ss_writes=(\d+) collisions=(\d+)',log);assert m
 counts=list(map(int,m.groups()));assert counts[0]>100000 and min(counts[1:])>0
 result=dict(passed=True,cycles=counts[0],row_copies=counts[1],cpu_writes=counts[2],savestate_writes=counts[3],write_collisions=counts[4],
  source_sha256=sha(a.prepared/'rtl/ppu.sv'),reference_sha256=sha(a.baseline/'rtl/ppu.sv'),
  public_sources={n:sha(ROOT/n) for n in ['tools/nes_oam_select165.py','tools/test_nes_oam_select165.py','tests/nes-functional/oam_banked_tb.sv']},
  scope='Every-edge outputs, native observer, all primary/secondary OAM and evaluator state. Directed collisions, seeded randomized inputs, full NTSC/PAL cadence. Not formal equivalence or full game test.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
