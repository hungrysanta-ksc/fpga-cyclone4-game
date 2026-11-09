/* Bounded incremental recipe producer, not a production ABI. */
#include <stdint.h>
struct input671 {
 const uint16_t *cells, *map;
 uint8_t *sent, *out;
 unsigned row, source, column, epoch;
};
static uint16_t checksum(const uint8_t *p,unsigned n){
 uint16_t c=65535;
 while(n--){unsigned x=(c>>8)^*p++;x^=x>>4;
  c=(uint16_t)((c<<8)^(x<<12)^(x<<5)^x);}
 return c;
}
/* Caller owns the immutable source and final row, and clears sent[128] on
 * BEGIN/STOP. Existing planner has already frozen these slots this frame.
 * A failed enqueue aborts the frame; retry requires resetting sent state. */
unsigned recipe671(const struct input671 *s){
 if(s->row>=64||s->source>32||s->column>=64||s->epoch>=2)return 0;
 uint8_t *p=s->out;unsigned n=0;
 p[0]=s->row;p[1]=s->source;p[2]=s->column;p[3]=s->epoch;p[5]=0;
 uint16_t c=checksum((const uint8_t *)(s->map+s->row*32),64);
 p[6]=c;p[7]=c>>8;
 if(s->source!=32)for(unsigned i=0;i<33;i++){
  unsigned col=(s->column+i)&63;
  if(col/32!=s->row/32)continue;
  unsigned cell=s->cells[s->source*33+i],slot=s->map[s->row*32+col%32]&1023;
  if(!slot||cell>=32768)return 0;
  unsigned bit=1u<<(slot&7);
  if(!(s->sent[slot>>3]&bit)){
   s->sent[slot>>3]|=bit;unsigned at=8+4*n++;
   p[at]=cell;p[at+1]=(cell>>8)&31;p[at+2]=slot;p[at+3]=slot>>8;
  }
 }
 p[4]=n;return 8+4*n;
}
