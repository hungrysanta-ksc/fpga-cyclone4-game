/* SPDX-License-Identifier: MIT */
#include <stdio.h>
#include "nes_clock_report090.h"
const char *clock_label090(enum clock_result088 r) {
 switch(r) {
 case CLOCK088_ACTIVE:return "CLOCK ACTIVE";
 case CLOCK088_ABSENT:return "CLOCK ABSENT";
 case CLOCK088_UNSTABLE:return "CLOCK UNSTABLE";
 case CLOCK088_NO_PROGRESS:return "NO CLOCK PROGRESS";
 default:return 0;
 }
}
static unsigned long le090(const uint8_t *p){return (unsigned long)((uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24);}
unsigned clock_text090(char *out,unsigned size,const struct clock_report088 *r) {
 if(!out||!size||!r||r->captured>2||!clock_label090(r->result))return 0;
 unsigned used=0;
#define APPEND(...) do {int count=snprintf(out+used,size-used,__VA_ARGS__);if(count<0||(unsigned)count>=size-used){out[0]=0;return 0;}used+=(unsigned)count;}while(0)
 APPEND("CLOCKREPORT090 / FPGA CF87 / MCU CONFIG089 READER088\n"
        "RESULT: %s\n"
        "ACTIVE means observed activity, NOT frequency or electrical approval.\n"
        "CLKIN_ASSUMED_HZ: 8000000 (not measured)\n"
        "WINDOW_CYCLES: 8000000; REFERENCE_DIVISOR: 16\n"
        "START_TICK: %lu; ELAPSED_TICKS_10MS: %lu\n"
        "ATTEMPTS: %lu; SPI_FRAMES: %lu; CAPTURED_WINDOWS: %u\n"
        "Initial snapshot is a baseline; startup window1 is excluded.\n",
        clock_label090(r->result),(unsigned long)r->started,(unsigned long)r->elapsed,
        (unsigned long)r->attempts,(unsigned long)r->frames,r->captured);
 for(unsigned i=0;i<3;i++) {
  const uint8_t *s=i?r->sample[i-1]:r->initial;
  APPEND("%s%u RAW:",i?"SAMPLE":"INITIAL",i);
  for(unsigned j=0;j<16;j++)APPEND(" %02X",(unsigned)s[j]);
  APPEND("\n  SEQUENCE: %lu; COUNT: %lu; WINDOW: %lu; DIVISOR: %u\n"
         "  FLAGS: %02X; VALID: %u; LIVE: %u; EVER_GAP: %u; LAST_GAP: %u\n",
         le090(s+2),le090(s+6),le090(s+10),(unsigned)s[14],(unsigned)s[1],
         s[1]&1u,(s[1]>>1)&1u,(s[1]>>2)&1u,(s[1]>>3)&1u);
 }
 APPEND("Uncaptured samples remain zero; consult CAPTURED_WINDOWS.\n"
        "FILE ALONE DOES NOT PROVE SAVE SUCCESS: check TXT SAVED + READBACK OK.\n"
        "Power off, restore normal044, then use the normal menu.\n");
#undef APPEND
 return used;
}
