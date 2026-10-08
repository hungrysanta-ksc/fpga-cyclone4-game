/* SPDX-License-Identifier: GPL-2.0-only */
/* Each reset_case is an independent power-on, never an in-session recovery. */
static void reset_case(unsigned fat32,unsigned hc){
 nes_diag_leave();nes_return_reset();nes_diag_sd_reset();(void)f_mount(NULL,"",0);
 stage=stage_mask=commands=write_commands=read_commands=commits=read_nibbles=syncs=0;
 first_fault_stage=first_fault_command=first_fault_rises=0;
 level=rises=falls=receiving=cmd_pending=cmd_value=cmd_bits=cmd_number=cmd_sector=0;
 data_end=samples=data_mask=data_value=fault=fault_at=command_fault=busy_clocks=wp=tick_div=tick_origin=0;
 during_blocktrans=TRANS_NONE;sd_offload=ff_sd_offload=sd_offload_partial=0;card=1;ccs=0;disk_state=DISK_CHANGED;
 memset(csd,0,sizeof(csd));memset(cid,0,sizeof(cid));memset(&di,0,sizeof(di));rca=0;report_init081_used=false;
 init_response_pos=init_response_len=init_cmd_bits=init_command=init_commands=0;
 init_busy_clocks=init_clk=init_complete=fast_mode=0;
 cmdlevel=cmdout=cmdclocks=attempts=assigned=ios=log_count=0;
 corrupt_at=corrupt_kind=timeout_at=never_ready=never_unbusy=0;
 memset(init_response,0,sizeof(init_response));memset(init_wire,0,sizeof(init_wire));
 marker_mask=marker_delay_fail=pinfault=0;
 held=1;prog=configured=sent=postinit=io=atfault=atcorrupt=0;
 display_ticks=delay_stage=release_mask=init_delays=fail_delay=slow_clock=stage_tick_cost=0;
 snes_boot_configured=file_res=newcard=0;high_capacity=hc;nvic.ISER[2]=1u<<(OTG_FS_IRQn&31);
 memset(rom,0xcc,sizeof(rom));memset(screen,0xcc,sizeof(screen));
 sectors=fat32?70000:8192;memset(media,0,sizeof(media));memset(&fatfs,0,sizeof(fatfs));
 media[0]=0xeb;media[1]=0x3c;media[2]=0x90;memcpy(media+3,"REPORT82",8);word(11,512);media[13]=1;media[16]=2;media[21]=0xf8;word(510,0xaa55);
 if(!fat32){memcpy(media+54,"FAT16   ",8);word(14,1);word(17,512);word(19,8192);word(22,32);root_sector=65;for(unsigned i=0;i<2;i++){word((1+i*32)*512,0xfff8);word((1+i*32)*512+2,0xffff);}}
 else {memcpy(media+82,"FAT32   ",8);word(14,32);dword(32,70000);dword(36,547);dword(44,2);word(48,1);root_sector=1126;
  for(unsigned i=0;i<2;i++){unsigned at=(32+i*547)*512;dword(at,0x0ffffff8);dword(at+4,0x0fffffff);dword(at+8,0x0fffffff);}
  dword(512,0x41615252);dword(512+484,0x61417272);dword(512+488,0xffffffff);dword(512+492,2);word(512+510,0xaa55);
 }
}
static unsigned rd16(const uint8_t *p){return p[0]|(unsigned)p[1]<<8;}
static uint32_t rd32(const uint8_t *p){return rd16(p)|(uint32_t)rd16(p+2)<<16;}
/* Independent inspection of committed card bytes, not a new firmware IO or
 * a FatFS cache read after the terminal releases RESET. */
static void inspect_saved(unsigned fat32){
 const uint8_t *dir=media+root_sector*512u;assert(!memcmp(dir,"HW084000TXT",11)&&rd32(dir+28)==3072);
 unsigned cluster=rd16(dir+26)|(fat32?rd16(dir+20)<<16:0),at=0;
 const char header[]="SDREPORT084-NATIVE077\nSTORAGE PAYLOAD; FILE ALONE DOES NOT PROVE SUCCESS\n";
 unsigned cluster_bytes=media[13]*512u;
 while(at<3072){
  assert(cluster>=2&&cluster<sectors);
  const uint8_t *data=media+((fat32?1126u:97u)+(cluster-2)*media[13])*512u;
  for(unsigned i=0;i<cluster_bytes&&at<3072;i++,at++){
   uint8_t expected=at<sizeof(header)-1?(uint8_t)header[at]:(at%64==63?'\n':'A'+at%26);
   assert(data[i]==expected);
  }
  cluster=fat32?rd32(media+32u*512+cluster*4)&0x0fffffff:rd16(media+512+cluster*2);
 }
 assert(cluster>=(fat32?0x0ffffff8:0xfff8));
}
static void assert_failed(void){
 assert(held&&nes_return_failed()&&!nvic.ISER[2]&&!nes_return_log_allowed());
 unsigned oldios=ios,oldio=io,oldcmd=commands,oldinit=init_commands;
 enum nes_diag_error first=nes_diag_status()->error;
 /* Reentry must retain the original fault and issue no more shared IO. */
 assert(!report_session084());
 assert(ios==oldios&&io==oldio&&commands==oldcmd&&init_commands==oldinit&&nes_diag_status()->error==first);
 checks++;
}
int main(void){
#ifdef _WIN32
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);_set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
 setvbuf(stdout,0,_IONBF,0);
 assert(legacy(cfgware,sizeof(cfgware),golden_mini,sizeof(golden_mini))==153544);
 assert(legacy(bootrle,sizeof(bootrle),golden_boot,sizeof(golden_boot))==65535);
 unsigned total[2]={0,0},total_io=0;
 for(unsigned fat32=0;fat32<2;fat32++)for(unsigned hc=0;hc<2;hc++){
  reset_case(fat32,hc);assert(report_session084());
  assert(!held&&!nes_return_failed()&&!nvic.ISER[2]&&!nes_return_log_allowed());
  assert(init_commands==17&&attempts==3&&rca==0x12340000&&ccs==hc&&disk_state==DISK_OK);
  assert(command_kind[1]==17&&command_stage[1]==1&&fatfs.fs_type==(fat32?FS_FAT32:FS_FAT16));
  assert(stage_mask==0x3fe&&release_mask==0x3fe&&marker_mask==7&&postinit==1&&sent==153544&&display_ticks==650);
  assert(!memcmp(rom,golden_boot,sizeof(rom))&&row(8,"TXT SAVED + READBACK OK"));
  assert(row(11,"/HW084000.TXT")&&row(13,"Save code: 0"));
  inspect_saved(fat32);checks++;
  printf("normal FAT%u %s init=%u native=%u read=%u write=%u sram=%u checkpoints=7\n",fat32?32:16,hc?"SDHC":"SDSC",init_commands,commands,read_commands,write_commands,io);
  if(hc){total[fat32]=commands;total_io=io;}
 }
 /* Occupied prefix reproduces083 exhaustion;084 scans before CREATE_NEW. */
 for(unsigned fat32=0;fat32<2;fat32++){
  reset_case(fat32,1);
  unsigned end=fat32?12000:7000;
  for(unsigned c=fat32?3:2;c<end;c++)for(unsigned f=0;f<2;f++){
   if(fat32)dword((32+f*547)*512+c*4,0x0fffffff);
   else word((1+f*32)*512+c*2,0xffff);
  }
  assert(report_session084());inspect_saved(fat32);
  assert(rd16(media+root_sector*512+26)==end);checks++;
  printf("occupied FAT%u first_cluster=%u native=%u ticks=%u\n",fat32?32:16,end,commands,display_ticks);
 }
 /* Multi-sector clusters: a report spans three clusters or fits in one. */
 for(unsigned csize=2;csize<=8;csize*=4){
  reset_case(0,1);sectors=csize==2?16384:60000;word(19,sectors);media[13]=csize;
  assert(report_session084());assert(fatfs.fs_type==FS_FAT16&&fatfs.csize==csize);
  inspect_saved(0);checks++;
 }
 /* No suitable contiguous extent: do not create a zero-byte file. */
 reset_case(0,1);
 for(unsigned c=2;c<8192;c+=2)for(unsigned f=0;f<2;f++)word((1+f*32)*512+c*2,0xffff);
 assert(!report_session084());assert(stage==1&&marker_mask==7&&!write_commands&&media[root_sector*512]==0);assert_failed();
 /* A late read error while scanning preserves the hint and performs no write. */
 reset_case(1,1);
 for(unsigned c=3;c<12000;c++)for(unsigned f=0;f<2;f++)dword((32+f*547)*512+c*4,0x0fffffff);
 fault=R1_BAD;fault_at=20;
 assert(!report_session084());assert(stage==1&&!write_commands&&fatfs.last_clust==2);assert_failed();
 /* Every command failure in a dense FAT32 session, including scan, allocation
  * and readback. Scan failures must not publish a hint or write a directory. */
 for(unsigned n=1;n<=116;n++){
  reset_case(1,1);
  for(unsigned c=3;c<12000;c++)for(unsigned f=0;f<2;f++)dword((32+f*547)*512+c*4,0x0fffffff);
  fault=R1_BAD;fault_at=n;assert(!report_session084());assert(commands==n);
  if(stage==1){assert(!write_commands&&media[root_sector*512]==0);if(marker_mask==7)assert(fatfs.last_clust==2);}
  assert_failed();
 }
 /* Root growth is explicitly outside the preflight hint guarantee. FatFS
  * starts a chain extension after root cluster2, ignoring last_clust. This
  * must remain bounded at CREATE (no report/data sector written). */
 reset_case(1,1);
 for(unsigned c=3;c<12000;c++)for(unsigned f=0;f<2;f++)dword((32+f*547)*512+c*4,0x0fffffff);
 for(unsigned i=0;i<16;i++){uint8_t *d=media+root_sector*512+i*32;memset(d,'X',11);d[0]='A'+i;d[11]=0x20;}
 assert(!report_session084());assert(stage==2&&!write_commands);assert_failed();
 /* End-of-volume hint wraps without treating tail and head as contiguous. */
 reset_case(1,1);dword(512+492,68874);assert(report_session084());inspect_saved(1);checks++;
 /* Every fast response failure position in the successful FAT16 session,
  * including its first mount CMD17, through writer and readback. */
 for(unsigned fat32=0;fat32<2;fat32++)for(unsigned n=1;n<=total[fat32];n++){
  reset_case(fat32,1);fault=R1_BAD;fault_at=n;assert(!report_session084());assert(commands==n);assert_failed();
 }
 for(unsigned f=END_BAD;f<=DATA_TIMEOUT;f++){
  if(f==READ_ALTER)continue; /* Logical compare failure keeps IO healthy. */
  reset_case(0,1);fault=f;fault_at=(f==READ_ALTER)?0:1;
  assert(!report_session084());assert_failed();
 }
 reset_case(0,1);fault=READ_ALTER;assert(report_session084());
 assert(!held&&!nes_return_failed()&&row(8,"TXT SAVE FAILED"));
 assert(row(13,"Save code: 7"));checks++;
 /* Cross-subsystem failure: boot, checkpoint and terminal SRAM positions. */
 for(unsigned n=1;n<=total_io;n++){
  reset_case(0,1);atfault=n;assert(!report_session084());assert(io==n);assert_failed();
 }
 for(unsigned s=2;s<=8;s++){
  reset_case(0,1);delay_stage=s;assert(!report_session084());assert(stage==s);assert_failed();
 }
 /* Read corruption of all post-boot screen writes, including every stage
  * and the terminal result. Boot ROM corruption remains covered by080. */
 for(unsigned n=565;n<=total_io;n+=2){
  reset_case(0,1);atcorrupt=n;assert(!report_session084());assert(io==n);assert_failed();
 }
 reset_case(0,1);stage_tick_cost=200;assert(!report_session084());assert(stage==6);assert_failed();
 reset_case(0,1);tick_origin=UINT32_MAX-100;assert(report_session084());inspect_saved(0);checks++;
 reset_case(0,1);fail_delay=1;assert(!report_session084());assert(!commands&&marker_mask==1&&io==569);assert_failed();
 reset_case(0,1);corrupt_at=3;corrupt_kind=1;assert(!report_session084());assert(!commands&&marker_mask==1&&io==569);assert_failed();
 reset_case(0,1);never_ready=1;slow_clock=1;assert(!report_session084());assert(!commands&&marker_mask==1&&io==569);assert_failed();
 reset_case(0,1);wp=1;assert(report_session084());assert(!held&&!write_commands&&row(8,"TXT SAVE FAILED"));checks++;
 reset_case(0,1);card=0;assert(!report_session084());assert(!commands&&marker_mask==1&&io==569);assert_failed();
 for(unsigned m=1;m<=7;m=m*2+1){reset_case(0,1);marker_delay_fail=m;assert(!report_session084());assert(marker_mask==m&&(m==7?commands==1:commands==0));assert_failed();}
 for(unsigned p=1;p<=4;p++){reset_case(0,1);pinfault=p;assert(!report_session084());assert(!commands&&!init_commands&&!marker_mask);assert_failed();}
 printf("PASS084 checks=%u physical=0 production_changed=1\n",checks);return 0;
}
