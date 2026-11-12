/* SPDX-License-Identifier: MIT
 * Fixed-prefix experiment for the pinned 727 long ARM image. R4..R6 are
 * send635's bank index, sink and command buffer at its original memcpy call.
 * Four diagnostic words hold the bounded job with the original stack payload.
 */
.syntax unified
.thumb
.cpu cortex-m4
.global start746, full746, piece746, fallback746
.equ scratch, 0x2001fe00
start746:
 ldr r3, =scratch
 str r6, [r3]
 str r1, [r3,#4]
 ldr r0, [r5,r4,lsl #2]
 str r0, [r3,#8]
 movs r0,#0
 str r0,[r3,#12]
 b.w send_tail
full746:
 push.w {r0-r8,lr}
 bl finish
 pop.w {r0-r8,lr}
 b.w retry_status
fallback746:
 push.w {r0-r8,lr}
 bl finish
 pop.w {r0-r8,lr}
 b.w submit_tile
piece746:
 push.w {r0-r8,lr}
 movs r2,#56
 bl copy_part
 pop.w {r0-r8,lr}
 ldr r3,[r4,#8]
 ldr r0,[r4,#12]
 blx r3
 cmp r0,#0
 bne.w next_poll
 mov r0,r4
 movs r1,#2
 b.w fail_through
finish:
 ldr r3,=scratch
 ldr r0,[r3,#12]
 rsbs r2,r0,#112
copy_part:
 push {r4-r6,lr}
 ldr r4,=scratch
 ldr r5,[r4,#12]
 ldr r0,[r4]
 ldr r1,[r4,#4]
 add r0,r5
 add r1,r5
 adds r6,r5,r2
 bl copy_bytes
 cmp r6,#112
 bne partial
 ldr r0,[r4]
 ldr r1,[r4,#8]
 str r1,[r0,#112]
 movs r6,#116
partial:
 str r6,[r4,#12]
 pop {r4-r6,pc}
.ltorg
