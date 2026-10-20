/* SPDX-License-Identifier: MIT */
/* Split the original command, not its receipt. Every resulting packet keeps
 * one descriptor for the actual SNES command and the retained FPGA receipt.
 * The reference program itself is NOT sent or executed by this experiment. */
static unsigned scroll274,raw274;
static unsigned program274(unsigned type,unsigned start,unsigned length){
 if(type==4)return 0;
 if(type==3)return ((start|length)&15)?0xffffffffu:4*((length/16+15)/16);
 if(type!=5)return 0xffffffffu;
 unsigned end=start+length,cost=0;
 if(start<scroll274){
  if(start||end<scroll274)return 0xffffffffu;
  cost+=2+4*((scroll274+254)/255);start=scroll274;
 }
 if(start<1121)start=end<1121?end:1121;
 if(start<end&&start<3169){
  unsigned stop=end<3169?end:3169;
  if((start-1121)%16||(stop-1121)%16)return 0xffffffffu;
  cost+=4*((((stop-start)/16)+15)/16);start=stop;
 }
 if(start<end&&raw274){
  if((start-3169)%16||(end!=3418&&(end-3169)%16))return 0xffffffffu;
  cost+=6*((end-start+15)/16);
 }
 return cost;
}
static unsigned cut274(unsigned type,unsigned end){
 if(type==3)return end&~15u;
 if(type!=5)return end;
 if(end>=3169)return 3169+(end-3169)/16*16;
 if(end>=1121)return 1121+(end-1121)/16*16;
 return end>=scroll274?end:0;
}
static unsigned part274(const uint8_t *p,unsigned offset,const uint8_t *data,unsigned size,unsigned dry){
 if(dry)return 1;
 for(unsigned i=0;i<16;i++)wire259[i+1]=p[i];
 w16(wire259+11,offset);w16(wire259+13,size);
 for(unsigned i=0;i<size;i++)wire259[17+i]=data[i];
 return send(16+size);
}
static unsigned parts274(const uint8_t *p,unsigned n,unsigned dry){
 unsigned op=p[0],type=p[1],start=u16(p+10),length=n-16;
 if(op==2){
  unsigned limit=type==3?512:type==4?544:type==5?3418:0;
  if(!length||start+length>limit)return fail(21);
  unsigned at=0;
  while(at<length){
   unsigned take=length-at;
   for(;;){
    unsigned cost=program274(type,start+at,take);
    if(cost==0xffffffffu)return fail(21);
    if(!cost||16+take+2+cost<=256)break;
    unsigned end=cut274(type,start+at+take-1);
    if(end<=start+at)return fail(21);
    take=end-start-at;
   }
   if(!part274(p,start+at,p+16+at,take,dry))return 0;
   at+=take;
  }
  return 1;
 }
 if(op==10){
  if(type!=2||u16(p+14)||!length||start+length>256)return fail(21);
  for(unsigned at=0;at<length;){
   unsigned take=length-at;if(take>235)take=235;
   if(!part274(p,start+at,p+16+at,take,dry))return 0;
   at+=take;
  }
  return 1;
 }
 if(op==11){
  if(type!=2||u16(p+14)||length<2||p[16]!=3)return fail(21);
  unsigned at=17,from=17,expanded=0,part_expanded=0,program=0;
  while(at<n){
   unsigned tag=p[at],count=(tag&127)+1,bytes=(tag&128)?1:1+count;
   unsigned cost=(tag&128)?2:3;
   if(at+bytes>n||start+expanded+count>256)return fail(21);
   if(18+1+(at-from)+bytes+program+cost>256){
    if(at==from)return fail(21);
    if(!dry){
     for(unsigned i=0;i<16;i++)wire259[i+1]=p[i];
     w16(wire259+11,start+part_expanded);w16(wire259+13,1+at-from);
     wire259[17]=3;for(unsigned i=from;i<at;i++)wire259[18+i-from]=p[i];
     if(!send(17+at-from))return 0;
    }
    from=at;part_expanded=expanded;program=0;
   }
   expanded+=count;program+=cost;at+=bytes;
  }
  if(!dry){
   for(unsigned i=0;i<16;i++)wire259[i+1]=p[i];
   w16(wire259+11,start+part_expanded);w16(wire259+13,1+at-from);
   wire259[17]=3;for(unsigned i=from;i<at;i++)wire259[18+i-from]=p[i];
   if(!send(17+at-from))return 0;
  }
  return 1;
 }
 return fail(21);
}
