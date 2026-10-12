# SPDX-License-Identifier: MIT
"""Focused actual MMC3/BgPainter/SpriteAddressGen boundaries, not ROM boot."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,VHDL,SV,EXTRA,sha
from nes_native_tap165 import NEW as CACHE
from nes_native_raster165 import NEW as RASTER
from nes_native_scene165 import NEW as SCENE
from nes_native_fetch165 import prepare,NEW
from nes_native_fetch165 import PORTS,OUT
from nes_native_scene165 import PORTS as SCENE_PORTS
from nes_native_raster165 import PORTS as RASTER_PORTS

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 inputs=prepare(a.evidence,a.out)
 tb='tests/nes-functional/native_fetch165_tb.sv';shutil.copy2(ROOT/tb,a.out/Path(tb).name)
 join_tb='tests/nes-functional/native_fetch_join165_tb.sv';shutil.copy2(ROOT/join_tb,a.out/Path(join_tb).name)
 # Extract, do not retype, the exact two-instance wiring from the generated
 # joint. The surrounding CPU/PPU/PLL/board is only compiled, not simulated.
 joint=(a.out/'nes_live_joint.sv').read_text()
 begin=joint.index('wire native_required_initialized,')
 end=joint.index('.memory_data(native_memory_data));',begin)+len('.memory_data(native_memory_data));')
 binding=joint[begin:end]
 ports=SCENE_PORTS+OUT+(PORTS+RASTER_PORTS).replace('output wire','input wire')
 ports+='''input wire clk,reset,tap_ce,rom_fault,ppumem_read,rom_ppu_valid,
 input wire [8:0] scanline,cycle,input wire [1:0] tap_attribute,
 input wire [13:0] native_chr_logical,input wire [21:0] ppumem_addr,input wire [7:0] ppumem_din,
 input wire [7:0] native_nt_data,native_oam_data,input wire native_nt_write,native_oam_write,
 output wire [10:0] native_nt_address,output wire [7:0] native_oam_address'''
 (a.out/'fetch_join_harness.sv').write_text('module fetch_join_harness(\n'+ports+');\n'+binding+'\nendmodule\n')
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-6000:];return s
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 run('vlog',['-sv','-mfcu',*SV,*EXTRA,'nes_live_joint.sv',*[Path(n).name for n in CACHE+RASTER+SCENE+NEW],
             'nes_native_scene_fetch165.sv','fetch_join_harness.sv',Path(tb).name,Path(join_tb).name],'vlog')
 s=run('vsim',['-c','work.native_fetch165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'fetch')
 m=re.search(r'PASS FETCH165 checks=(\d+) events=(\d+) pixels=(\d+) rejects=(\d+)',s);assert m
 s=run('vsim',['-c','work.native_fetch_join165_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'join')
 jm=re.search(r'PASS FETCHJOIN165 checks=(\d+)',s);assert jm
 files=CACHE+RASTER+SCENE+NEW+[tb,join_tb,'tools/nes_native_fetch165.py','tools/test_nes_native_fetch165.py',
  'tools/nes_native_scene165.py','tools/nes_native_raster165.py','tools/nes_native_tap165.py','tools/nes_game147.py','tools/nes_functional.py']
 result=dict(passed=True,checks=int(m[1]),events=int(m[2]),pixels=int(m[3]),rejects=int(m[4]),join_checks=int(jm[1]),inputs=inputs,
  public_sources={n:sha(ROOT/n) for n in files},generated_sources={n:sha(a.out/n) for n in SV+EXTRA+['nes_live_joint.sv','nes_native_scene_fetch165.sv','fetch_join_harness.sv']},
  raw_log_sha256={n.name:sha(n) for n in a.out.glob('*.log')},warnings={n.name:len(re.findall(r'\*\* Warning:',n.read_text(errors='replace'))) for n in a.out.glob('*.log')},
  hardware=False,complete_frame_readiness=False,
  scope='Synthetic fetch schedules through actual MMC3; original BgPainter pixel pipeline and actual SpriteAddressGen metadata/address boundaries. Exact generated collector/scene binding exercised with synthetic state and zero memory sources; surrounding parent joint compiled only. Not ROM execution, descriptor storage, required tile fill, host CDC, SNES output or fit.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(m[0]+'; '+jm[0],flush=True)
if __name__=='__main__':main()
