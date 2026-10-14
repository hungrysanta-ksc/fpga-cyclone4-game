# SPDX-License-Identifier: MIT
"""Execute extracted MCU history reader on strict/malformed schema2 replies."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_game147 import ROOT,sha
from decode_nes_reject180 import record,decode


def main():
    p=argparse.ArgumentParser()
    for n in ['arm','gcc','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
    s=(a.arm/'src/nes_run136.inc').read_text();s=s[s.index('static bool history157('):s.index('static bool identify136(')]
    pre='''#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
#include "nes_run136.h"
struct nes_rom_spi_io {int unused;};
struct nes_run136_report nes_run136;
static unsigned mode,reads;
static bool nes_rom_spi_transfer(const struct nes_rom_spi_io *io,uint8_t *tx,uint8_t *rx){
 (void)io;reads++;memset(rx,0,8);rx[1]=0xe5;
 if(tx[0]==0x77){rx[2]=3;rx[3]=16;rx[4]=5;rx[5]=1;rx[6]=96;rx[7]=2;
  switch(mode){case 1:rx[1]=0xdf;break;case 2:rx[2]=4;break;case 3:rx[3]=17;break;case 4:rx[4]=16;break;
  case 5:rx[5]=2;break;case 6:rx[6]=95;break;case 7:rx[7]=1;break;case 8:rx[2]=0;break;
  case 9:rx[3]=3;break;case 10:return false;case 13:rx[3]=3;rx[4]=3;break;case 14:rx[2]=rx[3]=rx[4]=0;break;}
 }else{assert(tx[0]>=0xa0&&tx[0]<=0xbf);if(mode==11)return false;if(mode==12)rx[1]=0xdf;
  for(unsigned j=0;j<6;j++)rx[j+2]=(tx[0]-0xa0)*6+j;}
 return true;
}
'''
    post='''int main(void){struct nes_rom_spi_io io={0};
 for(mode=0;mode<15;mode++){memset(&nes_run136,0xff,sizeof nes_run136);reads=0;
  bool good=mode==0||mode>=13;assert(history157(&io)==good);assert(nes_run136.history_valid==good);assert(reads<=33);
  if(good){unsigned count=mode==0?16:mode==13?3:0;assert(nes_run136.history_count==count);
   for(unsigned i=0;i<count;i++)for(unsigned j=0;j<12;j++)assert(nes_run136.history[i][j]==((i+(mode==0?5:0))&15)*12+j);}
 }puts("PASS180 C history15 cases malformed/version1 rejected,chronological wrap,partial,empty,bounded33");return 0;}
'''
    f=a.out/'history.c';f.write_text(pre+s+post,encoding='utf8')
    env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
    for cmd,label in [([str(a.gcc),'-std=c11','-Wall','-Wextra','-Werror','-O2','-I',str(a.arm/'src'),str(f),'-o',str(a.out/'history.exe')],'build'),([str(a.out/'history.exe')],'run')]:
        with (a.out/(label+'.log')).open('wb') as out:r=subprocess.run(cmd,stdout=out,stderr=subprocess.STDOUT,env=env,timeout=60)
        assert r.returncode==0,(label,r.returncode,(a.out/(label+'.log')).read_text(errors='replace'))
    # Independent literal vector for every bit-field boundary, not a model of RTL state.
    fields=[(1,2),(255,8),(0x1888242,25),(193,9),(339,9),(24,8),(224,8),(32,6),(128,8),(128,8),(31,5)]
    v=0
    for x,bits in fields:v=(v<<bits)|x
    raw=f'{v:024x}';r=record(raw)
    assert [r[n] for n in ['kind','generation_mod256','errors','first_line','first_dot','first_mask','rows','groups','objects','exceptions','palettes_saturated31']]==[x for x,_ in fields]
    assert (r['rom_fault'],r['raster_errors'],r['compact_errors'],r['fetch_errors'])==(True,0x88,0x82,0x42)
    text='ppu_history_kind=LAST16_REJECT180_V2\nppu_history_valid=1\nppu_history_count=1\nppu_history_flags=1\nppu_history_00='+raw+'\n'
    assert len(decode(text)['events'])==1
    for bad in [text.replace('V2','V1'),text.replace('valid=1','valid=0'),text.replace('_00=','_01=')]:
        try:decode(bad)
        except AssertionError:pass
        else:raise AssertionError('invalid decoder input accepted')
    result=dict(passed=True,reader_cases=15,decoder_vectors=4,source_sha256=sha(a.arm/'src/nes_run136.inc'),generated_sha256=sha(f),
        public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_reject180_host.py','tools/decode_nes_reject180.py']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS180 C history15/decoder4')


if __name__=='__main__':main()
