#ifndef GBC_SAVE_H
#define GBC_SAVE_H
#include <stdint.h>
/* G12S: normal battery saves, not emulator save states. */
uint8_t gbc_save_load(const uint8_t *rom_filename, uint32_t size, uint8_t has_rtc);
uint8_t gbc_save_exit(void);
void gbc_save_disarm(void);
void gbc_save_poll(void);
void gbc_save_set_auto(uint8_t enable);
uint8_t gbc_save_status(void);
uint8_t gbc_save_now(void);
uint8_t gbc_save_before_state_load(void);
void gbc_save_after_state_load(void);
#endif
