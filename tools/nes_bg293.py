# SPDX-License-Identifier: MIT
"""Publish the final BG batch only at the checked BG/OBJ phase boundary."""
from nes_delta231 import once
from nes_native289 import prepare as native289


def apply_bg(d):
    p=d/'nes_planner285.c';s=p.read_text()
    s=once(s,'static bool flush285(void){','static unsigned reserve_bytes293,reserve_plans293;\nstatic bool flush285(void){\n reserve_bytes293=reserve_plans293=0;')
    s=once(s,'static bool emit285(','''static bool flush_bg293(void){
 unsigned bytes=batch_size285,plans=batch_count285;
 if(!flush285())return false;
 /* Preserve the ORIGINAL mixed BG/OBJ batch's sorting boundary. The next
  * OBJ batch spends its old remaining capacity despite the earlier E9. */
 reserve_bytes293=bytes;reserve_plans293=plans;return true;
}
static bool emit285(''')
    s=once(s,'if(batch_count285==15||batch_size285+n>240)', 'if(batch_count285+reserve_plans293==15||batch_size285+n+reserve_bytes293>240)')
    s=once(s,'return batch_count285<15||flush285();','return batch_count285+reserve_plans293<15||flush285();')
    s=once(s,'unsigned begin285(void){','unsigned begin285(void){\n reserve_bytes293=reserve_plans293=0;')
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_planner211.c';s=p.read_text()
    assert 'unsigned step286(void)' in s and 'ctx286.g<ctx286.groups' in s
    s+='\nunsigned bg_done293(void){return ctx286.phase==2&&ctx286.g==ctx286.groups;}\n'
    p.write_text(s,encoding='utf-8',newline='\n')
    p=d/'nes_input286.inc';s=p.read_text()
    s='extern unsigned bg_done293(void);\n'+s
    s=once(s,'if(result==2&&!flush285())return 0;', 'if(result==2&&!flush285())return 0;if(result==1&&bg_done293()&&!flush_bg293())return 0;')
    p.write_text(s,encoding='utf-8',newline='\n')


def prepare(d):
    result=native289(d);apply_bg(d);return result


def unbatch(data):
    """Return exact encoded records; framing alone may change, not semantics."""
    at=0;out=[]
    while at<len(data):
        assert at+3<=len(data)
        size=int.from_bytes(data[at:at+2],'little');count=data[at+2];at+=3;end=at+size
        assert 0<count<=15 and size<=240 and end<=len(data)
        for _ in range(count):
            assert at<end
            op=data[at]
            if op&128:
                assert op in (128,129,130);n={128:7,129:8,130:3}[op]
            else:
                assert op in (0,1,2) and at+16<=end;n=16+2*data[at+1].bit_count()
            assert at+n<=end;out.append(data[at:at+n]);at+=n
        assert at==end
    return out
