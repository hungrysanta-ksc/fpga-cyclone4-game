/* SPDX-License-Identifier: MIT
 * Measurement kernel only. UNIT is the size in bytes of one dirty group.
 * The caller owns the bank identity, cold initialization and final ACK.
 */
#include <stdint.h>

#if UNIT != 8 && UNIT != 16 && UNIT != 32
#error Unsupported dirty group size
#endif
#define WORDS (4096u / UNIT / 32u)

void map513_fill(uint32_t *mask, uint32_t value) {
    for (unsigned i = 0; i < WORDS; ++i)
        mask[i] = value;
}

void map513_mark(uint32_t *mask, unsigned word_index) {
    unsigned group = word_index / (UNIT / 2u);
    mask[group / 32u] |= UINT32_C(1) << (group % 32u);
}

void map513_prepare(uint32_t *a, uint32_t *b, const uint32_t *changed) {
    for (unsigned i = 0; i < WORDS; ++i) {
        a[i] |= changed[i];
        b[i] |= changed[i];
    }
}

static unsigned dirty(const uint32_t *mask, unsigned group) {
    return (mask[group / 32u] >> (group % 32u)) & 1u;
}

/* Restrict the single literal DMA to the first and last marked group. */
uint32_t map513_span(const uint32_t *mask, unsigned offset, unsigned length) {
    unsigned lo = offset / UNIT;
    unsigned end = (offset + length) / UNIT;
    while (lo < end && !dirty(mask, lo))
        ++lo;
    if (lo == end)
        return offset;
    while (!dirty(mask, end - 1))
        --end;
    return ((end - lo) * UNIT << 16) | (lo * UNIT);
}
