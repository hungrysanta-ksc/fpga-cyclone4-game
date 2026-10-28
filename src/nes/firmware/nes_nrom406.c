// SPDX-License-Identifier: MIT
#include "nes_nrom406.h"

bool nes_nrom406_header(const uint8_t h[16], uint32_t size,
                        struct nes_nrom406_profile *p) {
 if (!h || !p || h[0]!='N' || h[1]!='E' || h[2]!='S' || h[3]!=0x1a ||
     (h[4]!=1 && h[4]!=2) || h[5]!=1 || (h[6]&0xfe)!=0 || h[7]!=0)
  return false;
 for (unsigned i=8;i<16;i++) if (h[i]) return false;
 uint32_t prg=(uint32_t)h[4]*16384u;
 if (size!=16u+prg+8192u) return false;
 p->prg_bytes=prg;
 p->file_bytes=size;
 p->vertical=(h[6]&1u)!=0;
 return true;
}

bool nes_nrom406_layout(const struct nes_nrom406_profile *p,
                        uint32_t at, bool *from_file, uint32_t *file_at) {
 if (!p || !from_file || !file_at ||
     (p->prg_bytes!=16384u && p->prg_bytes!=32768u) ||
     p->file_bytes!=16u+p->prg_bytes+8192u || at>=0x60000u)
  return false;
 *from_file=false;
 *file_at=0;
 if (at<p->prg_bytes) {
  *from_file=true;
  *file_at=16u+at;
 } else if (at>=0x40000u && at<0x42000u) {
  *from_file=true;
  *file_at=16u+p->prg_bytes+(at-0x40000u);
 }
 return true;
}
