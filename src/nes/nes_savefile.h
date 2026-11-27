#ifndef NES_SAVEFILE_H
#define NES_SAVEFILE_H
#include <stdint.h>
#include <stdbool.h>

/* Battery SRAM uses slot zero. Machine checkpoints use slots one through four.
 * Call only with FatFS ownership. Load into isolated staging, then restore the core. */
struct nes_save_id { uint32_t rom_crc, rom_bytes, slot; };
enum nes_save_result { NES_SAVE_IO=-1, NES_SAVE_MISSING=0, NES_SAVE_OK=1 };
int nes_savefile_read(struct nes_save_id id, void *staging, unsigned bytes);
int nes_savefile_available(struct nes_save_id id, unsigned bytes);
int nes_savefile_write(struct nes_save_id id, const void *staging, unsigned bytes);
/* Transfer canonical file offsets in ascending order. A failed callback or
 * verification leaves the machine paused; the caller owns STOP/recovery. */
typedef bool (*nes_save_page)(void *ctx,unsigned offset,uint8_t *page,unsigned bytes);
int nes_savefile_pages(struct nes_save_id id,bool load,nes_save_page transfer,void *ctx);
#endif

