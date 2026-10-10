# SPDX-License-Identifier: MIT
"""MCU143 naming and bounded phase polling; exact142 FPGA logic/IDs retained."""
from pathlib import Path
import argparse,json,re,shutil
from nes_spi_boot import ROOT,sha
from nes_menu098 import once
def put(p,s):p.write_text(s,encoding='utf8',newline='\n')
def prepare(base,out,kind):
 assert kind in ['arm','host'] and not out.exists()
 e=base/'nes-screen142/evidence';m=json.loads((ROOT/'analysis/screen142-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 for n,h in pins.items():
  if not n.startswith(kind+'/'):continue
  rel=n[len(kind)+1:];p=Path(rel)
  if kind=='arm' and (any(x.startswith(('obj-','.dep-')) for x in p.parts) or p.suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or p.name in ['.ARG_VERSION','executed-builder.ps1']):continue
  if kind=='host' and p.suffix not in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:continue
  assert sha(e/n)==h,n
  d=out/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,d);copied[rel]=h
 root=out/'src' if kind=='arm' else out
 names=['nes_menu_diagnostic.c','nes_checkpoint112.c','nes_h1_stm32.c','nes_run136.inc','nes_cf86_session094.c','nes_cf86_session094.h','nes_rom_verify.c']
 if kind=='host':names+=['card.c','config097_card.inc','host109.c','platform.c']
 for n in names:
  p=root/n;parts=re.split(r'(\b0x[0-9a-fA-F]+)',p.read_text(encoding='utf8'));put(p,''.join(x if i%2 else x.replace('142','143') for i,x in enumerate(parts)))
 p=root/'nes_run136.h';put(p,once(p.read_text(),'uint8_t screen_valid,screen_stage,screen_error,screen_flags;','uint8_t screen_valid,screen_stage,screen_error,screen_flags,screen_phase_mask;'))
 p=root/'nes_run136.inc';s=p.read_text();s=once(s,'nes_run136.screen_valid=1;', '''if(rx[2]>=0x31&&rx[2]<=0x34)nes_run136.screen_phase_mask|=1u<<(rx[2]-0x31);
 if(rx[2]==6||rx[2]==0x63)nes_run136.screen_phase_mask|=8u;
 nes_run136.screen_valid=1;''')
 s=once(s,'i<200','i<600')
 s=once(s,'  }\n }\n if(!nes_run136.first_error','  }\n  if(!screen143(io))return nes_cf86_fail094();\n }\n if(!nes_run136.first_error')
 put(p,s)
 p=root/'nes_menu_diagnostic.c';s=p.read_text();s=once(s,'screen_frames=%u\\n",','screen_frames=%u\\nscreen_phase_mask=%u\\n",');s=once(s,'nes_run136.screen_flags,nes_run136.screen_frames);','nes_run136.screen_flags,nes_run136.screen_frames,nes_run136.screen_phase_mask);');put(p,s)
 if kind=='arm':put(root/'VERSION','RELEASE_VERSION = "NES-SCREEN143"\n')
 else:
  p=root/'host109.c';s=once(p.read_text(),'?4:203','?4:603')
  s=once(s,'nes_run136.last==20000&&nes_run136.stopped==20000','nes_run136.last==60000&&nes_run136.stopped==60000')
  s=once(s,'display_end142-display_begin142>=10000000000ull'.replace('142','143'),'display_end143-display_begin143>=30000000000ull')
  put(p,s)
  p=root/'platform.c';s=p.read_text();s=once(s,'tx[0]>=0x70&&tx[0]<=0x72','tx[0]>=0x70&&tx[0]<=0x73');s=once(s,'assert(reset_held&&stop_count);reply[1]=0xd9;reply[2]=6;', '''assert((reset_held&&stop_count)||(!reset_held&&start_count136));reply[1]=0xd9;
    reply[2]=stop_count?0x63:observe_count136<62?0x31:observe_count136<122?0x32:observe_count136<182?0x33:0x63;''');put(p,s)
 put(out/'preparation143.json',json.dumps(dict(copied=copied,changed={n:sha(out/n) for n,h in copied.items() if sha(out/n)!=h}),indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--kind',choices=['arm','host'],required=True);a=p.parse_args();prepare(a.baseline,a.out,a.kind)
