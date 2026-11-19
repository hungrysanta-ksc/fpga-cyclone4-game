/* The inactive bank may be omitted only in columns known equal in both
 * last ACKed banks. A disagreeing column is always sent in its entirety. */
#include <stdint.h>
#include <string.h>
typedef uint16_t mapword869 __attribute__((may_alias));
struct right869 {
    /* keep is the first of two rows equal to their predecessor. */
    uint32_t differing, keep;
    uint16_t words[21*32];
};
_Static_assert(sizeof(struct right869)<=1368,"reuse the two-bank summary storage");

static uint32_t compare869(const struct right869 *h,const mapword869 *map)
{
    uint32_t diff=0;
    const uint16_t *row=h->words;
    for (unsigned y=0;y<23;++y,map+=32) {
        if (y && (y<h->keep || y>h->keep+1)) row+=32;
        if (!memcmp(row,map,64)) continue;
        for (unsigned col=0;col<32;++col)
            if (row[col]!=map[col]) diff |= 1u<<col;
    }
    return diff;
}

/* The sink already owns epoch/serial checks. Invalidate before touching
 * storage and publish keep last, only on the existing final ACK path. */
static void remember869(struct right869 *h,const mapword869 *map,int same)
{
    if (h->keep && same) {
        h->differing=0;
        return;
    }
    uint32_t diff=h->keep ? compare869(h,map) : UINT32_MAX;
    h->keep=0;
    unsigned keep=1;
    while (keep<22 && memcmp(map+(keep-1)*32,map+keep*32,128)) ++keep;
    if (keep==22) return;
    memcpy(h->words,map,keep*64);
    memcpy((uint8_t *)h->words+keep*64,map+(keep+2)*32,(21-keep)*64);
    h->differing=diff; h->keep=keep;
}

static unsigned right_packet869(const struct right869 *h,const mapword869 *map,uint32_t serial,uint16_t *out)
{
    if (!h->keep || h->differing==UINT32_MAX) return 0;
    uint32_t mask=h->differing | compare869(h,map);
    if (!mask) return 0;
    unsigned col=__builtin_ctz(mask);
    unsigned bits=mask>>col;
    if (bits!=1 && bits!=3) return 0;
    uint32_t base=serial-2;
    memcpy(out,&base,4); out[2]=2048; out[3]=(uint16_t)(col*2);
    unsigned n=4;
    for (;mask;mask &= mask-1,++col)
        for (unsigned y=0;y<23;++y) out[n++]=map[y*32+col];
    return n*2;
}
