# SPDX-License-Identifier: MIT
"""Compile089 configuration with the pinned STM32F401 headers; object only."""
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,put,run,sha
PIN='1a43873e74e8a5cc888d099874d9ff17caa6959b4b12ffdd53a9d0987100a3d5'
def main():
 p=argparse.ArgumentParser()
 for n in ['out','evidence084','arm-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.arm_bin=a.arm_bin.resolve();o=a.out.resolve();e=a.evidence084.resolve();assert str(o).isascii() and sha(e/'manifest.json')==PIN
 o.mkdir(parents=True,exist_ok=False);pins=json.loads((e/'manifest.json').read_bytes())['files'];headers={};prefix='work/arm-01/source/src/'
 for n,h in pins.items():
  if n.startswith(prefix) and n.endswith('.h'):
   assert sha(e/n)==h;dest=o/n[len(prefix):];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,dest);headers[n[len(prefix):]]=h
 for n in ['nes_clock_config089.c','nes_clock_config089.h']:shutil.copy2(ROOT/'src/nes/firmware'/n,o/n)
 shutil.copy2(__file__,o/'executed-driver.py')
 args=['-c','-Os','-g','-std=gnu99','-mthumb','-mcpu=cortex-m4','-mfloat-abi=hard','-DF_OSC=8000000UL','-I.','-Iinclude','-Iinclude/arm','-Iobj-report079','-Istm32f4xx','-Wall','-Wstrict-prototypes','-Werror','-Wno-strict-aliasing','-ffunction-sections','-fdata-sections','nes_clock_config089.c','-o','config.o']
 run([a.arm_bin/'arm-none-eabi-gcc.exe',*args],o,'compile')
 dis=run([a.arm_bin/'arm-none-eabi-objdump.exe','-dr','config.o'],o,'disassembly');attrs=run([a.arm_bin/'arm-none-eabi-readelf.exe','-A','config.o'],o,'attributes')
 assert 'nes_clock_config089' in dis and 'Tag_CPU_name: "7E-M"' in attrs
 for n in ['report_decode080','nes_return_io_step','nes_diag_wait_step','nes_return_delay','fpga_set_prog_b','fpga_get_initb','fpga_get_done','fpga_postinit']:assert n in dis,n
 result=dict(source_sha256=sha(o/'nes_clock_config089.c'),header_sha256=sha(o/'nes_clock_config089.h'),object_sha256=sha(o/'config.o'),object_bytes=(o/'config.o').stat().st_size,headers=headers,args=args,linked_firmware=False,physical=False,installable=False)
 put(o/'result.json',json.dumps(result,indent=2)+'\n');print('PASS ARM089 object '+str(result['object_bytes'])+' bytes; no linked firmware')
if __name__=='__main__':main()
