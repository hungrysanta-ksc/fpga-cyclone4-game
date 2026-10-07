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
int main(int argc,char **argv){
 assert(argc==3);static uint8_t packed[1048576],raw[2097152];
 FILE *f=fopen(argv[1],"rb");assert(f);unsigned pn=fread(packed,1,sizeof(packed),f);assert(feof(f)&&!ferror(f)&&!fclose(f));
 f=fopen(argv[2],"rb");assert(f);unsigned rn=fread(raw,1,sizeof(raw),f);assert(feof(f)&&!ferror(f)&&!fclose(f));
 setup(packed,pn,OK,0);assert(nes_diag_fpga_pgm((const uint8_t *)"actual-candidate"));
 assert(produced==rn&&!memcmp(output,raw,rn));assert(closes==1&&post==1&&!mask&&file_res==FR_OK);
 printf("PASS PAIR066 actual programmer compressed=%u raw=%u all_bytes=1 no_retry=1\n",pn,rn);return 0;
}
