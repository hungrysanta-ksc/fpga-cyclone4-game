// SPDX-License-Identifier: MIT
// Capture actual 227 plan service SPI batch; E8 responses are modeled.
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "nes_plan_service200.c"
static FILE *wire;static unsigned sent;static bool ended;
bool nes_sink195_bulk(struct nes_native_sink165 *s,const uint8_t d[12]){(void)s;(void)d;assert(0);return false;}
static bool guard(void *p){(void)p;return true;}
static bool exchange(void *p,const uint8_t *tx,uint8_t *rx,unsigned n){
 (void)p;if(tx[0]==0xe8){memset(rx,0,n);assert(n==20);rx[1]=0xd7;rx[2]=4;rx[3]=ended?2:1;rx[4]=(uint8_t)(sent>>8);rx[5]=(uint8_t)sent;rx[19]=crc8(rx+1,18);return true;}
 assert(tx[0]==0xe9&&!ended);unsigned len=tx[1]+256u*tx[2];assert(n==len+8&&tx[3]==3&&len==13);
 assert(crc16(tx+4,len)==((unsigned)tx[len+4]<<8|tx[len+5])&&crc8(tx,len+6)==tx[len+6]&&tx[len+7]==0xa5);
 assert(tx[len+1]==0x83&&tx[len+2]==4&&tx[len+3]==0);assert(fwrite(tx,1,n,wire)==n);sent++;ended=true;memset(rx,0,n);return true;
}
int main(int argc,char **argv){
 assert(argc==3&&sizeof(struct nes_plan191)==40);FILE *f=fopen(argv[1],"rb");wire=fopen(argv[2],"wb");assert(f&&wire);
 struct nes_native_sink165 sink={0};sink.state=NES_SINK165_BUILD;sink.generation=4;struct nes_plan200 p={0};p.sink=&sink;p.transfer=exchange;p.guard=guard;p.poll_limit=4;
 struct nes_plan191 q;unsigned count=0;while(fread(&q,sizeof q,1,f)==1){assert(nes_plan200_emit(&p,&q));count++;}assert(feof(f));fclose(f);
 assert(count==2&&nes_plan200_finish(&p)&&p.finished&&sent==1&&ended);fclose(wire);puts("PASS actual 227 plan service two plans and END in one E9 batch");return 0;
}
