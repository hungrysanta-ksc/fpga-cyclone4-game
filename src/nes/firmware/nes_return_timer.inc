/* SPDX-License-Identifier: MIT */
bool nes_return_delay(unsigned time,bool milliseconds) {
 if(nes_return_failed())return false;
 uint64_t count=(uint64_t)(CONFIG_CPU_FREQUENCY/(milliseconds?1000u:1000000u))*time;
 if(count>UINT32_MAX){nes_return_fail(NES_DIAG_TIMER);return false;}
 uint32_t ticks=(uint32_t)(((uint64_t)time+(milliseconds?9u:9999u))/(milliseconds?10u:10000u)+2u);
 uint64_t polls=count+100000u;if(polls>UINT32_MAX)polls=UINT32_MAX;
 struct nes_diag_wait wait=nes_diag_wait_start(ticks,(uint32_t)polls);
 BITBAND(TIM2->SR,TIM_SR_UIF_Pos)=0;
 TIM2->CNT=(uint32_t)count;
 TIM2->CR1=TIM_CR1_URS|TIM_CR1_DIR|TIM_CR1_CEN;
 bool ok=true;
 while(!BITBAND(TIM2->SR,TIM_SR_UIF_Pos)){
  if(!nes_diag_wait_step(&wait)){ok=false;nes_return_fail(NES_DIAG_TIMER);break;}
 }
 BITBAND(TIM2->SR,TIM_SR_UIF_Pos)=0;TIM2->CR1=0;
 return ok;
}
