/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SDINV_MOCK_H
#define SDINV_MOCK_H
#include <stdint.h>
typedef unsigned UINT,FRESULT;
typedef struct {unsigned size,pos,mode;} FIL;
#define FR_OK 0u
#define FR_EXIST 1u
#define FA_READ 1u
#define FA_WRITE 2u
#define FA_CREATE_NEW 4u
#define f_size(f) ((f)->size)
FRESULT f_open(FIL *,const char *,unsigned);
FRESULT f_read(FIL *,void *,UINT,UINT *);
FRESULT f_write(FIL *,const void *,UINT,UINT *);
FRESULT f_sync(FIL *);
FRESULT f_close(FIL *);
#endif
