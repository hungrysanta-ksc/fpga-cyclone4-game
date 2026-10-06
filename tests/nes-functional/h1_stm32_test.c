/* SPDX-License-Identifier: MIT */
/* Runs the production GPIO binding and unchanged034 session against a pin-level
 * SPI device model. This is not a STM32 or FPGA hardware execution. */
#include <assert.h>
#include <string.h>
#include "h1_stm32_mock.h"
#include "../../src/nes/firmware/nes_h1_stm32.c"
mock_gpio port_a,port_b;
mock_spi spi_1;
unsigned file_res;
const uint8_t *fpga_config;
static bool held,active,selected,reset_seen,usb_enabled;
static uint32_t expected_mode;
static unsigned configs,releases,stops,arms,polls,checks,bits,command_byte;
static unsigned fail_h1,fail_base,wrong_id,status_fault,no_id,busy,base_bad;
static unsigned value,reply,epoch;
static uint64_t now_us,last_rise,last_fall,ss_at,last_ss_end;
static unsigned edge_count;
static const uint32_t original_mode=0xa5aaaaaa,original_output=0x55aa553f;
static const uint32_t original_cr1=0x0344;
static FILE *trace;

unsigned NVIC_GetEnableIRQ(int irq){assert(irq==67);return usb_enabled;}
void NVIC_DisableIRQ(int irq){assert(irq==67);usb_enabled=false;}
void NVIC_EnableIRQ(int irq){
 assert(irq==67 && held && !gpio_owned && checks==1);usb_enabled=true;
}
static unsigned response(unsigned c) {
 switch(c) {
 case 0xf0:return no_id?0:0xa5;
 case 0xf1:return wrong_id?0x35:0x34;
 case 0xf2:return active?(status_fault && polls>=1?6:3):2;
 case 0xf3:return epoch & 255;
 case 0xf4:return epoch>>8;
 default:return 0;
 }
}
void pin_write(mock_gpio *p,unsigned b,bool high) {
 bool before=(p->ODR & (1u<<b))!=0;
 if(high)p->ODR|=1u<<b;else p->ODR&=~(1u<<b);
 if(before==high)return;
 if(p==&port_a && b==4) {
  if(!high) {
   assert(!selected && !(port_b.ODR & (1u<<3)));
   assert(now_us-last_ss_end>=1);
   assert(!(spi_1.CR1 & SPI_CR1_SPE));
   assert((port_b.MODER&H1_MODE_MASK)==((1u<<6)|(1u<<10)));
   selected=true;bits=value=command_byte=0;ss_at=now_us;
  } else if(selected) {
   assert(bits==16 || bits==24);
   assert(now_us-last_rise>=1 && !(port_b.ODR & (1u<<3)));
   if(command_byte==0xe8 || command_byte==0xe9) {
    assert(bits==24 && (value & 65535)==0xa55a && held);
    if(command_byte==0xe8){active=true;epoch++;arms++;}
    else {active=false;stops++;}
   }
   if(trace)fprintf(trace,"%llu\t%02x\t%06x\t%u\n",
       (unsigned long long)now_us,command_byte,value,bits);
   selected=false;last_ss_end=now_us;
  }
 }
 if(p==&port_b && b==3 && selected) {
  if(high) {
   assert(now_us-ss_at>=1);
   if(bits) {
    assert(now_us-last_rise>=4);
    assert(now_us-last_fall>=2);
    if(!(bits%8))assert(now_us-last_fall>=3);
   }
   last_rise=now_us;edge_count++;
   value=(value<<1)|((port_b.ODR>>5)&1u);
   unsigned bit=bits%8;
   port_b.IDR=(port_b.IDR & ~(1u<<4))|(((reply>>(7-bit))&1u)<<4);
   bits++;
   if(bits==8){command_byte=value;reply=response(command_byte);}
  } else {
   assert(now_us-last_rise>=2);last_fall=now_us;
  }
 }
}
void delay_us(unsigned us){assert(us>0);now_us+=us;}
void delay_ms(unsigned ms){assert(ms>0);now_us+=(uint64_t)ms*1000;}
void snes_reset(unsigned asserted) {
 held=asserted!=0;
 if(!held){assert(active && epoch && gpio_owned);releases++;}
}
unsigned get_snes_reset(void) {
 assert(!held && !usb_enabled);polls++;
 if(polls==1){port_b.MODER^=1u<<24;expected_mode^=1u<<24;}
 reset_seen=polls>=3;
 return reset_seen;
}
void fpga_pgm(uint8_t *image) {
 assert(held && !gpio_owned && !usb_enabled);configs++;
 bool is_base=strcmp((const char *)image,(const char *)FPGA_BASE)==0;
 file_res=(is_base?fail_base:fail_h1);
 if(!file_res){fpga_config=image;active=false;epoch=0;}
 if(is_base) {
  assert((port_b.MODER&H1_MODE_MASK)==(original_mode&H1_MODE_MASK));
  assert((port_b.ODR&H1_OUT_MASK)==(original_output&H1_OUT_MASK));
  assert(spi_1.CR1==original_cr1);
  /* Simulate unrelated pin configuration during H1; binding must preserve it. */
  assert(port_b.MODER==expected_mode);
 }
}
int fpga_get_done(void){return 1;}
unsigned fpga_test(void) {
 assert(held && !gpio_owned && !selected);
 assert(strcmp((const char *)fpga_config,(const char *)FPGA_BASE)==0);
 assert(!busy);checks++;return base_bad?0:0xa5;
}
static void setup(void) {
 assert(!gpio_owned);
 port_a=(mock_gpio){0,1u<<4,0};
 port_b=(mock_gpio){original_mode,original_output,0};
 spi_1=(mock_spi){original_cr1,SPI_SR_TXE};
 held=active=selected=reset_seen=false;
 configs=releases=stops=arms=polls=checks=bits=command_byte=0;
 fail_h1=fail_base=wrong_id=status_fault=no_id=busy=base_bad=0;
 value=reply=epoch=edge_count=0;now_us=100;last_ss_end=last_rise=last_fall=ss_at=0;
 fpga_config=FPGA_BASE;file_res=0;usb_enabled=true;expected_mode=original_mode;
}
int main(int argc,char **argv) {
 assert(argc==2);trace=fopen(argv[1],"w");assert(trace);
 setup();assert(nes_h1_run());assert(held && reset_seen);
 assert(configs==2 && arms==1 && stops==1 && releases==1 && checks==1 && usb_enabled);
 printf("PASS normal RESET/menu restoration, %u timed SCK edges\n",edge_count);
 setup();assert(nes_h1_run());assert(arms==1 && stops==1);puts("PASS re-entry");
 setup();fail_h1=1;assert(nes_h1_run());assert(!releases && !arms && !stops);
 puts("PASS missing H1 image restores base under RESET");
 setup();wrong_id=1;assert(nes_h1_run());assert(!releases && !arms && stops==1);
 puts("PASS wrong protocol ID fail closed");
 setup();no_id=1;assert(nes_h1_run());assert(!releases && stops==1);
 puts("PASS bounded missing identity");
 setup();busy=1;spi_1.SR|=SPI_SR_BSY;assert(!nes_h1_run());
 assert(!releases && !checks && held && now_us==1100);
 puts("PASS stuck hardware SPI bounded rejection");
 setup();status_fault=1;assert(nes_h1_run());assert(releases==1 && stops==1 && !reset_seen);
 puts("PASS running status fault stops and restores");
 setup();fail_base=1;assert(!nes_h1_run());assert(held && !gpio_owned && !checks && !usb_enabled);
 puts("PASS missing base keeps RESET asserted");
 setup();base_bad=1;assert(!nes_h1_run());assert(held && checks==1);
 puts("PASS invalid base token keeps RESET asserted");
 setup();usb_enabled=false;assert(nes_h1_run());assert(!usb_enabled);
 puts("PASS pre-disabled USB IRQ remains disabled");
 const char *yes[]={"/test.nh1","/test.NH1","/a.b.nH1"};
 const char *no[]={"","a","a.","a.n","a.nh","a.nh12","/a.nh1/game.sfc","game.egbc","game.nes"};
 for(unsigned i=0;i<sizeof(yes)/sizeof(*yes);i++)assert(nes_h1_is_marker((const uint8_t *)yes[i]));
 for(unsigned i=0;i<sizeof(no)/sizeof(*no);i++)assert(!nes_h1_is_marker((const uint8_t *)no[i]));
 puts("PASS marker boundary cases");
 fclose(trace);return 0;
}
