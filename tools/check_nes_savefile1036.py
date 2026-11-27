"""Run the embedded save journal against files in an isolated directory on the host."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile

from prepare_nes_ff3_checkpoint import ROOT, BASE

HOST_FF = """
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef unsigned UINT;
typedef int FRESULT;
typedef struct { FILE *fp; unsigned bytes; } FIL;
enum { FR_OK, FR_NO_FILE, FR_NO_PATH, FA_READ=4, FA_WRITE=8, FA_CREATE_ALWAYS=16 };
#define f_size(f) ((f)->bytes)
static inline FRESULT f_open(FIL *f,const char *name,int mode){
    const char *base=strrchr(name,'/')+1;
    f->fp=fopen(base,mode==FA_READ?"rb":"wb");
    if(!f->fp)return FR_NO_FILE;
    fseek(f->fp,0,SEEK_END); f->bytes=ftell(f->fp); rewind(f->fp);
    return FR_OK;
}
static inline int f_read(FIL *f,void *dst,UINT n,UINT *got){
    *got=fread(dst,1,n,f->fp);return ferror(f->fp);
}
static inline int f_write(FIL *f,const void *src,UINT n,UINT *got){
    *got=fwrite(src,1,n,f->fp);return ferror(f->fp);
}
#define f_close(f) fclose((f)->fp)
#define f_lseek(f,o) fseek((f)->fp,(o),SEEK_SET)
#define f_sync(f) fflush((f)->fp)
"""
CASES = r"""
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "nes_savefile.h"
int main(void){
    unsigned char p[21264],q[21264];
    for(int i=0;i<21264;i++)p[i]=i*91+(i>>2);
    struct nes_save_id a={0x4be84aa7,0x80000,0}, b=a;
    b.rom_crc++;
    assert(nes_savefile_read(a,q,8192)==0);
    assert(nes_savefile_write(a,p,8192)==1);
    assert(nes_savefile_read(b,q,8192)==0);
    assert(nes_savefile_read(a,q,8192)==1 && !memcmp(q,p,8192));
    p[42]^=255;
    assert(nes_savefile_write(a,p,8192)==1);
    assert(nes_savefile_read(a,q,8192)==1 && !memcmp(q,p,8192));
    FILE *f=fopen("4be84aa7-80000-0b.nsv","r+b");assert(f);
    fseek(f,36+42,SEEK_SET);fputc(p[42]^255,f);fclose(f);
    p[42]^=255;
    assert(nes_savefile_read(a,q,8192)==1 && !memcmp(q,p,8192));
    a.slot=3;
    assert(nes_savefile_write(a,p,21264)==1);
    assert(nes_savefile_read(a,q,21264)==1 && !memcmp(q,p,21264));
    a.slot=4; assert(nes_savefile_read(a,q,21264)==0);
    a.slot=3; assert(nes_savefile_write(a,p,8192)==-1);
    a.slot=0;
    f=fopen("4be84aa7-80000-0a.nsv","wb");assert(f);fclose(f);
    assert(nes_savefile_read(a,q,8192)==NES_SAVE_IO);
    assert(nes_savefile_write(a,p,8192)==NES_SAVE_IO);
    puts("PASS battery, checkpoint, two generations, corruption fallback, slot and ROM isolation");
}
"""

if __name__=="__main__":
    cc=Path("C:/altera_lite/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe")
    env={**os.environ,"PATH":str(cc.parent)+os.pathsep+os.environ["PATH"]}
    with tempfile.TemporaryDirectory(prefix="nes-savefile-") as tmp:
        tmp=Path(tmp)
        for name in ("crc32.c","crc32.h"): shutil.copy(BASE/"link/src"/name,tmp)
        for name in ("nes_savefile.h","nes_savefile.c"): shutil.copy(ROOT/"src/nes"/name,tmp)
        (tmp/"config.h").write_text("#include <stdint.h>\n")
        (tmp/"ff.h").write_text(HOST_FF)
        (tmp/"fileops.h").write_text("#define check_or_create_folder(x) FR_OK\n")
        (tmp/"test.c").write_text(CASES)
        subprocess.run([cc,"-std=c99","-Wall","-Werror","nes_savefile.c","crc32.c","test.c","-o","check.exe"],
                       env=env,cwd=tmp,check=True)
        subprocess.run([tmp/"check.exe"],env=env,cwd=tmp,check=True)
        for name in ("nes_checkpoint_host.h","nes_checkpoint_host.c"):
            shutil.copy(ROOT/"src/nes"/name,tmp)
        shutil.copy(ROOT/"tests/nes-functional/ff3_checkpoint_host.c",tmp)
        subprocess.run([cc,"-std=c99","-Wall","-Werror","nes_checkpoint_host.c","nes_savefile.c",
                        "crc32.c","ff3_checkpoint_host.c","-o","host.exe"],env=env,cwd=tmp,check=True)
        subprocess.run([tmp/"host.exe"],env=env,cwd=tmp,check=True)

