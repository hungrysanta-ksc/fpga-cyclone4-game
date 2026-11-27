/* SPDX-License-Identifier: MIT */
#include "config.h"
#include "ff.h"
#include "fileops.h"
#include "crc32.h"
#include "nes_savefile.h"
#include <stdio.h>
#include <string.h>

#define NES_STATE_DIR "/sd2snes/nesstate/"
/* The on-disk words are little-endian (Cortex-M4). Schema includes the
 * checkpoint memory layout. A future incompatible layout needs a new schema. */
struct header { uint32_t magic, schema, rom_crc, rom_bytes, slot, bytes, serial, crc, head_crc; };
typedef char header_size_check[sizeof(struct header)==36 ? 1 : -1];

static uint32_t digest(const void *data,unsigned size)
{
    const uint8_t *p=data;
    uint32_t c=crc32_init();
    while(size--) c=crc32_update(c,*p++);
    return crc32_finalize(c);
}
static int valid(struct nes_save_id id, unsigned bytes)
{
    return (id.rom_bytes==0x80000u || id.rom_bytes==0xc0000u) &&
           (id.slot==0 ? bytes==8192 : id.slot<=4 && bytes==21264);
}
static void path_for(char path[64],struct nes_save_id id,int bank)
{
    snprintf(path,64,NES_STATE_DIR "%08lx-%05lx-%lu%c.nsv",
             (unsigned long)id.rom_crc,(unsigned long)id.rom_bytes,
             (unsigned long)id.slot,bank?'b':'a');
}
/* Invalid banks are ignored when there is a valid previous generation.
 * An I/O failure is ambiguous and must never authorize overwriting a bank. */
static int inspect(struct nes_save_id id,unsigned bytes,int bank,uint32_t *serial,uint8_t *staging)
{
    FIL file;
    char path[64];
    struct header h;
    uint8_t scratch[256];
    UINT n;
    path_for(path,id,bank);
    FRESULT rc=f_open(&file,path,FA_READ);
    if(rc==FR_NO_FILE || rc==FR_NO_PATH) return NES_SAVE_MISSING;
    if(rc!=FR_OK) return NES_SAVE_IO;
    enum { DAMAGED=2 };
    int result=DAMAGED;
    if(f_size(&file)!=sizeof h+bytes) goto close;
    if(f_read(&file,&h,sizeof h,&n)!=FR_OK || n!=sizeof h){result=NES_SAVE_IO;goto close;}
    if(h.magic!=0x5353454e || h.schema!=1 || h.rom_crc!=id.rom_crc ||
       h.rom_bytes!=id.rom_bytes || h.slot!=id.slot || h.bytes!=bytes ||
       h.head_crc!=digest(&h,sizeof h-4)) goto close;
    uint32_t crc=crc32_init();
    for(unsigned offset=0;offset<bytes;){
        unsigned take=bytes-offset;
        if(take>sizeof scratch) take=sizeof scratch;
        uint8_t *dst=staging ? staging+offset : scratch;
        if(f_read(&file,dst,take,&n)!=FR_OK || n!=take){result=NES_SAVE_IO;goto close;}
        for(unsigned i=0;i<n;i++) crc=crc32_update(crc,dst[i]);
        offset+=n;
    }
    if(crc32_finalize(crc)==h.crc){*serial=h.serial;result=NES_SAVE_OK;}
close:
    return f_close(&file)==FR_OK ? result : NES_SAVE_IO;
}
static int latest(struct nes_save_id id,unsigned bytes,uint32_t *serial,int *bank)
{
    uint32_t a=0,b=0;
    int va=inspect(id,bytes,0,&a,0),vb=inspect(id,bytes,1,&b,0);
    if(va<0 || vb<0) return NES_SAVE_IO;
    if(va!=NES_SAVE_OK && vb!=NES_SAVE_OK)
        return va==NES_SAVE_MISSING && vb==NES_SAVE_MISSING ? NES_SAVE_MISSING : NES_SAVE_IO;
    *bank=vb==NES_SAVE_OK && (va!=NES_SAVE_OK || (int32_t)(b-a)>0);
    *serial=*bank?b:a;
    return NES_SAVE_OK;
}

/* These locals include a FatFS sector buffer. Release it before the journal
 * verifies the other bank or reopens the completed file. */
static __attribute__((noinline)) bool transfer_file(struct nes_save_id id,unsigned bytes,
    int bank,uint32_t serial,bool load,nes_save_page transfer,void *ctx)
{
    char path[64];
    path_for(path,id,bank);
    FIL file;
    if(f_open(&file,path,load?FA_READ:(FA_WRITE|FA_CREATE_ALWAYS))!=FR_OK) return false;
    struct header h={0};
    UINT n;
    bool ok;
    if(load){
        ok=f_size(&file)==sizeof h+bytes && f_read(&file,&h,sizeof h,&n)==FR_OK &&
           n==sizeof h && h.head_crc==digest(&h,sizeof h-4) && h.magic==0x5353454e &&
           h.schema==1 && h.rom_crc==id.rom_crc && h.rom_bytes==id.rom_bytes &&
           h.slot==id.slot && h.serial==serial && h.bytes==bytes;
    }else{
        /* A partial file is ineligible even when its payload is complete. */
        ok=f_write(&file,&h,sizeof h,&n)==FR_OK && n==sizeof h;
    }
    uint8_t page[256];
    uint32_t crc=crc32_init();
    for(unsigned offset=0;ok && offset<bytes;offset+=sizeof page){
        unsigned take=bytes-offset;
        if(take>sizeof page) take=sizeof page;
        if(load) ok=f_read(&file,page,take,&n)==FR_OK && n==take;
        if(ok) ok=transfer(ctx,offset,page,take);
        if(ok){
            for(unsigned i=0;i<take;i++) crc=crc32_update(crc,page[i]);
            if(!load) ok=f_write(&file,page,take,&n)==FR_OK && n==take;
        }
    }
    crc=crc32_finalize(crc);
    if(ok && load) ok=crc==h.crc;
    if(ok && !load){
        h=(struct header){0x5353454e,1,id.rom_crc,id.rom_bytes,id.slot,bytes,serial,crc,0};
        h.head_crc=digest(&h,sizeof h-4);
        ok=f_sync(&file)==FR_OK && f_lseek(&file,0)==FR_OK &&
           f_write(&file,&h,sizeof h,&n)==FR_OK && n==sizeof h && f_sync(&file)==FR_OK;
    }
    return f_close(&file)==FR_OK && ok;
}

int nes_savefile_pages(struct nes_save_id id,bool load,nes_save_page transfer,void *ctx)
{
    unsigned bytes=id.slot?21264:8192;
    if(!transfer || !valid(id,bytes)) return NES_SAVE_IO;
    int bank=1;
    uint32_t serial=0, stored;
    int status=latest(id,bytes,&serial,&bank);
    if(status==NES_SAVE_IO || (load && status!=NES_SAVE_OK)) return status;
    if(!load){
        if(check_or_create_folder(NES_STATE_DIR)!=FR_OK) return NES_SAVE_IO;
        bank^=1;
        ++serial;
    }
    if(!transfer_file(id,bytes,bank,serial,load,transfer,ctx)) return NES_SAVE_IO;
    if(!load && (inspect(id,bytes,bank,&stored,0)!=NES_SAVE_OK || stored!=serial))
        return NES_SAVE_IO;
    return NES_SAVE_OK;
}
int nes_savefile_available(struct nes_save_id id,unsigned bytes)
{
    int bank;
    uint32_t serial;
    return valid(id,bytes)?latest(id,bytes,&serial,&bank):NES_SAVE_IO;
}

int nes_savefile_read(struct nes_save_id id,void *staging,unsigned bytes)
{
    int bank;
    uint32_t serial,actual;
    if(!staging || !valid(id,bytes)) return NES_SAVE_IO;
    int rc=latest(id,bytes,&serial,&bank);
    if(rc!=NES_SAVE_OK) return rc;
    return inspect(id,bytes,bank,&actual,staging)==NES_SAVE_OK && actual==serial ?
           NES_SAVE_OK : NES_SAVE_IO;
}
int nes_savefile_write(struct nes_save_id id,const void *staging,unsigned bytes)
{
    FIL f;
    UINT n;
    char path[64];
    int bank=1;
    uint32_t serial=0,stored;
    if(!staging || !valid(id,bytes) || latest(id,bytes,&serial,&bank)<0 ||
       check_or_create_folder(NES_STATE_DIR)!=FR_OK) return NES_SAVE_IO;
    struct header h={0x5353454e,1,id.rom_crc,id.rom_bytes,id.slot,bytes,serial+1,digest(staging,bytes),0};
    h.head_crc=digest(&h,sizeof h-4);
    bank^=1;
    path_for(path,id,bank);
    if(f_open(&f,path,FA_WRITE|FA_CREATE_ALWAYS)!=FR_OK) return NES_SAVE_IO;
    int ok=f_write(&f,&h,sizeof h,&n)==FR_OK && n==sizeof h &&
           f_write(&f,staging,bytes,&n)==FR_OK && n==bytes && f_sync(&f)==FR_OK;
    if(f_close(&f)!=FR_OK || !ok) return NES_SAVE_IO;
    return inspect(id,bytes,bank,&stored,0)==NES_SAVE_OK && stored==h.serial ?
           NES_SAVE_OK : NES_SAVE_IO;
}

