/* SPDX-License-Identifier: MIT */
unsigned card_commands096(void){return commands;}
unsigned card_edges096(void){return rises;}
unsigned card_writes096(void){return write_commands;}
static unsigned fat32_096;
void card_profile096(unsigned n){fat32_096=n&1;ccs=!(n&2);}
void card_fault096(unsigned f,unsigned at){fault=f;fault_at=at;}
void card_present096(unsigned n){card=n;}
void card_invalidate096(void){fs.fs_type=0;}
void card_phase_fault096(unsigned phase,unsigned f,unsigned index){target_phase096=phase;target_index096=index;phase_commands096=0;fault=f;fault_at=0;}
void card_summary096(void){for(unsigned p=1;p<=5;p++){unsigned n=0;for(unsigned c=1;c<=commands;c++)if(command_stage[c]==p)n++;if(n)printf("PHASE096 phase=%u commands=%u\n",p,n);}}
static void put_file096(const char *path,const uint8_t *data,unsigned size){
 FIL f;UINT n;nes_return_log_allow(true);
 assert(f_open(&f,path,FA_CREATE_ALWAYS|FA_WRITE)==FR_OK);
 for(unsigned i=0;i<size;){unsigned count=size-i;if(count>512)count=512;
  /* Fixture preparation is outside the measured session. */
  nes_return_log_allow(true);assert(f_write(&f,data+i,count,&n)==FR_OK&&n==count);i+=n;
 }
 nes_return_log_allow(true);assert(f_close(&f)==FR_OK);
}
void card_setup096(const uint8_t *rom,unsigned size){
 setup096=1;sectors=fat32_096?70000:8192;root_sector=fat32_096?1126:65;disk_state=DISK_OK;
 media[0]=0xeb;media[1]=0x3c;media[2]=0x90;memcpy(media+3,"NATIVE96",8);
 word(11,512);media[13]=1;media[16]=2;media[21]=0xf8;word(510,0xaa55);
 if(!fat32_096){memcpy(media+54,"FAT16   ",8);word(14,1);word(17,512);word(19,8192);word(22,32);
  for(unsigned i=0;i<2;i++){word((1+i*32)*512,0xfff8);word((1+i*32)*512+2,0xffff);}}
 else {memcpy(media+82,"FAT32   ",8);word(14,32);dword(32,70000);dword(36,547);dword(44,2);word(48,1);
  for(unsigned i=0;i<2;i++){unsigned at=(32+i*547)*512;dword(at,0x0ffffff8);dword(at+4,0x0fffffff);dword(at+8,0x0fffffff);}
  dword(512,0x41615252);dword(512+484,0x61417272);dword(512+488,0xffffffff);dword(512+492,2);word(512+510,0xaa55);
 }
 nes_diag_begin();nes_return_log_allow(true);assert(f_mount(&fs,"",1)==FR_OK);
 assert(f_mkdir("/sd2snes")==FR_OK);nes_return_log_allow(true);assert(f_mkdir("/sd2snes/nes")==FR_OK);
 put_file096(size==98320?"/sd2snes/nes/banks32.nes":"/sd2snes/nes/fine_x.nes",rom,size);
 uint8_t config[1100];for(unsigned i=0;i<1100;i++)config[i]=(uint8_t)(i%64);
 /* Exercise literal, escaped control, short run and long run across sectors. */
 config[0]=0x9b;config[1]=0x9b;config[2]=0x5b;config[3]=0xa1;config[4]=3;
 config[5]=0x77;config[6]=0xb2;config[7]=0x02;config[8]=0x01;
 put_file096("/sd2snes/fpga_n86.bi3",config,sizeof(config));
 put_file096("/sd2snes/fpga_base.bi3",config,sizeof(config));
 nes_return_reset();nes_diag_sd_reset();setup096=0;
 commands=read_commands=write_commands=commits=rises=falls=read_nibbles=0;
}
