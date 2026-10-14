# SPDX-License-Identifier: MIT
"""Exercise all6 VRAM chunks with max legal BG/OBJ lengths via valid bulk DATA.

Bulk DATA is a SNES packet-boundary fixture, not the production tile-at-a-time
MCU API. Actual C packet/ACK code is included, no forged ACK or VRAM injection.
"""
import inspect
import test_nes_banked169 as prior
src=inspect.getsource(prior.main)
src=src.replace('a=p.parse_args()',"p.add_argument('--reuse-reference',type=Path)\n a=p.parse_args()")
src=src.replace("s='#include \"nes_sink_trace168.h\"\\n'+s", "s='#include \"nes_sink_trace168.h\"\\n#include \"nes_native_sink165.c\"\\n'+s")
src=src.replace("'producer169.c','nes_native_sink165.c','nes_sink_trace168.c'", "'producer169.c','nes_sink_trace168.c'")
anchor=" (a.out/'producer169.c').write_text(s,encoding='utf8',newline='\\n')"
assert src.count(anchor)==1
patch='''
 s=s.replace('GetTickCount()-started<15000','GetTickCount()-started<60000')
 s=s.replace(' for(unsigned i=0;i<bg;i++)assert(nes_sink165_pattern(&s,0,i,pattern+i*16,16));', '''+repr(''' if(gen==17){unsigned old=bg*16;for(unsigned i=old;i<16384;i++)pattern[i]=pattern[i%old];bg=1024;p.bg_count=1024;
  for(unsigned at=0;at<16384;at+=240){unsigned n=16384-at;if(n>240)n=240;assert(packet(&s,2,0,at,pattern+at,n));}s.bg_next=1024;
 }else for(unsigned i=0;i<bg;i++)assert(nes_sink165_pattern(&s,0,i,pattern+i*16,16));''')+''')
 s=s.replace(' for(unsigned i=0;i<obj;i++)assert(nes_sink165_pattern(&s,1,i,pattern+i*32,32));', '''+repr(''' if(gen==17){unsigned old=obj*32;for(unsigned i=old;i<4096;i++)pattern[i]=old?pattern[i%old]:0;obj=128;p.obj_count=128;
  for(unsigned at=0;at<4096;at+=240){unsigned n=4096-at;if(n>240)n=240;assert(packet(&s,2,1,at,pattern+at,n));}s.obj_next=128;
 }else for(unsigned i=0;i<obj;i++)assert(nes_sink165_pattern(&s,1,i,pattern+i*32,32));''')+''')
'''
src=src.replace(anchor,patch+anchor)
src=src.replace("[('overflow',True),('budget',True),('overflow',False),('budget',False),('stop',False)]","[('budget',True),('budget',False)]")
src=src.replace("[('budget',True),('budget',False)]","([('budget',False)] if a.reuse_reference else [('budget',True),('budget',False)])")
src=src.replace(' results=[]', ''' results=[]
 if a.reuse_reference:
  assert (a.reuse_reference/'reference/sink-program.hex').read_bytes()==(a.out/'reference/sink-program.hex').read_bytes()
  shutil.copytree(a.reuse_reference/'budget-reference',a.out/'budget-reference')''')
src=src.replace("'tools/test_nes_banked169.py',","'tools/test_nes_banked169.py','tools/test_nes_banked169_max.py',")
src=src.replace("assert(copied>0,'fallback not exercised')","assert(copied==9,'max6 plus reverse3 chunks')")
src=src.replace("copied=copied+1 end", "if packetword(8)==17 then assert(rd(0x1025)==0xe3,'maximum scene must trigger E3')end;copied=copied+1 end")
src=src.replace("'PASS BANKED169'","'PASS MAX BANKED169'")
src=src.replace('--timeout=240','--timeout=480').replace('m.wait(timeout=250)','m.wait(timeout=490)')
ns=dict(prior.__dict__);exec(compile(src,'max_banked169','exec'),ns)
if __name__=='__main__':ns['main']()
