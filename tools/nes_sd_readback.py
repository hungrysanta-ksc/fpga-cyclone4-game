# SPDX-License-Identifier: MIT
"""060 buffered SD binding to059; frozen044/056/059 source is preserved."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_mcu_loader import ROOT,FW,source as source056,materialize as loader,run,sha
from build_nes_video_workloads import build

def source():
 return source056()+'\n'+(FW/'nes_sd_readback.inc').read_text(encoding='utf-8')

def materialize(out):
 loader(out)
 for n in ['nes_rom_verify.c','nes_rom_verify.h','nes_sd_readback.h']:shutil.copy2(FW/n,out/n)
 (out/'nes_h1_stm32.c').write_text(source(),encoding='utf-8',newline='\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True)
 p.add_argument('--mutation',choices=['crc','close'])
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 shutil.copy2(Path(__file__),out/'executed-driver.py');materialize(out)
 if a.mutation:
  path=out/'nes_h1_stm32.c';text=path.read_text()
  old='||(c->crc^0xffffffffu)!=c->expected_crc' if a.mutation=='crc' else 'if(r->file_result!=FR_OK){r->result=NES_MCU_LOAD_CLOSE;return false;}'
  assert text.count(old)==1
  path.write_text(text.replace(old,''),encoding='utf-8',newline='\n')
 for n in ['mcu_loader_platform.h','sd_readback_host.c']:shutil.copy2(ROOT/'tests/nes-functional'/n,out/n)
 for n in ['config','bits','timer','snes','fpga','fpga_spi','fileops','uart']:(out/(n+'.h')).write_text('#include "mcu_loader_platform.h"\n')
 fixtures={c:build(out/c,c) for c in ['fine_x','banks32']}
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-O2','-ffunction-sections','-fdata-sections','-Wl,--gc-sections',
  'nes_rom_spi.c','nes_rom_verify.c','nes_h1_stm32.c','nes_h1_session.c','sd_readback_host.c','-o','host.exe'],out,'compile')
 command=[str(x) for x in [out/'host.exe',out/'fine_x/mmc3.nes',out/'banks32/mmc3.nes',out/'waveform.txt',out/'load-waveform.txt']]
 if a.mutation:
  with (out/'host.log').open('wb') as f:cp=subprocess.run(command,cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  log=(out/'host.log').read_text(errors='replace');prior=28 if a.mutation=='crc' else 29
  assert cp.returncode!=0 and 'Assertion failed: r->result==expected' in log and f'PASS SD lifecycle fault={prior} ' in log
  r=dict(candidate='NES-SD-READBACK-060',mutation=a.mutation,expected_failure_verified=True,incorrect_design_passed=False,
   exit_code=cp.returncode,files={p.name:sha(p) for p in sorted(out.iterdir()) if p.suffix in ['.c','.h','.log']},driver_sha256=sha(out/'executed-driver.py'))
  (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS expected failure: missing final '+a.mutation+' validation');return
 log=run(command,out,'host')
 marker='PASS SD READBACK lifecycle=41 header_rejections=18 no_start=1 no_sd_writes=1'
 assert marker in log
 r=dict(candidate='NES-SD-READBACK-060',host_model_pass=True,actual_stm32_execution=False,marker=marker,
  files={p.name:sha(p) for p in sorted(out.iterdir()) if p.suffix in ['.c','.h','.log']},
  fixtures={c:m['sha256'] for c,m in fixtures.items()},waveform_sha256=sha(out/'waveform.txt'),load_waveform_sha256=sha(out/'load-waveform.txt'),driver_sha256=sha(out/'executed-driver.py'))
 (out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(marker)

if __name__=='__main__':main()
