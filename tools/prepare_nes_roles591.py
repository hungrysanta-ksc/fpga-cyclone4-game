# SPDX-License-Identifier: MIT
"""Replace map record decoding/BEGIN/packet execution in a copy of pinned577.

No product selection. Retained nonmap semantics and D0-D3 are deliberately priced.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha

ROOT=Path(__file__).resolve().parents[1]
FIELDS=''' uint32_t r_epoch,r_serial,r_active,r_request,r_seen;
 uint16_t r_base_count,r_mapcrc,r_crc,r_length,r_token;
 uint8_t r_phase,r_ord,r_row,r_toggle;
 bool r_base,r_hello,r_cold,r_repair,r_pending,r_commit;
'''
CRC='''static void canonical591(struct nes_native165 *s,uint64_t v,unsigned n){
 while(n--){unsigned x=(s->r_crc>>8)^((unsigned)v&255);x^=x>>4;
  s->r_crc=(uint16_t)((s->r_crc<<8)^(x<<12)^(x<<5)^x);s->r_length++;v>>=8;}
}
'''

def prepare(src,out):
 pins=json.loads((ROOT/'analysis/whole580-manifest.json').read_text())
 assert sha(src/'obj-nes-100/sd2snes.elf')==pins['artifacts']['ELF']
 out.mkdir(parents=True,exist_ok=False);names=['nes_native165.c','nes_native165.h','nes_native_runtime165.c'];old={}
 for n in names:old[n]=(src/n).read_text(encoding='utf8')
 s=old['nes_native165.h'];s=once(s,'struct nes_native165 {','struct nes_native165 {\n'+FIELDS)
 (out/'nes_native165.h').write_text(s,encoding='utf8',newline='\n')
 s=old['nes_native165.c'];s=once(s,'#include <string.h>','#include <string.h>\n#include "crc32.h"')
 s=once(s,'s->state=NES_NATIVE165_FAILED;s->error=', 's->r_base=false;s->state=NES_NATIVE165_FAILED;s->error=')
 a=s.index(' if(kind==7&&index==0){');b=s.index(' if(gen!=s->generation)',a);s=s[:a]+s[b:]
 s=once(s,'static bool logical_record(',CRC+'static bool logical_record(')
 s=once(s,' s->records++;return true;',' canonical591(s,v,widths[kind]);s->records++;return true;')
 # Remove both deployed map codec branches, not leave an unused adapter.
 a=s.index(' if(kind==6 &&');b=s.index(' if(kind==7 &&',a);s=s[:a]+s[b:]
 a=s.index(' if(kind==0&&');b=s.index(' if(kind!=7 ||',a);s=s[:a]+s[b:]
 s=once(s,'  s->last_tile+=n;', '  for(unsigned i=0;i<n;i++)canonical591(s,s->raw_pixels[start+i],1);\n  s->last_tile+=n;')
 a=s.index('bool nes_native165_packet(');b=s.index('static void frame(',a)
 include=(ROOT/'tools/nes_rows591.inc').read_text(encoding='utf8')
 split=include.index('static bool request591(')
 s=s[:a]+include[:split]+s[b:]
 a=s.index('bool nes_native165_poll(');s=s[:a]+include[split:]+'\n'+s[a:]
 s=once(s,'!(r[2]&0xfc)','!(r[2]&0xf8)')
 s=once(s,' uint8_t tx[259]={0},rx[259];frame(tx,0xd0,0,0);',
  ' if(!s->r_hello&&!request591(s,fn,ctx,true))return false;\n if(s->r_pending&&!request591(s,fn,ctx,false))return false;\n uint8_t tx[259]={0},rx[259];frame(tx,0xd0,0,0);')
 s=once(s,'if(!n||n>256)','if(!n||n>254)')
 marker=' if(s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)){'
 s=once(s,marker,''' if(s->r_commit){s->r_serial=s->r_active;s->r_base_count=s->counts[0];s->r_base=true;s->r_commit=false;}
 if(s->r_pending&&!request591(s,fn,ctx,false))return false;
'''+marker)
 # The cached status is from before REQUEST, so do not reuse it on that path.
 s=once(s,' if(s->r_pending&&!request591(s,fn,ctx,false))return false;\n if(s->state==',
  ' if(s->r_pending){if(!request591(s,fn,ctx,false))return false;return true;}\n if(s->state==')
 s=once(s,'if(s&&s->state==NES_NATIVE165_COMMITTED)s->state=NES_NATIVE165_IDLE;',
  'if(s&&s->state==NES_NATIVE165_COMMITTED){s->state=NES_NATIVE165_IDLE;s->r_hello=false;s->r_phase=0;s->r_ord=0;}')
 (out/'nes_native165.c').write_text(s,encoding='utf8',newline='\n')
 s=once(old['nes_native_runtime165.c'],'nes_native165_reset(r);','nes_native165_reset(r);r->r_epoch=epoch;')
 (out/'nes_native_runtime165.c').write_text(s,encoding='utf8',newline='\n')
 report=dict(stage=591,baseline_ELF=sha(src/'obj-nes-100/sd2snes.elf'),baseline={n:sha(src/n) for n in names},patched={n:sha(out/n) for n in names},
  tools={n:sha(ROOT/'tools'/n) for n in ('nes_rows591.inc','prepare_nes_roles591.py')},
  removed=['old map RLE/packed4 decode','old BEGIN reset/control','old packet parser'],
  retained=['nonmap RLE/raster/raw semantics','D0-D3 and physical SPI guard','required tags and canonical semantics','final display ACK/EA runtime'],
  added=['8B summary decision','full-row reply and one repair','fresh canonicalCRC16','D4 HELLO/REQUEST and D0 toggle confirmation','source identity and base history'])
 (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
 print(json.dumps(report))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('src','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.src,a.out)
