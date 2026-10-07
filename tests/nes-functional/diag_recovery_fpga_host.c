/* SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "nes_diag_runtime.h"
typedef unsigned UINT,FRESULT;
typedef struct {unsigned size,pos;} FIL;
#define FR_OK 0u
#define FR_DISK_ERR 1u
#define FA_READ 1u
#define f_size(f) ((f)->size)
#define RLE_ESC 0x9b
#define RLE_RUN 0x5b
#define RLE_RUNLONG 0x77
static const uint8_t *input;
static unsigned input_length,advertised,opens,closes,reads,produced,post,mask,prog;
static uint8_t output[2100000];
static uint32_t now,tick_step;
static unsigned fault;
enum {OK,OPEN,READ,CLOSE,PROG,INIT,DONE_HIGH,DONE_LOW,LIMIT};
static const uint8_t *fpga_config;
static unsigned gbc_spi_pacing;
static FRESULT file_res;
#define FPGA_PROGBREG 0
#define FPGA_PROGBBIT 0
#define BITBAND(a,b) (fault==PROG?1u:prog)
#define FPGA_DIN_MASK() (++mask)
#define FPGA_DIN_UNMASK() (--mask)
static void send_byte(uint8_t value){assert(mask&&produced<sizeof(output));output[produced++]=value;}
#define FPGA_SEND_BYTE_SERIAL(v) send_byte(v)
#define CCLK() ((void)0)
static void fpga_init(void){prog=1;}
static void fpga_set_prog_b(unsigned value){prog=value;}
static unsigned fpga_get_initb(void){return fault!=INIT;}
static unsigned fpga_get_done(void){return fault==DONE_HIGH?1:fault==DONE_LOW?0:produced>0;}
static void fpga_postinit(void){post++;}
static FRESULT f_open(FIL *f,const char *p,unsigned mode){assert(p&&mode==FA_READ);opens++;*f=(FIL){advertised,0};return fault==OPEN?1:0;}
static FRESULT f_read(FIL *f,void *p,UINT n,UINT *got){reads++;if(fault==READ){*got=0;return 1;}*got=input_length-f->pos;if(*got>n)*got=n;memcpy(p,input+f->pos,*got);f->pos+=*got;return 0;}
static FRESULT f_close(FIL *f){(void)f;closes++;return fault==CLOSE?1:0;}
uint32_t nes_diag_ticks(void){now+=tick_step;return now;}
void nes_diag_observe(const struct nes_diag_report *r,bool a){(void)r;(void)a;}
#include "nes_diag_fpga.inc"
static void setup(const uint8_t *p,unsigned n,unsigned fail,uint32_t step){input=p;input_length=advertised=n;fault=fail;now=0;tick_step=step;opens=closes=reads=produced=post=mask=0;fpga_config=(const uint8_t *)"old";nes_diag_begin();}
int main(void){
 unsigned cases=0;
 const uint8_t golden[]={0xaa,RLE_ESC,RLE_RUN,RLE_RUN,0x23,3,RLE_RUNLONG,0x45,0,1,0xbb};
 setup(golden,sizeof(golden),OK,0);assert(nes_diag_fpga_pgm((const uint8_t *)"fixture"));
 assert(produced==262&&output[0]==0xaa&&output[1]==RLE_RUN&&output[261]==0xbb);
 for(unsigned n=2;n<5;n++)assert(output[n]==0x23);
 for(unsigned n=5;n<261;n++)assert(output[n]==0x45);
 assert(opens==1&&closes==1&&post==1&&!mask&&file_res==FR_OK);cases++;
 const uint8_t single[]={0xaa};
 const unsigned failures[]={OPEN,READ,CLOSE,PROG,INIT,DONE_HIGH,DONE_LOW};
 const enum nes_diag_error errors[]={NES_DIAG_FPGA_OPEN,NES_DIAG_FPGA_READ,NES_DIAG_FPGA_CLOSE,NES_DIAG_FPGA_PROG,NES_DIAG_FPGA_INIT,NES_DIAG_FPGA_DONE,NES_DIAG_FPGA_DONE};
 for(unsigned n=0;n<7;n++){
  printf("FPGA fault=%u\n",failures[n]);fflush(stdout);
  setup(single,1,failures[n],1);assert(!nes_diag_fpga_pgm((const uint8_t *)"fixture"));
  assert(nes_diag_status()->error==errors[n]&&opens==1&&closes==(failures[n]!=OPEN)&&!post&&!mask);cases++;
 }
 const uint8_t malformed[][4]={{RLE_ESC},{RLE_RUN,0xaa},{RLE_RUN,0xaa,0},{RLE_RUNLONG,0xaa,1},{RLE_RUNLONG,0xaa,0,0}};
 const unsigned sizes[]={1,2,3,3,4};
 for(unsigned n=0;n<5;n++){
  setup(malformed[n],sizes[n],OK,0);assert(!nes_diag_fpga_pgm((const uint8_t *)"fixture"));
  assert(nes_diag_status()->error==NES_DIAG_FPGA_FORMAT&&closes==1&&!mask&&!post);cases++;
 }
 setup(single,1,OK,0);advertised=0;assert(!nes_diag_fpga_pgm((const uint8_t *)"fixture")&&nes_diag_status()->error==NES_DIAG_FPGA_LIMIT);cases++;
 setup(single,1,OK,0);advertised=1048577;assert(!nes_diag_fpga_pgm((const uint8_t *)"fixture")&&nes_diag_status()->error==NES_DIAG_FPGA_LIMIT);cases++;
 setup(single,1,OK,0);advertised=2;assert(!nes_diag_fpga_pgm((const uint8_t *)"fixture")&&nes_diag_status()->error==NES_DIAG_FPGA_FORMAT);cases++;
 setup(single,1,INIT,0);assert(!nes_diag_fpga_pgm((const uint8_t *)"fixture")&&nes_diag_status()->error==NES_DIAG_FPGA_INIT);cases++;
 uint8_t huge[132];for(unsigned n=0;n<sizeof(huge);n+=4){huge[n]=RLE_RUNLONG;huge[n+1]=0xaa;huge[n+2]=huge[n+3]=255;}
 setup(huge,sizeof(huge),OK,0);assert(!nes_diag_fpga_pgm((const uint8_t *)"fixture")&&nes_diag_status()->error==NES_DIAG_FPGA_LIMIT&&produced==2097152u&&!mask);cases++;
 setup(golden,sizeof(golden),OK,1000);assert(!nes_diag_fpga_pgm((const uint8_t *)"fixture")&&nes_diag_status()->error==NES_DIAG_FPGA_LIMIT);cases++;
 now=UINT32_MAX-2;tick_step=0;struct nes_diag_wait w=nes_diag_wait_start(5,8);
 now=1;assert(nes_diag_wait_step(&w));now=2;assert(!nes_diag_wait_step(&w));cases++;
 w=nes_diag_wait_start(100,2);assert(nes_diag_wait_step(&w)&&nes_diag_wait_step(&w)&&!nes_diag_wait_step(&w));cases++;
 nes_diag_begin();nes_diag_fail(NES_DIAG_SD_BUSY);nes_diag_fail(NES_DIAG_FPGA_OPEN);assert(nes_diag_status()->error==NES_DIAG_SD_BUSY);nes_diag_leave();assert(!nes_diag_active());cases++;
 printf("PASS RECOVERY064 FPGA cases=%u frozen_tick=1 wrap=1 retries=0\n",cases);return 0;
}
