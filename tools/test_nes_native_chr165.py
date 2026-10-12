# SPDX-License-Identifier: MIT
"""Standalone passive CHR cache, using private target-ROM bytes as a fixture."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ['rom','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 assert sha(a.rom)=='dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
 a.out.mkdir(parents=True);rom=a.rom.read_bytes();chr_data=rom[16+262144:];assert len(chr_data)==131072
 (a.out/'chr.hex').write_text(''.join(f'{b:02x}\n' for b in chr_data))
 sources={}
 for n in ['src/nes/diagnostic/nes_native_chr165.sv','tests/nes-functional/native_chr165_tb.sv']:
  shutil.copy2(ROOT/n,a.out/Path(n).name);sources[n]=sha(ROOT/n)
 for tool,args in [('vlib',['work']),('vlog',['-sv','nes_native_chr165.sv','native_chr165_tb.sv']),('vsim',['-c','work.native_chr165_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (a.out/(tool+'.log')).open('wb') as f:
   r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=240)
  text=(a.out/(tool+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-4000:]
 match=re.search(r'PASS165 CHR tiles=(\d+) captured=(\d+) checks=(\d+) negatives=(\d+)',text);assert match,text[-3000:]
 result=dict(passed=True,tiles=int(match[1]),captured=int(match[2]),checks=int(match[3]),negative_checks=int(match[4]),public_sources=sources,
  rom_sha256=sha(a.rom),scope='Single-clock standalone cache, synthetic PPU sample schedule and real immutable CHR bytes. Not actual PPU/mapper execution, host CDC, synthesis, complete rendering or hardware.',hardware=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(match[0],flush=True)
if __name__=='__main__':main()
