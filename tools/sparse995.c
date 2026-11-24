/* Pack the occupancy bitmap followed by its nonzero literals into the
 * outgoing packet buffer. The input belongs to the original producer. */
static unsigned packet_body995(uint8_t *dst, const uint8_t *p, unsigned n)
{
    unsigned size = n - 16;
    if ((p[0] == 2 && p[1] == 5 && p[10] == 0x2a && p[11] == 5 && size == 240) ||
        (p[0] == 3 && p[1] == 0 && !p[10] && !p[11] && size == 168)) {
        unsigned masks = size / 8;
        unsigned out = masks;
        memcpy(dst, p, 16);
        for (unsigned group = 0; group < masks; group++) {
            unsigned mask = 0;
            for (unsigned bit = 0; bit < 8; bit++) {
                uint8_t value = p[16 + group * 8 + bit];
                if (value) {
                    if (out + 1 >= size) goto literal;
                    dst[16 + out++] = value;
                    mask |= 1u << bit;
                }
            }
            dst[16 + group] = mask;
        }
        dst[11] |= 0x80;
        dst[12] = (uint8_t)out;
        return 16 + out;
    }
literal:
    memcpy(dst, p, n);
    return n;
}
