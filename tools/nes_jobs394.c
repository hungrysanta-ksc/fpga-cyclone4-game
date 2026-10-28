/* SPDX-License-Identifier: MIT */
/* Included in the actual output264 translation unit. No job/payload arrays:
 * one immutable wire buffer is synchronously retired before its next use. */
static uint32_t columns394[64];
#ifndef JOBS394_COLD_QUANTUM
#define JOBS394_COLD_QUANTUM 0
#endif
static unsigned tile_store394,map_store394,ordinary394;
static void reset_jobs394(void){tile_store394=map_store394=ordinary394=wire_busy394=0;}
static unsigned common394(unsigned kind,unsigned flags,unsigned bytes){
 if(bytes>246||state259.error||state259.sequence==65535)return fail(30);
 wire_busy394=1; /* E2 work must not replace this pending immutable payload. */
 for(unsigned i=0;(uint16_t)(state259.sent-state259.retired)>=2;i++)
  if(i==65536||!status(0,8))return fail(6);
 wire259[0]=0xe1;wire259[1]=kind;wire259[2]=flags;
 w16(wire259+3,state259.sequence);w32(wire259+5,state259.serial);w16(wire259+9,bytes);
 unsigned c=65535;for(unsigned i=0;i<bytes+11;i++)c=crc16(c,wire259[i]);
 wire259[bytes+11]=c>>8;wire259[bytes+12]=c;
 if(direct394){
  extern int physical267(uint8_t *,unsigned);extern unsigned wait_armed284;
  if(!physical267(wire259,bytes+13)||!progress282(wire259,bytes+13))return fail(1);wait_armed284=0;
 }else if(!io259(wire259,bytes+13))return fail(1);
 if(kind==0x90||kind==0x92)issued312++;
 state259.sent++;state259.sequence++;status259[7]=0;phase_ready302=0;wire_busy394=0;return 1;
}
static void record394(uint8_t *r,unsigned dest,unsigned store,unsigned n,unsigned flags,unsigned bank,unsigned vmain,unsigned region,unsigned first){
 w16(r,dest);w16(r+2,store);w16(r+4,n);r[6]=flags;r[7]=bank;r[8]=vmain;r[9]=region;w16(r+10,first);
}
static unsigned emit394(const uint8_t *record,const uint8_t *data,unsigned encoded){
 uint8_t r[12];for(unsigned i=0;i<12;i++)r[i]=record[i];
 unsigned mode=(r[6]>>2)&3;
 if(encoded<=234){
  for(unsigned i=0;i<12;i++)wire259[11+i]=r[i];
  for(unsigned i=0;i<encoded;i++)wire259[23+i]=data[i];
  return common394(0x90,0,12+encoded);
 }
 if(mode!=1||encoded!=u16(r+4))return fail(31);
 for(unsigned i=0;i<12;i++)wire259[11+i]=r[i];
 if(!common394(0x91,0,12))return 0;
 for(unsigned at=0;at<encoded;){
  unsigned n=encoded-at;unsigned cap=r[9]>=3?224:244;if(n>cap)n=cap;
  w16(wire259+11,at);for(unsigned i=0;i<n;i++)wire259[13+i]=data[at+i];
  if(!common394(0x92,0,n+2))return 0;at+=n;
 }
 return 1;
}
static unsigned tile394(const uint8_t *p){
 uint8_t r[12];unsigned kind=p[1],first=u16(p+10)/(kind?32:16),n=u16(p+14);
 if(kind>1||!n||n>2048||n%(kind?32:16)||tile_store394+n>8192)return fail(32);
 while(n){
  unsigned take=JOBS394_COLD_QUANTUM&&state259.serial<=2&&n>JOBS394_COLD_QUANTUM?JOBS394_COLD_QUANTUM:n;
  unsigned dest=kind?0x2000+state259.bank*0x2000+first*16:state259.bank*0x6000+first*8;
  record394(r,dest,0x8000+tile_store394,take,0,0x7e,0x80,kind,first);
  if(!emit394(r,0,0))return 0;tile_store394+=take;first+=take/(kind?32:16);n-=take;
 }return 1;
}
static unsigned ordinary_job394(const uint8_t *p,unsigned n){
 uint8_t r[12];unsigned region=p[1],first=u16(p+10),encoded=n-16,decoded=p[0]==2?encoded:u16(p+14);
 unsigned mode=p[0]==2?1:p[0]==8?3:2;
 if(region<3||region>5||!decoded||first+decoded>(region==3?512:region==4?544:3418))return fail(33);
 unsigned flags=3|(mode<<2);
 if(region==5&&p[0]==5&&first==21&&decoded==1100&&encoded==2&&!p[16]&&!p[17])flags|=64;
 record394(r,0,(region==3?0x6000:region==4?0x6200:0x6500)+state259.bank*0x8000+first,decoded,flags,0x7f,0,region,first);
 if(!emit394(r,p+16,encoded))return 0;
 if(region<5)ordinary394|=1u<<region;return 1;
}
static unsigned refs394(void){
 uint8_t r[12];for(unsigned region=3;region<5;region++)if(ordinary394&(1u<<region)){
  record394(r,0,(region==3?0x6000:0x6200)+state259.bank*0x8000,region==3?512:544,(region==3?1:2)|16,0x7f,0,region,0);
  if(!emit394(r,0,0))return 0;
 }return 1;
}
unsigned jobs_map394(const uint8_t *map){
 unsigned rows=0,cols=0,previous=4096;
 for(unsigned c=0;c<64;c++)columns394[c]=0;
 for(unsigned g=0;g<256;g++)for(unsigned b=map_byte327(g);b;b&=b-1){
  unsigned w=g*8+__builtin_ctz(b);if(w!=previous+1)rows++;previous=w;
  columns394[(w&31)+(w>>10)*32]|=UINT32_C(1)<<((w>>5)&31);
 }
 for(unsigned c=0;c<64;c++)for(unsigned m=columns394[c]&~(columns394[c]<<1);m;m&=m-1)cols++;
 if((cols<rows?cols:rows)>256)return fail(34);
 uint8_t r[12];
 if(cols<rows){
  for(unsigned c=0;c<64;c++)while(columns394[c]){
   unsigned row=__builtin_ctz(columns394[c]),count=0,first=(c>>5)*1024+row*32+(c&31);
   while(row+count<32&&(columns394[c]&(UINT32_C(1)<<(row+count)))){columns394[c]&=~(UINT32_C(1)<<(row+count));count++;}
   record394(r,0x3000+state259.bank*0x2000+first,0xc000+map_store394,count*2,4|32,0x7e,0x81,2,first);
   for(unsigned i=0;i<12;i++)wire259[11+i]=r[i];
   for(unsigned i=0;i<count;i++){wire259[23+i*2]=map[(first+i*32)*2];wire259[24+i*2]=map[(first+i*32)*2+1];}
   if(!common394(0x90,0,12+count*2))return 0;map_store394+=count*2;
  }
 }else for(unsigned w=0;w<2048;){
  if(!(w&7)&&!map_byte327(w>>3)){w+=8;continue;}
  if(!(map_byte327(w>>3)&(1u<<(w&7)))){w++;continue;}
  unsigned first=w++;while(w<2048&&(map_byte327(w>>3)&(1u<<(w&7))))w++;
  unsigned n=(w-first)*2;record394(r,0x3000+state259.bank*0x2000+first,0xc000+map_store394,n,4,0x7e,0x80,2,first);
  if(!emit394(r,map+first*2,n))return 0;map_store394+=n;
 }
 return 1;
}
