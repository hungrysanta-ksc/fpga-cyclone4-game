/* SPDX-License-Identifier: MIT */
#include "nes_clock_report090.h"
static void format_boundaries090(void){
 struct clock_report088 r={0};r.result=CLOCK088_ACTIVE;r.captured=2;
 r.started=r.elapsed=r.attempts=r.frames=UINT32_MAX;
 memset(r.initial,255,16);memset(r.sample,255,sizeof(r.sample));
 char full[3072];unsigned length=clock_text090(full,sizeof(full),&r);assert(length&&length<3072);
 unsigned char guarded[3074];
 for(unsigned size=1;size<=length+2;size++){
  memset(guarded,0xA5,sizeof(guarded));unsigned n=clock_text090((char *)guarded+1,size,&r);
  assert(guarded[0]==0xA5&&guarded[size+1]==0xA5);
  if(size<=length)assert(!n&&guarded[1]==0);else assert(n==length&&!memcmp(guarded+1,full,length+1));
 }
 assert(!clock_text090(0,3072,&r)&&!clock_text090(full,0,&r)&&!clock_text090(full,sizeof(full),0));
 r.captured=3;assert(!clock_text090(full,sizeof(full),&r));r.captured=0;r.result=CLOCK088_IO_ERROR;assert(!clock_text090(full,sizeof(full),&r));
 checks++;
}
static unsigned rd16(const uint8_t *p){return p[0]|(unsigned)p[1]<<8;}
static uint32_t rd32(const uint8_t *p){return rd16(p)|(uint32_t)rd16(p+2)<<16;}
static void inspect090(unsigned fat32,unsigned save){
 const uint8_t *dir=media+root_sector*512;assert(!memcmp(dir,"HW090000TXT",11));
 unsigned size=rd32(dir+28);assert(size>600&&size<3072);
 unsigned cluster=rd16(dir+26)|(fat32?rd16(dir+20)<<16:0),at=0;char text[3072];
 while(at<size){
  assert(cluster>=2&&cluster<sectors);const uint8_t *d=media+((fat32?1126u:97u)+(cluster-2)*media[13])*512u;
  for(unsigned i=0;i<media[13]*512u&&at<size;i++)text[at++]=(char)d[i];
  cluster=fat32?rd32(media+32u*512+cluster*4)&0x0fffffff:rd16(media+512+cluster*2);
 }
 assert(cluster>=(fat32?0x0ffffff8:0xfff8));text[size]=0;
 const char *labels[]={"RESULT: CLOCK ACTIVE\n","RESULT: CLOCK ABSENT\n","RESULT: CLOCK UNSTABLE\n","RESULT: NO CLOCK PROGRESS\n"};
 assert(clock_mode<4&&strstr(text,labels[clock_mode]));
 assert(!strncmp(text,"CLOCKREPORT090 / FPGA CF87",24));
 assert(strstr(text,"CLKIN_ASSUMED_HZ: 8000000 (not measured)"));
 assert(strstr(text,"FILE ALONE DOES NOT PROVE SAVE SUCCESS"));
 if(clock_mode==3){assert(strstr(text,"CAPTURED_WINDOWS: 0"));assert(strstr(text,"SAMPLE1 RAW: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"));}
 else {
  assert(strstr(text,"CAPTURED_WINDOWS: 2"));
  assert(strstr(text,"SEQUENCE: 2; COUNT:")&&strstr(text,"SEQUENCE: 3; COUNT:"));
  assert(strstr(text,clock_mode==1?"SEQUENCE: 2; COUNT: 0;":"SEQUENCE: 2; COUNT: 1250000;"));
 }
 if(save){char name[64];snprintf(name,sizeof(name),"saved-mode%u-fat%u-hc%u.txt",clock_mode,fat32,high_capacity);FILE *f=fopen(name,"wb");assert(f&&fwrite(text,1,size,f)==size);fclose(f);}
}
static void failed090(void){
 assert(held&&nes_return_failed()&&!nvic.ISER[2]&&!nes_return_log_allowed());
 unsigned oldio=io,oldcmd=commands,oldinit=init_commands,oldcycle=clock_cycle,oldsent=sent;
 enum nes_diag_error first=nes_diag_status()->error;
 assert(!report_session090());
 assert(io==oldio&&commands==oldcmd&&init_commands==oldinit&&clock_cycle==oldcycle&&sent==oldsent&&nes_diag_status()->error==first);checks++;
}
int main(void){
#ifdef _WIN32
 SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX);_set_error_mode(_OUT_TO_STDERR);_set_abort_behavior(0,_WRITE_ABORT_MSG|_CALL_REPORTFAULT);
#endif
 setvbuf(stdout,0,_IONBF,0);FILE *f=fopen("clock087.rbf","rb");assert(f&&fread(clock_raw,1,sizeof(clock_raw),f)==sizeof(clock_raw)&&fgetc(f)==EOF);fclose(f);
 assert(legacy(cfgware,sizeof(cfgware),golden_mini,sizeof(golden_mini))==153544);
 assert(legacy(bootrle,sizeof(bootrle),golden_boot,sizeof(golden_boot))==65535);
 format_boundaries090();unsigned totals[2]={0,0},lastio=0;
 for(unsigned kind=0;kind<4;kind++)for(unsigned fat32=0;fat32<2;fat32++)for(unsigned hc=0;hc<2;hc++){
  reset_case(fat32,hc);clock_mode=kind;assert(report_session090());
  assert(!held&&!nes_return_failed()&&!nvic.ISER[2]&&!nes_return_log_allowed()&&clock_cycle==3&&postinit==3);
  assert(init_commands==17&&marker_mask==7&&clock_marker==1&&stage_mask==0x3fe&&release_mask==0x3fe);
  assert(prewrite_checks<1000000&&writer_checks<10000&&row(8,"TXT SAVED + READBACK OK")&&row(11,"/HW090000.TXT")&&row(13,"Save code: 0"));
  assert(!memcmp(rom,golden_boot,sizeof(rom)));inspect090(fat32,1);checks++;
  printf("NORMAL090 mode=%u FAT%u hc=%u prewrite=%u writer=%u native=%u sram=%u tick=%u\n",kind,fat32?32:16,hc,prewrite_checks,writer_checks,commands,io,nes_diag_ticks());
  if(kind==0&&hc){totals[fat32]=commands;lastio=io;}
 }
 /* Real scan/allocation on a dense FAT32 after the longest normal observation. */
 reset_case(1,1);clock_mode=3;
 for(unsigned c=3;c<12000;c++)for(unsigned i=0;i<2;i++)dword((32+i*547)*512+c*4,0x0fffffff);
 assert(report_session090());inspect090(1,0);assert(rd16(media+root_sector*512+26)==12000&&prewrite_checks<1000000);checks++;
 printf("DENSE090 no_progress prewrite=%u writer=%u native=%u\n",prewrite_checks,writer_checks,commands);
 for(unsigned fat32=0;fat32<2;fat32++)for(unsigned n=1;n<=totals[fat32];n++){
  reset_case(fat32,1);fault=R1_BAD;fault_at=n;assert(!report_session090()&&commands==n);failed090();
 }
 const unsigned points[]={1,2,562,563,568,569,570,571,580,900,1126,1130};
 for(unsigned i=0;i<sizeof(points)/sizeof(points[0]);i++){reset_case(0,1);atfault=points[i];assert(!report_session090()&&io==atfault);failed090();}
 for(unsigned n=lastio-10;n<=lastio;n++){reset_case(0,1);atfault=n;assert(!report_session090()&&io==n);failed090();}
 for(unsigned n=2;n<=8;n++){reset_case(0,1);delay_stage=n;assert(!report_session090()&&stage==n);failed090();}
 for(unsigned n=1;n<=8;n=n==1?3:n==3?7:n==7?8:9){reset_case(0,1);marker_delay_fail=n;assert(!report_session090());failed090();}
 reset_case(0,1);clock_mode=4;assert(!report_session090()&&!commands&&!init_commands&&clock_cycle==2);failed090();
 reset_case(0,1);clock_status_fail=256;assert(!report_session090()&&!commands&&!init_commands&&sent==256);failed090();
 reset_case(0,1);clock_done_fail=1;assert(!report_session090()&&!commands&&!init_commands);failed090();
 reset_case(0,1);clock_delay_fail=1;assert(!report_session090()&&!commands&&!init_commands);failed090();
 reset_case(0,1);card=0;assert(!report_session090()&&!commands&&clock_cycle==3);failed090();
 reset_case(0,1);corrupt_at=3;corrupt_kind=1;assert(!report_session090()&&!commands);failed090();
 reset_case(0,1);fault=READ_ALTER;assert(report_session090()&&row(8,"TXT SAVE FAILED")&&row(13,"Save code: 7")&&!nes_return_failed());checks++;
 reset_case(0,1);wp=1;assert(report_session090()&&!write_commands&&row(8,"TXT SAVE FAILED"));checks++;
 reset_case(0,1);tick_origin=UINT32_MAX-100;assert(report_session090());inspect090(0,0);checks++;
 printf("PASS CLOCK_SESSION090 checks=%u physical=0\n",checks);return 0;
}
