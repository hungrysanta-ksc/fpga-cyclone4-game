/* Bounded shadow of two displayed banks. Call publish only after the existing
 * independent display ACK. A failed update closes this history for reuse. */
#include <stdint.h>
#include <string.h>

enum { colors = 64, columns = 52, height = 23, stored = 21, empty = 255 };
typedef uint16_t mapword869 __attribute__((may_alias));
struct history {
    uint32_t epoch, serial[2], repeat;
    uint16_t palette[colors];
    uint8_t ids[2][64], dict[columns][stored], color_count;
};
_Static_assert(sizeof(struct history) <= 1368, "replace existing column_map");

struct publication {
    uint32_t epoch, serial;
    const mapword869 *map;
    uint16_t page, col, count, bank;
    uint32_t mode; /* 0 unchanged, 1 strip, 2 refresh both 23-row pages */
    uint32_t other_rows[2]; /* ordinary map coverage outside the strip */
};

static uint32_t choose_rows(const mapword869 *map)
{
    uint32_t mask = 0;
    unsigned run=0,best=0,first=0;
    for (unsigned y = 1; y < height; ++y) {
        if (memcmp(map+y*32, map+(y-1)*32, 64) ||
            memcmp(map+1024+y*32, map+1024+(y-1)*32, 64)) {
            run=0;
            continue;
        }
        if (!mask) mask=1u<<y;
        else if (!(mask & (mask-1))) mask |= 1u<<y;
        if (++run>best) { best=run; first=y+1-run; }
    }
    if (best>=2) return 3u<<first;
    return (mask & (mask-1)) ? mask : 0;
}

static int column(struct history *h, const mapword869 *src, uint8_t *id)
{
    uint8_t values[stored];
    unsigned n = 0;
    for (unsigned row = 0; row < height; ++row) {
        uint16_t word = src[row*32];
        if (h->repeat & (1u<<row)) {
            if (word != src[(row-1)*32]) return 0;
            continue;
        }
        unsigned i = 0;
        while (i<h->color_count && h->palette[i]!=word) ++i;
        if (i==colors) return 0;
        if (i==h->color_count) {
            h->palette[i] = word;
            ++h->color_count;
        }
        values[n++] = (uint8_t)i;
    }
    *id = empty;
    /* Use only referenced entries. An unreferenced entry can immediately be
     * recycled. The peer's references remain live throughout the update. */
    uint64_t live = 0;
    for (unsigned bank=0; bank<2; ++bank)
        for (unsigned j=0; j<64; ++j) {
            unsigned v=h->ids[bank][j];
            if (v!=empty) live |= UINT64_C(1)<<v;
        }
    unsigned free_slot = columns;
    for (unsigned i=0; i<columns; ++i) {
        if (!(live & (UINT64_C(1)<<i))) {
            if (free_slot==columns) free_slot=i;
        } else if (!memcmp(values,h->dict[i],stored)) {
            *id=(uint8_t)i;
            return 1;
        }
    }
    if (free_slot==columns) return 0;
    memcpy(h->dict[free_slot],values,stored);
    *id=(uint8_t)free_slot;
    return 1;
}

int publish869(struct history *h, const struct publication *p)
{
    unsigned bank=p->bank, mode=p->mode;
    if (bank>1 || !p->serial || mode>2) return 0;
    if (h->epoch!=p->epoch || (!h->serial[0] && !h->serial[1])) {
        h->serial[0]=h->serial[1]=0;
        h->repeat=choose_rows(p->map);
        if (!h->repeat) return 0;
        h->epoch=p->epoch;
        h->color_count=0;
        memset(h->ids,empty,sizeof(h->ids));
    }
    if (!h->serial[bank] || p->serial<3 || h->serial[bank]!=p->serial-2)
        mode=2;
    if (!mode && !(p->other_rows[0] | p->other_rows[1])) {
        h->serial[bank]=p->serial;
        return 1;
    }
    h->serial[bank]=0;
    unsigned begin=0,end=0;
    if (mode==2) {
        end=64;
    } else if (mode==1) {
        if ((p->page!=0 && p->page!=2048) || !p->count || p->count>2 ||
            p->col+p->count>32) return 0;
        begin=p->page/64+p->col;
        end=begin+p->count;
    }
    int has_ordinary=(p->other_rows[0] | p->other_rows[1])!=0;
    unsigned limit=has_ordinary ? 64 : end;
    for (unsigned j=has_ordinary ? 0 : begin; j<limit; ++j) {
        const mapword869 *src=p->map+(j/32)*1024+j%32;
        if (j<begin || j>=end) {
            unsigned rows=p->other_rows[j/32] & 0x7fffffu;
            int dirty=0;
            while (rows) {
                unsigned row=__builtin_ctz(rows), index=row;
                unsigned skipped=h->repeat & ((2u<<row)-1);
                while (skipped) { --index; skipped &= skipped-1; }
                unsigned id=h->ids[bank][j];
                if (src[32*row]!=h->palette[h->dict[id][index]]) { dirty=1; break; }
                rows &= rows-1;
            }
            if (!dirty) continue;
        }
        if (!column(h,src,&h->ids[bank][j])) {
            memset(h->ids[bank],empty,sizeof(h->ids[bank]));
            return 0;
        }
    }
    h->serial[bank]=p->serial;
    return 1;
}

void stop869(struct history *h)
{
    h->serial[0]=h->serial[1]=0;
}

/* The receiver compares both published banks for omitted words. Different
 * column IDs guarantee a difference somewhere, so send that entire column. */
unsigned prepare869(const struct history *h, const struct publication *p, uint16_t out[50])
{
    unsigned bank=p->bank;
    if (bank>1 || (p->page && p->page!=2048) || p->serial<=2 || h->epoch!=p->epoch ||
        h->serial[bank]!=p->serial-2 || h->serial[1-bank]!=p->serial-1) return 0;
    unsigned first=0, count=0;
    for (unsigned col=0; col<32; ++col) {
        unsigned pos=p->page/64+col, id=h->ids[bank][pos];
        if (id==h->ids[1-bank][pos]) {
            const uint8_t *cell=h->dict[id];
            unsigned row=0;
            for (; row<height; ++row) {
                if (row && !(h->repeat & (1u<<row))) ++cell;
                if (h->palette[*cell]!=p->map[p->page/2+32*row+col]) break;
            }
            if (row==height) continue;
        }
        if (!count) first=col;
        if (col!=first+count || ++count>2) return 0;
    }
    if (!count) return 0;
    uint32_t base=h->serial[bank];
    memcpy(out,&base,4);
    out[2]=p->page;
    out[3]=(uint16_t)(first*2);
    unsigned n=4;
    for (unsigned col=first; col<first+count; ++col)
        for (unsigned row=0; row<height; ++row)
            out[n++]=p->map[p->page/2+32*row+col];
    return n*2;
}
