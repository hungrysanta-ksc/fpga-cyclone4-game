// SPDX-License-Identifier: MIT
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "nes_budget210.h"
#include "nes_cost471.h"
#include "nes_plan215.h"
struct nes_plan215 nes_plan215;
static char text[6144];
int main(void){
 nes_budget210_reset();memset(nes_budget210.bins,255,sizeof nes_budget210.bins);nes_budget210.failed_transfers=UINT32_MAX;
 nes_cost471_begin();assert(!nes_cost471_available);
 for(unsigned i=0;i<12;i++){nes_cost471_ops[i].cycles=UINT64_MAX;nes_cost471_ops[i].calls=nes_cost471_ops[i].bytes=nes_cost471_ops[i].max_cycles=UINT32_MAX;}
 for(unsigned i=0;i<3;i++)nes_cost471_phases[i]=nes_cost471_ops[0];
 nes_cost471_end();int n=nes_budget210_format(text,sizeof text);
 assert(n>4096&&n<(int)sizeof text&&text[n]==0&&strstr(text,"cost_schema=471")&&strstr(text,"cost_phase_02="));
 assert(strstr(text,"4294967295,4294967295,4294967295,4294967295,4294967295"));
 printf("PASS471 worst-case budget+cost report bytes=%d capacity=%u fallback_available=%u\n",n,(unsigned)sizeof text,(unsigned)nes_cost471_available);return 0;
}
