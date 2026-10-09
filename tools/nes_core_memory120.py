# SPDX-License-Identifier: MIT
"""Replay pinned actual052 core at part access delay; no hardware/production edit."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,difflib
from nes_ncr1_live import ROOT,FILES,verify_case
from nes_functional import VHDL,SV,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();assert str(o).isascii() and not o.exists()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 manifest=json.loads((ROOT/'analysis/rom-physical-artifacts.json').read_bytes())
 pinned=[v for rows in manifest.values() if isinstance(rows,list) for v in rows if isinstance(v,dict) and 'path' in v and 'sha256' in v]
 prefix='analysis/local-rom-physical-052/live/'
 pins={x['path'][len(prefix):]:x['sha256'] for x in pinned if x['path'].startswith(prefix)}
 assert pins['result.json']==sha(a.baseline/'result.json')
 baseline=json.loads((a.baseline/'result.json').read_bytes())
 o.mkdir();inputs={}
 for n,h in baseline['sources'].items():
  assert sha(a.baseline/n)==h and pins[n]==h,n
  dest=o/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.baseline/n,dest);inputs[n]=h
 # Final052 reader only differs in attributes and explicit widths from live052.
 shutil.copy2(ROOT/'src/nes/nes_rom_physical.sv',o/'nes_rom_physical.sv')
 old=(o/'ncr1_live_tb.sv').read_text();s=old
 def edit(before,after):
  nonlocal s
  assert s.count(before)==1,before;s=s.replace(before,after)
 edit('module ncr1_live_tb;','module ncr1_live_tb #(parameter integer READ120=3,parameter realtime ACCESS120=25.0);')
 edit('.READ_CYCLES(3)', '.READ_CYCLES(READ120)')
 edit('rom_physical_model #(.FIXTURE(1))','rom_physical_model #(.FIXTURE(1),.ACCESS_NS(ACCESS120))')
 edit(' integer physical_requests=0,physical_responses=0,physical_start=0,physical_min=1000,physical_max=0;',''' integer physical_requests=0,physical_responses=0,physical_start=0,physical_min=1000,physical_max=0;
 integer cpu_samples120=0,ppu_samples120=0;
 always @(posedge clk)if(!reset)begin
  if(rom_cpu_sample && cpumem_addr<65536)cpu_samples120++;
  if(tap_ce && ppumem_read && ppumem_addr>=22'h200000 && ppumem_addr<22'h208000)ppu_samples120++;
  if(physical_responses>=8192 && cpu_samples120>=128 && ppu_samples120>=128)begin
   $display("PASS120 MEMORY responses=%0d cpu_samples=%0d ppu_samples=%0d latency=%0d..%0d tick=%0d",physical_responses,cpu_samples120,ppu_samples120,physical_min,physical_max,bg_tick);
   $finish;
  end
  if(bg_tick>=1000000)$fatal(1,"MEM120 observation coverage incomplete cpu=%0d ppu=%0d",cpu_samples120,ppu_samples120);
 end
 ''')
 edit('if(rom_fault)begin','if(rom_fault)begin\n $display("MEM120 fault_latency=%0d..%0d pending_age=%0d responses=%0d",physical_min,physical_max,bg_tick-physical_start,physical_responses);')
 (o/'ncr1_live_tb.sv').write_text(s,encoding='utf-8')
 (o/'testbench.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='052/ncr1_live_tb.sv',tofile='120/ncr1_live_tb.sv')),encoding='utf-8')
 meta=dict(candidate='NES-CORE-MEMORY-120',inputs=inputs,sources={n:sha(o/n) for n in inputs},cases=[],passed=False,production_changed=False,memory_period_ns=11.904762,core_period_ns=46.560846,scope='Actual052 CPU/PPU/early service/CDC, pin model access delay. No board/PLL/STM32/loader/physical timing proof.')
 def save():(o/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
 def run(tool,args,cwd,log):
  with (cwd/log).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=900)
  return r.returncode
 save();assert run('vlib',['work'],o,'vlib.log')==0
 for i,n in enumerate(VHDL):assert run('vcom',['-2008',n],o,f'vcom-{i}.log')==0
 sv=SV+['cart_nrom.sv','nes_probe.sv']+[n+'.sv' for n in FILES+['nes_local_memory','nes_rom_service','nes_rom_physical']]+['rom_backend_model.sv','ncr1_live_tb.sv']
 assert run('vlog',['-sv','-mfcu',*sv],o,'vlog.log')==0
 for cycles,access in [(3,25),(3,70),(7,70),(8,70)]:
  for case in ['fine_x','banks32']:
   group=o/f'read{cycles}-access{access}';group.mkdir(exist_ok=True);c=group/case;c.mkdir()
   for n in ['prg.hex','chr.hex','manifest.json']:
    name=case+'/'+n;assert sha(a.baseline/name)==pins[name],name;shutil.copy2(a.baseline/name,c/n)
   (c/'modelsim.ini').write_text('[Library]\nwork = '+(o/'work').as_posix()+'\nothers = '+(a.questa_bin.parent/'modelsim.ini').as_posix()+'\n')
   code=run('vsim',['-c','-ini','modelsim.ini','work.ncr1_live_tb',f'-gREAD120={cycles}',f'-gACCESS120={access}.0','+CHR32='+str(int(case=='banks32')),'-do','onerror {quit -code 1}; run -all; quit -f'],c,'simulation.log')
   log=(c/'simulation.log').read_text(errors='replace');fatal=re.search(r'\*\* Fatal: ([^\r\n]+)',log)
   row=dict(case=case,read_cycles=cycles,access_ns=access,process_exit=code,log_sha256=sha(c/'simulation.log'))
   if fatal:
    row.update(outcome='rejected',reason=fatal[1]);assert 'ROM byte mismatch' in fatal[1] or 'ROM DEADLINE/PROTOCOL' in fatal[1],fatal[1]
    m=re.search(r'MEM120 fault_latency=(\d+)\.\.(\d+) pending_age=(\d+) responses=(\d+)',log)
    if m:row.update(latency_min=int(m[1]),latency_max=int(m[2]),pending_age=int(m[3]),responses=int(m[4]))
   else:
    assert code==0 and not re.search(r'\*\* (?:Error|Fatal):',log)
    m=re.search(r'PASS120 MEMORY responses=(\d+) cpu_samples=(\d+) ppu_samples=(\d+) latency=(\d+)\.\.(\d+) tick=(\d+)',log);assert m,log[-2000:]
    row.update(outcome='pass',responses=int(m[1]),cpu_samples=int(m[2]),ppu_samples=int(m[3]),latency_min=int(m[4]),latency_max=int(m[5]),tick=int(m[6]),scope='bounded memory-sample prefix, not8frame/video equivalence')
   if access==25:assert row['outcome']=='pass',row
   meta['cases'].append(row);save();print(json.dumps(row),flush=True)
 meta['passed']=True;save()
if __name__=='__main__':main()
