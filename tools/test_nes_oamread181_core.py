# SPDX-License-Identifier: MIT
"""Bounded actual CPU/PPU/MMC3 OAM DMA comparison, ideal ROM/RAM backend."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,VHDL,SV,sha
from build_nes_oam_dma import build,pattern

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(exist_ok=False)
 build(a.out/'diagnostic');m=json.loads((a.prepared/'preparation.json').read_bytes())
 files=VHDL+SV+['cart_nrom.sv','nes_probe.sv']
 original=(ROOT/'tests/nes-functional/oam_dma_tb.sv').read_text()
 # Mirror the original 32KiB diagnostic over the board's 256KiB MMC3 window.
 # This changes only the ideal test backend, not the selected core or ROM code.
 tb=original.replace('cpumem_addr<32768','cpumem_addr<262144').replace('prg[cpumem_addr]','prg[cpumem_addr[14:0]]')
 tb=tb.replace('dut.core.ppu.spriteeval.oam[j]','dut.core.ppu.spriteeval.oam_read(j)')
 header=(a.prepared/'nes_probe.sv').read_text().split('module nes_probe(',1)[1].split(');',1)[0]
 extra=["wire [7:0] native_oam_address=0;wire chr_32k=0;"]
 direction=signed=width=''
 for part in header.split(','):
  part=part.strip();decl=re.fullmatch(r'(input|output)\s+wire\s+(signed\s+)?(\[[^\]]+\]\s*)?(\w+)',part)
  if decl:direction,signed,width,name=decl.groups();signed=signed or '';width=width or ''
  else:assert re.fullmatch(r'\w+',part),part;name=part
  if direction=='output' and not re.search(r'\b'+name+r'\s*[;,]',tb):extra.append(f'wire {signed}{width}{name};')
 tb=tb.replace('nes_probe dut(.*);','\n'.join(extra)+'\nnes_probe dut(.*);')
 # Observe that every consumed read address/control is stable from negedge
 # to posedge in this real CPU/PPU run. The source RTL itself is not instrumented.
 probe='''
 reg [63:0] half_inputs;integer half_checks=0;
 wire [63:0] read_inputs={23'd0,dut.core.ppu.spriteeval.oam_read_addr,
  dut.core.ppu.spriteeval.oam_row_last,dut.core.ppu.spriteeval.oam_addr_ex,
  dut.core.ppu.spriteeval.oam_addr,dut.core.ppu.spriteeval.Savestate_OAMAddr,
  dut.core.ppu.spriteeval.ce,dut.core.ppu.spriteeval.Savestate_OAMRdEn,
  dut.core.ppu.spriteeval.oam_copy_write,dut.core.ppu.spriteeval.oam_cpu_write,
  dut.core.ppu.spriteeval.Savestate_OAMWrEn,1'b0};
 always @(negedge clk)half_inputs=read_inputs;
 always @(posedge clk)if(!reset_nes && started)begin
  if(read_inputs!==half_inputs)$fatal(1,"half-cycle address/control changed");half_checks++;
 end
'''
 tb=tb.replace('initial begin\n $readmemh',probe+'\ninitial begin\n $readmemh')
 tb=tb.replace('$display("PASS NES DIAGNOSTIC");', '$display("PASS OAMREAD181 CORE half_checks=%0d",half_checks);$display("PASS NES DIAGNOSTIC");')
 results={}
 for label,folder in [('baseline',a.baseline),('candidate',a.prepared)]:
  d=a.out/label;d.mkdir()
  for n in files:
   expected=m['sources'][n] if label=='candidate' else m['baseline_oamread_sources'][n]
   assert sha(folder/n)==expected,n;dest=d/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(folder/n,dest)
  shutil.copy2(a.out/'diagnostic/prg.hex',d/'prg.hex')
  (d/'nes_tb.sv').write_text(tb,encoding='utf8',newline='\n')
  def run(exe,args,logname):
   with (d/(logname+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=180)
   s=(d/(logname+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:];return s
  run('vlib',['work'],'vlib')
  for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
  run('vlog',['-sv','-mfcu',*SV,'cart_nrom.sv','nes_probe.sv','nes_tb.sv'],'compile')
  log=run('vsim',['-c','work.nes_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation')
  match=re.search(r'PASS OAMREAD181 CORE half_checks=(\d+)',log);assert match,log[-3000:]
  assert 'branch_cases=16 period_errors=0 unknown_bus=0' in log
  results[label]=dict(half_checks=int(match[1]),bus_sha256=sha(d/'dma-bus.tsv'),oam_sha256=sha(d/'oam.tsv'))
 assert results['baseline']==results['candidate']
 # Independent expected final OAM bytes for all 16 DMA cases.
 cases=json.loads((a.out/'diagnostic/manifest.json').read_bytes())['cases'];checked=0
 for line in (a.out/'candidate/oam.tsv').read_text().splitlines():
  cols=line.split()
  if cols[0]!='O':continue
  case,address,value=map(int,cols[1:]);c=cases[case-1];expected=pattern(c['page'],(address-c['oam_start'])%256)
  if address%4==2:expected&=0xe3
  assert value==expected,(case,address,value,expected);checked+=1
 assert checked==4096
 result=dict(passed=True,results=results,dma_cases=16,independent_bytes=checked,scope=__doc__,rom='original MIT diagnostic; not SMB3',
   source_sha256=sha(a.prepared/'rtl/ppu.sv'),runner_sha256=sha(Path(__file__)),physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result),flush=True)
if __name__=='__main__':main()
