// SPDX-License-Identifier: MIT
#ifndef NES_NROM406_H
#define NES_NROM406_H
#include <stdbool.h>
#include <stdint.h>

// Narrow experimental mapper0 profile; not the production loader entry.
struct nes_nrom406_profile {
 uint32_t prg_bytes;
 uint32_t file_bytes;
 bool vertical;
};
bool nes_nrom406_header(const uint8_t header[16], uint32_t size,
                        struct nes_nrom406_profile *profile);
// Translate one byte of the existing 384KiB physical loader layout into a
// source file byte offset or a deterministic zero-padding byte. This does not
// implement the file CRC, SPI transport, loader state machine or readback.
bool nes_nrom406_layout(const struct nes_nrom406_profile *profile,
                        uint32_t physical_offset, bool *from_file,
                        uint32_t *file_offset);
#endif
