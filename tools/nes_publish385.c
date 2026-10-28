/* SPDX-License-Identifier: MIT */
/* Component candidate only. A next-source decoder may advance receiver280,
 * but it must not expand/commit the next planner input before this display
 * retires. Reuse the current input/resident/dirty metadata;no shadow record.
 * The incremental SPI/IRQ scheduler and next-hint namespace are not here. */
#include "nes_delta231.h"
extern struct nes_native165 input285;
extern struct nes_resident211 resident285;
extern struct nes_dirty231 dirty285;
extern volatile unsigned source_cancel367;
extern unsigned source_error367;
extern uint32_t raw_groups352,display_epoch352,display_serial352,display_count352;

unsigned publish385(void){
 if(source_cancel367||source_error367||input285.state!=NES_NATIVE165_COMMITTED||
    input285.patch_count>2||dirty285.open||!dirty285.valid||dirty285.fault||
    resident285.open||!resident285.displayed||resident285.fault||
    !resident285.epoch||!resident285.serial||resident285.serial==UINT32_MAX||
    input285.generation!=resident285.generation||dirty285.generation!=resident285.generation||
    dirty285.epoch!=resident285.epoch||dirty285.serial!=resident285.serial){
  raw_groups352=UINT32_MAX;display_epoch352=0;return 0;
 }
 display_epoch352=resident285.epoch;display_serial352=resident285.serial;
 display_count352=(uint32_t)input285.patch_count*256u;return 1;
}
