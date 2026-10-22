# SPDX-License-Identifier: MIT
"""Emit one ordered short 0x87 BG-close record, never a frame END."""
from nes_bg294 import prepare as previous
from nes_delta231 import once

def prepare(d):
    previous(d)
    p=d/'nes_planner285.c';s=p.read_text()
    s=once(s,'reserve_bytes293=bytes;reserve_plans293=plans;return true;', """reserve_bytes293=bytes;reserve_plans293=plans;
 if(output_size285+6>sizeof output285)return false;
 output285[output_size285++]=3;output285[output_size285++]=0;output285[output_size285++]=1;
 output285[output_size285++]=0x87;output285[output_size285++]=resident285.generation;output285[output_size285++]=resident285.generation>>8;return true;""")
    p.write_text(s,newline='\n')
    p=d/'nes_native289.c';s=p.read_text()
    s=once(s,'static unsigned at290,used290,kind290,first290;', 'static unsigned at290,used290,kind290,first290,bg_seen295;')
    s=s.replace('at290=used290=kind290=first290=0;', 'at290=used290=kind290=first290=bg_seen295=0;')
    s=once(s,'if(k==3||((p[0]&128)?p[0]>130:p[0]>2))return 0;', """if(p[0]==0x87){
    if(bg_seen295||count||end-at!=3||(p[1]|(unsigned)p[2]<<8)!=resident285.generation)return 0;
    if(used&&!bulk289(kind,first,used))return 0;
    used=0;bg_seen295=1;at+=3;continue;
   }
   if(k==3||((p[0]&128)?p[0]>130:p[0]>2)|| (bg_seen295?k!=1:k==1))return 0;""")
    s=once(s,'if(!resident285.prepared||!dirty285.prepared||!video285.valid)return 0;', 'if(!bg_seen295||!resident285.prepared||!dirty285.prepared||!video285.valid)return 0;')
    p.write_text(s,newline='\n')

def unbatch(data):
    at=0;out=[];closed=False;generation=None
    while at<len(data):
        assert at+3<=len(data)
        size=int.from_bytes(data[at:at+2],'little');count=data[at+2];at+=3;end=at+size
        assert 0<count<=15 and size<=240 and end<=len(data)
        for i in range(count):
            op=data[at];n=3 if op==135 else {128:7,129:8,130:3}[op] if op&128 else 16+2*data[at+1].bit_count()
            assert at+n<=end
            g=int.from_bytes(data[at+(1 if op&128 else 2):at+(3 if op&128 else 4)],'little')
            if generation is None:generation=g
            assert g==generation
            if op==135:assert not closed and count==1;closed=True
            else:
                assert op in (0,1,2,128,129,130) and ((op&3)==1 if closed else (op&3)!=1)
                out.append(data[at:at+n])
            at+=n
        assert at==end
    assert closed
    return out
