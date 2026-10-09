# SPDX-License-Identifier: MIT
"""Actual131 top/CPU/PPU/memory/loader lifecycle; only PLL/RAM and image fixture modeled."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_cdc125_sta import ROOT,sha,put
from nes_functional import VHDL,SV
from nes_ncr1_live import FILES
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();assert not o.exists() and str(o).isascii()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 e=a.baseline/'nes-counter131/evidence';meta=json.loads((ROOT/'analysis/counter131-verification.json').read_bytes());assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];o.mkdir();inputs={}
 names=VHDL+SV+['cart_nrom.sv','nes_probe.sv']+[n+'.sv' for n in FILES+['nes_local_memory','nes_rom_service','nes_rom_physical','nes_rom_loader','nes_rom_boot','nes_rom_spi','nes_spi_boot','nes_domain_reset124','nes_diag_clock_guard127','nes_diag_startup_guard','nes_live_joint']]
 for n in names:
  src=e/'fit05'/n;assert sha(src)==pins['fit05/'+n],n;dest=o/n;dest.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(src,dest);inputs['fit05/'+n]=sha(src)
 n='rom_boot_model.sv';assert sha(e/'test02'/n)==pins['test02/'+n];shutil.copy2(e/'test02'/n,o/n);inputs['test02/'+n]=sha(e/'test02'/n)
 # Quartus accepts these forward declarations; Questa requires declaration first.
 # Hoist only declarations without initializers. No connection/process changes.
 top=o/'nes_live_joint.sv';original=top.read_text();s=original;decls=[]
 for d in ['wire guard_allow,guard_fault,external_memory_ready,startup_ready,release_memory;',
           'wire rom_cpu_sample,rom_cpu_valid,rom_ppu_valid,rom_fault;',
           'wire [3:0] rom_error_code;','wire rom_request;wire [21:0] rom_address;']:
  assert s.count(d)==1;decls.append(d);s=s.replace(d,'')
 pos=s.index(');')+2;s=s[:pos]+'\n'+'\n'.join(decls)+s[pos:];put(top,s)
 put(o/'top-normalization.json',json.dumps(dict(input_sha256=inputs['fit05/nes_live_joint.sv'],hoisted=decls,output_sha256=sha(top)),indent=2)+'\n')
 for n in ['run133_tb.sv','run133_pll_model.sv']:shutil.copy2(ROOT/'tests/nes-functional'/n,o/n)
 shutil.copy2(__file__,o/'executed-run133.py')
 m=dict(candidate='NES-RUN-CONTRACT-133',passed=False,base_manifest=sha(e/'manifest.json'),inputs=inputs,sources={n:sha(o/n) for n in names+['rom_boot_model.sv','run133_tb.sv','run133_pll_model.sv','executed-run133.py']},runs={},production_changed=False,full_image_write_repeated=False,full_check_repeated=False,pll_model=True,physical_trial=False)
 def save():put(o/'run133.json',json.dumps(m,indent=2)+'\n')
 def run(tool,args,label,timeout=600):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
  assert r.returncode==0,label
  return (o/(label+'.log')).read_text(errors='replace')
 def sim(label,phase,expected):
  log=run('vsim',['-c','run133_tb',f'+PHASE_PS={phase}','-do','onerror {quit -code 1}; run -all; quit -f'],label)
  assert expected in log,label
  if expected.startswith('PASS'):assert '** Fatal:' not in log,label
  shutil.copy2(o/'lifecycle133.tsv',o/(label+'.tsv'));m['runs'][label]=dict(expected=expected,passed=True,summary=[x for x in log.splitlines() if 'PASS133' in x or '** Fatal:' in x]);save()
 save();run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 run('vlog',['-sv','-mfcu',*[n for n in names if n not in VHDL],'rom_boot_model.sv','run133_pll_model.sv','run133_tb.sv'],'compile')
 for phase in [0,3500]:sim('normal-'+str(phase),phase,'PASS133 joint')
 s=(o/'nes_live_joint.sv').read_text();assert s.count('common_reset=raw_stop || !memory_ready;')==1
 put(o/'early-core.sv',s.replace('common_reset=raw_stop || !memory_ready;','common_reset=raw_stop;'))
 run('vlog',['-sv','early-core.sv'],'early-core-compile');sim('early-core',3500,'** Fatal: RUN133 core release skipped RAM scrub')
 assert s.count('raw_stop=boot_reset || !run_enable;')==1
 put(o/'missing-stop.sv',s.replace('raw_stop=boot_reset || !run_enable;','raw_stop=boot_reset;'))
 run('vlog',['-sv','missing-stop.sv'],'missing-stop-compile');sim('missing-stop',3500,'** Fatal: RUN133 consumer released before initialization')
 m['passed']=True;save();print('PASS133 actual joint lifecycle + two top-level causal controls')
if __name__=='__main__':main()
