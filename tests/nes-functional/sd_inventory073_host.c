/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "nes_sd_inventory.h"
struct mock {uint8_t *data[4];uint32_t size[4],pos;unsigned current,opens,closes,reads,seeks,steps,blocked,fail,limit,missing;};
enum {NORMAL,NATIVE_READ,SHORT_READ,CLOSE_ERROR,SEEK_ERROR};
static int open_file(void *ctx,const char *path,uint32_t *size){struct mock *m=ctx;assert(!m->blocked);m->opens++;for(unsigned i=0;i<4;i++)if(!strcmp(path,sdinv_paths[i])){m->current=i;m->pos=0;*size=m->size[i];return m->missing&(1u<<i)?1:0;}assert(0);return 2;}
static int read_file(void *ctx,uint8_t *out,unsigned n,unsigned *got){struct mock *m=ctx;assert(!m->blocked);m->reads++;assert(m->pos+n<=m->size[m->current]);if(m->fail==NATIVE_READ){m->blocked=1;*got=0;return 2;}*got=m->fail==SHORT_READ?n-1:n;memcpy(out,m->data[m->current]+m->pos,*got);m->pos+=*got;return 0;}
static int seek_file(void *ctx,uint32_t at){struct mock *m=ctx;assert(!m->blocked);m->seeks++;assert(at<=m->size[m->current]);m->pos=at;return m->fail==SEEK_ERROR;}
static int close_file(void *ctx){struct mock *m=ctx;assert(!m->blocked);m->closes++;return m->fail==CLOSE_ERROR;}
static int step(void *ctx){struct mock *m=ctx;m->steps++;return !m->limit||m->steps<m->limit;}
static int blocked(void *ctx){return ((struct mock *)ctx)->blocked;}
static void le32(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(8*i));}
static void firmware(uint8_t *p,unsigned n,unsigned seed){for(unsigned i=0;i<n;i++)p[i]=(uint8_t)(seed+i);memcpy(p,"STM3",4);le32(p+8,n-512);le32(p+12,sdinv_crc32(p+512,n-512));}
int main(int argc,char **argv){
 assert(argc==2);unsigned tests=0;
 uint8_t fw0[1024],fw1[1024],base[]={0x9b,0x5b,0x77,0x11,0xff,0xff,'x'};
 firmware(fw0,sizeof(fw0),1);firmware(fw1,sizeof(fw1),2);
 uint8_t *menu=calloc(1,0x20000);assert(menu);
 for(unsigned i=0;i<4;i++){uint32_t at=sdinv_header_addresses[i];memset(menu+at,'A'+i,80);menu[at+76]=0;menu[at+77]=0x80;}
 menu[0]=0x78;
 struct mock seed={.data={fw0,fw1,base,menu},.size={1024,1024,sizeof(base),0x20000}};
 struct sdinv_io io={0,open_file,read_file,seek_file,close_file,step,blocked};struct sdinv_report r;struct mock m=seed;io.ctx=&m;
 assert(sdinv_collect(&io,&r));assert(r.finished&&!r.blocked&&m.opens==4&&m.closes==4);tests++;
 for(unsigned i=0;i<4;i++){assert(r.files[i].status==SDINV_OK&&r.files[i].consumed==seed.size[i]&&r.files[i].crc32==sdinv_crc32(seed.data[i],seed.size[i]));tests++;}
 assert(r.files[0].format_ok&&r.files[1].format_ok&&r.files[2].format_ok&&r.files[2].expanded==65537);tests++;
 for(unsigned i=0;i<6;i++){assert(r.headers[i].address==sdinv_header_addresses[i]&&r.headers[i].available==(i<4));tests++;}
 char output[6144];int n=sdinv_format(&r,output,sizeof(output));assert(n>0&&n<(int)sizeof(output));
 char *tail=strstr(output,"payload_crc32=");assert(tail);unsigned crc;assert(sscanf(tail,"payload_crc32=%x",&crc)==1&&crc==sdinv_crc32(output,(unsigned)(tail-output)));tests++;
 FILE *f=fopen(argv[1],"wb");assert(f&&fwrite(output,1,(unsigned)n,f)==(unsigned)n&&!fclose(f));
 assert(sdinv_format(&r,output,16)==-1);tests++;
 for(unsigned fail=NATIVE_READ;fail<=SEEK_ERROR;fail++){
  m=seed;m.fail=fail;io.ctx=&m;int ok=sdinv_collect(&io,&r);
  if(fail==NATIVE_READ){assert(!ok&&r.blocked&&m.opens==1&&m.closes==0&&m.reads==1);}
  else {assert(ok&&r.finished&&!r.blocked&&r.files[fail==SEEK_ERROR?3:0].status==SDINV_IO);}
  tests++;
 }
 for(unsigned limit=1;limit<20;limit++){
  m=seed;m.limit=limit;io.ctx=&m;assert(!sdinv_collect(&io,&r)&&r.blocked&&!r.finished);tests++;
 }
 for(unsigned i=0;i<4;i++){
  m=seed;m.missing=1u<<i;io.ctx=&m;assert(sdinv_collect(&io,&r)&&r.files[i].status==SDINV_ABSENT&&m.closes==3);tests++;
 }
 for(unsigned i=0;i<4;i++){
  m=seed;m.size[i]=i==2?1048577u:i==3?0x400201u:262657u;io.ctx=&m;
  assert(sdinv_collect(&io,&r)&&r.files[i].status==SDINV_LIMIT&&m.closes==4);tests++;
 }
 uint8_t bad[][4]={{0x9b},{0x5b,1},{0x77,1,1},{0x5b,1,0},{0x77,1,0,0}};unsigned lengths[]={1,2,3,3,4};
 for(unsigned i=0;i<5;i++){m=seed;m.data[2]=bad[i];m.size[2]=lengths[i];io.ctx=&m;assert(sdinv_collect(&io,&r)&&!r.files[2].format_ok);tests++;}
 fw0[512]^=1;m=seed;io.ctx=&m;assert(sdinv_collect(&io,&r)&&!r.files[0].format_ok);tests++;
 assert(sdinv_crc32("123456789",9)==0xcbf43926u);tests++;
 free(menu);printf("PASS073 collector checks=%u native_no_extra_IO=1 input_writes=0 synthetic_only=1\n",tests);return 0;
}
