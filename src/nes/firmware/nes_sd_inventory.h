/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NES_SD_INVENTORY_H
#define NES_SD_INVENTORY_H
#include <stdint.h>
#include <stddef.h>
#define SDINV_FILES 4
#define SDINV_HEADERS 6
/* open: 0 success, 1 absent, other IO error. No callback writes input files. */
struct sdinv_io {
 void *ctx;
 int (*open)(void *,const char *,uint32_t *);
 int (*read)(void *,uint8_t *,unsigned,unsigned *);
 int (*seek)(void *,uint32_t);
 int (*close)(void *);
 int (*step)(void *);
 int (*blocked)(void *);
};
enum sdinv_status {SDINV_UNVISITED,SDINV_OK,SDINV_ABSENT,SDINV_LIMIT,SDINV_IO};
struct sdinv_file {uint32_t size,consumed,crc32,body_crc32,expanded,expanded_crc32;unsigned status,format_ok;uint8_t prefix[16];};
struct sdinv_header {uint32_t address,reset_address;unsigned available,reset_available;uint8_t data[80],reset;};
struct sdinv_report {struct sdinv_file files[SDINV_FILES];struct sdinv_header headers[SDINV_HEADERS];unsigned blocked,finished;};
extern const char *const sdinv_paths[SDINV_FILES];
extern const uint32_t sdinv_header_addresses[SDINV_HEADERS];
int sdinv_collect(const struct sdinv_io *,struct sdinv_report *);
uint32_t sdinv_crc32(const void *,unsigned);
int sdinv_format(const struct sdinv_report *,char *,size_t);
int sdinv_write_report(const char *,unsigned,char *,size_t);
void sdinv_run(void) __attribute__((noreturn));
#endif
