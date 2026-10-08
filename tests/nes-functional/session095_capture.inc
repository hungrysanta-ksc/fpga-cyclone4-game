/* SPDX-License-Identifier: MIT */
static FILE *trace095;
static unsigned ss095,sck095,mosi095,bits095,samples095,frames095,guard_ns095;
static unsigned long long start095,guard_reads095;
static uint8_t tx095[8],rx095[8];
unsigned guard_read095(unsigned value,unsigned bit){
 ns+=guard_ns095;guard_reads095++;return (value>>bit)&1u;
}
static unsigned long long pack095(const uint8_t *p){unsigned long long v=0;for(unsigned i=0;i<8;i++)v=(v<<8)|p[i];return v;}
static void record(int expect){
 (void)expect; /* Delay callback is before the guard; sample at SCK falling. */
 if(!trace095)return;
 unsigned ss=!!(mock_a.ODR&16),sck=!!(mock_b.ODR&8),mosi=!!(mock_b.ODR&32);
 if(!ss&&mosi!=mosi095){
  assert(!sck&&samples095==bits095);
  assert(ns-start095==2000ull+guard_ns095+bits095*(4000ull+2*guard_ns095)+(bits095/8)*2000ull);
 }
 if(ss!=ss095){
  if(!ss){assert(!sck);start095=ns;bits095=samples095=0;memset(tx095,0,8);memset(rx095,0,8);}
  else {assert((bits095==16||bits095==64)&&samples095==bits095&&!sck);
   assert(ns-start095==4000ull+bits095*(4000ull+2*guard_ns095)+(bits095/8)*2000ull);
   fprintf(trace095,"%llu %llu %u %016llx %016llx %u\n",start095,ns,bits095,pack095(tx095),pack095(rx095),guard_ns095);frames095++;
  }
 }
 if(!ss&&sck!=sck095){
  if(sck){unsigned bit=bits095;assert(bit<64);assert(ns-start095==4000ull+guard_ns095+bit*(4000ull+2*guard_ns095)+(bit/8)*2000ull);tx095[bit/8]|=(uint8_t)(!!(mock_b.ODR&32)<<(7-bit%8));bits095++;}
  else {unsigned bit=samples095;assert(bit<bits095);assert(ns-start095==6000ull+2*guard_ns095+bit*(4000ull+2*guard_ns095)+(bit/8)*2000ull);rx095[bit/8]|=(uint8_t)(!!(mock_b.IDR&16)<<(7-bit%8));samples095++;}
 }
 ss095=ss;sck095=sck;mosi095=mosi;
}
