/* Validate decoded geometry independently of the installed FPGA profiles. */
#include <assert.h>
#include <stdio.h>
#include "../../src/nes/nes_cartridge_header.h"

int main(void) {
    struct nes_cartridge cart;
    uint8_t h[16] = {'N','E','S',26,2,1,0xaf,0xbb,0x5c,0,0x76,0x87,3,9,1,7};
    const uint32_t payload_end = 528 + 32768 + 8192;
    assert(nes_decode_cart(h, payload_end + 7, &cart));
    assert(cart.format == NES_20 && cart.mapper == 0xcba && cart.submapper == 5);
    assert(cart.prg_offset == 528 && cart.prg_size == 32768 && cart.chr_offset == 33296);
    assert(cart.chr_size == 8192 && cart.tail_size == 7 && cart.wiring == 15);
    assert(cart.work_ram == 0x76 && cart.pattern_ram == 0x87 && cart.timing == 3);
    assert(cart.device == 7 && cart.console == 3 && cart.console_detail == 9 && cart.misc == 1);
    assert(!nes_cart_profile(&cart));
    assert(!nes_decode_cart(h, payload_end, &cart));
    for (unsigned exponent = 0; exponent < 64; exponent++) {
        for (unsigned m = 0; m < 4; m++) {
            const unsigned multiplier = 2*m + 1;
            uint32_t actual;
            int ok = nes_rom_size(exponent*4 + m, 15, 14, &actual);
            if (exponent >= 32 || ((uint64_t)multiplier << exponent) > UINT32_MAX) {
                assert(!ok);
            } else {
                assert(ok && actual == ((uint64_t)multiplier << exponent));
            }
        }
    }
    h[14] = 0;
    for (unsigned pos = 0; pos < payload_end; pos++)
        assert(!nes_decode_cart(h, pos, &cart));
    assert(nes_decode_cart(h, payload_end, &cart));
    memcpy(h,"UNIF",4);
    assert(!nes_decode_cart(h,32,&cart) && cart.format == NES_UNIF);
    memcpy(h,"FDS\032",4);
    assert(!nes_decode_cart(h,16,&cart) && cart.format == NES_FDS);
    puts("PASS decoded metadata, trainer offsets, truncation, all 256 exponent encodings and container signatures");
    return 0;
}
