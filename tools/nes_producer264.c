/* SPDX-License-Identifier: MIT
 * Executable consumer specification. DPI runs this C on the host, NOT a65816.
 * Inputs are bytes read through the real packet/DMA bus, never expected images.
 * The event buffer belongs to the test harness; it is not proposed target RAM.
 */
#include <stdint.h>
#include <string.h>
static uint8_t packet[256],meta[2][8570],dma[2048],mapmask[256],mapseen[256];
static uint8_t touched[8570],requirements264[206];
static uint32_t events[32768];
static unsigned used,bank,serial,generation,open263,error263,manifest_at;
static unsigned u16(const uint8_t *p){return p[0]|(unsigned)p[1]<<8;}
static uint32_t u32(const uint8_t *p){return u16(p)|(uint32_t)u16(p+2)<<16;}
static int fail(unsigned e){if(!error263)error263=e;return -(int)error263;}
static void emit(unsigned kind,unsigned value){
 if(used>=32768){error263=90;return;}events[used++]=0x800000u|(kind<<18)|value;
}
static void range(unsigned first,unsigned count,const uint8_t *bytes,unsigned unit){
 while(count){unsigned n=count>16?16:count;emit(1,first|(n<<12));
  for(unsigned i=0;i<n*unit;i++)emit(2,bytes[i]);
  first+=n;count-=n;bytes+=n*unit;
 }
}
static int seal263(unsigned n){
 if(n!=206||u16(packet+12)!=190||manifest_at!=256||memcmp(mapmask,mapseen,256))return fail(20);
 /* Every fresh granule must be completely supplied by actual ordinary writes. */
 for(unsigned unit=0;unit<160;unit++){
  unsigned at=unit<32?4096+unit*16:6273+(unit-32)*16,any=0,all=1;
  for(unsigned j=0;j<16;j++){any|=touched[at+j];all&=touched[at+j];}
  if(any&&!all)return fail(21);
  if(any)range(unit<32?1152+unit:1184+unit-32,1,meta[bank]+at,16);
 }
 for(unsigned block=0;block<16;block++){
  unsigned at=8321+block*16,len=block==15?9:16,any=0,all=1;
  for(unsigned j=0;j<len;j++){any|=touched[at+j];all&=touched[at+j];}
  if(any&&!all)return fail(22);
  if(any){emit(4,block<<2);for(unsigned j=0;j<len;j++)emit(5,meta[bank][at+j]);}
 }
 for(unsigned i=40;i<206;i++)emit(3,packet[i]);
 for(unsigned i=0;i<256;i++)emit(3,mapmask[i]);
 unsigned len=0,lines=0;
 while(len<1121&&meta[bank][5152+len]){
  if(meta[bank][5152+len]>=128)return fail(23);
  lines+=meta[bank][5152+len];len+=5;
 }
 if(len>=1121||lines!=224)return fail(23);
 len++;
 for(unsigned i=0;i<len;i++)if(!touched[5152+i])return fail(24);
 emit(4,1);for(unsigned i=0;i<len;i++)emit(5,meta[bank][5152+i]);
 emit(4,2);emit(6,1);open263=0;return (int)used;
}
/* Scalar DPI ABI avoids simulator-specific array allocation. */
int producer263(int command,int a,int b){
 if(command==0){memset(meta,0,sizeof(meta));serial=0;open263=0;error263=0;used=0;return 0;}
 if(error263)return -(int)error263;
 if(command==1){if(a<0||a>=256||b<0||b>255)return fail(1);packet[a]=(uint8_t)b;return 0;}
 if(command==3){if(a<0||(unsigned)a>=used)return fail(2);return (int)events[a];}
 if(command==4){if(a<0||a>=8570)return fail(3);return meta[bank][a];}
 if(command==5){if(a<0||a>=2048||b<0||b>255)return fail(4);dma[a]=(uint8_t)b;return 0;}
 if(command==6){ /* Map descriptor is observed BEFORE DMA; receipt is independent RTL. */
  if(!open263||a<0||b<=0||b>32||a+b>2048)return fail(5);
  for(int i=a;i<a+b;i++){if(mapseen[i/8]&(1u<<(i%8)))return fail(6);mapseen[i/8]|=1u<<(i%8);}
  return 0;
 }
 if(command==7){if(a<0||a>=4096||b<0||b>255)return fail(7);meta[bank][a]=(uint8_t)b;return 0;}
 if(command!=2||a<16||a>256||a!=16+(int)u16(packet+12))return fail(8);
 used=0;unsigned op=packet[0],section=packet[1],first=u16(packet+10),count=u16(packet+14),payload=u16(packet+12);
 if(op==1){
  unsigned next=u32(packet+4);
  if(open263||a!=28||section||u16(packet+16)!=0x2472||packet[19]||u32(packet+24)!=1||
     next!=serial+1||u32(packet+20)!=serial||packet[18]!=((next-1)&1))return fail(9);
  serial=next;generation=u16(packet+8);bank=packet[18];open263=1;
  manifest_at=0;memset(touched,0,sizeof(touched));memset(mapmask,0,sizeof(mapmask));memset(mapseen,0,sizeof(mapseen));return 0;
 }
 if(!open263||u32(packet+4)!=serial||u16(packet+8)!=generation)return fail(10);
 if(op==7){
  unsigned unit=section?32:16;
  if(section>1||payload!=4||!count||count>2048||first%unit||count%unit||first+count>(section?4096:16384))return fail(11);
  range((section?1024:0)+first/unit,count/unit,dma,unit);return (int)used;
 }
 if(op==2||op==4||op==5||op==8){
  unsigned base=section==3?4096:section==4?4608:section==5?5152:0;
  unsigned limit=section==3?512:section==4?544:section==5?3418:0;
  unsigned pattern=op==2?payload:op==8?4:2;
  if(op==2)count=payload;
  if(!base||!count||first+count>limit||payload!=pattern||count%pattern)return fail(12);
  for(unsigned i=0;i<count;i++){meta[bank][base+first+i]=packet[16+i%pattern];touched[base+first+i]=1;}
  return 0;
 }
 if(op==15){if(a!=206)return fail(30);memcpy(requirements264,packet,206);requirements264[0]=3;return 0;}
 if(op==3){if(a!=16)return fail(31);memcpy(packet,requirements264,206);return seal263(206);}
 if(op==10||op==11){
  if(section!=2||first!=manifest_at||count||!payload)return fail(25);
  unsigned at=16;
  if(op==11){if(payload<2||packet[at++]!=3)return fail(26);}
  while(at<(unsigned)a){
   unsigned code=op==11?packet[at++]:0,len=op==11?(code&127)+1:(unsigned)a-at;
   if(manifest_at+len>256||(!(code&128)&&at+len>(unsigned)a))return fail(27);
   for(unsigned i=0;i<len;i++)mapmask[manifest_at++]=(code&128)?0:packet[at++];
  }
  return 0;
 }
 return fail(13);
}
