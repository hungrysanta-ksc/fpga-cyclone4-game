# SPDX-License-Identifier: MIT
"""Bounded R2 transport prototype against577. No deployable FPGA/profile.

Replaces physical D0/D2/E0/E8, preserves record/body checks and final ownership.
Generated full firmware is a cost/test artifact, never an installation package.
"""
import argparse,json
from pathlib import Path
from nes_abi582 import sha
from nes_raw506 import once

INGRESS = r'''
static unsigned le584(const uint8_t *p){return p[0]|(unsigned)p[1]<<8;}
static void put584(uint8_t *p,uint32_t v,unsigned n){while(n--){*p++=(uint8_t)v;v>>=8;}}
static bool head584(struct nes_native165 *s,struct nes_ingress584 *t,
 nes_native165_transfer_fn fn,void *ctx,uint8_t command){
 uint8_t b[36]={0};b[0]=command;b[1]=t->pending;
 put584(b+2,t->epoch,4);put584(b+6,t->serial,4);
 put584(b+10,t->acked,2);put584(b+12,t->next,2);put584(b+14,crc16(b,14),2);
 if(!fn(ctx,b,b,sizeof b))return fail(s,21);
 uint8_t *h=b+18;unsigned flags=h[1],n=le584(h+14);
 if(h[0]!=0x84||(flags&~7)||crc16(h,16)!=le584(h+16)||
    memcmp(h+4,&t->epoch,4)||memcmp(h+8,&t->serial,4)||le584(h+12)!=t->next||
    n>256||!!(flags&1)!=!!n)return fail(s,22);
 if(command==0xde && (!(flags&4)||le584(h+2)!=s->generation))return fail(s,26);
 if(command==0xdf && (flags||n))return fail(s,27);
 t->pending=false;t->length=(uint16_t)n;t->generation=(uint16_t)le584(h+2);
 return true;
}
bool nes_native165_poll(struct nes_native165 *s,nes_native165_transfer_fn fn,void *ctx,struct nes_ingress584 *t){
 if(!s||!fn||!t||s->state==NES_NATIVE165_FAILED||s->state==NES_NATIVE165_COMMITTED)return false;
 if(!t->length&&!head584(s,t,fn,ctx,0xdc))return false;
 unsigned n=t->length;if(!n)return true;
 uint8_t b[261]={0};b[0]=0xdd;put584(b+1,t->next,2);
 if(!fn(ctx,b,b,n+5)){nes_cost471_transfer_stops++;return fail(s,23);}
 if(le584(b+1)!=t->next||crc16(b+1,n+2)!=le584(b+n+3)){
  nes_cost471_crc_errors++;return fail(s,23);
 }
 if(!nes_native165_packet(s,t->next,b+3,n)||s->generation!=t->generation)return fail(s,23);
 t->acked=t->next++;t->pending=true;t->length=0;
 /* Release the final packet now, not after display/EA. Capture may proceed;
  * the next input COMMIT remains owned by the runtime's old finalACK/EA. */
 return s->state!=NES_NATIVE165_COMMITTED||head584(s,t,fn,ctx,0xdf);
}
bool nes_native165_prepare(struct nes_native165 *s,bool accept,nes_native165_transfer_fn fn,void *ctx,struct nes_ingress584 *t){
 if(!s||!t||!accept||s->state!=NES_NATIVE165_COMPLETE)return false;
 if(!head584(s,t,fn,ctx,0xde))return false;
 s->state=NES_NATIVE165_PREPARED;return true;
}
'''

PROGRESS = r'''
static unsigned word584(const uint8_t *p){return p[0]|(unsigned)p[1]<<8;}
static bool transfer(void *,const uint8_t *,uint8_t *,unsigned);
static bool capture584(struct nes_native_runtime165 *s,const uint8_t *p){
 unsigned seq=word584(p+14);
 if(p[0]!=0x83||p[1]!=1||(word584(p+2)&~0x4f)||word584(p+22)||
    word584(p+12)!=s->generation584||memcmp(p+4,&s->content_epoch,4)||
    memcmp(p+8,&s->serial584,4)||crc_xmodem_block(0xffff,p,48)!=word584(p+48)||
    (s->have584&&((uint16_t)(seq-s->sequence584)==0||(uint16_t)(seq-s->sequence584)>=32768)))
  return fail(s,NES_RUNTIME165_IO);
 memcpy(s->snapshot584,p,50);s->sequence584=(uint16_t)seq;s->have584=true;s->fresh584=3;return true;
}
static bool progress584(void *ctx,uint8_t *out,unsigned owner){
 struct nes_native_runtime165 *s=ctx;
 if(owner>1||!guard(s))return false;
 unsigned bit=1u<<owner;
 if(!(s->fresh584&bit)){
  uint8_t b[52]={0xec};
  if(!transfer(s,b,b,52))return false;
 }
 memcpy(out,s->snapshot584,50);s->fresh584&=(uint8_t)~bit;return true;
}
'''

TRANSFER = r'''
static bool transfer(void *ctx,const uint8_t *tx,uint8_t *rx,unsigned n){
 struct nes_native_runtime165 *s=ctx;
 if(!guard(s)||n>261)return false;
 unsigned opcode=tx[0],original=n;
 bool carrier=opcode==0xe1||opcode==0xe9||opcode==0xec;
 bool begin=opcode==0xe1&&tx[1]==1;
 uint32_t serial=0;uint16_t gen=0;
 if(begin){memcpy(&serial,tx+5,4);memcpy(&gen,tx+9,2);}
 uint8_t b[261];
 if(carrier){memcpy(b,tx,n);if(n<52){memset(b+n,0,52-n);n=52;}}
 s->inside_transfer=true;
 bool ok=s->transfer(s->ctx,carrier?b:tx,carrier?b:rx,n);
 s->inside_transfer=false;s->transactions++;s->wire_bytes+=n;
 nes_budget210_wire(opcode,n,ok);
 if(!ok)return fail(s,NES_RUNTIME165_IO);
 if(!guard(s))return false;
 if(carrier){
  if(!capture584(s,b+2))return false;
  memcpy(rx,b,original);
  /* Pre-E9 plan readiness was consumed by that E9. Never spend it again. */
  if(opcode==0xe9)s->fresh584&=1;
  if(begin){s->serial584=serial;s->generation584=gen;s->fresh584=0;}
 }
 if(opcode==0xea)s->fresh584=0;
 return true;
}
'''

READ = r'''
static bool read509(struct nes_plan200 *p,uint8_t rx[20],uint8_t phase){
 uint8_t b[50];
 if(!p->window||!p->window->progress584||!p->window->progress584(p->ctx,b,1))return fail(p,3);
 memset(rx,0,20);rx[1]=0xd7;rx[2]=4;
 rx[3]=(b[2]&4?1:0)|(b[2]&8?2:0)|(b[2]&64?4:0);
 rx[4]=b[21];rx[5]=b[20];
 if(b[2]&2)memcpy(rx+6,b+36,12);
 /* CRC/epoch/serial/generation were checked once in the common receiver.
  * The existing independent bulk/ACK/count/END semantic checks remain. */
 if(!(b[2]&2)){for(unsigned i=36;i<48;i++)if(b[i])return status215(p,phase,NES_PLAN215_EMPTY,rx);}
 return true;
}
'''

def prepare(src,out):
    out.mkdir(parents=True,exist_ok=False)
    names=['nes_native165.c','nes_native165.h','nes_native_runtime165.c','nes_native_runtime165.h',
           'nes_sink_window184.c','nes_sink_window184.h','nes_plan_service200.c']
    code={n:(src/n).read_text() for n in names};pins={n:sha(src/n) for n in names}
    s=code['nes_native165.c'];start=s.index('static void frame(');end=s.index('void nes_native165_consumed(',start)
    s=s[:start]+INGRESS+s[end:]
    start=s.index('static uint8_t crc8(');end=s.index('\n',start)
    code['nes_native165.c']=s[:start]+s[end+1:]
    s=code['nes_native165.h'];s=once(s,' uint8_t status183[8];bool ready183;\n','')
    s=once(s,'void nes_native165_reset(', 'struct nes_ingress584 {uint32_t epoch,serial;uint16_t next,acked,length,generation;bool pending;};\nvoid nes_native165_reset(')
    s=once(s,'nes_native165_poll(struct nes_native165 *,nes_native165_transfer_fn,void *);','nes_native165_poll(struct nes_native165 *,nes_native165_transfer_fn,void *,struct nes_ingress584 *);')
    s=once(s,'nes_native165_prepare(struct nes_native165 *,bool,nes_native165_transfer_fn,void *);','nes_native165_prepare(struct nes_native165 *,bool,nes_native165_transfer_fn,void *,struct nes_ingress584 *);')
    code['nes_native165.h']=s
    s=code['nes_native_runtime165.h'];s=once(s,' struct nes_sink_window184 transport;',
       ' struct nes_ingress584 ingress584;uint8_t snapshot584[50],fresh584;bool have584;\n uint32_t serial584;uint16_t generation584,sequence584;\n struct nes_sink_window184 transport;')
    code['nes_native_runtime165.h']=s
    s=code['nes_native_runtime165.c'];s=once(s,'#include <string.h>','#include <string.h>\n#include "crc.h"')
    s=once(s,' if(!s->result)s->result=(uint8_t)reason;',' s->fresh584=0;s->ingress584.length=0;\n if(!s->result)s->result=(uint8_t)reason;')
    start=s.index('static bool transfer(');end=s.index('static bool finish_bg549(',start)
    s=s[:start]+PROGRESS+TRANSFER+s[end:]
    s=once(s,'s->content_epoch=epoch;','s->content_epoch=epoch;s->ingress584.epoch=epoch;s->ingress584.serial=1;')
    s=once(s,'nes_window184_init(&s->transport,transfer,guard,s,65536)','nes_window184_init(&s->transport,transfer,guard,s,65536,progress584)')
    s=once(s,'nes_native165_prepare(r,true,transfer,s)','nes_native165_prepare(r,true,transfer,s,&s->ingress584)')
    s=once(s,'nes_native165_poll(r,transfer,s)','nes_native165_poll(r,transfer,s,&s->ingress584)')
    s=once(s,'nes_native165_consumed(r);','s->ingress584.serial++;nes_native165_consumed(r);')
    code['nes_native_runtime165.c']=s
    s=code['nes_sink_window184.h'];s=once(s,'struct nes_sink_window184 {','struct nes_sink_window184 {\n bool (*progress584)(void *,uint8_t *,unsigned);')
    s=once(s,'void *,unsigned);\nbool nes_window184_enqueue','void *,unsigned,bool (*)(void *,uint8_t *,unsigned));\nbool nes_window184_enqueue')
    code['nes_sink_window184.h']=s
    s=code['nes_sink_window184.c']
    begin=s.index('static uint8_t crc8(');end=s.index('static bool io(',begin);s=s[:begin]+s[end:]
    begin=s.index(' uint8_t tx[20]={0xe0}');end=s.index(' unsigned pending=',begin)
    s=s[:begin]+''' uint8_t rx[50];if(s->error||!s->progress584(s->ctx,rx,0))return fail(s,3);
 uint16_t a=(uint16_t)(rx[16]|rx[17]<<8),r=(uint16_t)(rx[18]|rx[19]<<8);
 unsigned active=(uint16_t)(a-r);
 s->status_flags=(active!=0)|((rx[2]&1)?2:0)|(active==4?4:0);
 s->ack_status=(rx[2]&1)?rx[24]:0;
''' + s[end:]
    s=once(s,'a!=s->sent||pending>4||delta>pending||used>4||!!(rx[2]&1)!=(used!=0)||!!(rx[2]&4)!=(used==4)',
        '(uint16_t)(s->sent-a)>pending||pending>4||delta>pending||used>4')
    s=once(s,'if(rx[2]||a||r)','if(s->status_flags||a||r)')
    s=once(s,'!(rx[2]&2)','!(rx[2]&1)')
    s=once(s,'memcpy(ack,rx+7,12)','memcpy(ack,rx+24,12)')
    s=once(s,'void *ctx,unsigned limit){','void *ctx,unsigned limit,bool (*progress)(void *,uint8_t *,unsigned)){')
    s=once(s,'if(!fn||!guard||!limit','if(!fn||!guard||!progress||!limit')
    s=once(s,'s->poll_limit=limit;','s->poll_limit=limit;s->progress584=progress;')
    code['nes_sink_window184.c']=s
    s=code['nes_plan_service200.c'];begin=s.index('static bool read509(');end=s.index('static bool valid(',begin)
    code['nes_plan_service200.c']=s[:begin]+READ+s[end:]
    for n,s in code.items():(out/n).write_text(s,encoding='utf8',newline='\n')
    (out/'manifest.json').write_text(json.dumps(dict(stage=584,baseline=pins,patched={n:sha(out/n) for n in names},
        firmware_SHA256=sha(src/'obj-nes-100/firmware.stm'),scope=__doc__),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('src','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.src,a.out)
