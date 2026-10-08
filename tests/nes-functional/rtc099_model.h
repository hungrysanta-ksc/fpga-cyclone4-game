/* SPDX-License-Identifier: MIT */
/* Register/clock model ONLY. No instruction timing or physical MMIO claim. */
enum {R_TR,R_DR,R_ISR,R_CR,R_BKP0R,R_BKP2R,R_WPR,R_COUNT};
static uint32_t regs099[R_COUNT],aliases099[2][32];
static unsigned accesses099,polls099,delay099,stall099,inject099,ready_reads099;
static unsigned rtc_mode099,rtc_active099;
static uint32_t *reg099(unsigned r){accesses099++;return &regs099[r];}
static uint32_t *alias099(uint32_t *r,unsigned bit){
 unsigned bank=r==&regs099[R_ISR]?0:1;
 assert(bank==0||r==&regs099[R_CR]);
 if(!bank&&(bit==RTC_ISR_RSF_Pos||bit==RTC_ISR_INITF_Pos)){
  polls099++;ready_reads099++;
  if(inject099&&polls099==inject099)nes_return_fail(NES_DIAG_SPI);
  aliases099[0][bit]=!stall099&&polls099>delay099;
  assert(polls099<=200002); /* Includes earlier FatFS calls and RSF clear aliases. */
 }
 return &aliases099[bank][bit];
}
static void setup_rtc099(unsigned mode){
 memset(regs099,0,sizeof(regs099));memset(aliases099,0,sizeof(aliases099));
 regs099[R_TR]=0x123456;regs099[R_DR]=0x269008; /* valid BCD fixture, WDU=4 */
 regs099[R_BKP2R]=20;regs099[R_BKP0R]=RTC_MAGIC;regs099[R_WPR]=0;
 accesses099=polls099=delay099=stall099=inject099=ready_reads099=0;
 rtc_mode099=mode;rtc_active099=1;
}
