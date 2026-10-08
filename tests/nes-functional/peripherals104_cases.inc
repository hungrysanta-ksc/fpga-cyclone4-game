/* SPDX-License-Identifier: MIT */
extern volatile enum diskstates disk_state;
static void run_units104(unsigned mode){
 irq=0;reset_held=1;mock_a.IDR&=~1u;begin_lower100(0);init102();
 nes_return_reset();nes_diag_sd_reset();nes_diag_begin();timer_polls104=0;
 timer_harness_limit104=200000u;
 if(mode<10){
  timer_stall104=mode==1||mode==2||mode==7;tick_freeze104=mode==1||mode==7;
  if(mode==3){assert(!nes_return_delay(UINT32_MAX,true)&&!timer_started104);}
  else if(mode==4){nes_return_fail(NES_DIAG_SPI);unsigned old=timer_polls104;delay_us(1);delay_ms(1);assert(timer_polls104==old);}
  else if(mode==5){nes_diag_leave();delay_us(1);assert(!nes_return_failed());}
  else if(mode==6){nes_diag_leave();delay_ms(1);assert(!nes_return_failed());}
  else if(mode==7){delay_ms(0);assert(nes_return_failed());}
  else if(mode==8){ticks=UINT32_MAX-1;assert(nes_return_delay(1,false));}
  else if(mode==9){assert(nes_return_delay(0,false));}
  else {delay_us(1);assert(nes_return_failed()==(mode!=0));}
  if(nes_return_failed()){check_quiesce102();assert(nes_diag_status()->error==(mode==4?NES_DIAG_SPI:NES_DIAG_TIMER));}
  assert(!TIM2->CR1&&!timer_alias104);
 }else if(mode==10){
  mock_a.IDR&=~1u;assert(get_snes_reset()==1);
  for(unsigned i=0;i<8;i++)SysTick_Handler();
  assert(reset_changed&&reset_pressed&&((mock_c.MODER&3)==1)&&(mock_c.ODR&1));
  reset_changed=0;CFG.pair_mode_allowed=1;mock_a.IDR|=1u;assert(get_snes_reset()==0);
  for(unsigned i=0;i<8;i++)SysTick_Handler();
  assert(reset_changed&&!reset_pressed&&!(mock_c.ODR&1));
 }else if(mode==11){
  for(unsigned i=0;i<20;i++)SysTick_Handler();
  card_present096(0);for(unsigned i=0;i<13;i++)SysTick_Handler();assert(disk_state==DISK_REMOVED&&!sd_changed);
  card_present096(1);for(unsigned i=0;i<13;i++)SysTick_Handler();assert(disk_state==DISK_CHANGED&&!sd_changed);
 }else if(mode<20){
  const unsigned budgets[]={0,10,11,1000,1001,999,0,100000};
  cic_override104=1;cic_budget104=budgets[mode-12];cic_level104=mode!=18;
  unsigned expected=cic_budget104>1000?CIC_PAIR:cic_budget104>10?CIC_SCIC:(cic_level104^(cic_budget104&1)?CIC_OK:CIC_FAIL);
  unsigned n=cic_reads104;assert(get_cic_state()==expected&&cic_reads104-n==100001);
 }else{
  disk_state=DISK_OK;
  inject_uart104=1;uart_target104=mode-20;uart_count104=0;
  int n=diag_printf("IRQ104 %lu %lu abcdefghijklmnop\n",1234567890ul,4294967295ul);
  assert(n==(int)strlen("IRQ104 1234567890 4294967295 abcdefghijklmnop\n"));
  assert(irq_calls104==1&&!uart_irq104&&!sd_changed&&disk_state==DISK_CHANGED);
 }
 fprintf(stdout,"PASS104 unit=%u timerpoll=%u IRQ=%u CICreads=%u fault=%u\n",mode,timer_polls104,irq_calls104,cic_reads104,nes_diag_status()->error);
}
