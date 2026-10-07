# SPDX-License-Identifier: MIT
"""059 public C host model + callback waveform (not actual STM32 execution)."""
from pathlib import Path
import argparse,json,shutil,subprocess
from nes_spi_boot import ROOT,sha,put,run

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--gcc',type=Path,required=True)
 p.add_argument('--mutation',action='store_true')
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 shutil.copy2(Path(__file__),out/'executed-driver.py')
 names=['nes_rom_spi.c','nes_rom_spi.h','nes_rom_verify.c','nes_rom_verify.h']
 for n in names:shutil.copy2(ROOT/'src/nes/firmware'/n,out/n)
 names+=['rom_verify_host.c'];shutil.copy2(ROOT/'tests/nes-functional/rom_verify_host.c',out/names[-1])
 if a.mutation:
  target=out/'nes_rom_verify.c';s=target.read_text()
  old='if(rx[3]!=expected){r->error=NES_VERIFY_DATA;goto fail;}'
  assert s.count(old)==1
  put(target,s.replace(old,'expected=rx[3]; /* deliberately wrong: blindly ACK returned data */'))
 run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-O2','nes_rom_spi.c','nes_rom_verify.c','rom_verify_host.c','-o','host.exe'],out,'compile')
 if a.mutation:
  with (out/'host.log').open('wb') as f:
   cp=subprocess.run([str(out/'host.exe'),str(out/'waveform.txt')],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  log=(out/'host.log').read_text(errors='replace')
  assert cp.returncode!=0 and '!nes_rom_verify(&io,total,source,0,&r)' in log
  put(out/'result.json',json.dumps(dict(candidate='NES-SPI-READBACK-059',negative_control_verified=True,incorrect_design_passed=False,
      expected_failure='host rejects blind ACK after altered byte',exit_code=cp.returncode,
      sources={n:sha(out/n) for n in names},log_sha256=sha(out/'host.log'),driver_sha256=sha(Path(__file__))),indent=2)+'\n')
  print('PASS expected failure: blind MCU ACK rejected by corruption regression');return
 log=run([out/'host.exe',out/'waveform.txt'],out,'host')
 marker='PASS MCU VERIFY full_bytes=180224 full_images=2 negative_cases=10 waveform_reads=32 waveform_acks=32 waveform_frames=101 no_start_on_error=1'
 assert marker in log
 put(out/'result.json',json.dumps(dict(candidate='NES-SPI-READBACK-059',host_model_pass=True,actual_stm32_execution=False,marker=marker,
     sources={n:sha(out/n) for n in names},waveform_sha256=sha(out/'waveform.txt'),driver_sha256=sha(Path(__file__))),indent=2)+'\n')
 print(marker)

if __name__=='__main__':main()
