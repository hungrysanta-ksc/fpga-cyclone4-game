/* SPDX-License-Identifier: GPL-2.0-only */
/* Card state transitions are decoded from the wire. No disk_state shortcut
 * switches between slow initialization and native block transfer models. */
static uint8_t csd[17],cid[17];
static uint32_t rca;
static diskinfo0_t di;
static unsigned init_response_pos,init_response_len,init_cmd_bits,init_command;
static unsigned init_busy_clocks,init_clk,init_complete,fast_mode;
static unsigned cmdlevel,cmdout,cmdclocks,attempts,assigned,ios;
static unsigned log_commands[5000],log_count;
static unsigned corrupt_at,corrupt_kind,timeout_at,never_ready,never_unbusy;
static uint8_t init_response[17],init_wire[6];
static uint8_t model_crc(const uint8_t *p,unsigned n){
 unsigned r=0;for(unsigned i=0;i<n*8;i++){
  unsigned feedback=((r>>6)^((p[i/8]>>(7-i%8))&1))&1;
  r=((r<<1)&127)^(feedback?9:0);
 }return (uint8_t)((r<<1)|1);
}
#include "slow-model.inc"
static void dispatch_set(unsigned p,unsigned v){
 assert(!nes_return_failed()&&held&&!nvic.ISER[2]);
 if(fast_mode){ios++;set_pin(p,v);}else init_set_pin(p,v);
}
static unsigned dispatch_input(unsigned p){
 assert(!nes_return_failed()&&held&&!nvic.ISER[2]);
 return fast_mode?input(p):init_read_pin(p);
}
static void dispatch_mode(unsigned p,unsigned out){
 assert(!nes_return_failed()&&held&&!nvic.ISER[2]);
 if(!fast_mode&&init_complete&&p==CMD&&out){
  assert(init_response_pos>=56&&init_command==16&&init_commands==17);
  fast_mode=1;level=init_clk;
 }
 if(fast_mode){ios++;if(out)mode_out(p);else mode_in(p);}
 else init_mode_pin(p,out);
}
