/* SPDX-License-Identifier: MIT
 * Isolated 727 Thumb entry points. The stack, guard and receipt comparisons are
 * the normal linked routines. These hooks only change the quiet retry budget.
 */
.syntax unified
.thumb
.cpu cortex-m4
.global begin747, measured747, eager747
.equ timer,0xe0001004
.equ stamp,0x2001fe10
begin747:
 ldr r1,=timer
 ldr r1,[r1]
 ldr r0,=stamp
 str r1,[r0]
 mov r1,r5
 b.w status_arg
measured747:
 ldr r3,=stamp
 ldr r3,[r3]
 ldr r0,[r8,#4]
 subs r10,r0,r3
 /* Cap long interrupt or input-service outliers at two normal wait slots. */
 cmp.w r10,#21504
 it hi
 movhi.w r10,#21504
 mov r9,r0
 b.w guard_loop
eager747:
 movs.w r10,#0
 ldr r9,[r8,#4]
 b.w guard_loop
.global compare747
compare747:
 cmp r3,r10
 b.w repeat_wait
.ltorg

/* Fold byte*x^8 modulo x^8+x^2+x+1. R0 and R1 have the normal CRC ABI. */
.global final_crc747
final_crc747:
 movs r2,#0
crc_byte747:
 ldrb r3,[r0],#1
 eors r3,r2
 eor r2,r3,r3,lsr #6
 eor r3,r2,r3,lsr #7
 eor r2,r3,r3,lsl #1
 eor r2,r2,r3,lsl #2
 uxtb r2,r2
 subs r1,#1
 bne crc_byte747
 mov r0,r2
 bx lr
