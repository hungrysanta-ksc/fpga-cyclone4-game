# SPDX-License-Identifier: MIT
"""Compile real STM32F401 GPIO reader object against pinned084 headers.
This is NOT a linked or callable firmware image; main/session integration remains.
"""
from pathlib import Path
import argparse,json,shutil,re
from nes_spi_boot import ROOT,put,run,sha
PIN='1a43873e74e8a5cc888d099874d9ff17caa6959b4b12ffdd53a9d0987100a3d5'

def main():
 p=argparse.ArgumentParser()
 for n in ['out','evidence084','arm-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();e=a.evidence084.resolve();assert str(out).isascii();assert sha(e/'manifest.json')==PIN
 out.mkdir(parents=True,exist_ok=False);manifest=json.loads((e/'manifest.json').read_text())['files'];headers={}
 prefix='work/arm-01/source/src/'
 for n,h in manifest.items():
  if n.startswith(prefix) and n.endswith('.h'):
   assert sha(e/n)==h;nout=n[len(prefix):];dest=out/nout;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,dest);headers[nout]=h
 for n in ['nes_clock_reader088.c','nes_clock_reader088.h']:shutil.copy2(ROOT/'src/nes/firmware'/n,out/n)
 shutil.copy2(__file__,out/'executed-driver.py')
 args=['-c','-Os','-g','-std=gnu99','-mthumb','-mcpu=cortex-m4','-mfloat-abi=hard','-DF_OSC=8000000UL',
  '-I.','-Iinclude','-Iinclude/arm','-Iobj-report079','-Istm32f4xx','-Wall','-Wstrict-prototypes','-Werror','-Wno-strict-aliasing','-ffunction-sections','-fdata-sections','nes_clock_reader088.c','-o','reader.o']
 run([a.arm_bin/'arm-none-eabi-gcc.exe',*args],out,'compile')
 dis=run([a.arm_bin/'arm-none-eabi-objdump.exe','-dr','reader.o'],out,'disassembly')
 attrs=run([a.arm_bin/'arm-none-eabi-readelf.exe','-A','reader.o'],out,'attributes')
 assert 'nes_clock_collect088' in dis and 'Tag_CPU_name: "7E-M"' in attrs
 for called in ['nes_return_delay','nes_return_io_step','nes_diag_ticks','get_snes_reset','fpga_get_done','nes_return_fail']:assert called in dis,called
 put(out/'result.json',json.dumps(dict(candidate='NES-CLOCK-READER-088',source_sha256=sha(out/'nes_clock_reader088.c'),header_sha256=sha(out/'nes_clock_reader088.h'),object_sha256=sha(out/'reader.o'),object_bytes=(out/'reader.o').stat().st_size,headers=headers,compile_args=args,arm_object_only=True,linked_firmware=False,hardware_execution=False,installable=False),indent=2)+'\n')
 print('PASS Cortex-M4 hard-float object; not linked firmware',flush=True)

if __name__=='__main__':main()
