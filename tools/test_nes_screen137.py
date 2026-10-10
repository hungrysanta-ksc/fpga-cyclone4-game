# SPDX-License-Identifier: MIT
"""New physical SNES bus plus actual135 core/reader/encoder/transport integration."""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_screen137 import prepare,ROOT,put,sha
from nes_functional import VHDL
from build_nes_chr_residency import decode
from build_nes_trace_replay import convert
def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;names=prepare(a.baseline,o)
 assert os.environ.get('SALT_LICENSE_SERVER','') in ['18000@localhost','18000@127.0.0.1']
 for n in ['run133_pll_model.sv','screen137_tb.sv']:shutil.copy2(ROOT/'tests/nes-functional'/n,o/n)
 shutil.copy2(a.baseline/'nes-command135/evidence/fit03/rom_boot_model.sv',o/'rom_boot_model.sv')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  assert r.returncode==0,label
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 sv=[n for n in names if n not in VHDL and n not in ['nes_clock_pll123.v','fxpak_nes_run134_top.sv']]
 run('vlog',['-sv','-mfcu',*sv,'run133_pll_model.sv','nes_screen_bus137.sv','fxpak_nes_screen137_top.sv','rom_boot_model.sv','screen137_tb.sv'],'compile')
 run('vsim',['-c','screen137_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'simulation')
 log=(o/'simulation.log').read_text(errors='replace');assert 'PASS137 packets=3' in log and '** Fatal:' not in log
 data=bytes(int(v,16) for v in (o/'packets.hex').read_text().split());assert len(data)==6024
 atlas=convert(bytes(int(v,16) for v in (o/'chr.hex').read_text().split())).ljust(32768,b'\0')
 frames=[]
 for i in range(3):
  packet=data[i*2008:(i+1)*2008];pixels=bytes(int(v,16) for v in (o/f'frame-{i+1}.hex').read_text().split())
  assert len(pixels)==61440 and decode(packet,atlas)==pixels
  (o/f'packet-{i+1}.bin').write_bytes(packet)
  frames.append(dict(sequence=i+1,pixels=len(pixels),packet_sha256=sha(o/f'packet-{i+1}.bin'),fine_x=packet[6]))
 put(o/'result137.json',json.dumps(dict(passed=True,frames=frames,physical=False,
   scope='Actual core +70ns PSRAM model +SPI START/STOP +122 seeded PRG/CHR and verified state; SNES bus task model, not65816 co-simulation.',
   pass_lines=[s for s in log.splitlines() if 'PASS137' in s]),indent=2)+'\n')
 print('PASS137 three actual-core packets exactly reproduce184320 PPU pixels')
if __name__=='__main__':main()
