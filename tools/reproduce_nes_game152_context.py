# SPDX-License-Identifier: MIT
"""Reproduce released152 tagged-context rejection without changing firmware."""
from pathlib import Path
import argparse,hashlib,json,subprocess
p=argparse.ArgumentParser()
for n in ['baseline','out','gcc']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();E=a.baseline/'nes-game152/evidence';O=a.out
assert str(O).isascii()
assert hashlib.sha256((E/'arm/src/nes_run136.inc').read_bytes()).hexdigest()=='796d8c70c0735602f3a371d9aca4945d6fb8b2f08e3b1dd655d9853f66747ec8'

O.mkdir(exist_ok=False)
src=(E/'arm/src/nes_run136.inc').read_text()
assert src.count('(hi[3]&0x80u) || ')==1
header=(E/'arm/src/nes_run136.h').read_text()
(O/'nes_run136.h').write_text(header)
prefix=r'''
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
struct nes_rom_spi_io {int unused;};
struct nes_rom_spi_status {uint8_t flags;uint32_t count;};
struct nes_menu_probe_report {bool board_seen;uint8_t board_id;};
struct nes_mcu_load_report {bool stop_ok;};
static int fail_count,leave_count,stop_count,checkpoint_stop,mode;
static uint8_t error=2;
static uint64_t context=UINT64_C(0xe200c2f430217a19);
#define NES_ROM_STOP 0xee
static bool nes_rom_spi_transfer(const struct nes_rom_spi_io *io,const uint8_t *tx,uint8_t *rx){
 (void)io;memset(rx,0,8);rx[1]=mode==1?0xdb:0xdc;
 switch(tx[0]){
 case 0x70:rx[2]=stop_count?3:2;rx[3]=error;rx[7]=100;break;
 case 0x71:rx[2]=mode==2?0:1;for(int i=3;i<8;i++)rx[i]=context>>(8*(10-i));break;
 case 0x72:rx[2]=1;rx[3]=context>>16;rx[4]=context>>8;rx[5]=context;rx[6]=mode==3?1:error;rx[7]=1;break;
 case 0x73:rx[2]=6;rx[4]=4;rx[7]=1;break;
 case 0xee:stop_count++;break;
 default:assert(0);
 }return true;
}
static bool sd_query(const struct nes_rom_spi_io *i,struct nes_rom_spi_status *s){(void)i;s->flags=2;s->count=393216;return true;}
static bool nes_checkpoint112(const char *s,uint32_t a,uint32_t b){(void)a;(void)b;if(!strcmp(s,"DISPLAY_STOPPED"))checkpoint_stop++;return true;}
static bool nes_rom_verified_start(const struct nes_rom_spi_io *i,uint32_t t){(void)i;(void)t;return true;}
static bool nes_cf86_fail094(void){fail_count++;return false;}
static bool nes_cf86_check094(void){return true;}
static bool nes_display_enter146(void){return true;}
static bool nes_display_leave146(void){leave_count++;return true;}
static void wait_us(unsigned a,unsigned b){(void)a;(void)b;}
static void nes_rom_spi_frame(uint8_t *t,unsigned c,uint32_t n,unsigned a){(void)n;(void)a;memset(t,0,8);t[0]=c;}
'''
suffix=r'''
int main(void){
 struct nes_rom_spi_io io={0};struct nes_mcu_load_report r={0};
 bool ok=run136(&io,393216,&r);
 printf("tagged PPU: returned=%d fail=%d leave=%d stop=%d checkpoint=%d context_valid=%d hi=%08x lo=%08x\n",ok,fail_count,leave_count,stop_count,checkpoint_stop,nes_run136.context_valid,nes_run136.context_hi,nes_run136.context_lo);
 if(FIXED){assert(ok&&fail_count==0&&leave_count==1&&stop_count==1&&checkpoint_stop==1&&nes_run136.context_valid);assert(nes_run136.context_hi==0xe200c2f4&&nes_run136.context_lo==0x30217a19);}
 else {assert(!ok&&fail_count==1&&!leave_count&&!stop_count&&!checkpoint_stop&&!nes_run136.context_valid);}
 context &= UINT64_C(0x7fffffffffffffff);nes_run136.rom_error=2;
 assert(context146(&io));
 context |= UINT64_C(0x8000000000000000);
 for(mode=1;mode<=3;mode++)assert(!context146(&io));
 puts("PASS retained untagged format and three invalid replies rejected");
 return 0;
}
'''
gcc=str(a.gcc)
results={}
for name,fixed in [('released152',False),('one_condition_control',True)]:
 s=src.replace('(hi[3]&0x80u) || ','') if fixed else src
 p=O/(name+'.c');p.write_text(prefix+s+'\n#define FIXED '+str(int(fixed))+'\n'+suffix)
 exe=O/(name+'.exe')
 build=subprocess.run([gcc,'-std=c99','-Wall',str(p),'-o',str(exe)],capture_output=True)
 (O/(name+'-build.log')).write_bytes(build.stdout+build.stderr);assert build.returncode==0
 run=subprocess.run([str(exe)],capture_output=True);(O/(name+'.log')).write_bytes(run.stdout+run.stderr);assert run.returncode==0,(name,run.stdout,run.stderr)
 results[name]=run.stdout.decode()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result=dict(passed=True,released_source_sha256=sha(E/'arm/src/nes_run136.inc'),results=results,
 scope='Exact released run136/context146 C with stubbed transport/guard and synthetic tagged PPU fault. One-condition control is local proof only, not a firmware fix or confirmation of actual152 fault cause.')
(O/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
