/* SPDX-License-Identifier: MIT
 * ABI cost probe, NOT selected firmware. Serial32 is retained on every record.
 * mode0 preserves compact payloads; mode1 normalizes descriptors/plan/metadata.
 * Output tokens are not invented: map bases and tile references remain binding.
 */
#include <stdint.h>
uint8_t output364[2048];
static uint8_t body364[512];
uint32_t size364,packets364,sequence364;
static uint32_t serial364;
static unsigned rd(const uint8_t *p){return p[0]|((unsigned)p[1]<<8);}
static uint32_t rd32(const uint8_t *p){return rd(p)|((uint32_t)rd(p+2)<<16);}
static void wr(uint8_t *p,unsigned n){p[0]=n;p[1]=n>>8;}
static void wr32(uint8_t *p,uint32_t n){wr(p,n);wr(p+2,n>>16);}
static void copy(uint8_t *d,const uint8_t *s,unsigned n){while(n--)*d++=*s++;}
static unsigned crc(const uint8_t *p,unsigned n){
 unsigned c=65535;while(n--){c^=(unsigned)*p++<<8;for(unsigned j=0;j<8;j++)c=(c<<1)^((c&32768)?0x1021:0);}return c&65535;
}
void reset364(void){sequence364=0;serial364=0;}
static unsigned emit(unsigned kind,unsigned route,unsigned n){
 if(n>512||size364+n+13>sizeof output364||sequence364>65535)return 0;
 uint8_t *p=output364+size364;p[0]=0xeb;p[1]=kind;p[2]=route;
 wr(p+3,sequence364++);wr(p+5,n);wr32(p+7,serial364);copy(p+11,body364,n);
 unsigned c=crc(p,n+11);p[n+11]=c>>8;p[n+12]=c;size364+=n+13;packets364++;return 1;
}
static unsigned dense(const uint8_t *p,unsigned n,unsigned expected,unsigned offset,unsigned kind,unsigned prefix){
 unsigned at=0,m=2+prefix,total=0;wr(body364,offset);
 while(at<n){unsigned h=p[at++],count=(h&127)+1;if(total+count>expected)return 0;
  while(count--){if(!(h&128)&&at>=n)return 0;body364[m++]=(h&128)?0:p[at++];total++;
   if(m==240){if(!emit(kind,3,m))return 0;offset+=m-2;wr(body364,offset);m=2;}
  }
 }
 if(total!=expected)return 0;return m==2||emit(kind,3,m);
}
unsigned convert364(const uint8_t *tx,unsigned len,unsigned mode,uint32_t serial){
 size364=packets364=0;if(len<3||mode>1)return 0;
 if(serial!=serial364){serial364=serial;sequence364=0;}
 if(tx[0]==0xe9){
  unsigned n=rd(tx+1),count=tx[3];if(len!=n+8||!count||count>16)return 0;
  const uint8_t *p=tx+4,*end=p+n;
  if(!mode){copy(body364,p,n);return emit(count,1,n);}
  for(unsigned i=0;i<count;i++){
   if(p>=end)return 0;uint8_t *d=body364+i*32;for(unsigned j=0;j<32;j++)d[j]=0;
   unsigned k=p[0];
   if(k&128){
    unsigned kind=k&127,sz=(kind==0)?7:(kind==1)?8:3;if(p+sz>end)return 0;
    d[0]=kind;d[2]=p[1];d[3]=p[2];
    if(kind<2){copy(d+4,p+3,4);d[8]=(kind==0)?255:p[7];
     const uint8_t rows[6]={0x40,0x22,0x6d,0x64,0x6b,0xff};copy(d+9,rows,6);d[15]=1;}
    p+=sz;
   }else{
    if(p+16>end)return 0;copy(d,p,16);p+=16;
    for(unsigned j=0;j<8;j++)if(d[1]&(1u<<j)){if(p+2>end)return 0;copy(d+16+j*2,p,2);p+=2;}
   }
  }
  return p==end&&emit(count,2,count*32);
 }
 if(tx[0]!=0xe1||len<19)return 0;const uint8_t *p=tx+1;
 unsigned op=p[0],section=p[1],n=rd(p+12),start=rd(p+10),span=rd(p+14),kind=op|(section<<4);
 if(n+19!=len||op>15||section>5||rd32(p+4)!=serial)return 0;
 const uint8_t *v=p+16;
 if(!mode){wr(body364,start);wr(body364+2,span);copy(body364+4,v,n);return emit(kind,0,n+4);}
 if(op==14){
  if(n<5)return 0;uint32_t token=rd32(v);unsigned count=v[4],at=5,m=5,ranges=0;
  if(!count||count>47||token>0xffffffffu-count)return 0;wr32(body364,token);body364[4]=0;
  for(unsigned i=0;i<count;i++){
   if(at+3>n)return 0;unsigned off=rd(v+at),bytes=v[at+2];at+=3;
   if(!bytes||bytes>64||((off|bytes)&1)||off+bytes>4096||at+bytes>n)return 0;
   if(m+8+bytes>240){body364[4]=ranges;if(!emit(kind,5,m))return 0;token+=ranges;ranges=0;m=5;wr32(body364,token);}
   wr(body364+m,off);wr(body364+m+2,bytes);wr(body364+m+4,bytes);body364[m+6]=0;body364[m+7]=section;
   copy(body364+m+8,v+at,bytes);m+=8+bytes;at+=bytes;ranges++;
  }
  body364[4]=ranges;return at==n&&emit(kind,5,m);
 }
 if(op==15){
  if(n<25||v[24]!=1)return 0;
  copy(body364+2,v,24);return dense(v+25,n-25,166,0,kind,24);
 }
 if(op==11)return n>1&&v[0]==3&&dense(v+1,n-1,256,0,kind,0);
 if(op==10){wr(body364,start);copy(body364+2,v,n);return emit(kind,3,n+2);}
 if(op==1||op==3||op==13){copy(body364,v,n);return emit(kind,4,n);}
 /* Fixed descriptors retain compressed repeat seeds and explicit token bytes. */
 unsigned expanded=(op==2)?n:span,format=(op==4||op==5)?1:(op==8)?2:(op==7)?3:0;
 if(op==2&&n>238){
  unsigned at=0;while(at<n){unsigned bytes=n-at;if(bytes>238)bytes=238;
   wr(body364,start+at);wr(body364+2,bytes);wr(body364+4,bytes);body364[6]=0;body364[7]=section;
   copy(body364+8,v+at,bytes);if(!emit(kind,6,bytes+8))return 0;at+=bytes;}
  return 1;
 }
 wr(body364,start);wr(body364+2,expanded);wr(body364+4,n);body364[6]=format;body364[7]=section;
 copy(body364+8,v,n);return emit(kind,6,n+8);
}
