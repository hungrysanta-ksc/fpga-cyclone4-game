/* SPDX-License-Identifier: MIT */
/* Owned RX + existing wire259 are disjoint immutable raw block slots.
 * SPI is synchronous. No DMA or unexecuted CPU/SPI overlap is assumed. */
static uint8_t source_rx371[250];
static unsigned source_enabled371;
static struct {uint16_t generation;uint8_t n,flags,state;} source_next371;
unsigned source_pop371(unsigned generation,unsigned flags){
 if(source_cancel367||source_token367>=65535)return 0;
 uint8_t h[8];h[0]=0xd5;h[1]=(uint8_t)(source_token367>>8);h[2]=(uint8_t)source_token367;
 h[3]=(uint8_t)generation;h[4]=(uint8_t)(generation>>8);h[5]=(uint8_t)flags;
 h[6]=(uint8_t)source_crc8_367(h,6);h[7]=0xa5;
 if(!physical267(h,8)||source_cancel367)return 0;
 source_token367++;return 1;
}
static int source_fetch371(uint8_t *p,unsigned *length,unsigned *flags,unsigned *terminal){
 unsigned generation=source_next371.generation;uint8_t h[13]={0};
 h[0]=0xd4;h[1]=(uint8_t)(source_token367>>8);h[2]=(uint8_t)source_token367;
 h[3]=(uint8_t)generation;h[4]=(uint8_t)(generation>>8);
 h[6]=(uint8_t)source_crc8_367(h,6);h[7]=0xa5;
 if(!source_io367(h,13,1))return source_fail367(1);
 unsigned n=h[9],token=((unsigned)h[10]<<8)|h[11];*flags=h[8];*length=n;
 if((*flags&0xfc)!=0xa8||source_crc8_367(h+8,4)!=h[12]||
    token!=source_token367||n>248||((*flags&1)!=0)!=(n!=0)){
  (void)source_io367(h,0,2);return source_fail367(2);
 }
 if(!source_io367(p,n?n+2:0,2))return source_fail367(3);
 if(source_cancel367)return source_fail367(4);
 if(!n){source_empty367++;return 1;}
 uint16_t c=65535;for(unsigned j=0;j<n;j++)c=crc_source368(c,p[j]);
 if(c!=(((unsigned)p[n]<<8)|p[n+1]))return source_fail367(5);
 if(source_token367>=65535)return source_fail367(7);
 /* A coincident literal suffix only delays credit,never grants acceptance. */
 *terminal=n>=6&&p[n-6]==255&&p[n-5]==255&&p[n-4]==0&&p[n-3]==4;
 if(!*terminal&&!source_pop371(generation,1))return source_fail367(9);
 return 1;
}
int source_progress371(void){
 if(!source_enabled371)return 1;
 if(source_cancel367)return 0;
 if(source_hint_count367||receiver280.cold||receiver280.serial<3)return 1;
 /* First validated non-map closes the ordered MAP frontier. Map-only
  * blocks may offer their validated prefix at block end. */
 if(source_enabled371==1&&receiver280.phase==1&&receiver280.last<32)return 1;
 unsigned bytes=source_hint367();
 if(bytes){
  if(!physical267(source_buffer367(),bytes)||source_cancel367)return 0;
  source_hint_count367++;
  /* Hint consumed wire259. Fetch one raw block into that free buffer,
   * return CRC-checked storage,then continue current immutable RX semantics.
   * No next-block bytes are used to build the already transmitted hint. */
  if(source_next371.state&16){
   unsigned n=0,flags=0,terminal=0;source_next371.state=0;
   if(!source_fetch371(source_buffer367(),&n,&flags,&terminal))return 0;
   if(n){source_next371.n=(uint8_t)n;source_next371.flags=(uint8_t)flags;source_next371.state=(uint8_t)(1|(terminal?2:0));}
  }
 }
 return 1;
}
unsigned source_receive367(void){
 if(source_cancel367||source_error367)return 0;
 unsigned generation=receiver280.valid?(uint16_t)(receiver280.generation+1):1;
 source_next371.generation=(uint16_t)generation;source_next371.state=0;
 source_blocks367=source_empty367=source_hint_count367=source_hint_tags367=0;
 irq_end284();
 for(unsigned polls=0;polls<65536;polls++){
  unsigned n=0,flags=0,terminal=0;uint8_t *p=source_rx371;
  if(source_next371.state&1){
   p=(source_next371.state&4)?source_rx371:source_buffer367();n=source_next371.n;flags=source_next371.flags;terminal=(source_next371.state&2)!=0;source_next371.state=0;
  }else if(!source_fetch371(p,&n,&flags,&terminal))return 0;
  if(!n){irq_begin284();wait284();continue;}
  source_next371.state=(!terminal&&!source_hint_count367)?16:0;
  /* Once the causal hint has released wire259,alternate both raw slots.
   * Release the next block before current semantics; do not parse out of order.
   * The source may then fill its returned bank while this CPU parses p. */
  if(!terminal&&source_hint_count367){
   uint8_t *next=p==source_rx371?source_buffer367():source_rx371;
   unsigned nn=0,nf=0,nt=0;
   if(!source_fetch371(next,&nn,&nf,&nt))return 0;
   if(nn){source_next371.n=(uint8_t)nn;source_next371.flags=(uint8_t)nf;source_next371.state=(uint8_t)(1|(nt?2:0)|(next==source_rx371?4:0));}
  }
  geometry_groups367=0;source_enabled371=1;
  unsigned accepted=feed280(history286,p,n);
  if(accepted){source_enabled371=2;accepted=source_progress371();}
  source_enabled371=0;
  if(!accepted||receiver280.generation!=generation)return source_fail367(5);
  source_blocks367++;
  if(receiver280.valid&&receiver280.phase==0){
   if(!terminal||!(flags&2)||(source_next371.state&1))return source_fail367(8);
   if(!source_pop371(generation,3))return source_fail367(9);
   irq_end284();return 1;
  }
  if(terminal&&!source_pop371(generation,1))return source_fail367(9);
 }
 return source_fail367(10);
}
