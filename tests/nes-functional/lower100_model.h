/* SPDX-License-Identifier: MIT */
/* Byte-level base FPGA responder, SPI flags/DR and CS model. Not RTL/timing. */
static unsigned lower_active100,mode100,unit100,cs100=1,op100,pos100,addr100;
static unsigned tx100,drreads100,select100,deselect100,memwrites100,memreads100;
static unsigned failed_tx100,failed_select100,failed_reads100,failed_seen100;
static unsigned phase100,pending_rx100,reply100,stuck100,frozen100,firstbyte100;
static uint32_t step_ns100=1000;
typedef struct {uint32_t LISR,LIFCR;} Dma100;
typedef struct {uint32_t NDTR,PAR,M0AR,CR;} Stream100;
static Dma100 dma100;static Stream100 stream100;static uint32_t dummy_dr100,dummy_cr2100;
#define DMA2 (&dma100)
#define DMA2_Stream0 (&stream100)
#define __NOP() ((void)0)
static void gbc_spi_byte_gap(void){assert(!nes_diag_active());}
static void snapshot100(void){
 if(lower_active100&&nes_return_failed()&&!failed_seen100){failed_seen100=1;failed_tx100=tx100;failed_select100=select100;failed_reads100=drreads100;}
}
static void cs_pin100(MockGPIO *p,unsigned b,bool high){
 assert(p==GPIOA&&b==4);snapshot100();
 if(!high){
  assert(cs100);select100++;cs100=0;op100=0xff;pos100=0;
 }else if(!cs100){deselect100++;cs100=1;}
 if(high)p->ODR|=1u<<b;else p->ODR&=~(1u<<b);
}
static unsigned status100(void){
 if(!lower_active100)return mock_spi.SR;
 snapshot100();unsigned s=SPI_SR_TXE|(pending_rx100?1u:0u);
 if(mode100==1||stuck100==1)s|=SPI_SR_BSY;
 if(mode100==2||stuck100==2)s&=~SPI_SR_TXE;
 if(mode100==3||stuck100==3)s&=~1u;
 if(mode100==5||stuck100==5)s|=1u;
 return s;
}
static unsigned ready100(void){
 if(!lower_active100)return mock_a.IDR;
 snapshot100();return mode100==4||stuck100==4?0:32;
}
static void write_dr100(uint8_t v){
 snapshot100();tx100++;assert(!cs100);pending_rx100=1;reply100=0;
 if(pos100++==0){op100=v;firstbyte100=tx100;return;}
 if(op100==0){addr100=((addr100<<8)|v)&0xffffffu;return;}
 if(op100==0x98){
  assert(addr100<sizeof(menu_ram097));menu_ram097[addr100]=v;memwrites100++;
  if(addr100>=SRAM_MENU_ADDR&&addr100<SRAM_MENU_ADDR+65536)menu_bytes098++;
  addr100++;
 }else if(op100==0x88){
  assert(addr100<sizeof(menu_ram097));reply100=menu_ram097[addr100];memreads100++;
  if(addr100==SRAM_SCRATCHPAD)reliable098++;
  if(mode100==11&&addr100==SRAM_MENU_ADDR+32768)reply100^=1;
  addr100++;
 }
 if(mode100>=6&&mode100<=10&&op100==0x98&&addr100==SRAM_MENU_ADDR+129)stuck100=mode100-5;
 if(mode100==12&&op100==0x98&&addr100==SRAM_MENU_CFG_ADDR+1)stuck100=2;
 if(mode100==13&&op100==0x98&&addr100==SRAM_MCU_STATUS_ADDR+1)stuck100=2;
}
static unsigned read_dr100(void){snapshot100();drreads100++;pending_rx100=0;return reply100;}
static void begin_lower100(unsigned mode){
 lower_active100=1;mode100=mode;cs100=1;op100=0xff;pos100=addr100=0;
 tx100=drreads100=select100=deselect100=memwrites100=memreads100=0;
 failed_seen100=pending_rx100=stuck100=0;mock_a.ODR|=16;
 if(mode==15){mode100=4;frozen100=1;scenario096=1010;}
 if(mode==16){mode100=4;step_ns100=10000000;}
}
static void assert_quiet100(void){
 snapshot100();assert(failed_seen100&&tx100==failed_tx100&&select100==failed_select100&&drreads100==failed_reads100&&cs100);
 unsigned t=tx100,s=select100,r=drreads100;mode100=stuck100=0;
 set_rom_mask(0xffffff);sram_writelong(0,SRAM_SCRATCHPAD);(void)sram_readlong(SRAM_SCRATCHPAD);
 FPGA_SELECT_ASYNC();FPGA_DESELECT_ASYNC();
 assert(t==tx100&&s==select100&&r==drreads100&&cs100);
}
