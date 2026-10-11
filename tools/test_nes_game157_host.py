# SPDX-License-Identifier: MIT
"""Actual C auxiliary reader/formatter and STOP flow with bounded synthetic SPI."""
from pathlib import Path
import argparse,ast,json,subprocess
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
 tree=ast.parse((ROOT/'tools/reproduce_nes_game152_context.py').read_text())
 prefix=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='prefix' for t in n.targets))
 prefix=prefix.replace('mode==1?0xdb:0xdc','0xe0').replace('mode==2?0:1','1').replace('mode==3?1:error','error')
 prefix=prefix.replace('case 0x71:','case 0x74:case 0x71:').replace('case 0x72:','case 0x75:case 0x72:')
 prefix=prefix.replace('default:assert(0);',r'''
 case 0x76:assert(stop_count==1);rx[2]=1;rx[7]=1;break;
 case 0x77:
  assert(stop_count==1);rx[2]=3;rx[3]=16;rx[4]=5;rx[5]=1;rx[6]=96;rx[7]=1;
  switch(mode){case 1:rx[1]=0xdf;break;case 2:rx[2]=4;break;case 3:rx[3]=17;break;case 4:rx[4]=16;break;case 5:rx[5]=2;break;case 6:rx[6]=95;break;case 7:rx[7]=2;break;case 8:rx[2]=0;break;case 9:rx[3]=3;break;case 10:return false;}
  break;
 default:
  assert(tx[0]>=0xa0&&tx[0]<=0xbf&&stop_count==1);
  if(mode==11)return false;
  if(mode==12)rx[1]=0xdf;
  for(unsigned j=0;j<6;j++)rx[j+2]=(tx[0]-0xa0)*6+j;
  break;''')
 for n in ['nes_run136.h','nes_run136.inc']:(a.out/n).write_bytes((a.arm/'src'/n).read_bytes())
 fmt=(a.arm/'src/nes_menu_diagnostic.c').read_text().split('static int pad157_format',1)[1].split('static void save_report',1)[0]
 suffix=r'''
int main(void){
 struct nes_rom_spi_io io={0};struct nes_mcu_load_report r={0};char text[4096];
 for(mode=0;mode<=12;mode++){
  nes_run136=(struct nes_run136_report){0};fail_count=leave_count=stop_count=checkpoint_stop=0;
  assert(run136(&io,393216,&r));
  assert(!fail_count&&leave_count==1&&stop_count==1&&checkpoint_stop==1&&nes_run136.context_valid&&nes_run136.ppu_state_valid&&nes_run136.pad_valid);
  assert(nes_run136.history_valid==(mode==0));
  if(!mode){assert(nes_run136.history_count==16&&nes_run136.history_flags==3);for(unsigned i=0;i<16;i++)for(unsigned j=0;j<12;j++)assert(nes_run136.history[i][j]==((i+5)&15)*12+j);}
 }
 nes_run136.pad_valid=1;nes_run136.pad_count=16;nes_run136.history_valid=1;nes_run136.history_count=16;
 for(unsigned mask=0;mask<256;mask++){
  memset(text,'x',900);text[900]=0;
  for(unsigned i=0;i<16;i++){nes_run136.pad_ticks[i]=UINT32_MAX;nes_run136.pad_buttons[i]=mask;memset(nes_run136.history[i],mask,12);}
  int n=pad157_format(text,sizeof(text),900);n=history157_format(text,sizeof(text),n);
  assert(n>900&&n<sizeof(text)&&text[n]==0&&strstr(text,"ppu_history_15="));
  assert(history157_format(text,902,900)==-1);
 }
 puts("PASS157 actual RUN STOP auxiliary13cases,chronological32pages,combinedformatter256masks bounded");return 0;
}
'''
 (a.out/'test.c').write_text(prefix+'\n#include "nes_run136.inc"\nstatic int pad157_format'+fmt+suffix)
 for label,cmd in [('build',[str(a.gcc),'-std=c99','-Wall',str(a.out/'test.c'),'-o',str(a.out/'test.exe')]),('run',[str(a.out/'test.exe')])]:
  r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(a.out/(label+'.log')).write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')
 result=dict(passed=True,recovery_cases=13,formatter_masks=256,source_sha256=sha(a.arm/'src/nes_run136.inc'),format_source_sha256=sha(a.arm/'src/nes_menu_diagnostic.c'),physical=False,scope='Actual RUN/STOP/decoder/formatter; synthetic SPI, not full FatFS or board execution.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS157 MCU STOP/history/format')
if __name__=='__main__':main()
