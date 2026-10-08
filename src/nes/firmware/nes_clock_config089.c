/* SPDX-License-Identifier: GPL-2.0-only */
#include "config.h"
#include "bits.h"
#include "fpga.h"
#include "snes.h"
#include "nes_menu_return.h"
#include "nes_report_boot080.h"
#include "nes_clock_config089.h"
extern const uint8_t *fpga_config;
extern uint8_t gbc_spi_pacing;
extern int snes_boot_configured,sd_offload,ff_sd_offload,during_blocktrans;
int fpga_get_done(void);
static bool active089;
struct stream089 {unsigned bytes;uint32_t crc;bool send;struct nes_diag_wait limit;};
static bool owned089(void) {
 return nes_diag_active()&&!nes_return_failed()&&!nes_return_log_allowed()&&
  !sd_offload&&!ff_sd_offload&&!during_blocktrans&&get_snes_reset()&&
  !(NVIC->ISER[OTG_FS_IRQn>>5]&(1u<<(OTG_FS_IRQn&31)));
}
static bool fail089(enum nes_diag_error e) {snes_reset(1);nes_return_fail(e);return false;}
static bool guard089(void) {
 if(!owned089()||!nes_return_io_step())return fail089(NES_DIAG_FPGA_LIMIT);
 return true;
}
static bool wait089(unsigned pin,bool high,enum nes_diag_error error) {
 struct nes_diag_wait w=nes_diag_wait_start(100,100000);
 do {
  if(!guard089())return false;
  bool value=pin==0?!!BITBAND(FPGA_PROGBREG->GPIO_I,FPGA_PROGBBIT):pin==1?!!fpga_get_initb():!!fpga_get_done();
  if(value==high)return true;
 }while(nes_diag_wait_step(&w));
 return fail089(error);
}
static bool byte089(void *ctx,uint8_t value) {
 struct stream089 *s=ctx;
 /* Ownership is tested for every byte. Time/global-poll accounting is once
  * per at most32 bytes, not a per-byte restart of the existing scope. */
 if(!owned089())return fail089(NES_DIAG_FPGA_LIMIT);
 if(!(s->bytes&31u)&&(!guard089()||!nes_diag_wait_step(&s->limit)))return fail089(NES_DIAG_FPGA_LIMIT);
 if(s->send&&!fpga_get_initb())return fail089(NES_DIAG_FPGA_INIT);
 s->crc^=value;
 for(unsigned b=0;b<8;b++)s->crc=(s->crc>>1)^(0xedb88320u& (0u-(s->crc&1u)));
 if(s->send)FPGA_SEND_BYTE_SERIAL(value);
 s->bytes++;return true;
}
bool nes_clock_config089(const struct clock_image089 *image) {
 if(active089)return fail089(NES_DIAG_FPGA_LIMIT);
 active089=true;bool touched=false,masked=false,ok=false;uint32_t saved_cr1=0;
 struct stream089 s={0,0xffffffffu,false,{0}};
 if(!guard089()||!image||!image->rle||!image->size||image->size>131072u||image->raw_size!=510856u)goto format;
 s.limit=nes_diag_wait_start(500,40000);
 /* Validate the complete embedded stream and CRC before touching nCONFIG.
  * The second pass verifies the exact bytes actually sent as well. */
 if(!report_decode080(image->rle,image->size,image->raw_size,byte089,&s)||
    (s.crc^0xffffffffu)!=image->crc||!guard089())goto format;
 struct nes_diag_wait spi_wait=nes_diag_wait_start(25,100000);
 while(SPI1->SR&SPI_SR_BSY) {
  if(!guard089()||!nes_diag_wait_step(&spi_wait))goto format;
 }
 if(!(SPI1->SR&SPI_SR_TXE)||!guard089())goto format;
 snes_boot_configured=0;fpga_config=0;gbc_spi_pacing=0;saved_cr1=SPI1->CR1;
 SET_BIT(FPGA_SSREG,FPGA_SSBIT);SPI1->CR1&=~SPI_CR1_SPE;
 fpga_init();touched=true;fpga_set_prog_b(0);
 if(!wait089(0,false,NES_DIAG_FPGA_PROG)||!nes_return_delay(10,false)||!guard089()||
    !wait089(1,false,NES_DIAG_FPGA_INIT)||!wait089(2,false,NES_DIAG_FPGA_DONE))goto done;
 fpga_set_prog_b(1);
 if(!wait089(1,true,NES_DIAG_FPGA_INIT)||!wait089(2,false,NES_DIAG_FPGA_DONE))goto done;
 s.bytes=0;s.crc=0xffffffffu;s.send=true; /* local500ticks spans BOTH passes */
 FPGA_DIN_MASK();masked=true;
 if(!report_decode080(image->rle,image->size,image->raw_size,byte089,&s)||
    (s.crc^0xffffffffu)!=image->crc)goto format;
 FPGA_DIN_UNMASK();masked=false;
 for(unsigned n=0;n<3;n++){if(!guard089()||!fpga_get_initb())goto format;CCLK();}
 if(!nes_return_delay(1,true)||!guard089()||!wait089(2,true,NES_DIAG_FPGA_DONE))goto done;
 if(!fpga_get_initb())goto format;
 fpga_postinit(); /* DATA0 -> MCU_RDY input; CF87 identity checked by reader. */
 SPI1->CR1=saved_cr1;
 ok=true;goto done;
format:
 fail089(NES_DIAG_FPGA_FORMAT);
done:
 if(masked)FPGA_DIN_UNMASK();
 if(!ok) {
  if(!nes_return_failed())fail089(NES_DIAG_FPGA_FORMAT);
  if(touched){fpga_set_prog_b(0);fpga_set_cclk(0);} /* safe cancellation only */
 }
 active089=false;return ok;
}
