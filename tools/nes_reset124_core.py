# SPDX-License-Identifier: MIT
"""Actual052 core with reset124 CF86 registered reader at READ16/70ns at168MHz control."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,difflib
from nes_ncr1_live import ROOT,FILES,verify_case
from nes_functional import VHDL,SV,sha
from nes_reset124 import materialize

def compare(group,baseline,case,pins):
 result=verify_case(group,case)
 c,old=group/case,baseline/case
 offsets=[]
 for n in ['live.tsv']+[f'{kind}-{i}.{ext}' for i in range(1,5) for kind,ext in [('packet','bin'),('frame','hex')]]:
  assert sha(old/n)==pins[case+'/'+n],n
 for i in range(1,5):
  p,q=(c/f'packet-{i}.bin').read_bytes(),(old/f'packet-{i}.bin').read_bytes()
  assert p[:12]+p[16:]==q[:12]+q[16:],('packet',case,i)
  assert (c/f'frame-{i}.hex').read_bytes()==(old/f'frame-{i}.hex').read_bytes(),('pixels',case,i)
  offsets.append(int.from_bytes(p[12:16],'little')-int.from_bytes(q[12:16],'little'))
 assert len(set(offsets))==1,offsets
 rows=lambda p:[s.split() for s in p.read_text().splitlines() if not s.startswith('B ')]
 before,after=rows(old/'live.tsv'),rows(c/'live.tsv')
 assert len(before)==len(after)
 for p,q in zip(before,after):
  j=4 if p[0]=='E' else 2
  assert p[:j]+p[j+1:]==q[:j]+q[j+1:] and int(q[j])-int(p[j])==offsets[0],(p,q)
 log=(c/'simulation.log').read_text()
 physical=re.search(r'PHYSICAL responses=(\d+) latency=(\d+)\.\.(\d+)',log)
 requests=int(re.search(r'ROM SERVICE requests=(\d+)',log)[1])
 assert physical and requests-int(physical[1]) in (0,1)
 result.update(tick_offsets_vs052=offsets,rom_requests=requests,rom_responses=int(physical[1]),latency_min=int(physical[2]),latency_max=int(physical[3]))
 return result

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
 o.mkdir();shutil.copy2(__file__,o/'executed-driver.py');inputs={}
 for n,h in baseline['sources'].items():
  assert sha(a.baseline/n)==h and pins[n]==h,n
  dest=o/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.baseline/n,dest);inputs[n]=h
 shutil.copy2(ROOT/'src/nes/diagnostic/nes_diag_safe_rom_physical.sv',o/'nes_rom_physical.sv')
 old=(o/'ncr1_live_tb.sv').read_text();s=old
 def edit(before,after):
  nonlocal s
  assert s.count(before)==1,before;s=s.replace(before,after)
 edit('module ncr1_live_tb;','module ncr1_live_tb #(parameter realtime PHASE122=3.5);')
 edit('.READ_CYCLES(3)','.READ_CYCLES(16)')
 edit('physical(.clk(clk),',"physical(.check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),.check_ready(),.check_response(),.check_response_address(),.check_data(),.clk(clk),")
 edit('initial begin #3.5;forever #5.952381 mem_clk','initial begin #(PHASE122);forever #2.9761905 mem_clk')
 edit('rom_physical_model #(.FIXTURE(1))','rom_physical_model #(.FIXTURE(1),.ACCESS_NS(70.0))')
 (o/'ncr1_live_tb.sv').write_text(s,encoding='utf-8')
 (o/'testbench.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='052/ncr1_live_tb.sv',tofile='122/ncr1_live_tb.sv')),encoding='utf-8')
 materialize(o,'core')
 meta=dict(candidate='NES-DOMAIN-RESET-124-CORE',inputs=inputs,sources={n:sha(o/n) for n in [*inputs,'nes_domain_reset124.sv','executed-reset124.py']},cases=[],passed=False,production_changed=False,read_cycles=16,access_ns=70,phases_ns=[3.5],quantized_memory_period_ns=5.952,quantized_core_period_ns=46.560,scope='Actual052 CPU/PPU/early service/CDC + reset124 CF86 registered reader at168MHz control/16cycles maintaining95.232ns capture access. Four frames each fixture per phase; fixed70ns pin model. No board/PLL/STM32/loader/SNES software or physical timing proof.')
 def save():(o/'result.json').write_text(json.dumps(meta,indent=2)+'\n')
 def run(tool,args,cwd,log):
  with (cwd/log).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
  txt=(cwd/log).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (?:Error|Fatal):',txt),str(cwd/log)
 save();run('vlib',['work'],o,'vlib.log')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],o,f'vcom-{i}.log')
 sv=SV+['cart_nrom.sv','nes_probe.sv']+[n+'.sv' for n in FILES+['nes_local_memory','nes_rom_service','nes_rom_physical']]+['rom_backend_model.sv','nes_domain_reset124.sv','ncr1_live_tb.sv']
 run('vlog',['-sv','-mfcu',*sv],o,'vlog.log')
 for phase in meta['phases_ns']:
  for case in ['fine_x']:
   group=o/f'phase{int(phase*1000):05d}';group.mkdir(exist_ok=True);c=group/case;c.mkdir()
   for n in ['prg.hex','chr.hex','manifest.json']:
    name=case+'/'+n;assert sha(a.baseline/name)==pins[name],name;shutil.copy2(a.baseline/name,c/n)
   (c/'modelsim.ini').write_text('[Library]\nwork = '+(o/'work').as_posix()+'\nothers = '+(a.questa_bin.parent/'modelsim.ini').as_posix()+'\n')
   print(f'RUN122 phase={phase} case={case}',flush=True)
   run('vsim',['-c','-ini','modelsim.ini','work.ncr1_live_tb',f'-gPHASE122={phase}','+CHR32='+str(int(case=='banks32')),'-do','onerror {quit -code 1}; run -all; quit -f'],c,'simulation.log')
   row=compare(group,a.baseline,case,pins);row.update(phase_ns=phase,log_sha256=sha(c/'simulation.log'))
   meta['cases'].append(row);save();print(json.dumps(row),flush=True)
 meta['passed']=True;save()
if __name__=='__main__':main()
