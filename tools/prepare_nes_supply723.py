"""723: publish fresh warm BG at its completed row; defer intervening row E1.

Initial map offers before fresh BG remain; no-BG frames keep719 ordering.
Cold retains the three-row first-BG callback. Warm uses the existing callback
once per completed row with new BG records. C (--preserve-first-pair) waits
for the existing initial BG pair to be accepted before arming that callback.
No per-frame/phase constants,
new state, map reconstruction, or post-planner map/receipt policy change.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

def run(a):
 assert sha(a.base/'obj-nes-100/firmware.stm') in (
 'fe7a9383c5b34f40d11a020661365cac6be6c0401a5f68c26c2c100a71887def',
 '4d1a9a381ce9b88b8329b3cfa976e57dd296f6559643e3a479db5952cd0b50cb')
 n='nes_native_runtime165.c';s=(a.base/n).read_text()
 s=once(s,'if(!s->resident->finish_bg_row)s->resident->first_bg_rows=3;',
  'if(!s->resident->finish_bg_row)s->resident->first_bg_rows=s->plan.bank_history==2?1:3;')
 s=once(s,'(ok&&!s->plan.early)?finish_bg549:NULL;',
  '(ok&&(s->plan.bank_history==2||!s->plan.early))?finish_bg549:NULL;')
 s=once(s,' return nes_sink527_early(&s->sink,s->video,s->resident,final);',
  ''' /*723 Once fresh warm BG exists, its row-complete plan precedes E1.
  * Earlier map prefixes and no-fresh-BG frames retain their original offers.
  * The existing final callback/map cursor still owns immutable map bytes. */
 if(!final && s->plan.bank_history==2 && s->plan.early)return true;
 return nes_sink527_early(&s->sink,s->video,s->resident,final);''')
 files={n:s}
 if a.preserve_first_pair:
  files[n]=once(s,'(ok&&(s->plan.bank_history==2||!s->plan.early))?finish_bg549:NULL;',
   '(ok&&((s->plan.bank_history==2&&s->plan.sent>1)||!s->plan.early))?finish_bg549:NULL;')
 if a.shared_crc:
  n='nes_plan_service200.c';s=(a.base/n).read_text()
  s=once(s,'static uint8_t crc8(','uint8_t nes_wire723_crc8(').replace('crc8(rx+1,18)','nes_wire723_crc8(rx+1,18)').replace('crc8(b,n+6)','nes_wire723_crc8(b,n+6)').replace('crc8(cmd,5)','nes_wire723_crc8(cmd,5)')
  files[n]=s
  n='nes_sink_window184.c';s=(a.base/n).read_text()
  s=once(s,'static uint8_t crc8(uint8_t c,uint8_t b){c^=b;for(unsigned i=0;i<8;i++)c=(uint8_t)(c&128?(c<<1)^7:c<<1);return c;}\n','')
  s=once(s,'uint8_t c=0;for(unsigned i=1;i<19;i++)c=crc8(c,rx[i]);','uint8_t c=nes_wire723_crc8(rx+1,18);')
  files[n]=s
  n='crc.h';files[n]=once((a.base/n).read_text(),'uint8_t crc7update(',
   '/* Shared NES wire CRC8; init0/poly07, independent call per response. */\nuint8_t nes_wire723_crc8(const uint8_t *data, unsigned length);\n\nuint8_t crc7update(')
 a.out.mkdir(parents=True,exist_ok=False)
 for n,s in files.items():(a.out/n).write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe.json')).write_text(json.dumps(dict(stage=723,shared_crc=a.shared_crc,preserve_first_pair=a.preserve_first_pair,scope=__doc__,base=sha(a.base/'obj-nes-100/firmware.stm'),sources={n:sha(a.out/n) for n in files},new_RAM_B=0,new_RTL=False,new_65816=False),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--shared-crc',action='store_true')
 p.add_argument('--preserve-first-pair',action='store_true')
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
