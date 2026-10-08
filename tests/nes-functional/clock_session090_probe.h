/* SPDX-License-Identifier: MIT */
/* GPIO response seam; real088 reader remains compiled separately. */
struct gpio088 gpio_b,gpio_ss;struct spi088 spi;
static unsigned clock_mode,clock_frames,clock_bit,clock_byte,clock_shift,clock_command;
static unsigned clock_ss,clock_sck,clock_mosi,clock_rx,clock_cycle,clock_extra;
static unsigned clock_status_fail,clock_done_fail,clock_marker,clock_delay_fail;
static uint8_t clock_packet[16],clock_raw[510856];
static uint64_t clock_us,clock_epoch;
static unsigned shared_checks,prewrite_checks,writer_checks;
bool __real_nes_return_io_step(void);
void __real_nes_return_log_allow(bool);
bool __wrap_nes_return_io_step(void){shared_checks++;return __real_nes_return_io_step();}
void __wrap_nes_return_log_allow(bool allow){
 if(allow)prewrite_checks=shared_checks;else if(nes_return_log_allowed())writer_checks=shared_checks-prewrite_checks;
 __real_nes_return_log_allow(allow);
}
static void clock_le(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(8*i));}
static void clock_capture(void){
 uint32_t seq=clock_mode==3?0:(uint32_t)((clock_us-clock_epoch)/1000000);
 uint32_t count=clock_mode==1?0:seq?1250000:0;
 memset(clock_packet,0,16);clock_packet[0]=clock_mode==4?0x86:0x87;
 clock_packet[1]=(uint8_t)((clock_mode==1?4:6)|(seq?1:0)|((clock_mode==1&&seq)||seq==1?8:0));
 if(clock_mode==2&&seq)clock_packet[1]|=8;
 clock_le(clock_packet+2,seq);clock_le(clock_packet+6,count);clock_le(clock_packet+10,8000000);clock_packet[14]=16;
}
void model_set(struct gpio088 *r,unsigned p,unsigned v){
 if(nes_return_failed())assert((r==&gpio_ss&&v)||(r==&gpio_b&&p==3&&!v));
 if(v)r->ODR|=1u<<p;else r->ODR&=~(1u<<p);
 if(r==&gpio_ss){assert(p==0);if(clock_ss&&!v){clock_bit=clock_byte=clock_shift=clock_command=0;clock_frames++;}clock_ss=v;return;}
 assert(r==&gpio_b&&(p==3||p==5));if(p==5){clock_mosi=v;return;}
 if(!clock_ss&&!clock_sck&&v){
  uint8_t answer=clock_byte==0?0:clock_command==0xcf?0x87:clock_command==0xc0&&clock_byte<=16?clock_packet[clock_byte-1]:0;
  clock_rx=(answer>>(7-clock_bit))&1;clock_shift=(clock_shift<<1)|clock_mosi;
  if(++clock_bit==8){clock_bit=0;if(!clock_byte){clock_command=clock_shift&255;if(clock_command==0xc0)clock_capture();}clock_byte++;clock_shift=0;}
 }
 clock_sck=v;
}
unsigned model_input(void){assert(!nes_return_failed()&&clock_cycle==2&&held&&!clock_ss&&clock_sck);return clock_rx;}
void model_cclk(void){assert(!nes_return_failed()&&clock_cycle==2);clock_extra++;}
void fpga_set_cclk(uint8_t n){assert(!n);}
static void reset_clock090(void){
 clock_mode=clock_frames=clock_bit=clock_byte=clock_shift=clock_command=clock_sck=clock_mosi=clock_rx=0;clock_ss=1;
 clock_cycle=clock_extra=clock_status_fail=clock_done_fail=clock_marker=clock_delay_fail=0;
 clock_us=clock_epoch=0;shared_checks=prewrite_checks=writer_checks=0;
 memset(&gpio_b,0,sizeof(gpio_b));memset(&gpio_ss,0,sizeof(gpio_ss));spi.CR1=0x345;spi.SR=SPI_SR_TXE;
}
