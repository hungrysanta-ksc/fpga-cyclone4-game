# SPDX-License-Identifier: MIT
"""Require existing bridge admission before releasing SNES; allocate frame work after READY."""
from pathlib import Path
import argparse,json,shutil
from nes_runtime213 import ROOT,BASE,sha,once
from nes_board181 import copy_pins

def board(s):
 a=s.index('/* This MUST remain a distinct call:')
 old=s[a:]
 frames=old[old.index(' (void)nes_runtime165_begin'):]
 # The two phases cannot share a stack frame. Preserve the frame loop byte for byte.
 return s[:a]+'''#include "nes_startup222.inc"
/* Large RUN storage exists only after the low-stack startup gates pass. */
static void native_frames222(const struct nes_rom_spi_io *io,uint32_t content_epoch) __attribute__((noinline));
static void native_frames222(const struct nes_rom_spi_io *io,uint32_t content_epoch){
 (void)io;
 struct {struct nes_native165 receiver;struct nes_native_video165 video;struct nes_resident211 resident;} work;
'''+frames+'''
static bool native_session165(const struct nes_rom_spi_io *io,uint32_t content_epoch) __attribute__((noinline));
static bool native_session165(const struct nes_rom_spi_io *io,uint32_t content_epoch){
 native_io165=io;native_first165=true;native_observed165=getticks();
 if(!native_preflight222(io)){
  native_runtime165.result=NES_RUNTIME165_SERVICE;
  if(!nes_run136.first_error)nes_run136.first_error=7;
  native_io165=NULL;return false;
 }
 if(!nes_display_enter146()){native_io165=NULL;return false;}
 if(!native_postflight222(io)){
  native_runtime165.result=NES_RUNTIME165_SERVICE;
  if(!nes_run136.first_error)nes_run136.first_error=8;
  native_io165=NULL;return true;
 }
 if(native_boot172(io))native_frames222(io,content_epoch);
 native_io165=NULL;return true;
}
'''

def run(s):
 s=once(s,' if(!nes_display_enter146())return false;\n native_session165(io,content_epoch);',
          ' bool released222=native_session165(io,content_epoch);')
 return once(s,' if(!nes_display_leave146())return false;',
             ' if(released222&&!nes_display_leave146())return false;')

def budget(s):
 s=once(s,'struct nes_boot214 nes_boot214;', '#include "nes_startup222.h"\nstruct nes_startup222 nes_startup222;\nstruct nes_boot214 nes_boot214;')
 s=s.replace('budget_schema=221','budget_schema=222')
 extra=r''' int startup=snprintf(text+n,size-(unsigned)n,
  "startup_schema=222\nstartup_reason=%lu\nstartup_post_reason=%lu\nstartup_signals_hex=%08lx\nstartup_ticks=%lu\nstartup_reply_hex=",
  (unsigned long)nes_startup222.reason,(unsigned long)nes_startup222.post_reason,(unsigned long)nes_startup222.signals,(unsigned long)nes_startup222.ticks);
 if(startup<0||(unsigned)startup>=size-(unsigned)n)return -1;
 n+=startup;
 for(unsigned i=0;i<20;i++){
  int hex=snprintf(text+n,size-(unsigned)n,"%02x",(unsigned)nes_startup222.reply[i]);
  if(hex<0||(unsigned)hex>=size-(unsigned)n)return -1;
  n+=hex;
 }
 if(size-(unsigned)n<2)return -1;
 text[n++]='\n';text[n]=0;
 int post=snprintf(text+n,size-(unsigned)n,"startup_post_reply_hex=");
 if(post<0||(unsigned)post>=size-(unsigned)n)return -1;
 n+=post;
 for(unsigned i=0;i<20;i++){
  int hex=snprintf(text+n,size-(unsigned)n,"%02x",(unsigned)nes_startup222.post_reply[i]);
  if(hex<0||(unsigned)hex>=size-(unsigned)n)return -1;
  n+=hex;
 }
 if(size-(unsigned)n<2)return -1;
 text[n++]='\n';text[n]=0;
'''
 return once(s,' int boot=snprintf(',extra+' int boot=snprintf(')

def prepare(out):
 prior=BASE/'probes/nes-index221/arm01';p=json.loads((prior/'preparation-index221.json').read_bytes())
 pins=p['copied']|p['changed']|p['added'];copy_pins(prior,out,pins);src=out/'src'
 for ext in ['h','inc']:shutil.copyfile(ROOT/f'src/nes/firmware/nes_startup222.{ext}',src/f'nes_startup222.{ext}')
 for name,change in [('nes_runtime_board165.inc',board),('nes_run136.inc',run),('nes_budget210.c',budget)]:
  f=src/name;f.write_text(change(f.read_text()),encoding='utf8',newline='\n')
 for name in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
  f=src/name;s=f.read_text()
  for x,y in [('NES-GAME-221','NES-GAME-222'),('GAME 221','GAME 222'),('game221.nes','game222.nes'),('fpga_n221.bi3','fpga_n222.bi3'),('last-221.txt','last-222.txt'),('NES221','NES222'),('nes-progress-221.txt','nes-progress-222.txt'),('nes-budget-221.txt','nes-budget-222.txt'),('NES-GAME221-DEV','NES-GAME222-DEV')]:s=s.replace(x,y)
  f.write_text(s,encoding='utf8',newline='\n')
 changed={n:sha(out/n) for n in pins if sha(out/n)!=pins[n]}
 assert set(changed)=={'src/'+n for n in ['nes_runtime_board165.inc','nes_run136.inc','nes_budget210.c','nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']}
 added={f'src/nes_startup222.{ext}':sha(src/f'nes_startup222.{ext}') for ext in ['h','inc']}
 public=['tools/nes_startup222.py','src/nes/firmware/nes_startup222.h','src/nes/firmware/nes_startup222.inc']
 r=dict(copied=pins,changed=changed,added=added,public_sources={n:sha(ROOT/n) for n in public},new_fpga=False,physical=False,
        root_cause_reproduced=False,extra_static_bytes=56,extra_startup_spi_bytes_max=40,no_restart_or_packet_retry=True)
 (out/'preparation-startup222.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps(changed))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
