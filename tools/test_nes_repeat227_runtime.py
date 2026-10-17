# SPDX-License-Identifier: MIT
"""Actual227 RUN including op8 queue, exact OAM expansion and existing faults."""
import inspect
import test_nes_fast226_runtime as prior
from nes_repeat227 import once
s=inspect.getsource(prior.main)
extra=r"""
    s=s.replace('0x2121','0x2271')
    s=once(s,'static uint32_t ticks(', 'static uint8_t oam227[2][544];static unsigned repeat227_count;\nstatic uint32_t ticks(')
    s=once(s,'   verify_bank();final_acks++;', '   assert(!memcmp(oam227[cache.target],output.oam,544));verify_bank();final_acks++;')
    s=once(s,'  else assert(p[0]==1||p[1]>=2);', '''  else if(p[1]==4){
   unsigned at=u16(p+10),len=u16(p+(p[0]==2?12:14));
   assert(len&&at+len<=544);
   if(p[0]==8){assert(u16(p+12)==4&&len>=8&&len<=512&&!(at&3)&&!(len&3)&&at+len<=512);repeat227_count++;}
   else assert(p[0]==2||p[0]==4||p[0]==5);
   for(unsigned j=0;j<len;j++)oam227[cache.target][at+j]=p[16+(p[0]==2?j:p[0]==8?(j&3):(j&1))];
  }
  else assert(p[0]==1||p[1]>=2);''')
"""
s=once(s,"    f=d/'host213.c';s=f.read_text()", "    f=d/'host213.c';s=f.read_text()\n"+extra)
s=s.replace(".replace('226','225')",".replace('227','225')")
ns=dict(prior.__dict__);ns['__file__']=__file__;exec(compile(s,'runtime227','exec'),ns)
if __name__=='__main__':ns['main']()
