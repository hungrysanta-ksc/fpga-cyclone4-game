/* Bounded producer cost. The caller lends exact published target/peer pages. */
#include <stdint.h>

enum { rows = 23, columns = 32 };
struct request {
    const uint16_t *target;
    const uint16_t *peer;
    const uint16_t *map;
    uint16_t *payload;
    uint32_t serial;
    uint16_t page;
};

/* Returns zero to use the full-row path. No history is modified here. */
unsigned pack_strip868(const struct request *r)
{
    uint32_t mask = 0;
    for (unsigned row = 0; row < rows; ++row) {
        uint32_t changed = 0;
        for (unsigned col = 0; col < columns; ++col) {
            unsigned i = row * columns + col;
            uint16_t value = r->map[i];
            if (r->target[i] != value || r->peer[i] != value)
                changed |= UINT32_C(1) << col;
        }
        if (row == 0) {
            if (!changed)
                return 0;
            unsigned bits = changed >> __builtin_ctz(changed);
            if (bits != 1 && bits != 3)
                return 0;
            mask = changed;
        } else if (changed != mask) {
            return 0;
        }
    }

    unsigned col = __builtin_ctz(mask);
    uint16_t *out = r->payload;
    *out++ = (uint16_t)r->serial;
    *out++ = (uint16_t)(r->serial >> 16);
    *out++ = r->page;
    *out++ = (uint16_t)(col * 2);
    for (; mask; mask &= mask - 1, ++col)
        for (unsigned row = 0; row < rows; ++row)
            *out++ = r->map[row * columns + col];
    return (unsigned)(out - r->payload) * 2;
}

/* history is immutable until final display ACK. Its size, dictionary indices
 * and generation are checked when the snapshot is installed. Palette bytes
 * are little endian. A different column ID means at least one cell differs,
 * so send the whole column without reading either old column word by word. */
unsigned pack_published868(const struct request *r, const uint8_t *history)
{
    const uint8_t *palette = history + 6;
    const uint8_t *ids = palette + 2 * history[0];
    const uint8_t *dictionary = ids + 128;
    uint32_t repeat = history[2] | ((uint32_t)history[3] << 8)
                                | ((uint32_t)history[4] << 16);
    unsigned width = rows;
    for (uint32_t bits = repeat; bits; bits &= bits - 1)
        --width;
    unsigned first = columns;
    unsigned count = 0;
    unsigned page = r->page == 2048 ? columns : 0;
    for (unsigned col = 0; col < columns; ++col) {
        unsigned id = ids[page + col];
        if (id == ids[64 + page + col]) {
            const uint8_t *cell = dictionary + id * width;
            uint32_t bits = repeat;
            unsigned row = 0;
            for (; row < rows; ++row) {
                if (row && !(bits & 1))
                    ++cell;
                bits >>= 1;
                const uint8_t *value = palette + 2 * *cell;
                if (r->map[row * columns + col] != (value[0] | (value[1] << 8)))
                    break;
            }
            if (row == rows)
                continue;
        }
        if (!count)
            first = col;
        if (col != first + count || ++count > 2)
            return 0;
    }
    if (!count)
        return 0;
    uint16_t *out = r->payload;
    *out++ = (uint16_t)r->serial;
    *out++ = (uint16_t)(r->serial >> 16);
    *out++ = r->page;
    *out++ = (uint16_t)(first * 2);
    for (unsigned col = first; col < first + count; ++col)
        for (unsigned row = 0; row < rows; ++row)
            *out++ = r->map[row * columns + col];
    return (unsigned)(out - r->payload) * 2;
}
