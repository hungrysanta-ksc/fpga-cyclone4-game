# SPDX-License-Identifier: MIT
"""Actual65816 execution of split byte-domain commands; independent of RTL decode."""
import probe_nes_consumer313 as old
original=old.base.packets

def packets(path):
    for p in original(path):
        if p[0] not in (2,4,5,8) or p[1]!=5:
            yield p;continue
        start=int.from_bytes(p[10:12],'little')
        length=int.from_bytes(p[12:14] if p[0]==2 else p[14:16],'little')
        done=0
        while done<length:
            first=start+done;bound=1121 if first<1121 else 3169 if first<3169 else 3418
            take=min(length-done,bound-first);assert take>0
            q=bytearray(p[:16]);q[10:12]=first.to_bytes(2,'little')
            if p[0]==2:
                q[12:14]=take.to_bytes(2,'little');q+=p[16+done:16+done+take]
            else:
                period=4 if p[0]==8 else 2
                q[14:16]=take.to_bytes(2,'little');q+=bytes(p[16+(done+i)%period] for i in range(period))
            yield bytes(q);done+=take

old.base.packets=packets
if __name__=='__main__':old.main()
