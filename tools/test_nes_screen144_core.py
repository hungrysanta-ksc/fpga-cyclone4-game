# SPDX-License-Identifier: MIT
"""One changed-CHR run through current CPU/PPU/service/reader and NCR1 transport."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,re
from nes_spi_boot import ROOT,sha
from nes_functional import VHDL,SV
from nes_ncr1_live import FILES,verify_case
from nes_screen144 import build,banner

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--verify-existing',action='store_true')
 a=p.parse_args();o=a.out;assert (a.verify_existing or not o.exists()) and str(o).isascii()
 assert a.verify_existing or os.environ.get('SALT_LICENSE_SERVER') in ['18000@localhost','18000@127.0.0.1']
 old=a.baseline/'nes-reset124/evidence-final';current=a.baseline/'nes-screen143/evidence-final'
 for e,m in [(old,'reset124'),(current,'screen143')]:
  assert sha(e/'manifest.json')==json.loads((ROOT/f'analysis/{m}-verification.json').read_bytes())['manifest_sha256']
 oldpins=json.loads((old/'manifest.json').read_bytes())['files'];pins=json.loads((current/'manifest.json').read_bytes())['files']
 src=old/'core01';meta=json.loads((src/'result.json').read_bytes());o.mkdir(exist_ok=a.verify_existing);sources={}
 for n in meta['sources']:
  if Path(n).suffix not in ['.sv','.v','.vhd']:continue
  ref=current/'fit'/n if 'fit/'+n in pins else src/n
  h=pins['fit/'+n] if 'fit/'+n in pins else oldpins['core01/'+n]
  assert sha(ref)==h,n
  dst=o/n;dst.parent.mkdir(parents=True,exist_ok=True)
  if a.verify_existing:assert sha(dst)==h,n
  else:shutil.copy2(ref,dst)
  sources[n]=h
 def run(exe,args,cwd,log):
  with (cwd/log).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=1200)
  s=(cwd/log).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (?:Error|Fatal):',s),(log,s[-2000:])
 if not a.verify_existing:
  run('vlib',['work'],o,'vlib.log')
  for i,n in enumerate(VHDL):run('vcom',['-2008',n],o,f'vcom-{i}.log')
  sv=SV+['cart_nrom.sv','nes_probe.sv']+[n+'.sv' for n in FILES+['nes_local_memory','nes_rom_service','nes_rom_physical']]+['rom_backend_model.sv','nes_domain_reset124.sv','ncr1_live_tb.sv']
  run('vlog',['-sv','-mfcu',*sv],o,'vlog.log')
  c=o/'fine_x';build(a.baseline,c)
  (c/'modelsim.ini').write_text('[Library]\nwork = '+(o/'work').as_posix()+'\nothers = '+(a.questa_bin.parent/'modelsim.ini').as_posix()+'\n')
  run('vsim',['-c','-ini','modelsim.ini','work.ncr1_live_tb','-gPHASE122=3.5','+CHR32=0','-do','onerror {quit -code 1}; run -all; quit -f'],c,'simulation.log')
 c=o/'fine_x'
 result=verify_case(o,'fine_x')
 # Independent spatial oracle: constant PRG writes tile0..255 repeatedly;
 # fine-X scroll1 and the selected CHR bank must reproduce the drawn banner.
 color=[15,33,48,22];banks=[]
 for i in range(1,5):
  packet=(c/f'packet-{i}.bin').read_bytes();tile=int.from_bytes(packet[20:22],'little');bank=tile//512
  assert bank in [0,1];banks.append(bank)
  drawn=banner(bank)
  expected=bytes(color[drawn[(y%64)*256+(x+1)%256]] for y in range(240) for x in range(256))
  actual=bytes.fromhex((c/f'frame-{i}.hex').read_text());assert actual==expected,('banner',i,bank,sum(x!=y for x,y in zip(actual,expected)))
 assert len(set(banks))==2,banks
 result.update(current_sources=sources,banks=banks,independent_banner_pixels=245760,scope='Current selected CPU/PPU/service/reader RTL and124 transport testbench, one phase, four changed-CHR frames. No FPGA board/STM32/SNES concurrent simulation or new timing claim.')
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS144 core banners',banks,flush=True)
if __name__=='__main__':main()
