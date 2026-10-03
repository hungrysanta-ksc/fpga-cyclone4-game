#ifndef GBC_RTC_CODEC_H
#define GBC_RTC_CODEC_H
#include <stdint.h>
#include <string.h>
/* Standard VBA/SameBoy footer: ten LE32 registers + Unix LE64 timestamp.
 * VBA32 (44 bytes) and raw SRAM are accepted on import as well. */
static uint64_t gbc_rtc_get64(const uint8_t *p,unsigned n) {
 uint64_t x=0;for(unsigned i=0;i<n;i++)x|=(uint64_t)p[i]<<(8*i);return x;
}
static void gbc_rtc_put64(uint8_t *p,uint64_t x,unsigned n) {
 for(unsigned i=0;i<n;i++)p[i]=(uint8_t)(x>>(8*i));
}
static int gbc_rtc_regs_valid(const uint8_t *r) {
 return r[0]<60&&r[1]<60&&r[2]<24&&!(r[4]&0x3e);
}
static void gbc_rtc_advance(uint8_t *r,uint64_t elapsed) {
 if(r[4]&0x40)return;
 uint64_t t=r[0]+60u*(r[1]+60u*r[2])+86400ull*(r[3]+256u*(r[4]&1))+elapsed;
 uint64_t days=t/86400;t%=86400;
 r[0]=t%60;r[1]=(t/60)%60;r[2]=t/3600;r[3]=days;
 r[4]=(r[4]&0xc0)|(days>=512?0x80:0)|((days>>8)&1);
}
static int gbc_rtc_decode(uint8_t regs[10],const uint8_t *footer,unsigned n,uint64_t now) {
 memset(regs,0,10);if(!n)return 1;
 if(n!=44&&n!=48)return 0;
 for(unsigned i=0;i<10;i++){
  if(footer[i*4+1]||footer[i*4+2]||footer[i*4+3])return 0;
  regs[i]=footer[i*4];
 }
 if(!gbc_rtc_regs_valid(regs)||!gbc_rtc_regs_valid(regs+5))return 0;
 uint64_t then=gbc_rtc_get64(footer+40,n-40);
 /* Future/zero timestamps retain the imported clock without an underflow. */
 if(then&&now>=then)gbc_rtc_advance(regs,now-then);
 return 1;
}
static void gbc_rtc_encode(uint8_t footer[48],const uint8_t regs[10],uint64_t now) {
 memset(footer,0,48);for(unsigned i=0;i<10;i++)footer[4*i]=regs[i];
 gbc_rtc_put64(footer+40,now,8);
}
/* STM32 driver returns month 1..12 (the legacy rtc.h comment says 0..11). */
static uint64_t gbc_rtc_epoch(unsigned year,unsigned month,unsigned day,unsigned hour,unsigned minute,unsigned second) {
 uint64_t days=0;
 for(unsigned y=1970;y<year;y++)days+=365+(!(y%4)&&((y%100)||!(y%400)));
 static const uint8_t md[12]={31,28,31,30,31,30,31,31,30,31,30,31};
 for(unsigned m=1;m<month;m++)days+=md[m-1]+(m==2&&!(year%4)&&((year%100)||!(year%400)));
 return (days+day-1)*86400+hour*3600u+minute*60u+second;
}
#endif
