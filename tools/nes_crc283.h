/* SPDX-License-Identifier: MIT */
/* CRC-8/poly07, same initial state and byte order. Two checked nibble steps
 * replace eight bit iterations. All received bytes remain covered. */
static inline unsigned crc_byte283(unsigned c,unsigned b){
 static const uint8_t lut[16]={0,7,14,9,28,27,18,21,56,63,54,49,36,35,42,45};
 c^=b;c=((c<<4)&255)^lut[c>>4];return ((c<<4)&255)^lut[c>>4];
}
