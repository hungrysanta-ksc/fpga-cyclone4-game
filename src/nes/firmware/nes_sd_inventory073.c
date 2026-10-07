/* SPDX-License-Identifier: GPL-2.0-only */
/* SDINFO073: read-only fixed-path collection, no FPGA/PSRAM/menu execution. */
#include "nes_sd_inventory.h"
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
const char *const sdinv_paths[SDINV_FILES]={"/sd2snes/firmware.before-sdinfo072.stm","/sd2snes/firmware.stm","/sd2snes/fpga_base.bi3","/sd2snes/m3nu.bin"};
const uint32_t sdinv_header_addresses[SDINV_HEADERS]={0xffb0,0x101b0,0x7fb0,0x81b0,0x40ffb0,0x4101b0};
static uint32_t byte_crc(uint32_t c,uint8_t b){c^=b;for(unsigned i=0;i<8;i++)c=(c>>1)^((0u-(c&1u))&0xedb88320u);return c;}
uint32_t sdinv_crc32(const void *p,unsigned n){const uint8_t *b=p;uint32_t c=~0u;while(n--)c=byte_crc(c,*b++);return c^~0u;}
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
struct decoder {unsigned state,token,value,lo,bad;uint32_t n,c;};
static void emit(struct decoder *d,unsigned n){
 if(!n||n>2097152u-d->n){d->bad=1;return;}
 for(unsigned i=0;i<n;i++)d->c=byte_crc(d->c,(uint8_t)d->value);
 d->n+=n;
}
static void decode_byte(struct decoder *d,unsigned b){
 if(d->bad)return;
 if(!d->state){
  if(b==0x9b||b==0x5b||b==0x77){d->token=b;d->state=1;}
  else {d->value=b;emit(d,1);}
 }else if(d->state==1){d->value=b;if(d->token==0x9b){emit(d,1);d->state=0;}else d->state=2;}
 else if(d->state==2){d->lo=b;if(d->token==0x5b){emit(d,b);d->state=0;}else d->state=3;}
 else {emit(d,d->lo|(b<<8));d->state=0;}
}
static int allowed(const struct sdinv_io *io,struct sdinv_report *r){
 if(io->blocked(io->ctx)||!io->step(io->ctx)){r->blocked=1;return 0;}return 1;
}
static int exact(const struct sdinv_io *io,struct sdinv_report *r,uint8_t *p,unsigned n){
 unsigned got=0;if(!allowed(io,r))return 0;
 return !io->read(io->ctx,p,n,&got)&&got==n&&!io->blocked(io->ctx);
}
int sdinv_collect(const struct sdinv_io *io,struct sdinv_report *r){
 memset(r,0,sizeof(*r));uint8_t data[256];
 for(unsigned i=0;i<SDINV_HEADERS;i++)r->headers[i].address=sdinv_header_addresses[i];
 for(unsigned index=0;index<SDINV_FILES;index++){
  struct sdinv_file *f=&r->files[index];if(!allowed(io,r))return 0;
  int opened=io->open(io->ctx,sdinv_paths[index],&f->size);
  if(opened){f->status=opened==1?SDINV_ABSENT:SDINV_IO;if(io->blocked(io->ctx)){r->blocked=1;return 0;}continue;}
  unsigned ok=1;uint32_t c=~0u,body=~0u;struct decoder d={0,0,0,0,0,0,~0u};
  uint32_t limit=index==2?1048576u:index==3?0x400200u:262656u;
  if(!f->size||f->size>limit){f->status=SDINV_LIMIT;ok=0;}
  while(ok&&f->consumed<f->size){
   unsigned n=f->size-f->consumed;if(n>sizeof(data))n=sizeof(data);
   if(!exact(io,r,data,n)){f->status=SDINV_IO;ok=0;break;}
   for(unsigned j=0;j<n;j++){
    uint32_t at=f->consumed+j;c=byte_crc(c,data[j]);
    if(at<16)f->prefix[at]=data[j];
    if(at>=512&&index<2)body=byte_crc(body,data[j]);
    if(index==2)decode_byte(&d,data[j]);
   }
   f->consumed+=n;
  }
  if(ok){
   f->status=SDINV_OK;f->crc32=c^~0u;f->body_crc32=body^~0u;
   f->format_ok=index<2?(f->size>=512&&!memcmp(f->prefix,"STM3",4)&&u32(f->prefix+8)==f->size-512&&u32(f->prefix+12)==f->body_crc32):index==2?(!d.bad&&!d.state&&d.n>0):1;
   if(index==2){f->expanded=d.n;f->expanded_crc32=d.c^~0u;}
  }
  if(ok&&index==3){
   for(unsigned i=0;i<SDINV_HEADERS;i++){
    struct sdinv_header *h=&r->headers[i];h->address=sdinv_header_addresses[i];
    if(h->address>f->size||f->size-h->address<80)continue;
    if(!allowed(io,r)||io->seek(io->ctx,h->address)||!exact(io,r,h->data,80)){f->status=SDINV_IO;ok=0;break;}
    h->available=1;unsigned vector=h->data[76]|((unsigned)h->data[77]<<8);
    uint32_t offset=(h->address&0xfff)==0x1b0?512:0;
    h->reset_address=(((h->address-offset)&~0x7fffu)|(vector&0x7fff))+offset;
    if(h->reset_address>=f->size)continue;
    if(!allowed(io,r)||io->seek(io->ctx,h->reset_address)||!exact(io,r,&h->reset,1)){f->status=SDINV_IO;ok=0;break;}
    h->reset_available=1;
   }
  }
  if(io->blocked(io->ctx)||r->blocked){r->blocked=1;return 0;}
  if(!allowed(io,r))return 0;
  if(io->close(io->ctx)){f->status=SDINV_IO;ok=0;}
  if(io->blocked(io->ctx)){r->blocked=1;return 0;}
 }
 r->finished=1;return 1;
}
struct text {char *p;size_t used,size;unsigned bad;};
static void add(struct text *t,const char *fmt,...){
 if(t->bad)return;
 va_list a;va_start(a,fmt);int n=vsnprintf(t->p+t->used,t->size-t->used,fmt,a);va_end(a);
 if(n<0||(size_t)n>=t->size-t->used){t->bad=1;return;}t->used+=(size_t)n;
}
int sdinv_format(const struct sdinv_report *r,char *p,size_t size){
 if(!size)return -1;
 struct text t={p,0,size,0};
 add(&t,"SDINFO073_BEGIN\r\nidentity=SDINFO073-BASE069\r\nread_only_inputs=yes\r\ncrc_is_authentication=no\r\nmenu_classification=offline_actual_C_pending\r\nbackup_restore_execution=not_performed\r\nnes_core_run=not_performed\r\nfinished=%u\r\nblocked=%u\r\n",r->finished,r->blocked);
 for(unsigned i=0;i<SDINV_FILES;i++){
  const struct sdinv_file *f=&r->files[i];
  add(&t,"file%u_path=%s\r\nfile%u_status=%u\r\nfile%u_size=%lu\r\nfile%u_consumed=%lu\r\nfile%u_crc32=%08lx\r\nfile%u_format_ok=%u\r\nfile%u_body_crc32=%08lx\r\nfile%u_expanded=%lu\r\nfile%u_expanded_crc32=%08lx\r\n",i,sdinv_paths[i],i,f->status,i,(unsigned long)f->size,i,(unsigned long)f->consumed,i,(unsigned long)f->crc32,i,f->format_ok,i,(unsigned long)f->body_crc32,i,(unsigned long)f->expanded,i,(unsigned long)f->expanded_crc32);
 }
 for(unsigned i=0;i<SDINV_HEADERS;i++){
  const struct sdinv_header *h=&r->headers[i];
  add(&t,"header%u_address=%08lx\r\nheader%u_available=%u\r\nheader%u_reset_address=%08lx\r\nheader%u_reset_available=%u\r\nheader%u_reset=%02x\r\nheader%u_bytes=",i,(unsigned long)h->address,i,h->available,i,(unsigned long)h->reset_address,i,h->reset_available,i,h->reset,i);
  for(unsigned j=0;j<80;j++)add(&t,"%02x",h->data[j]);
  add(&t,"\r\n");
 }
 if(t.bad)return -1;
 uint32_t crc=sdinv_crc32(p,(unsigned)t.used);
 add(&t,"payload_crc32=%08lx\r\nSDINFO073_END\r\n",(unsigned long)crc);
 return t.bad?-1:(int)t.used;
}
