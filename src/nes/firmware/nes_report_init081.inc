/* SPDX-License-Identifier: GPL-2.0-only */
/* Appended only to the report candidate's sdnative.c. Legacy initializer and
 * its active-diagnostic rejection remain byte-for-byte intact. SD v2 only:
 * missing CMD8 is a failure, never permission to consume a stale response. */
static bool report_init081_used;
static bool report_bad081(enum nes_diag_error e) {
 nes_diag_sd_error(e);disk_state=DISK_ERROR;return false;
}
static bool report_owned081(void) {
 if(nes_return_failed())return false;
 if(!nes_diag_active()||nes_return_log_allowed()||sd_offload||ff_sd_offload||
    during_blocktrans!=TRANS_NONE||!get_snes_reset()||
    (NVIC->ISER[OTG_FS_IRQn>>5]&(1u<<(OTG_FS_IRQn&31)))||!SDCARD_DETECT)
  return report_bad081(NES_DIAG_SD_STATE);
 return true;
}
static bool report_guard081(void) {
 return report_owned081()&&nes_return_io_step();
}
static bool report_half081(bool high) {
 if(!report_guard081()||!nes_return_delay(2,false)||!report_owned081())return false;
 if(high)SET_BIT(SD_CLKREG,SD_CLKBIT);else CLEAR_BIT(SD_CLKREG,SD_CLKBIT);
 return true;
}
static bool report_clock081(bool positive,unsigned n) {
 while(n--)if(!report_half081(positive)||!report_half081(!positive))return false;
 return true;
}
static uint32_t report_word081(const uint8_t *r) {
 return ((uint32_t)r[1]<<24)|((uint32_t)r[2]<<16)|((uint32_t)r[3]<<8)|r[4];
}
static bool report_crc081(const uint8_t *r,unsigned first,unsigned last) {
 uint8_t crc=0;
 for(unsigned i=first;i<last;i++)crc=crc7update(crc,r[i]);
 return r[last]==(uint8_t)((crc<<1)|1);
}
static bool report_command081(unsigned command,uint32_t argument,unsigned length,uint8_t *r) {
 uint8_t c[6]={(uint8_t)(0x40|command),(uint8_t)(argument>>24),
  (uint8_t)(argument>>16),(uint8_t)(argument>>8),(uint8_t)argument,0};
 if(!report_guard081())return false;
 memset(r,0,17);make_crc7(c);
 SET_BIT(SD_CMDREG,SD_CMDBIT);GPIO_MODE_OUT(SD_CMDREG,SD_CMDBIT);
 if(!report_clock081(true,5))return false;
 for(unsigned i=0;i<48;i++){
  if(!report_guard081())return false;
  if(c[i/8]&(0x80u>>(i%8)))SET_BIT(SD_CMDREG,SD_CMDBIT);
  else CLEAR_BIT(SD_CMDREG,SD_CMDBIT);
  if(!report_clock081(true,1))return false;
 }
 if(!report_clock081(true,1)||!report_guard081())return false;
 GPIO_MODE_IN(SD_CMDREG,SD_CMDBIT);
 if(length){
  unsigned polls=1000;
  while(BITBAND(SD_CMDREG->GPIO_I,SD_CMDBIT)){
   if(!polls--)return report_bad081(NES_DIAG_SD_RESPONSE);
   if(!report_clock081(false,1))return false;
  }
  for(unsigned i=0;i<length*8;i++){
   if(!report_guard081())return false;
   r[i/8]=(uint8_t)((r[i/8]<<1)|BITBAND(SD_CMDREG->GPIO_I,SD_CMDBIT));
   if(!report_clock081(false,1))return false;
  }
  bool valid;
  if(length==17)valid=r[0]==0x3f&&report_crc081(r,1,16);
  else if(command==41)valid=r[0]==0x3f&&r[5]==0xff; /* R3: no CRC */
  else valid=r[0]==command&&report_crc081(r,0,5);
  if(!valid)return report_bad081(NES_DIAG_SD_RESPONSE);
 }
 return report_clock081(false,8);
}
static bool report_r1081(unsigned command,uint32_t argument,uint8_t *r) {
 if(!report_command081(command,argument,6,r))return false;
 if(report_word081(r)&0xfdffe008u)return report_bad081(NES_DIAG_SD_RESPONSE);
 return true;
}
static bool report_app081(uint32_t address,uint8_t *r) {
 if(!report_r1081(55,address,r))return false;
 return (report_word081(r)&0x20u)?true:report_bad081(NES_DIAG_SD_RESPONSE);
}
static bool report_capacity081(const uint8_t *r,bool high,uint32_t *sectors) {
 uint64_t n;
 unsigned version=getbits((void *)r,8,2);
 if(high){
  if(version!=1)return report_bad081(NES_DIAG_SD_RESPONSE);
  n=((uint64_t)getbits((void *)r,66,22)+1)*1024;
 }else{
  if(version!=0)return report_bad081(NES_DIAG_SD_RESPONSE);
  unsigned bits=getbits((void *)r,52,4),mult=getbits((void *)r,86,3);
  if(bits<9||bits>11)return report_bad081(NES_DIAG_SD_RESPONSE);
  n=((uint64_t)getbits((void *)r,62,12)+1)<<(mult+2+bits-9);
 }
 if(!n||n>UINT32_MAX)return report_bad081(NES_DIAG_SD_RESPONSE);
 *sectors=(uint32_t)n;return true;
}
bool sdn_report_initialize081(void) {
 uint8_t r[17],new_csd[17],new_cid[17];uint32_t address,sectors;bool high;
 if(!report_guard081())return false;
 if(report_init081_used)return report_bad081(NES_DIAG_SD_STATE);
 report_init081_used=true;disk_state=DISK_ERROR;rca=0;ccs=0;
 /* Bootloader may leave a selected card. Deselect has no response when RCA
  * does not match; send once, then retain the old 2042 drain clocks. */
 if(!report_command081(7,0,0,r)||!report_clock081(false,2042)||!report_guard081())return false;
 SET_BIT(SD_DAT3REG,SD_DAT3BIT);GPIO_MODE_OUT(SD_DAT3REG,SD_DAT3BIT);
 if(!report_command081(0,0,0,r)||!report_command081(8,0x1aa,6,r))return false;
 if((report_word081(r)&0xfffu)!=0x1aau)return report_bad081(NES_DIAG_SD_RESPONSE);
 /* >1 second per SDA 4.2.3; independent attempt bound survives frozen ticks.
  * This sub-budget is never restarted on busy responses. */
 struct nes_diag_wait ready=nes_diag_wait_start(200,2048);
 for(;;){
  if(!nes_diag_wait_step(&ready))return report_bad081(NES_DIAG_SD_BUSY);
  if(!report_app081(0,r)||!report_command081(41,0x40fc0000u,6,r))return false;
  if(!(report_word081(r)&0x00fc0000u))return report_bad081(NES_DIAG_SD_RESPONSE);
  if(r[1]&0x80)break;
 }
 high=(r[1]&0x40)!=0;
 if(!report_guard081())return false;
 GPIO_MODE_IN(SD_DAT3REG,SD_DAT3BIT);CLEAR_BIT(SD_DAT3REG,SD_DAT3BIT);
 if(!report_command081(2,0,17,new_cid)||!report_command081(3,0,6,r))return false;
 address=report_word081(r)&0xffff0000u;
 if(!address||(report_word081(r)&0xe008u))return report_bad081(NES_DIAG_SD_RESPONSE);
 if(!report_command081(9,address,17,new_csd)||!report_capacity081(new_csd,high,&sectors)||
    !report_r1081(7,address,r))return false;
 struct nes_diag_wait busy=nes_diag_wait_start(100,250000);
 while(!BITBAND(SD_DAT0REG->GPIO_I,SD_DAT0BIT)){
  if(!nes_diag_wait_step(&busy))return report_bad081(NES_DIAG_SD_BUSY);
  if(!report_clock081(false,1))return false;
 }
 if(!report_r1081(13,address,r))return false;
 if((report_word081(r)&0x1f00u)!=0x900u)return report_bad081(NES_DIAG_SD_RESPONSE);
 if(!report_app081(address,r)||!report_r1081(6,2,r)||!report_r1081(16,512,r)||
    !report_guard081())return false;
 /* Publish driver state only after the complete command chain succeeds.
  * No printf/sdn_getinfo (legacy UART) or fault clearing on this route. */
 memcpy(csd,new_csd,17);memcpy(cid,new_cid,17);rca=address;ccs=high;
 di=(diskinfo0_t){sizeof(diskinfo0_t),0,DISK_TYPE_SD,2,sectors};
 disk_state=DISK_OK;return true;
}
DSTATUS sdn_report_mounted081(BYTE drv) {
 /* FatFS always calls disk_initialize on its first mount. This is a checked
  * status handoff, never a second initialization or permission to clear faults. */
 if(!report_guard081())return STA_NOINIT;
 if(drv||!report_init081_used||disk_state!=DISK_OK){
  report_bad081(NES_DIAG_SD_STATE);return STA_NOINIT;
 }
 return sdn_status(drv);
}
