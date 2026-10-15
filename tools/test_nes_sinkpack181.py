# SPDX-License-Identifier: MIT
"""Reuse actual C/file-mailbox/65816/PPU harness, not mocked display ACKs."""
from pathlib import Path
import inspect, json, struct
import test_nes_client181 as original
from nes_sinkpack181 import build, sink

HOST_PATCH=r'''
 if(get16(b+8)==13 && b[0]==4 && b[1]==2){
  if(!strcmp(mode,"packed_zero")){b[14]=b[15]=0;}
  if(!strcmp(mode,"packed_odd"))b[14]|=1;
  if(!strcmp(mode,"packed_large")){b[14]=242;b[15]=0;}
  if(!strcmp(mode,"packed_size")){b[12]=1;n=17;}
  if(!strcmp(mode,"packed_section"))b[1]=6;
  if(!strcmp(mode,"packed_offset")){b[10]=b[11]=255;}
  if(!strcmp(mode,"packed_token"))b[2]^=1;
 }
'''

def run():
    source=inspect.getsource(original.main)
    lua=(original.ROOT/'snes/video_probe/capture_client181.lua').read_text()
    marker="  acks=acks+1;log:write"
    assert lua.count(marker)==1
    lua=lua.replace(marker,"""  if ack[1]==0 and (pb(0)==2 or pb(0)==4) then
   local offsets={0,0x4000,0x5000,0x6000,0x6200,0x6500}
   local base=0x10000+word(0x1020)+offsets[pb(1)+1]+pw(10)
   local count=pb(0)==4 and pw(14) or pw(12)
   for i=0,count-1 do
    local expected=pb(16+(pb(0)==4 and (i%2) or i))
    assert(rd(base+i)==expected,'staging byte mismatch '..base..' '..i)
   end
  end
"""+marker)
    anchor="(ROOT/'snes/video_probe/capture_client181.lua').read_text()"
    assert source.count(anchor)==1;source=source.replace(anchor,'LUA_SOURCE')
    anchor=" env=os.environ.copy();"
    assert source.count(anchor)==1
    source=source.replace(anchor,""" candidate=a.out/'nes_native_sink165.c'
 candidate.write_text(sink(candidate.read_text()),encoding='utf8',newline='\\n')
 host=a.out/'host.c';text=host.read_text();anchor=' ordinal++;wire_bytes+=n;'
 assert text.count(anchor)==1;text=text.replace(anchor,HOST_PATCH+anchor)
 host.write_text(text,encoding='utf8',newline='\\n')
 sources['candidate/sink.c']=sha(candidate);sources['candidate/host.c']=sha(host)
 env=os.environ.copy();""")
    source=source.replace("print('PASS CLIENT181')","print('PASS SINKPACK181')")
    ns=dict(original.__dict__);ns.update(build=build,sink=sink,HOST_PATCH=HOST_PATCH,LUA_SOURCE=lua)
    exec(compile(source,'sinkpack181-test','exec'),ns);ns['main']()

def packets(directory):
    result={};stats={}
    for p in sorted(directory.glob('req-*.bin')):
        b=p.read_bytes();op,section=b[:2];gen=struct.unpack_from('<H',b,8)[0]
        at,n,expanded=struct.unpack_from('<HHH',b,10)
        q=stats.setdefault(gen,dict(packets=0,request_bytes=0,packed=0,saved=0))
        q['packets']+=1;q['request_bytes']+=len(b)
        assert len(b)==16+n
        if op not in (2,4):continue
        if op==4:
            assert n==2 and 4<=expanded<=240 and expanded%2==0
            data=b[16:]*(expanded//2);q['packed']+=1;q['saved']+=expanded-2
        else:
            assert expanded==0;data=b[16:]
        buf=result.setdefault((gen,section),bytearray());assert len(buf)==at
        buf.extend(data)
    return result,stats

def compare(new,old):
    a,stats=packets(new);b,_=packets(old);assert a==b
    for q in stats.values():
        q['minimum_spi_bytes']=q['request_bytes']+q['packets']*35
        q['minimum_spi_ms']=q['minimum_spi_bytes']*8/2625000*1000+q['packets']*0.024
    return dict(all_sections_identical=True,logical_bytes=sum(map(len,a.values())),frames=stats)

if __name__=='__main__':run()
