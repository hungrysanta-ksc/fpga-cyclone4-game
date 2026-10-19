# SPDX-License-Identifier: MIT
"""Host-executed planner HDMA semantics and ARM object cost; no MCU timing."""
from pathlib import Path
import argparse,ctypes,json,shutil,subprocess
from nes_delta231 import ROOT,BASE,sha

def oracle(b,mask,raw,scrollsize):
 # Independent wire-layout oracle for validate181, plus the planner's recorded
 # scroll length (SNES raw mode uses padded section length3418 instead).
 if mask not in (0x18,0x1e) or not 0<=raw<=7 or not 1<=scrollsize<=1121:return False
 total=0;i=0
 while i<1121 and b[i]:
  if b[i]>=128:return False
  total+=b[i];i+=5
 if i>=1121 or total!=224 or scrollsize!=i+1:return False
 if not raw:return True
 total=rawtotal=0;i=0
 while i<81:
  n=b[3169+i]
  if not n:break
  if i+4>=81 or n>=128 or b[3250+i]!=n or b[3331+i]!=n:return False
  total+=n
  if total>224:return False
  word=lambda at:int.from_bytes(b[at:at+2],'little')
  mode=word(3170+i)
  if mode not in (0,3):return False
  rawtotal+=n if mode==3 else 0
  if word(3251+i)!=mode:return False
  expected=(0x38,0x58,1,0) if mode else (0x31,0x51,17,17 if mask==0x18 else 0)
  if tuple(word(at+i) for at in (3172,3253,3332,3334))!=expected:return False
  i+=5
 if i>=81 or total!=224 or rawtotal!=raw or b[3250+i] or b[3331+i]:return False
 return all(int.from_bytes(b[k:k+2],'little')==i+1 for k in (3412,3414,3416))

WRAPPER=r'''
#include <string.h>
#include "nes_native_video165.h"
bool nes_hdma251_validate(const struct nes_native_video165 *);
__declspec(dllexport) int check251(const unsigned char *b,unsigned mask,unsigned raw,unsigned size){
 struct nes_native_video165 p;memset(&p,0,sizeof p);
 memcpy(p.hdma,b,1121);memcpy(p.patch.mode[0],b+3169,81);memcpy(p.patch.mode[1],b+3250,81);memcpy(p.patch.enable,b+3331,81);
 for(unsigned i=0;i<3;i++)p.patch.size[i]=b[3412+i*2]|((unsigned)b[3413+i*2]<<8);
 p.display_mask=mask;p.patch_count=raw;p.hdma_size=size;
 return nes_hdma251_validate(&p);
}
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
 def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
 def run(exe,args,label):
  q=subprocess.run([str(exe),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  (d/(label+'.log')).write_bytes(q.stdout);assert q.returncode==0,q.stdout.decode(errors='replace')[-4000:]
  return q.stdout.decode(errors='replace')
 for n in ('nes_native165.h','nes_native_video165.h'):
  f=pin(BASE/'probes/nes-runtime233/arm01/src'/n);shutil.copyfile(f,d/n)
 shutil.copyfile(pin(ROOT/'tools/nes_hdma251.c'),d/'nes_hdma251.c');shutil.copyfile(__file__,d/'probe.py');(d/'wrapper.c').write_text(WRAPPER)
 gcc='C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe'
 run(gcc,['-std=c99','-O2','-Wall','-Wextra','-Werror','-shared','nes_hdma251.c','wrapper.c','-o','test.dll'],'native')
 lib=ctypes.CDLL(str(d/'test.dll'));fn=lib.check251;fn.argtypes=[ctypes.POINTER(ctypes.c_ubyte),ctypes.c_uint,ctypes.c_uint,ctypes.c_uint];fn.restype=ctypes.c_int
 prior=BASE/'probes/nes-wholepath247/jointdecode-test02/run';seals={}
 for f in prior.glob('req-*.bin'):
  b=f.read_bytes()
  if b[0]==3:pin(f);seals[int.from_bytes(b[8:10],'little')]=b
 cases=accepted=rejected=0;frames=[]
 def check(b,mask,raw,size,expected=None):
  nonlocal cases,accepted,rejected
  ref=oracle(b,mask,raw,size);got=bool(fn((ctypes.c_ubyte*len(b)).from_buffer_copy(b),mask,raw,size));assert got==ref,(cases,mask,raw,size)
  if expected is not None:assert got==expected
  cases+=1;accepted+=got;rejected+=not got
 for g in range(1,72):
  b=pin(prior/f'expected-{g}.bin').read_bytes()[5152:];assert len(b)==3418
  seal=seals[g];mask=int.from_bytes(seal[34:36],'little');raw=int.from_bytes(seal[38:40],'little')
  size=next(i+1 for i in range(0,1121,5) if b[i]==0)
  check(b,mask,raw,size,True);frames.append(dict(frame=g+904,scroll_runs=(size-1)//5,patch_runs=(int.from_bytes(b[3412:3414],'little')-1)//5))
  # Every single byte mutation of control tables/lengths, including ignored
  # padding. The oracle decides acceptance; ignored padding is not called bad.
  for at in list(range(1121))+list(range(3169,3418)):
   z=bytearray(b);z[at]^=0x80;check(z,mask,raw,size)
  for m,r,s in [(0,raw,size),(mask,8,size),(mask,0,size),(mask,raw,0),(mask,raw,1122),(mask,raw,size+1)]:check(b,m,r,s)
 # Normal mode has no raw tables; two runs cover224 lines and exact length11.
 b=bytearray(3418);b[0]=127;b[5]=97
 check(b,0x18,0,11,True);check(b,0x1e,0,11,True)
 b[5]=96;check(b,0x18,0,11,False)
 # Maximum admitted storage:224 scroll runs and16 raw-mode table runs.
 # Recorded71 all have only4+4 runs, so they alone do not cover these bounds.
 b=bytearray(3418)
 for i in range(224):b[i*5]=1
 check(b,0x18,0,1121,True)
 for i in range(16):
  israw=i<7;n=1 if israw else 25 if i<15 else 17;mode=3 if israw else 0
  for off,values in [(3169,(mode,0,0x38 if israw else 0x31,0)),(3250,(mode,0,0x58 if israw else 0x51,0)),(3331,(1 if israw else 17,0,0 if israw else 17,0))]:b[off+i*5:off+i*5+5]=bytes((n,*values))
 for off in (3412,3414,3416):b[off:off+2]=(81).to_bytes(2,'little')
 check(b,0x18,7,1121,True)
 for at in (1120,3249,3330,3411,3412,3414,3416):
  z=bytearray(b);z[at]^=1;check(z,0x18,7,1121,False)
 arm=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
 run(arm/'arm-none-eabi-gcc.exe',['-std=c99','-Os','-Wall','-Wextra','-Werror','-mthumb','-mcpu=cortex-m4','-mfloat-abi=hard','-ffunction-sections','-fstack-usage','-c','nes_hdma251.c','-o','hdma.o'],'arm')
 sizeout=run(arm/'arm-none-eabi-size.exe',['hdma.o'],'size');dis=run(arm/'arm-none-eabi-objdump.exe',['-dr','hdma.o'],'disassembly')
 stack=(d/'hdma.su').read_text();result=dict(passed=True,frames=71,cases=cases,accepted=accepted,rejected=rejected,max_scroll_runs_tested=224,max_patch_runs_tested=16,arm_size=sizeout,stack_usage=stack,frames_detail=frames,input_hashes=pins,scope=__doc__,clock_MHz=84,hardware_cycles_measured=False,full_RUN_linked=False,transport_binding=False)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('frames_detail','input_hashes')}))
if __name__=='__main__':main()
