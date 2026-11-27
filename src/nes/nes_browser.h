/* SPDX-License-Identifier: MIT */
#ifndef NES_BROWSER_H
#define NES_BROWSER_H
#include <stdint.h>
#include <string.h>
#include <strings.h>

static inline int nes_filename(const uint8_t *path)
{
    const char *dot = path ? strrchr((const char *)path, '.') : NULL;
    return dot && !strcasecmp(dot, ".nes");
}

/* Each ID denotes a distinct synthesized cartridge wiring. */
static inline unsigned nes_image_id(const uint8_t h[16], uint32_t file_size)
{
    if (memcmp(h, "NES\032", 4) || h[4] != 32 ||
        (h[6] & ~2u) != 0x40 || h[7] || h[8] > 1)
        return 0;
    for (unsigned i = 9; i < 16; i++)
        if (h[i]) return 0;
    if (file_size != 16u + 524288u + h[5] * 8192u) return 0;
    if (h[5] == 32) return 0x7c;
    if (!h[5]) return 0x7d;
    return 0;
}
#endif

