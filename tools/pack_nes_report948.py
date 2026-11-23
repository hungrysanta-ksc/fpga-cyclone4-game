"""Store the end of each ASCII report word in its last byte for the same token ABI."""
import ast
import re

from nes_raw506 import once
from prepare_nes_report594 import literal


def compact(src):
    path=src/'nes_budget210.c'
    code=path.read_text()
    decl=re.search(r'static const char words\[\] = (".*?");',code)
    words=ast.literal_eval(decl[1]).encode('latin1').split(b'\0')[:-1]
    assert words and all(all(0<b<128 for b in word) for word in words)
    packed=b''.join(w[:-1]+bytes((w[-1]|128,)) if w else b'\x80' for w in words)
    reconstructed=[]
    word=bytearray()
    for b in packed:
        if b&127:
            word.append(b&127)
        if b&128:
            reconstructed.append(bytes(word))
            word.clear()
    assert not word and reconstructed==words
    code=once(code,decl[0],'static const unsigned char words[] = '+literal(packed)+';')
    old='const char *word=words; while(symbol-->128){while(*word++){} }\n   while (*word) *next++ = *word++;'
    new='''const unsigned char *word=words;
   while(symbol-->128){while(!(*word++ & 128)){} }
   unsigned ch;
   do {ch=*word++; if(ch&127)*next++=(char)(ch&127);} while(!(ch&128));'''
    path.write_text(once(code,old,new),newline='\n')

def check_link(src,reference):
    """Capture the format passed to vsnprintf by the actual linked ARM decoder."""
    from check_nes_frame862_arm import TimedProbe
    from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R2, UC_ARM_REG_LR, UC_ARM_REG_PC
    class Decoder(TimedProbe):
        def hook(self,u,at,size,user):
            if at==self.syms['vsnprintf']:
                ptr=u.reg_read(UC_ARM_REG_R2)
                self.decoded=bytes(u.mem_read(ptr,720)).split(b'\0',1)[0]
                u.reg_write(UC_ARM_REG_R0,len(self.decoded))
                u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
                return
            super().hook(u,at,size,user)

    decl=re.search(r'static const char words\[\] = (".*?");',(reference/'nes_budget210.c').read_text())
    words=ast.literal_eval(decl[1]).encode('latin1').split(b'\0')[:-1]
    q=Decoder(src)
    # Include ASCII on both sides and repeat every token, including empty words.
    for i,w in enumerate(words):
        encoded=bytes((65,i+128,i+128,66,0))
        q.u.mem_write(0x20012000,encoded)
        q.decoded=None
        q.call('nes_vreport828',[0x20014000,720,0x20012000,0])
        assert q.decoded==b'A'+w+w+b'B',i
    return len(words)
