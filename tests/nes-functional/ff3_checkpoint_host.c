/* Exercise the firmware transport and SD journal with an independent 59 peer. */
#include "nes_checkpoint_host.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>

static unsigned char state[21264],battery[8192],work[21264];
static unsigned n,index_word,bat_index,flags,dir,frames;
static bool corrupt,wrong_index;
static uint8_t crc(const uint8_t *p){
    unsigned value=0;
    for(int i=0;i<12;i++){
        value^=p[i]<<8;
        for(int b=0;b<8;b++) value=(value<<1)^((value&0x8000)?0x0700:0);
    }
    return (value>>8)&255;
}
static bool xfer(const uint8_t tx[13],uint8_t rx[13]){
    unsigned op=tx[1],idx=tx[2]*256+tx[3];
    frames++;
    assert(tx[0]==0x59 && tx[12]==crc(tx));
    memset(rx,0,13);rx[0]=0x59;rx[1]=flags;
    unsigned a=(flags&4)?index_word:bat_index;
    rx[2]=a>>8;rx[3]=a;
    if(flags&4) memcpy(rx+4,state+8*index_word,8);
    else if(flags&64) rx[4]=battery[bat_index];
    if(wrong_index && flags&4) rx[3]^=1;
    rx[12]=crc(rx)^corrupt;rx[0]=0;
    switch(op){
    case 0:break;
    case 1:flags|=3;break;
    case 2:assert(!(flags&16));flags=0;break;
    case 3:case 4:
        assert((flags&3)==3);
        dir=op==4;n=0;index_word=dir?0:1;flags=3|4|16|(dir?8:0);break;
    case 5:case 6:
        assert(idx==index_word && (op==6)==dir);
        if(dir)memcpy(state+8*idx,tx+4,8);else assert(!memcmp(state+8*idx,tx+4,8));
        if(++n==2658)flags=3|32;else index_word=(index_word+1)%2658;
        break;
    case 7: assert(idx<8192);bat_index=idx;flags=3|64;break;
    case 8: assert(idx<8192);battery[idx]=tx[4];flags=3;break;
    default:assert(0);
    }
    return true;
}
int main(void){
    struct nes_save_id id={0x12345678,0x80000,0};
    for(unsigned i=0;i<sizeof battery;i++)battery[i]=(i>>4)+i;
    assert(nes_state_file_action(xfer,id,0,work,sizeof work)==1);
    assert(nes_state_resume(xfer));memset(battery,0,sizeof battery);
    assert(nes_state_file_action(xfer,id,1,work,sizeof work)==1);
    for(unsigned i=0;i<sizeof battery;i++)assert(battery[i]==(uint8_t)((i>>4)+i));
    assert(nes_state_resume(xfer));
    uint8_t original[sizeof state];for(unsigned i=0;i<sizeof state;i++)original[i]=i*39+(i>>7);
    original[14]&=0xfc; /* FF3 is a 2A03 cartridge. */
    memset(original,0,4);memcpy(original+4,"\xc4\x14\x00\x00",4);
    memcpy(state,original,sizeof state);id.slot=2;
    assert(nes_state_file_action(xfer,id,0,work,sizeof work)==1);
    assert(nes_state_resume(xfer));memset(state,0,sizeof state);memset(work,0,sizeof work);
    assert(nes_state_file_action(xfer,id,1,work,sizeof work)==1);
    assert(!memcmp(original,state,sizeof state) && nes_state_resume(xfer));
    /* An old schema-1 save loads via pages, and a new paged save is readable
     * by the original contiguous reader. Check every byte, including the tail. */
    memset(state,0,sizeof state);
    assert(nes_state_file_pages(xfer,id,true)==NES_SAVE_OK);
    assert(!memcmp(original,state,sizeof state) && nes_state_resume(xfer));
    state[1024]^=0x83;
    assert(nes_state_file_pages(xfer,id,false)==NES_SAVE_OK && nes_state_resume(xfer));
    assert(nes_savefile_read(id,work,sizeof work)==NES_SAVE_OK && !memcmp(work,state,sizeof state));
    state[0]^=1;
    assert(nes_state_file_pages(xfer,id,false)==NES_SAVE_IO); /* wrong terminal header */
    assert(nes_savefile_read(id,work,sizeof work)==NES_SAVE_OK && work[0]==0 && work[1024]==state[1024]);
    flags=0; /* STOP then cold restart */
    id.slot=0;assert(nes_state_file_pages(xfer,id,false)==NES_SAVE_OK && nes_state_resume(xfer));
    memset(battery,0,sizeof battery);
    assert(nes_state_file_pages(xfer,id,true)==NES_SAVE_OK && nes_state_resume(xfer));
    for(unsigned i=0;i<sizeof battery;i++)assert(battery[i]==(uint8_t)((i>>4)+i));
    unsigned before=frames;id.slot=4;
    assert(nes_state_file_action(xfer,id,1,work,sizeof work)==0 && frames==before);
    id.slot=3;
    for(unsigned mode=1;mode<=3;mode++){
        original[14]=(original[14]&0xfc)|mode;
        assert(nes_savefile_write(id,original,sizeof original)==1);
        assert(nes_state_file_action(xfer,id,1,work,sizeof work)<0 && frames==before);
    }
    id.slot=2;corrupt=true;assert(nes_state_file_action(xfer,id,1,work,sizeof work)<0 && (flags&1));
    corrupt=false;wrong_index=true;assert(nes_state_file_action(xfer,id,1,work,sizeof work)<0 && (flags&1));
    puts("PASS file/transport: battery, full checkpoint across restart, quarantine on CRC or word-order fault");
}
