/* SPDX-License-Identifier: MIT */
static void check_nmi109(void){
 assert(nmi109&&masked109&&nes_css_fault108()==(css_case109==12?2u:1u));
 assert(!irq&&reset_held&&(mock_a.MODER&3)==1&&!(mock_a.ODR&3)&&!done);
 assert((mock_a.ODR&16)&&((mock_a.MODER>>8)&3)==1);
 assert(!(mock_b.ODR&40)&&!(mock_b.OTYPER&40)&&!(mock_a.OTYPER&16));
 assert(((mock_b.MODER>>6)&3)==1&&((mock_b.MODER>>10)&3)==1&&((mock_b.MODER>>8)&3)==0);
 assert(!mock_spi.CR1&&!mock_spi.CR2&&(RCC->APB2RSTR&RCC_APB2RSTR_SPI1RST));
 assert((RCC->CIR&0x7f00u)==0x3500&&!(RCC->CIR&RCC_CIR_CSSF));
 assert(stores109==13); /* NVIC store is represented by NVIC_DisableIRQ, not this seam. */
 assert(card_commands096()==fault_cmd109&&card_edges096()==fault_edge109&&configs==fault_config109&&config_bytes096==fault_byte109&&frames==fault_frame109&&tx100==fault_tx109&&uart_reads103==fault_uart109);
 nes_return_reset();assert(nes_return_failed());
 assert(!nes_css_begin108()&&!nes_css_end108());
 assert(!nes_menu_diagnostic_run((const uint8_t*)"NES VERIFY 094 80.nh1"));
 assert(card_commands096()==fault_cmd109&&card_edges096()==fault_edge109&&configs==fault_config109&&tx100==fault_tx109&&uart_reads103==fault_uart109);
 fprintf(stdout,"PASS109 CSS case=%u command=%u config=%u byte=%u frames=%u copied=%u released_before_fault=%u stores=%u\n",css_case109,fault_cmd109,configs,config_bytes096,frames,menu_bytes098,release097,stores109);
}
static void check_reject109(void){
 unsigned commands=card_commands096(),edges=card_edges096();
 assert(!nes_menu_diagnostic_run((const uint8_t*)"NES VERIFY 094 80.nh1"));
 assert(!css_on109&&!nes_css_fault108()&&nes_return_failed()&&!irq&&reset_held&&!configs&&!release097);
 assert(card_commands096()==commands&&card_edges096()==edges);
 assert(!!(RCC->CR&RCC_CR_CSSON)==(css_case109==22));
 fprintf(stdout,"PASS109 CSS reject=%u before file IO\n",css_case109);
}
