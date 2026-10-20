# SPDX-License-Identifier: MIT
"""Generate the actual ARM serializer with bounded command splitting."""
from nes_delta231 import ROOT,once

def source():
 s=(ROOT/'tools/nes_output270.c').read_text()
 s=once(s,'static unsigned h2(', (ROOT/'tools/nes_split274.inc').read_text()+'\nstatic unsigned h2(')
 s=once(s,'w16(c+22,digest);','scroll274=scroll;raw274=raw;\n w16(c+22,digest);')
 s=once(s,'  for(unsigned i=0;i<n;i++)wire259[i+1]=p[i];',
 '''  if(p[0]==2||p[0]==10||p[0]==11){
   if(!parts274(p,n,1)||!parts274(p,n,0))return 0;
   continue;
  }
  for(unsigned i=0;i<n;i++)wire259[i+1]=p[i];''')
 return s
