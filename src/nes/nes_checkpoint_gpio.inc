/* Included in nes_h1_stm32.c to share its SPI ownership and pin restoration. */
#include "nes_checkpoint_host.h"

static bool checkpoint_exchange(const uint8_t tx[13],uint8_t rx[13])
{
    load_select(NULL,true);
    delay_us(1);
    for(unsigned i=0;i<13;i++){
        uint8_t byte=0;
        for(unsigned bit=0x80;bit;bit>>=1){
            load_mosi(NULL,(tx[i]&bit)!=0);
            delay_us(1);
            load_clock(NULL,true);
            delay_us(1);
            byte=(byte<<1)|load_miso(NULL);
            load_clock(NULL,false);
        }
        rx[i]=byte;
    }
    delay_us(1);
    load_select(NULL,false);
    delay_us(1);
    return true;
}

static bool ff3_writing_save;

/* The active game uses the ordinary buffered SD path only while its NES
 * has acknowledged pause and released the renderer. Recheck the hardware
 * owner at every sector, including FAT and directory metadata writes. */
bool nes_ff3_write_allowed(void)
{
    return ff3_writing_save && gpio_owned && nes_board_id==0x7d &&
           nes_cf86_monitoring094() && !get_snes_reset() && nes_cf86_check094();
}

/* Called by the foreground menu between completed runtime steps. A frame
 * already in the collector or waiting for the final SNES ACK must retire
 * before the NES can acknowledge PAUSE. Keep the normal receiver running. */
static bool ff3_drain_frame(void *ctx)
{
    return nes_runtime165_step(ctx);
}

int nes_menu_state_io(unsigned slot,bool load)
{
    bool borrowed=gpio_owned;
    if(nes_board_id!=0x7d || (!borrowed && !slow_begin())) return NES_SAVE_IO;
    struct nes_save_id id={nes_content_crc,NES_CART_BYTES,slot};
    int result=NES_SAVE_IO;
    bool running=native_runtime165.receiver!=NULL;
    if(slot<=4 && !native_runtime165.inside_transfer &&
       ((load && !running) ||
        nes_state_pause(checkpoint_exchange,running?ff3_drain_frame:NULL,&native_runtime165))){
        ff3_writing_save=!load;
        result=nes_state_file_pages(checkpoint_exchange,id,load);
        ff3_writing_save=false;
    }
    if(!borrowed) slow_end();
    return result;
}

bool nes_menu_state_resume(void)
{
    bool borrowed=gpio_owned;
    if(nes_board_id!=0x7d || (!borrowed && !slow_begin())) return false;
    bool ok=nes_state_resume(checkpoint_exchange);
    if(!borrowed) slow_end();
    return ok;
}

/* Called after verified START and the 8192-cycle scrub, before native_frames222
 * allocates the large render workspace. CPU reset is still held by the FPGA. */
bool __attribute__((noinline)) nes_restore_boot_battery(void)
{
    delay_us(2000);
    int result=nes_menu_state_io(0,true);
    return result!=NES_SAVE_IO && nes_menu_state_resume();
}
