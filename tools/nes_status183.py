# SPDX-License-Identifier: MIT
"""Reuse CRC-checked positive next-block status, never a negative observation."""
from pathlib import Path
import argparse,json
from nes_board181 import copy_pins
from nes_game147 import ROOT,sha
from nes_clip178 import replace
def receiver(s):
 s=replace(s,' if(!fn(ctx,tx,rx,8)||!status(rx))return fail(s,21);', ''' /* D2 retirement was confirmed by the previous D0. A sealed block cannot
  * change until our D2 or COMMON reset. Reuse only its positive metadata;
  * READ data CRC and POP+retirement checks still run for every block. */
 if(s->ready183){memcpy(rx,s->status183,8);s->ready183=false;}
 else if(!fn(ctx,tx,rx,8))return fail(s,21);
 if(!status(rx))return fail(s,21);''')
 s=replace(s,' (uint16_t)((rx[3]<<8)|rx[4])!=(uint16_t)(tok+1))return fail(s,27);\n return true;', ''' (uint16_t)((rx[3]<<8)|rx[4])!=(uint16_t)(tok+1))return fail(s,27);
 if(s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)){
  memcpy(s->status183,rx,8);s->ready183=true;
 }
 return true;''')
 s=replace(s,' uint8_t tx[8],rx[8];frame(tx,0xd0,0,0);',' s->ready183=false;\n uint8_t tx[8],rx[8];frame(tx,0xd0,0,0);')
 return s
def header(s):return replace(s,' bool token_valid;uint16_t next_token;',' bool token_valid;uint16_t next_token;\n uint8_t status183[8];bool ready183;')
def prepare(prior,out):
 assert sha(prior/'src/obj-nes-100/firmware.stm')=='5c6e70ea05a1e1969b6eb7715109abc1073d4da27cda619c04b6feaa6eb6b59d'
 prep=json.loads((prior/'preparation-dma182.json').read_bytes());pins=prep['copied']|prep['changed']|prep['added'];copy_pins(prior,out,pins);changed={}
 def write(n,s):(out/n).write_text(s,encoding='utf-8',newline='\n');changed[n]=sha(out/n)
 write('src/nes_native165.c',receiver((prior/'src/nes_native165.c').read_text()))
 write('src/nes_native165.h',header((prior/'src/nes_native165.h').read_text()))
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  s=(out/n).read_text()
  for a,b in [('NES-GAME-182','NES-GAME-183'),('GAME 182','GAME 183'),('game182.nes','game183.nes'),('fpga_n182.bi3','fpga_n183.bi3'),('last-182.txt','last-183.txt'),('NES182 seq=','NES183 seq='),('nes-progress-182.txt','nes-progress-183.txt'),('NES-GAME182-DEV','NES-GAME183-DEV')]:s=s.replace(a,b)
  write(n,s)
 r=dict(copied=pins,changed=changed,added={},baseline_firmware=sha(prior/'src/obj-nes-100/firmware.stm'),public_sources={'tools/nes_status183.py':sha(ROOT/'tools/nes_status183.py')},fpga_unchanged=True)
 for n in ['preparation-status183.json','preparation-runlease165.json']:(out/n).write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
 return r
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prior',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.prior,a.out)['changed']))
