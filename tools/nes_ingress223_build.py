# SPDX-License-Identifier: MIT
"""Materialize paired board220 and ARM222 with tested223 geometry changes only."""
from pathlib import Path
import argparse,json,shutil
from nes_ingress223 import ROOT,BASE,sha
from nes_board181 import copy_pins


def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--kind',choices=['board','arm'],required=True)
    a=p.parse_args();out=a.out;d=a.candidate
    prep=json.loads((d/'preparation.json').read_bytes())
    for name,h in prep['generated'].items():assert sha(d/name)==h,name
    if a.kind=='board':
        old=BASE/'probes/nes-status220/source02'
        prior=json.loads((old/'preparation220.json').read_bytes())['sources']
        out.mkdir(parents=True,exist_ok=False)
        for name,h in prior.items():
            assert sha(old/name)==h,name
            (out/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/name,out/name)
        for n in ['nes_native_export203.sv','nes_native_spi165.sv']:shutil.copyfile(d/n,out/n)
        changed=[n for n,h in prior.items() if sha(out/n)!=h]
        assert set(changed)=={'nes_native_export203.sv','nes_native_spi165.sv'}
        result=dict(sources={n:sha(out/n) for n in prior},baseline=prior,changed=changed,
                    qsf_sdc_unchanged=True,adopted=False,no_package=True)
    else:
        old=BASE/'probes/nes-startup222/arm02'
        prepold=json.loads((old/'preparation-startup222.json').read_bytes())
        pins=prepold['copied']|prepold['changed']|prepold['added'];copy_pins(old,out,pins)
        shutil.copyfile(d/'nes_native165.c',out/'src/nes_native165.c')
        for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
            f=out/'src'/n;s=f.read_text()
            for x,y in [('NES-GAME-222','NES-GAME-223'),('GAME 222','GAME 223'),('game222.nes','game223.nes'),
                        ('fpga_n222.bi3','fpga_n223.bi3'),('last-222.txt','last-223.txt'),('NES222','NES223'),
                        ('nes-progress-222.txt','nes-progress-223.txt'),('nes-budget-222.txt','nes-budget-223.txt'),
                        ('NES-GAME222-DEV','NES-GAME223-DEV')]:s=s.replace(x,y)
            f.write_text(s,encoding='utf8',newline='\n')
        changed={n:sha(out/n) for n in pins if sha(out/n)!=pins[n]}
        assert set(changed)=={'src/'+n for n in ['nes_native165.c','nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']}
        result=dict(copied=pins,changed=changed,added={},budget_schema=222,new_fpga=True,physical=False)
    result['public_sources']={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__)),
                              'tools/nes_ingress223.py':sha(ROOT/'tools/nes_ingress223.py')}
    result['candidate']=prep
    (out/'preparation-ingress223.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(kind=a.kind,changed=changed)))


if __name__=='__main__':main()
