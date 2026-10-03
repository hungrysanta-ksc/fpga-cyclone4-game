#include "gbc_state_format.h"
#include <string.h>
#include "crc32.h"
static uint32_t state_get32(const uint8_t *p) {
 return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static void state_put32(uint8_t *p,uint32_t v) {unsigned i;for(i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static uint32_t state_crc(const uint8_t *p,unsigned n) {
 uint32_t c=crc32_init();unsigned i;for(i=0;i<n;i++)c=crc32_update(c,p[i]);return crc32_finalize(c);
}
static int state_ram_valid(uint32_t n) {
 return n==0||n==512||n==2048||n==8192||n==32768||n==65536||n==131072;
}
int gbc_state_identity_valid(const gbc_state_identity *id) {
 return id && id->slot<4 && id->rom_bytes>=16384 && id->rom_bytes<=0x800000 &&
  !(id->rom_bytes&16383) && state_ram_valid(id->ram_bytes);
}
int gbc_state_header_make(uint8_t out[64],const gbc_state_identity *id,uint32_t generation,uint32_t payload_crc) {
 if(!out||!gbc_state_identity_valid(id))return 0;
 memset(out,0,64);memcpy(out,"EGBCST01",8);
 state_put32(out+8,64);state_put32(out+12,GBC_STATE_SCHEMA);
 state_put32(out+16,id->rom_bytes);state_put32(out+20,id->rom_crc);state_put32(out+24,id->ram_bytes);
 state_put32(out+28,GBC_STATE_CORE_BYTES);state_put32(out+32,GBC_STATE_CORE_BYTES+id->ram_bytes);
 state_put32(out+36,payload_crc);state_put32(out+40,id->slot);state_put32(out+44,generation);
 state_put32(out+60,state_crc(out,60));return 1;
}
int gbc_state_validate(gbc_state_reader read,void *ctx,uint32_t bytes,const gbc_state_identity *id,uint32_t *generation,uint32_t *payload_crc) {
 uint8_t h[64],b[512];uint32_t offset,total,c=crc32_init();unsigned i;
 if(!read||!gbc_state_identity_valid(id))return 0;
 total=GBC_STATE_CORE_BYTES+id->ram_bytes;
 if(bytes!=64+total||!read(ctx,0,h,64))return 0;
 if(memcmp(h,"EGBCST01",8)||state_get32(h+8)!=64||state_get32(h+12)!=GBC_STATE_SCHEMA||
    state_get32(h+16)!=id->rom_bytes||state_get32(h+20)!=id->rom_crc||
    state_get32(h+24)!=id->ram_bytes||state_get32(h+28)!=GBC_STATE_CORE_BYTES||
    state_get32(h+32)!=total||state_get32(h+40)!=id->slot||state_get32(h+60)!=state_crc(h,60))return 0;
 for(i=48;i<60;i++)if(h[i])return 0;
 for(offset=0;offset<total;) {
  uint16_t n=(uint16_t)(total-offset>sizeof(b)?sizeof(b):total-offset);
  if(!read(ctx,64+offset,b,n))return 0;
  for(i=0;i<n;i++)c=crc32_update(c,b[i]);
  offset+=n;
 }
 c=crc32_finalize(c);if(c!=state_get32(h+36))return 0;
 if(generation)*generation=state_get32(h+44);
 if(payload_crc)*payload_crc=c;
 return 1;
}
uint16_t gbc_state_region(uint32_t offset,uint32_t ram_bytes,uint16_t limit,uint32_t *address) {
 static const uint32_t sizes[6]={32768,16384,160,128,128,368};
 static const uint32_t bases[6]={0xf18000,0xf14000,0xf10400,0xf10300,0xf10200,0xf10000};
 unsigned i;uint32_t size,base;
 if(!address||!limit||!state_ram_valid(ram_bytes))return 0;
 for(i=0;i<7;i++) {
  size=i<6?sizes[i]:ram_bytes;base=i<6?bases[i]:0xe00000;
  if(offset<size) {uint32_t n=size-offset;*address=base+offset;return (uint16_t)(n<limit?n:limit);}
  offset-=size;
 }
 return 0;
}
