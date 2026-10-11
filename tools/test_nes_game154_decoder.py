# SPDX-License-Identifier: MIT
"""Test the actual supplemental-state C decoder with malformed SPI replies."""
from pathlib import Path
import argparse,ast,json,subprocess
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists();o.mkdir(parents=True)
 tree=ast.parse((ROOT/'tools/reproduce_nes_game152_context.py').read_text())
 prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
 prefix=prefix.replace('0xdc','0xdd').replace('case 0x71:','case 0x74:').replace('case 0x72:','case 0x75:')
 prefix=prefix.replace('(void)io;memset(rx,0,8);','(void)io;if((mode==8&&tx[0]==0x74)||(mode==9&&tx[0]==0x75))return false;memset(rx,0,8);')
 prefix=prefix.replace('case 0x75:rx[2]=1;', 'case 0x75:rx[1]=mode==4?0xdc:0xdd;rx[2]=mode==5?0:1;')
 prefix=prefix.replace('rx[7]=1;break;\n case 0x73:', 'rx[7]=mode==6?2:1;if(mode==7)rx[6]=0;break;\n case 0x73:')
 suffix=r'''
int main(void){
 struct nes_rom_spi_io io={0};unsigned checks=0;
 for(unsigned bit=0;bit<64;bit++)for(unsigned err=1;err<=15;err++){
  context=UINT64_C(1)<<bit;error=err;nes_run136.rom_error=err;mode=0;
  assert(ppu154(&io)&&nes_run136.ppu_state_valid);
  assert((((uint64_t)nes_run136.ppu_state_hi<<32)|nes_run136.ppu_state_lo)==context);checks++;
 }
 error=2;nes_run136.rom_error=2;
 for(mode=1;mode<=9;mode++){
  nes_run136.ppu_state_valid=0;nes_run136.ppu_state_hi=0;nes_run136.ppu_state_lo=0;
  assert(!ppu154(&io)&&!nes_run136.ppu_state_valid&&!nes_run136.ppu_state_hi&&!nes_run136.ppu_state_lo);checks++;
 }
 mode=0;error=0;nes_run136.rom_error=0;assert(!ppu154(&io));checks++;
 printf("PASS154 decoder checks=%u valid=960 invalid=10\n",checks);return 0;
}
'''
 for n in ['nes_run136.h','nes_run136.inc']:(o/n).write_bytes((a.arm/'src'/n).read_bytes())
 source=o/'test.c';source.write_text(prefix+'\n#include "nes_run136.inc"\n'+suffix)
 for stage,cmd in [('build',[str(a.gcc),'-std=c99','-Wall',str(source),'-o',str(o/'test.exe')]),('run',[str(o/'test.exe')])]:
  r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(o/(stage+'.log')).write_bytes(r.stdout)
  assert r.returncode==0,r.stdout.decode(errors='replace')
 result=dict(passed=True,valid=960,invalid=10,source_sha256=sha(o/'nes_run136.inc'),physical=False)
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
