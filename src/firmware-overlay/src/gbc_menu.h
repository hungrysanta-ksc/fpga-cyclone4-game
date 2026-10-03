#ifndef GBC_MENU_H
#define GBC_MENU_H
void gbc_menu_begin(void);
void gbc_menu_bind_state(uint32_t rom_bytes,uint32_t rom_crc,uint32_t ram_bytes);
void gbc_menu_poll(void);
uint8_t gbc_menu_take_reset(void);
#endif
