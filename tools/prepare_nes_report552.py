# SPDX-License-Identifier: MIT
"""Invalidate the previous run's DWT report before the loader or boot gate can fail."""
import argparse
from pathlib import Path
from nes_raw506 import once, sha


def prepare(arm, out):
    assert sha(arm/'obj-nes-100/firmware.stm')=='e78d1180d515213df092a15188b27e1874d91c7c4bc100afe5930d94697c22c1'
    out.mkdir(parents=True,exist_ok=False)
    name='nes_cost471.c'
    s=once((arm/name).read_text(),'void nes_cost471_begin(void){','''static bool report_valid;
void nes_cost471_reset_report(void){report_valid=false;}
void nes_cost471_begin(void){
 report_valid=true;''')
    anchor=' int z=snprintf(text+n,size-(unsigned)n,"cost_schema=474'
    s=once(s,anchor,''' if(!report_valid){
  int z=snprintf(text+n,size-(unsigned)n,"cost_sampled=0\\n");
  return z<0||(unsigned)z>=size-(unsigned)n?-1:n+z;
 }
'''+anchor)
    (out/name).write_text(s,newline='\n')
    name='nes_cost471.h'
    (out/name).write_text(once((arm/name).read_text(),'void nes_cost471_begin','void nes_cost471_reset_report(void);\nvoid nes_cost471_begin'),newline='\n')
    name='nes_menu_diagnostic.c'
    anchor='memset(&native_runtime165,0,sizeof(native_runtime165));nes_budget210_reset();'
    source='#include "nes_cost471.h"\n'+(arm/name).read_text()
    (out/name).write_text(once(source,anchor,anchor+'nes_cost471_reset_report();'),newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('arm','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    prepare(a.arm,a.out)
