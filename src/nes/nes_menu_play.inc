/* FF3 play profile. The SNES continues consuming E1 until OPEN is acknowledged. */
static unsigned char ff3_next_slot;
static bool ff3_menu_open;
static uint32_t ff3_menu_tick;
extern int nes_menu_state_io(unsigned,bool);
extern bool nes_menu_state_resume(void);
static bool ff3_pause_menu(void);
static int ff3_slot_exists(unsigned);

static bool ff3_mail(const struct nes_rom_spi_io *io,uint8_t request,
                     unsigned result,uint8_t *observed)
{
    uint8_t tx[5]={0x7a,request,(uint8_t)~request,result,(uint8_t)~result},rx[5];
    if(!nes_native165_bulk(io,tx,rx,result?5:3) || (rx[1]^rx[2])!=255)return false;
    *observed=rx[1];
    return !result || rx[1]==request;
}

static bool __attribute__((noinline,noclone)) ff3_play_step(const struct nes_rom_spi_io *io)
{
    uint32_t now=getticks();
    if(!ff3_menu_open && (uint32_t)(now-ff3_menu_tick)<3)return true;
    ff3_menu_tick=now;
    uint8_t req;
    if(!nes_cf86_check094() || !ff3_mail(io,0,0,&req))return false;
    if(!req)return true;
    int rc=NES_SAVE_IO;
    if(req==1 && !ff3_menu_open){
        if(!ff3_pause_menu())return false;
        ff3_menu_open=true;
        rc=NES_SAVE_OK;
    }else if(ff3_menu_open){
        if(req==2)rc=nes_menu_state_io(0,false);
        else if(req>=0x10 && req<=0x13)rc=nes_menu_state_io(1+(req&3),false);
        else if(req>=0x20 && req<=0x23){
            unsigned slot=1+(req&3);
            rc=ff3_slot_exists(slot);
            if(rc==NES_SAVE_OK)ff3_next_slot=slot;
        }else if(req==5){
            if(!nes_menu_state_resume())return false;
            ff3_menu_open=false;
            rc=NES_SAVE_OK;
        }else if(req==7)rc=NES_SAVE_OK;
    }
    if(!ff3_mail(io,req,rc==NES_SAVE_OK?1:rc==NES_SAVE_MISSING?2:3,&req))return false;
    if(rc==NES_SAVE_IO)return false;
    if(ff3_next_slot || req==7)native_runtime165.result=NES_RUNTIME165_DEADLINE;
    return true;
}
