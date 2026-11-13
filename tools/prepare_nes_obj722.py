"""722A/B control-sharing probes;722C shares existing E1 CRC16 with E9.

Repeated descriptors retain the full12B comparison and FINISH receipt check.
Only new descriptors execute queue drain/submit; both publish flags once.
No wait constants, CRC/identity/STOP checks or wire/RTL/SNES ABI change.
C removes the inlined bit loop; seedFFFF/polynomial1021/positive payload
lengths are unchanged. The table routine already exists in the whole image.
"""
import argparse,json
from pathlib import Path
from nes_raw506 import sha,once
from prepare_nes_obj721 import run as prepare721

def run(a):
 prepare721(argparse.Namespace(base=a.base,out=a.out,variant='D'))
 p=a.out/'nes_plan_service200.c';s=p.read_text()
 s=once(s,'    *flags=result;return true;\n   }\n   if(!complete485(p))return false;',
  '   }else{\n   /*722 Only new ownership drains/submits; success flags share one exit. */\n   if(!complete485(p))return false;')
 s=once(s,'   memcpy(p->bulk,d,12);p->bulk_valid=p->bulk_pending=true;p->bulk_until=p->window->sent;\n  }',
  '   memcpy(p->bulk,d,12);p->bulk_valid=p->bulk_pending=true;p->bulk_until=p->window->sent;\n   }\n  }')
 if a.variant=='B':
  s=once(s,' if(p->finished)return valid(p);\n if(p->count){',' if(!p->finished && p->count){')
  s=once(s,' if(mode==NES_MAP553 && p->bank_history==2 && p->window && p->window->last[1]==2 &&',
   ' if(p->finished || (mode==NES_MAP553 && p->bank_history==2 && p->window && p->window->last[1]==2 &&')
  s=once(s,'(!(p->window->status_flags&8) || p->window->sent!=p->window->retired)){\n  if(!valid(p))return false;\n  return complete485(p);',
   '(!(p->window->status_flags&8) || p->window->sent!=p->window->retired))){\n  /*722 Share validation; finished never drives E9 or consumes another receipt. */\n  if(!valid(p))return false;\n  return p->finished || complete485(p);')
 if a.variant=='C':
  s=once(s,'#include <string.h>','#include <string.h>\n#include "crc.h"')
  s=once(s,'static uint16_t crc16(const uint8_t *b,unsigned n){uint16_t c=65535;while(n--){c^=(uint16_t)*b++<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)(c&32768?(c<<1)^0x1021:c<<1);}return c;}\n','')
  s=once(s,'uint16_t c=crc16(b+4,n);','/*722 Reuse the existing E1 CRC16 routine, seed/poly/covered bytes unchanged. */\n uint16_t c=crc_xmodem_block(0xffff,b+4,n);')
 p.write_text(s,encoding='utf8',newline='\n')
 (a.out.parent/(a.out.name+'-recipe722.json')).write_text(json.dumps(dict(stage=722,variant=a.variant,scope=__doc__,base_firmware=sha(a.base/'obj-nes-100/firmware.stm'),source=sha(p),new_RAM_B=0),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--variant',choices=('A','B','C'),default='C')
 for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
