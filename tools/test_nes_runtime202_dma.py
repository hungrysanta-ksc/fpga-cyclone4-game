# SPDX-License-Identifier: MIT
"""Extend the existing deployed-DMA alias test from248 to259 bytes for E1.
This is the actual DMA C with an asynchronous register model, not STM32 timing.
"""
from pathlib import Path
import argparse,json,os,subprocess
from nes_runtime202 import ROOT,BASE,sha
from nes_clip178 import replace
import test_nes_batch198_dma as prior

def main():
 import inspect,sys
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 source=inspect.getsource(prior.main).replace('248','259').replace('249','260').replace('744','777').replace('DMA198','DMA202')
 # The original fixture has261-byte guard buffers, sufficient for259+2.
 source=replace(source,"script_sha256=sha(Path(__file__))","script_sha256=sha(Path(__file__)),base_script_sha256=sha(ROOT/'tools/test_nes_batch198_dma.py')")
 ns=dict(prior.__dict__);ns['__file__']=__file__;exec(compile(source,'runtime202-dma','exec'),ns)
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
 os.environ['PATH']=str(gcc.parent)+os.pathsep+os.environ.get('PATH','')
 sys.argv=['dma202','--out',str(a.out.resolve()),'--gcc',str(gcc)];ns['main']()
if __name__=='__main__':main()
