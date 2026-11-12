/* A checked empty map queue permits OBJ immediately. The same input
 * callback is owed after OAM and can only run after a new checked drain. */
.syntax unified
.thumb
.cpu cortex-m4
.global hold747, pay747
.equ owed,0x2001fe18
hold747:
 ldr r3,=owed
 str r0,[r3]
 ldr r3,[r0,#8]
 ldr r0,[r0,#12]
 blx r3
 cmp r0,#0
 beq.w poll_fail
 b.w submit_obj
pay747:
 cbz r0,return747
 push {r4,lr}
 sub sp,#16
 ldr r3,=owed
 ldr r4,[r3]
 movs r0,#0
 str r0,[r3]
 mov r0,r4
 mov r1,sp
 bl drain_window
 cbz r0,done747
 ldr r3,[r4]
 ldr r1,[r4,#8]
 ldr r0,[r4,#12]
 mov ip,r3
 movs r2,#4
 movs r3,#0
 blx ip
done747:
 add sp,#16
 pop {r4,lr}
return747:
 add sp,#136
 pop {r4-r6,pc}
.ltorg
