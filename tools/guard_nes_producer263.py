# SPDX-License-Identifier: MIT
"""Consumer negative tests; native C execution, independent of RTL timing."""
import argparse,ctypes,json,shutil
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_joint261 import packets

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--test',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 assert sha(a.test/'nes_producer263.c')==sha(ROOT/'tools/nes_producer263.c')
 lib=ctypes.CDLL(str((a.test/'producer263.dll').resolve()));call=lib.producer263;call.argtypes=[ctypes.c_int]*3;call.restype=ctypes.c_int
 real=packets(BASE/'probes/nes-joint262/arm01/frame905.packets');begin=real[1];seal=real[-1]
 def packet(b):
  for i,v in enumerate(b):assert call(1,i,v)==0
  return call(2,len(b),0)
 def start():assert call(0,0,0)==0;assert packet(begin)==0
 def make(op,section=2,first=0,payload=b'',count=0):
  h=bytearray(begin[:16]);h[0]=op;h[1]=section;h[10:12]=first.to_bytes(2,'little');h[12:14]=len(payload).to_bytes(2,'little');h[14:16]=count.to_bytes(2,'little');return bytes(h)+payload
 cases=[]
 def test(name,body,want):
  start();got=body();assert got==want,(name,got,want);assert call(4,0,0)==want # first fault sticks
  cases.append(dict(name=name,error=-got))
 test('manifest missing',lambda:packet(seal),-20)
 test('manifest offset',lambda:packet(make(10,first=1,payload=bytes(1))),-25)
 test('RLE marker',lambda:packet(make(11,payload=b'\x02\xff\xff')),-26)
 test('RLE literal truncated',lambda:packet(make(11,payload=b'\x03\x03\x01')),-27)
 test('RLE output overflow',lambda:packet(make(11,payload=b'\x03\xff\xff\x80')),-27)
 test('manifest wrong section',lambda:packet(make(10,section=3,payload=bytes(1))),-25)
 test('ordinary bad bounds',lambda:packet(make(2,section=3,first=511,payload=b'\x01\x02')),-12)
 test('ordinary bad generation',lambda:packet(make(2,section=3,payload=b'\0\0')[:8]+b'\x02\0'+make(2,section=3,payload=b'\0\0')[10:]),-10)
 test('duplicate map descriptor',lambda:(call(6,0,1),call(6,0,1))[-1],-6)
 test('map descriptor overflow',lambda:call(6,2047,2),-5)
 def partial(section,first,data):
  assert packet(make(2,section=section,first=first,payload=data))==0
  assert packet(make(11,payload=b'\x03\xff\xff'))==0
  return packet(seal)
 test('partial CGRAM granule',lambda:partial(3,0,b'\x01'),-21)
 test('partial raw-tail granule',lambda:partial(5,3169,b'\x01'),-22)
 test('fresh scroll terminator missing',lambda:partial(5,0,b'\x70\0\0\0\0\x70\0\0\0\0'),-24)
 # Decode both forms with different bytes and require the independent map
 # observation to agree. This does not read the old422B fixture.
 start();assert packet(make(11,payload=b'\x03\xff\xff'))==0
 assert call(6,0,1)==0;assert packet(seal)==-20;cases.append(dict(name='manifest versus DMA descriptor mismatch',error=20))
 for name,b in [('wrong bank',begin[:18]+b'\x01'+begin[19:]),('wrong epoch',begin[:24]+b'\x02\0\0\0')]:
  assert call(0,0,0)==0;assert packet(b)==-9;cases.append(dict(name=name,error=9))
 vectors=[]
 for section,first,length in [(0,48,32),(1,96,64),(0,0,2048)]:
  start();data=bytes((i*73+11)%256 for i in range(length))
  for i,v in enumerate(data):assert call(5,i,v)==0
  count=packet(make(7,section=section,first=first,payload=b'\x01\0\0\0',count=length));assert count>0
  actual=[call(3,i,0) for i in range(count)];expected=[];unit=32 if section else 16
  for at in range(0,length,16*unit):
   n=min(16,(length-at)//unit);expected.append(0x840000|(1024 if section else 0)+(first+at)//unit|(n<<12))
   expected.extend(0x880000|b for b in data[at:at+n*unit])
  assert actual==expected;vectors.append(dict(section=section,first=first,bytes=length,events=count))
 r=dict(passed=True,cases=cases,tile_event_vectors=vectors,source_sha256=sha(ROOT/'tools/nes_producer263.c'),DLL_sha256=sha(a.test/'producer263.dll'),scope=__doc__)
 shutil.copyfile(__file__,d/'guard_nes_producer263.py');(d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(json.dumps(r))

if __name__=='__main__':main()
