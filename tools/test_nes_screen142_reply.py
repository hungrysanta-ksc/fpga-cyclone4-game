# SPDX-License-Identifier: MIT
"""Exercise the actual MCU snapshot decoder, preserving unknown SNES milestones."""
from pathlib import Path
import argparse,json,subprocess,shutil
from nes_spi_boot import sha
def main():
 p=argparse.ArgumentParser()
 for n in ['host','out','gcc']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out;assert not o.exists();o.mkdir()
 text=(a.host/'nes_run136.inc').read_text();fn=text[text.index('static bool screen142('):text.index('static bool identify136')]
 shutil.copy2(a.host/'nes_run136.h',o/'nes_run136.h')
 code='''#include <assert.h>
#include <string.h>
#include "nes_run136.h"
struct nes_rom_spi_io {int unused;};struct nes_run136_report nes_run136;
static unsigned calls;static bool success=true;static unsigned char response[8];
static bool nes_rom_spi_transfer(const struct nes_rom_spi_io *io,unsigned char *tx,unsigned char *rx){
 (void)io;calls++;assert(tx[0]==0x73);for(int i=1;i<8;i++)assert(tx[i]==0);
 memcpy(rx,response,8);return success;
}
'''+fn+'''
int main(void){struct nes_rom_spi_io io={0};
 unsigned char good[8]={0,0xd9,6,0,7,1,2,1};
 memcpy(response,good,8);assert(screen142(&io)&&nes_run136.screen_frames==258&&nes_run136.screen_stage==6);
 response[2]=0;response[4]=0;response[5]=response[6]=0;assert(screen142(&io)&&nes_run136.screen_stage==0&&nes_run136.screen_frames==0);
 response[2]=255;response[3]=7;assert(screen142(&io)&&nes_run136.screen_error==7);
 response[2]=93;response[3]=198;assert(screen142(&io)&&nes_run136.screen_stage==93&&nes_run136.screen_error==198);
 struct nes_run136_report saved=nes_run136;
 for(int c=0;c<4;c++){memcpy(response,good,8);success=true;
  if(c==0)response[1]=0xd8;if(c==1)response[7]=2;if(c==2)response[4]=128;if(c==3)success=false;
  assert(!screen142(&io)&&!memcmp(&saved,&nes_run136,sizeof(saved)));
 }
 assert(calls==8);return 0;
}
'''
 (o/'reply.c').write_text(code,encoding='utf-8',newline='\n')
 for label,cmd in [('compile',[str(a.gcc),'-std=c11','-O2','reply.c','-o','reply.exe']),('run',[str(o/'reply.exe')])]:
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run(cmd,cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=60)
  assert r.returncode==0,(label,r.returncode)
 (o/'result.json').write_text(json.dumps(dict(passed=True,cases=8,source_sha256=sha(a.host/'nes_run136.inc')),indent=2)+'\n')
 print('PASS142 actual decoder 8 cases; unknown stage/error retained')
if __name__=='__main__':main()
