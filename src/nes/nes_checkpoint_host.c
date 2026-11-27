/* SPDX-License-Identifier: MIT */
#include "nes_checkpoint_host.h"
#include <string.h>

enum { STATUS, PAUSE, RESUME, CAPTURE, RESTORE, ACK_WORD, SET_WORD, BAT_READ, BAT_WRITE };
enum { HELD=1, SAFE=2, PENDING=4, READING=8, BUSY=16, FINISHED=32, BAT_READY=64, FAULT=128 };
enum { STATE_WORDS=2658, BAT_BYTES=8192 };

static uint8_t checksum(const uint8_t *p)
{
    uint8_t c=0;
    for(unsigned n=0;n<12;n++){
        c^=p[n];
        for(unsigned i=0;i<8;i++) c=(c<<1)^((c&128)?7:0);
    }
    return c;
}

static bool command(nes_state_exchange exchange, uint8_t op, unsigned index,
                    const uint8_t *word, uint8_t rx[13])
{
    uint8_t tx[13]={0x59,op,index>>8,index};
    if(word) memcpy(tx+4,word,8);
    tx[12]=checksum(tx);
    if(!exchange(tx,rx)) return false;
    rx[0]=0x59;
    return checksum(rx)==rx[12] && !(rx[1]&FAULT);
}

static bool wait_flags(nes_state_exchange exchange, unsigned mask, unsigned value, uint8_t rx[13])
{
    /* Each real GPIO exchange takes at least 208 us. Bound a stalled endpoint. */
    for(unsigned i=0;i<2048;i++){
        if(!command(exchange,STATUS,0,NULL,rx)) return false;
        if((rx[1]&mask)==value) return true;
    }
    return false;
}

static unsigned index_of(const uint8_t rx[13])
{
    return (unsigned)rx[2]*256+rx[3];
}

bool nes_state_pause(nes_state_exchange exchange,bool (*drain)(void *),void *ctx)
{
    uint8_t rx[13];
    if(!command(exchange,PAUSE,0,NULL,rx)) return false;
    for(unsigned i=0;i<2048;i++){
        if(!command(exchange,STATUS,0,NULL,rx) || !(rx[1]&HELD) ||
           (rx[1]&(BUSY|PENDING))) return false;
        if(rx[1]&SAFE) return true;
        if(drain && !drain(ctx)) return false;
    }
    return false;
}

struct transfer {
    nes_state_exchange exchange;
    bool load,state;
};

static const uint8_t header_word[8]={0,0,0,0,0xc4,0x14,0,0};

static bool state_word(struct transfer *t,unsigned index,uint8_t *word)
{
    uint8_t rx[13];
    if(!wait_flags(t->exchange,PENDING|BUSY|SAFE|READING,
                   PENDING|BUSY|SAFE|(t->load?READING:0),rx) || index_of(rx)!=index) return false;
    if(!t->load) memcpy(word,rx+4,8);
    return command(t->exchange,t->load?SET_WORD:ACK_WORD,index,word,rx);
}

static bool transfer_page(void *ctx,unsigned offset,uint8_t *page,unsigned size)
{
    struct transfer *t=ctx;
    uint8_t rx[13];
    if(offset==0){
        /* Reject an incompatible checkpoint before the first core write. */
        if(t->state && t->load &&
           (memcmp(page+4,header_word+4,4) || (page[14]&3))) return false;
        if(!command(t->exchange,PAUSE,0,NULL,rx) ||
           !wait_flags(t->exchange,SAFE|HELD|BUSY,SAFE|HELD,rx)) return false;
        if(t->state && !command(t->exchange,t->load?RESTORE:CAPTURE,0,NULL,rx)) return false;
    }
    if(!t->state){
        for(unsigned i=0;i<size;i++){
            unsigned index=offset+i;
            uint8_t data[8]={t->load?page[i]:0};
            if(t->load && !command(t->exchange,BAT_WRITE,index,data,rx)) return false;
            if(!command(t->exchange,BAT_READ,index,NULL,rx) ||
               !wait_flags(t->exchange,BAT_READY|SAFE,BAT_READY|SAFE,rx) ||
               index_of(rx)!=index || (t->load && rx[4]!=page[i])) return false;
            page[i]=rx[4];
        }
        return true;
    }
    for(unsigned i=0;i<size;i+=8){
        unsigned index=(offset+i)/8;
        if(!t->load && index==0) memcpy(page,header_word,8);
        else if(!state_word(t,index,page+i)) return false;
    }
    if(offset+size==8*STATE_WORDS){
        /* The FPGA emits its constant size word last. Do not publish the file
         * until that independently read word matches the staged file prefix. */
        uint8_t actual[8];
        if(!t->load && (!state_word(t,0,actual) || memcmp(actual,header_word,8))) return false;
        return wait_flags(t->exchange,FINISHED|BUSY|PENDING|SAFE,FINISHED|SAFE,rx);
    }
    return true;
}

int nes_state_file_pages(nes_state_exchange exchange,struct nes_save_id id,bool load)
{
    if(!exchange) return NES_SAVE_IO;
    struct transfer t={exchange,load,id.slot!=0};
    return nes_savefile_pages(id,load,transfer_page,&t);
}

int nes_state_file_action(nes_state_exchange exchange,struct nes_save_id id,bool load,
                          uint8_t *image,unsigned capacity)
{
    unsigned bytes=id.slot?8*STATE_WORDS:BAT_BYTES;
    if(!exchange || !image || id.slot>4 || capacity<bytes) return NES_SAVE_IO;
    if(load){
        int rc=nes_savefile_read(id,image,bytes);
        if(rc!=NES_SAVE_OK) return rc;
    }
    struct transfer t={exchange,load,id.slot!=0};
    if(!transfer_page(&t,0,image,bytes)) return NES_SAVE_IO;
    return load?NES_SAVE_OK:nes_savefile_write(id,image,bytes);
}

bool nes_state_resume(nes_state_exchange exchange)
{
    uint8_t rx[13];
    return wait_flags(exchange,HELD|SAFE|BUSY|PENDING,HELD|SAFE,rx) &&
           command(exchange,RESUME,0,NULL,rx) && wait_flags(exchange,HELD|BUSY|PENDING,0,rx);
}
