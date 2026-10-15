/* SPDX-License-Identifier: MIT */
/* Real170 consumer replays exact RTL bytes; negative mutations are explicit. */
#include "nes_sink_spi165.h"
#include "nes_sink_io170.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
struct row {unsigned n;uint8_t tx[259],rx[259];};
static struct row rows[48][8];static unsigned counts[48];
struct replay {unsigned scene,pos,negative,guards;};
static bool guard(void *v){struct replay *r=v;r->guards++;return !(r->negative==2&&r->pos+1==counts[r->scene]);}
static bool transfer(void *v,const uint8_t *tx,uint8_t *rx,unsigned n){
 struct replay *r=v;assert(r->pos<counts[r->scene]);struct row *p=&rows[r->scene][r->pos++];
 assert(n==p->n&&!memcmp(tx,p->tx,n));memcpy(rx,p->rx,n);
 if(r->negative==1&&r->pos==counts[r->scene])rx[15]^=1;
 return true;
}
int main(int argc,char **argv){
 assert(argc==2);FILE *f=fopen(argv[1],"r");assert(f);unsigned id,n,x;
 while(fscanf(f,"%u %u",&id,&n)==2){assert(id<48&&n<=259&&counts[id]<8);struct row *r=&rows[id][counts[id]++];r->n=n;
  for(unsigned i=0;i<n;i++){assert(fscanf(f,"%x",&x)==1);r->tx[i]=(uint8_t)x;}
  for(unsigned i=0;i<n;i++){assert(fscanf(f,"%x",&x)==1);r->rx[i]=(uint8_t)x;}
 }assert(feof(f));fclose(f);
 for(unsigned s=0;s<48;s++)for(unsigned mode=0;mode<3;mode++){
  assert(counts[s]>=5);struct replay r={s,0,mode,0};struct nes_sink_spi165 spi={transfer,&r,guard,16};
  uint8_t ack[12];memset(ack,0xa5,12);memset(&nes_sink_io170,0,sizeof(nes_sink_io170));
  bool ok=nes_sink_spi165_exchange(&spi,rows[s][1].tx+1,16,ack);
  if(!mode){assert(ok&&r.pos==counts[s]);assert(!memcmp(ack,rows[s][counts[s]-1].rx+3,12));}
  else {assert(!ok);for(unsigned i=0;i<12;i++)assert(ack[i]==0xa5);
   assert((nes_sink_io170.reason&127)==(mode==1?SIO170_POLL_STATUS:SIO170_POLL_GUARD));}
 }
 puts("PASS ACKLEASE181 MCU rtl_replays=48 crc_negatives=48 guard_negatives=48");return 0;
}
