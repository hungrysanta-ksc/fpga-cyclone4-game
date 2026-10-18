# SPDX-License-Identifier: MIT
"""Private PC C2472 sender, independent model comparison required; NOT ARM."""
import inspect
import prepare_nes_maskrun247 as prior
from nes_delta231 import once

HELPER=r'''
static uint8_t maplast247[4096],mapstale247[2][256];static bool mapstarted247;
static bool map247(struct nes_native_sink165 *s,const struct nes_native_video165 *p,unsigned bank){
 if(!mapstarted247){memset(mapstale247,255,sizeof mapstale247);mapstarted247=true;}
 for(unsigned w=0;w<2048;w++)if(memcmp(p->map+2*w,maplast247+2*w,2)){
  mapstale247[0][w/8]|=(uint8_t)(1u<<(w%8));mapstale247[1][w/8]|=(uint8_t)(1u<<(w%8));
 }
 uint8_t b[240]={3};unsigned used=1,w=0;
 while(w<2048){
  if(!(mapstale247[bank][w/8]&(1u<<(w%8)))){w++;continue;}
  unsigned start=w,n=0;
  while(w<2048&&n<32&&(mapstale247[bank][w/8]&(1u<<(w%8)))){w++;n++;}
  if(used+3+2*n>240){if(!packet(s,9,2,0,b,used))return false;used=1;}
  b[used++]=(uint8_t)(start*2);b[used++]=(uint8_t)((start*2)>>8);b[used++]=(uint8_t)n;
  memcpy(b+used,p->map+start*2,n*2);used+=n*2;
 }
 return used==1||packet(s,9,2,0,b,used);
}
static bool manifest247(struct nes_native_sink165 *s,unsigned bank){
 /* Private fixture stack only: no claim this fits ARM RUN/IRQ. */
 uint8_t rle[512],b[240];unsigned at=0,ri=0;
 const uint8_t *map=mapstale247[bank];
 while(at<256){
  unsigned end=at+1;bool zero=map[at]==0;
  while(end<256&&end-at<128&&(map[end]==0)==zero)end++;
  rle[ri++]=(uint8_t)((zero?128:0)+end-at-1);
  if(!zero){memcpy(rle+ri,map+at,end-at);ri+=end-at;}
  at=end;
 }
 unsigned cost=0,used=1;
 for(unsigned i=0;i<ri;){unsigned n=1+((rle[i]&128)?0:(rle[i]&127)+1);
  if(used+n>240){cost+=used+19;used=1;}used+=n;i+=n;
 }
 cost+=used+19;
 if(cost>=294)return packet(s,10,2,0,map,240)&&packet(s,10,2,240,map+240,16);
 unsigned start=0;at=0;used=1;b[0]=3;
 for(unsigned i=0;i<ri;){unsigned count=(rle[i]&127)+1,n=1+((rle[i]&128)?0:count);
  if(used+n>240){if(!packet(s,11,2,start,b,used))return false;start=at;used=1;}
  memcpy(b+used,rle+i,n);used+=n;i+=n;at+=count;
 }
 return packet(s,11,2,start,b,used);
}
'''


def main():
 s=inspect.getsource(prior.main).replace('0x2471','0x2472')
 s=once(s,'if(!packet(s,10,2,0,mapstale247[r->target],240)||!packet(s,10,2,240,mapstale247[r->target]+240,16))return false;', 'if(!manifest247(s,r->target))return false;')
 ns=dict(prior.__dict__);ns.update(HELPER=HELPER,__file__=__file__,__doc__=__doc__)
 exec(compile(s,'jointdecode247-host','exec'),ns);ns['main']()


if __name__=='__main__':main()
