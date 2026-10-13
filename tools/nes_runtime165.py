# SPDX-License-Identifier: MIT
"""Build-source integration only. Never modifies installed164 or save SRAM."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha
from nes_native_spi165 import bulk_engine
from build_nes_game164 import palette
from test_nes_native_runtime165 import MODULES

def prepare(evidence,out):
 pins=json.loads((evidence/'manifest.json').read_bytes())['files']
 baseline=evidence/'arm';prep=json.loads((baseline/'preparation164.json').read_bytes())
 out.mkdir(parents=True,exist_ok=False);copied={};changed={};added={};diffs=[]
 for n in sorted(set(prep['copied'])|set(prep['added'])):
  src=baseline/n;assert sha(src)==pins['arm/'+n],n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);copied[n]=sha(src)
 def add(n,data):
  p=out/n;assert not p.exists();p.write_text(data,encoding='utf8',newline='\n');added[n]=sha(p)
 def edit(n,fn):
  p=out/n;old=p.read_text(encoding='utf8');new=fn(old);assert old!=new,n
  p.write_text(new,encoding='utf8',newline='\n');changed[n]=sha(p)
  diffs.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='164/'+n,tofile='165/'+n))
 def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
 for n in MODULES:
  for ext in ['c','h']:add('src/'+n+'.'+ext,(ROOT/'src/nes/firmware'/(n+'.'+ext)).read_text())
 add('src/nes_runtime_board165.inc',(ROOT/'src/nes/firmware/nes_runtime_board165.inc').read_text())
 add('src/nes_native165_bulk.inc',bulk_engine().replace('nes149_','nes165_').replace('NES149_','NES165_'))
 pal=palette();add('src/nes_palette165.inc','static const uint16_t native_palette165[64]={'+','.join(str(int.from_bytes(pal[i:i+2],'little')) for i in range(0,128,2))+'};\n')
 edit('src/Makefile',lambda s:once(s,'SRC  = main.c ff.c ccsbcs.c','SRC  = main.c ff.c ccsbcs.c '+' '.join(n+'.c' for n in MODULES)).replace('CFLAGS =','CFLAGS = -fstack-usage'))
 edit('src/nes_h1_stm32.c',lambda s:once(s,'#include "nes_game149_spi.inc"','#include "nes_game149_spi.inc"\n#include "nes_native165_bulk.inc"').replace('rx[1]!=0x6b','rx[1]!=0x74'))
 edit('src/nes_rom_verify.c',lambda s:s.replace('0x6b','0x74'))
 def run(s):
  s=once(s,'rx[1]!=0xe5||rx[7]!=1||(rx[4]&0xf8u)','rx[1]!=0xe6||rx[7]!=2||(rx[4]&0xf8u)')
  s=once(s,'candidate->board_id=0x6b','candidate->board_id=0x74')
  at=s.index('static bool run136(');s=s[:at]+'#include "nes_runtime_board165.inc"\n'+s[at:]
  start=s.index(' for(unsigned i=0;i<1200;i++)');end=s.index(' if(!nes_run136.first_error',start)
  s=s[:start]+' native_session165(io);\n if(!nes_cf86_check094())return false;\n'+s[end:]
  return s
 edit('src/nes_run136.inc',run)
 for n in ['src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION']:
  edit(n,lambda s:s.replace('164','165'))
 def diagnostic(s):
  s=once(s,'#include "nes_run136.h"','#include "nes_run136.h"\n#include "nes_native_runtime165.h"\nextern struct nes_native_runtime165 native_runtime165;')
  s=once(s,'board_expected_hex=6B','board_expected_hex=74')
  s=once(s,' n=history165_format(text,sizeof(text),n);',' n=history165_format(text,sizeof(text),n);\n if(n>0&&(size_t)n<sizeof(text)){\n  int used=snprintf(text+n,sizeof(text)-(size_t)n,"native_result=%u\\nnative_frames=%lu\\nnative_generation=%u\\nnative_transactions=%lu\\nnative_wire_bytes=%lu\\nnative_receiver_error=%u\\nnative_sink_error=%u\\nnative_video_error=%u\\n",native_runtime165.result,(unsigned long)native_runtime165.frames,native_runtime165.generation,(unsigned long)native_runtime165.transactions,(unsigned long)native_runtime165.wire_bytes,native_runtime165.receiver?native_runtime165.receiver->error:0,native_runtime165.sink.error,native_runtime165.video?native_runtime165.video->error:0);\n  n=used<0||(size_t)used>=sizeof(text)-(size_t)n?-1:n+used;\n }')
  s=once(s,' memset(&report,0,sizeof(report));',' memset(&native_runtime165,0,sizeof(native_runtime165));\n memset(&report,0,sizeof(report));')
  s=once(s,' char text[4096];FIL log;UINT written=0;',' char *text=nes_runtime165_log_buffer();FIL log;UINT written=0;')
  s=s.replace('sizeof(text)','4096')
  s=s.replace('native_runtime165.receiver?native_runtime165.receiver->error:0','native_runtime165.receiver_error').replace('native_runtime165.video?native_runtime165.video->error:0','native_runtime165.video_error')
  s=once(s,'extern struct nes_native_runtime165 native_runtime165;','extern struct nes_native_runtime165 native_runtime165;\nextern char *nes_runtime165_log_buffer(void);')
  return s
 edit('src/nes_menu_diagnostic.c',diagnostic)
 (out/'changes-runtime165.diff').write_text(''.join(diffs),encoding='utf8')
 result=dict(copied=copied,changed=changed,added=added,baseline_manifest_sha256=sha(evidence/'manifest.json'),installable=False,scope='Full ARM compile source; no SD package or hardware approval.')
 (out/'preparation-runtime165.json').write_text(json.dumps(result,indent=2)+'\n')
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
 a=p.parse_args();r=prepare(a.evidence,a.out);print(json.dumps(dict(copied=len(r['copied']),changed=len(r['changed']),added=len(r['added']))))
