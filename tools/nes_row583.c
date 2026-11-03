/* SPDX-License-Identifier: MIT
 * R2 standalone cost/atomicity kernel. Not linked into production firmware.
 * The caller owns epoch/base identity, packet CRC and whole geometry checks.
 */
#include <stdint.h>

static unsigned u16(const uint8_t *p) { return p[0] | ((unsigned)p[1] << 8); }

int nes_row583_apply(uint16_t *map, unsigned count, const uint8_t *b,
                     unsigned len, unsigned base_count) {
    uint16_t next[33];
    if (len < 6 || count > 1056 || b[0] != 0) return 0;
    unsigned mode = b[1], at = u16(b + 2), n = u16(b + 4);
    if (at % 33 || n != 33 || at + n > count) return 0;
    unsigned pos = 6;
    int shift = 0;
    const uint8_t *mask = 0;
    if (mode == 0) {
        if (len != 72) return 0;
    } else {
        if (base_count > 1056 || at + n > base_count ||
            (mode != 3 && mode != 4)) return 0;
        if (mode == 4) {
            if (len < 12) return 0;
            shift = (int8_t)b[pos++];
            if (shift != -1 && shift != 1) return 0;
        }
        if (len < pos + 5) return 0;
        mask = b + pos;
        if (mask[4] & 0xfe) return 0;
        pos += 5;
    }
    for (unsigned i = 0; i < 33; ++i) {
        unsigned v;
        if (!mask || ((mask[i >> 3] >> (i & 7)) & 1)) {
            if (pos + 2 > len) return 0;
            v = u16(b + pos); pos += 2;
        } else {
            int src = (int)i + shift;
            if ((unsigned)src >= 33) return 0;
            v = map[at + (unsigned)src];
        }
        if (v & 0x8000) return 0;
        next[i] = (uint16_t)v;
    }
    if (pos != len) return 0;
    /* Never partially commit a row, including on the final literal failure. */
    for (unsigned i = 0; i < 33; ++i) map[at + i] = next[i];
    return 1;
}
