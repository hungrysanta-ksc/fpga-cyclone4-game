# SPDX-License-Identifier: MIT
"""Inline273 references in the existing bounded274 packet/credit window."""
from nes_delta231 import ROOT,once
from nes_split274 import source as split

def source():
 s=split()
 producer=(ROOT/'tools/nes_primitive273.c').read_text()
 producer=producer.replace('static unsigned u16(', 'static unsigned u16p275(').replace('static uint32_t u32(', 'static uint32_t u32p275(')
 import re
 producer=re.sub(r'\bu16\(', 'u16p275(',producer)
 producer=re.sub(r'\bu32\(', 'u32p275(',producer)
 # Producer shares the existing wire buffer; no second packet buffer.
 s=once(s,'static unsigned send(unsigned n){', '''
static unsigned emit_at275,emit_overflow275;
void emit273(unsigned b){
 if(emit_at275<257)wire259[emit_at275++]=b;
 else emit_overflow275=1;
}
'''+producer+'''
static unsigned send(unsigned n){''')
 s=once(s,' unsigned c=65535;for(unsigned i=0;i<=n;i++)c=crc16(c,wire259[i]);', '''
 emit_at275=n+3;emit_overflow275=0;
 unsigned result275=packet273(wire259+1,n,2);
 if(!result275||emit_overflow275)return fail(22);
 unsigned program275=result275-1;
 if(program275){
  if(n+program275+2>256)return fail(22);
  for(unsigned i=n;i;i--)wire259[i+2]=wire259[i];
  wire259[1]=0;wire259[2]=n-1;n+=program275+2;
 }
 unsigned c=65535;for(unsigned i=0;i<=n;i++)c=crc16(c,wire259[i]);''')
 s=once(s,' if(!h2(seal262))return 0;', ' if(!reset273(serial,generation))return fail(22);\n if(!h2(seal262))return 0;')
 return s

def unwrap(p):
 if p[0]:return p,b''
 assert 18<=len(p)<=256
 n=p[1]+1
 assert 16<=n and n+2<len(p)
 return p[2:2+n],p[2+n:]
