# SPDX-License-Identifier: MIT
"""213 unchanged renderer/FPGA; retain why bounded pre-BEGIN startup exits."""
from pathlib import Path
import argparse,json,shutil
from nes_runtime213 import ROOT,BASE,sha,once
from nes_board181 import copy_pins

def prepare(out):
    prior=BASE/'probes/nes-runtime213/arm01'
    p=json.loads((prior/'preparation-runtime213.json').read_bytes())
    pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins)
    src=out/'src'
    for name in ['nes_boot214.h','nes_boot214.inc']:
        shutil.copyfile(ROOT/'src/nes/firmware'/name,src/name)
    f=src/'nes_runtime_board165.inc';f.write_text(once(f.read_text(),'#include "nes_boot172.inc"','#include "nes_boot214.inc"'),encoding='utf8')
    f=src/'nes_budget210.c';s=f.read_text()
    s=once(s,'struct nes_budget210 nes_budget210;','#include "nes_boot214.h"\nstruct nes_boot214 nes_boot214;\nstruct nes_budget210 nes_budget210;')
    s=once(s,' for(unsigned i=0;i<12;i++){',r''' int boot=snprintf(text+n,size-(unsigned)n,
  "boot_schema=214\nboot_reason=%lu\nboot_polls=%lu\nboot_ticks=%lu\nboot_first_hex=%08lx\nboot_last_hex=%08lx\nboot_signals_hex=%08lx\n",
  (unsigned long)nes_boot214.reason,(unsigned long)nes_boot214.polls,(unsigned long)nes_boot214.ticks,
  (unsigned long)nes_boot214.first,(unsigned long)nes_boot214.last,(unsigned long)nes_boot214.signals);
 if(boot<0||(unsigned)boot>=size-(unsigned)n)return -1;
 n+=boot;
 for(unsigned i=0;i<12;i++){''')
    s=s.replace('budget_schema=213','budget_schema=214');f.write_text(s,encoding='utf8')
    for name in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
        f=src/name;s=f.read_text()
        for x,y in [('NES-GAME-213','NES-GAME-214'),('GAME 213','GAME 214'),('game213.nes','game214.nes'),('fpga_n213.bi3','fpga_n214.bi3'),('last-213.txt','last-214.txt'),('NES213','NES214'),('nes-progress-213.txt','nes-progress-214.txt'),('nes-budget-213.txt','nes-budget-214.txt'),('NES-GAME213-DEV','NES-GAME214-DEV')]:s=s.replace(x,y)
        f.write_text(s,encoding='utf8')
    changed={n:sha(out/n) for n,h in pins.items() if sha(out/n)!=h}
    added={'src/'+n:sha(src/n) for n in ['nes_boot214.h','nes_boot214.inc']}
    sources=['tools/nes_startup214.py','src/nes/firmware/nes_boot214.h','src/nes/firmware/nes_boot214.inc']
    result=dict(copied=pins,changed=changed,added=added,public_sources={n:sha(ROOT/n) for n in sources},new_fpga=False,root_cause_fixed=False)
    (out/'preparation-startup214.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.out)['changed']))
