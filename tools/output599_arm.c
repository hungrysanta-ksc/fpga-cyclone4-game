/* SPDX-License-Identifier: MIT
 * Standalone Cortex-M4 output producer. All bases are frozen by the caller
 * until final display ACK. The caller discards them on an incomplete frame.
 */
#include <stdint.h>

struct range { uint16_t section, start, size; };
struct input {
    uint8_t previous[4096], current[4096], stale[64];
    uint8_t history[4474], desired[4474];
    uint16_t valid[3], count;
    struct range packets[64];
};
struct output {
    uint8_t masks[64], records[4224], declarations[7 * 32];
    uint16_t used, ranges, record_crc;
};

static uint16_t crc_byte(uint16_t crc, uint8_t byte)
{
    crc ^= (uint16_t)byte << 8;
    for (unsigned i = 0; i < 8; i++)
        crc = (crc << 1) ^ ((crc & 0x8000) ? 0x1021 : 0);
    return crc;
}

static void put16(uint8_t *p, uint16_t v)
{
    p[0] = v;
    p[1] = v >> 8;
}

/* Retain the complete record stream for byte comparison at the SNES reader. */
static void maps(const struct input *in, struct output *out)
{
    uint16_t n = 0, crc = 0xffff;
    for (unsigned row = 0; row < 64; row++) {
        unsigned mask = in->stale[row];
        for (unsigned i = 0; i < 64; i++)
            if (in->current[row*64+i] != in->previous[row*64+i])
                mask |= 1u << (i/8);
        out->masks[row] = mask;
        if (!mask) continue;
        unsigned first = n;
        out->records[n++] = row;
        out->records[n++] = mask;
        for (unsigned i = 0; i < 64; i++)
            if (mask & (1u << (i/8))) out->records[n++] = in->current[row*64+i];
        for (; first < n; first++) crc = crc_byte(crc, out->records[first]);
    }
    out->used = n;
    out->record_crc = crc;
}

int produce(const struct input *in, struct output *out)
{
    static const uint16_t offsets[] = {0, 512, 1056, 4474};
    unsigned count = 0, end = 0, last_section = 0, crc = 0;
    if (in->count > 64) return 0;
    maps(in, out);
    for (unsigned i = 0; i < in->count; i++) {
        struct range r = in->packets[i];
        if (r.section < 3 || r.section > 5 || !r.size) return 0;
        unsigned k = r.section-3, limit = (unsigned)r.start + r.size;
        if (limit > offsets[k+1]-offsets[k]) return 0;
        if (limit > in->valid[k]) continue;
        const uint8_t *src = in->desired + offsets[k] + r.start;
        const uint8_t *base = in->history + offsets[k] + r.start;
        unsigned j = 0;
        while (j < r.size && src[j] == base[j]) j++;
        if (j != r.size) continue;
        if (!count || r.section != last_section || r.start != end) {
            if (count == 32) return 0;
            uint8_t *p = out->declarations + 7*count++;
            p[0] = r.section;
            put16(p+1, r.start);
            crc = 0xffff;
        }
        uint8_t *p = out->declarations + 7*(count-1);
        end = limit;
        last_section = r.section;
        put16(p+3, end-(p[1]+256u*p[2]));
        for (j = 0; j < r.size; j++) crc = crc_byte(crc, src[j]);
        put16(p+5, crc);
    }
    out->ranges = count;
    return 1;
}
