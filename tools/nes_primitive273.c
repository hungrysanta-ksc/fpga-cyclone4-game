/* SPDX-License-Identifier: MIT */
/* Candidate producer, not firmware integration. The FPGA must still bind
 * every receipt to the actual consumed command and validate frame ownership.
 * emit273 is a measurement sink, not SPI; output is an unframed program.
 * mode 0: existing 24-bit semantic events; mode 1: bounded runs;
 * mode 2: ranges plus reads of the held original packet, no payload echo.
 */
#include <stdint.h>
extern void emit273(unsigned byte);
struct context273 {
 uint32_t serial;
 uint16_t generation,sequence,scroll,manifest;
 uint8_t raw,phase,begun,prelude;
};
static struct context273 context;
static unsigned dry,compact,reference,bytes,run_kind,run_n,range_first,range_n;
static uint8_t run[16];
static unsigned u16(const uint8_t *p){return p[0]|(unsigned)p[1]<<8;}
static uint32_t u32(const uint8_t *p){return u16(p)|(uint32_t)u16(p+2)<<16;}
static void put(unsigned b){bytes++;if(!dry)emit273(b&255);}
static void flush(void){
 if(range_n){put(1);put(range_first);put(range_first>>8);put(range_n);range_n=0;}
 if(run_n){put(run_kind);put(run_n);for(unsigned i=0;i<run_n;i++)put(run[i]);run_n=0;}
}
static void event(unsigned kind,unsigned value){
 if(!compact){unsigned w=0x800000|(kind<<18)|value|(kind==1?4096:0);put(w);put(w>>8);put(w>>16);return;}
 if(kind==1){
  if(run_n||(range_n&&(value!=range_first+range_n||range_n==16)))flush();
  if(!range_n)range_first=value;range_n++;return;
 }
 if(kind==3||kind==5||kind==7){
  if(range_n||(run_n&&(run_kind!=kind||run_n==16)))flush();
  run_kind=kind;run[run_n++]=value;return;
 }
 flush();put(kind);put(value);
}
static void range(unsigned first,unsigned count){
 for(unsigned i=0;i<count;i++)event(1,first+i);
}
static void readop(unsigned kind,unsigned offset,unsigned count,unsigned period){
 flush();
 while(count){
  unsigned take=count>255?255:count;
  put(kind);put(take);
  if(kind!=12)put(offset);
  if(kind==9)put(period);
  if(kind==9&&(period&15))period=(((period>>4)+take)%(period&15))<<4|(period&15);
  else offset+=take;
  count-=take;
 }
}
static unsigned value(const uint8_t *p,unsigned position){
 unsigned delta=position-u16(p+10);
 return p[16+(p[0]==2?delta:p[0]==8?delta&3:delta&1)];
}
static unsigned translate(const uint8_t *p,unsigned n){
 if(n<16||n>256||n!=16+u16(p+12)||u32(p+4)!=context.serial||
    u16(p+8)!=context.generation||u16(p+2)!=context.sequence||context.sequence==65535)return 0;
 unsigned op=p[0],type=p[1],at=u16(p+10),plen=u16(p+12),out=op==2?plen:u16(p+14);
 if(context.phase&&(op!=10&&op!=11&&op!=3))return 0;
 if(op==13){
  if(context.prelude||context.begun||n!=48||type!=5||at||out)return 0;
  context.scroll=u16(p+30);context.raw=p[36];
  if(!context.scroll||context.scroll>1121||context.raw>7)return 0;
  context.prelude=1;return 1;
 }
 if(!context.prelude||(op==1?context.begun:!context.begun))return 0;
 if(op==1){if(n!=28||type||at||out)return 0;context.begun=1;return 1;}
 if(op==14){
  if(type!=((context.serial-1)&1)||n<26||out||!p[20]||p[20]>47||
     u32(p+16)>0xffffffffu-p[20])return 0;
  unsigned pos=21;
  for(unsigned i=0;i<p[20];i++){
   if(pos+3>n)return 0;
   unsigned first=u16(p+pos),len=p[pos+2];pos+=3;
   if((first|len)&1||!len||len>64||first+len>4096||pos+len>n)return 0;
   pos+=len;
  }
  return pos==n; /* map DMA descriptors/values retained, no speculative receipt */
 }
 if(op==12){
  return type==((context.serial-1)&1)&&n>=20&&out&&out<=64&&!(out&1)&&
         plen==out+4&&at+out/2<=2048;
 }
 if(op==7){
  unsigned shift=type?5:4,unit=1u<<shift;
  if(type>1||plen!=4||!out||out>2048||(at|out)&(unit-1)||
     at+out>(type?4096:16384))return 0;
  range((type?1024:0)+(at>>shift),out>>shift);return 1;
 }
 if(op==15){
  if(context.phase||n!=206||type||at||out)return 0;
  if(reference){readop(11,16,24,0);readop(10,40,166,0);}
  else for(unsigned i=16;i<206;i++)event(i<40?7:3,p[i]);
  context.phase=1;return 1;
 }
 if(op==10||op==11){
  if(context.phase!=1||type!=2||at!=context.manifest||out||!plen)return 0;
  if(op==10){
   if(context.manifest+plen>256)return 0;
   if(reference)readop(10,16,plen,0);
   else for(unsigned i=16;i<n;i++)event(3,p[i]);
   context.manifest+=plen;
  }else{
   if(plen<2||p[16]!=3)return 0;
   for(unsigned i=17;i<n;){
    unsigned tag=p[i++],len=(tag&127)+1;
    if(context.manifest+len>256||(!(tag&128)&&i+len>n))return 0;
    if(reference){readop(tag&128?12:10,i,len,0);if(!(tag&128))i+=len;}
    else for(unsigned j=0;j<len;j++)event(3,tag&128?0:p[i++]);
    context.manifest+=len;
   }
  }
  return 1;
 }
 if(op==3){
  if(context.phase!=1||context.manifest!=256||n!=16||type||at||out)return 0;
  event(4,3);event(4,2);event(6,1);context.phase=2;return 1;
 }
 if(op!=2&&op!=4&&op!=5&&op!=8)return 0;
 unsigned end=at+out,limit=type==3?512:type==4?544:type==5?3418:0;
 if(!out||end>limit||(op==8?(plen!=4||(out&3)):op!=2&&(plen!=2||(out&1))))return 0;
 if(type==4)return 1; /* OAM has no receipt bits; actual SNES command retained */
 if(type==3){if((at|end)&15)return 0;range(1152+at/16,out/16);return 1;}
 if(at<context.scroll&&(at!=0||end<context.scroll))return 0;
 if(end>3169&&((at>3169&&(at-3169)%16)||(end!=3418&&(end-3169)%16)))return 0;
 for(unsigned pos=at;pos<end;){
  if(pos<context.scroll){
   if(pos==0)event(4,1);
   if(reference){
    readop(9,16,context.scroll,op==2?0:op==8?4:2);pos=context.scroll;
   }else event(5,value(p,pos++));
  }else if(pos<1121)pos=end<1121?end:1121;
  else if(pos<3169){
   if((pos-1121)%16||(end<3169&&(end-1121)%16))return 0;
   event(1,1184+(pos-1121)/16);pos+=16;
  }else if(!context.raw)break;
  else{
   if((pos-3169)%16==0)event(4,((pos-3169)/16)<<2);
   if(reference){
    unsigned count=end-pos;if(count>16)count=16;
    unsigned delta=pos-at,period=op==2?0:op==8?4:2;
    readop(9,16+(period?0:delta),count,period?((delta%period)<<4)|period:0);pos+=count;
   }else event(5,value(p,pos++));
  }
 }
 return 1;
}
unsigned reset273(uint32_t serial,unsigned generation){
 if(!serial||serial==0xffffffffu||generation>65535)return 0;
 context=(struct context273){.serial=serial,.generation=generation};return 1;
}
unsigned packet273(const uint8_t *packet,unsigned n,unsigned mode){
 /* Validate before emitting anything. The saved context and second pass are
  * charged to code, stack and instructions; no transaction buffer is hidden. */
 struct context273 saved=context;
 compact=mode!=0;reference=mode==2;dry=1;bytes=run_n=range_n=0;
 unsigned ok=translate(packet,n);flush();context=saved;
 if(!ok)return 0;
 dry=0;bytes=run_n=range_n=0;
 ok=translate(packet,n);flush();context.sequence++;
 return ok?bytes+1:0; /* +1 distinguishes a valid no-program packet */
}
unsigned complete273(void){return context.phase==2&&context.manifest==256;}
