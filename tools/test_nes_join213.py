# SPDX-License-Identifier: MIT
"""Actual213 RUN/200 SPI -> unchanged207 RTL -> actual212 65816.
Archived metadata input and loader/core arbitration are fixtures. Not live
SMB3, full board clocks, physical throughput, or 60fps evidence.
"""
from pathlib import Path
import inspect,json,shutil
import test_nes_join208 as prior
from nes_runtime213 import ROOT,BASE,sha,once

def prepare(out):
 pins,rtl=prior.prepare(out)
 src=BASE/'probes/nes-runtime213/arm01/src'
 prep=json.loads((src.parent/'preparation-runtime213.json').read_bytes());allpins=prep['copied']|prep['changed']|prep['added']
 for f in src.iterdir():
  if f.name.startswith('nes_') and f.suffix in ('.c','.h','.inc'):
   assert sha(f)==allpins['src/'+f.name];shutil.copyfile(f,out/f.name);pins[f.relative_to(BASE).as_posix()]=sha(f)
 h=(BASE/'probes/nes-metadata203/test04/host203.c').read_text();h=h[:h.index('static void decode(')]
 h=once(h,'static struct nes_native_runtime165 runtime;', 'static struct nes_native_runtime165 runtime;\nstatic struct nes_resident211 cache;')
 tail=(ROOT/'tests/nes-functional/join208_host.inc').read_text()
 tail=once(tail,'NULL,1000000)', 'NULL,1000000,&cache,0x5a04eed7u,true)')
 tail=once(tail,'  memcpy(queue[qsent%4],tx+1,size);', '''  if(tx[1]==7){
   unsigned len=u16(tx+15);assert(len&&len<=2048);uint8_t raw[2048];
   rpc(2,0x400800,NULL,len,raw,len);
   char name[80];sprintf(name,"tile-%04u.bin",qsent+1);
   FILE*f=fopen(name,"wb");assert(f&&fwrite(raw,1,len,f)==len);fclose(f);
  }
  memcpy(queue[qsent%4],tx+1,size);''')
 tail=once(tail,'if(cmd==0xea){assert(runtime.sink.displayed&&qacks==runtime.frames);retired_frames++;}',
 '''if(cmd==0xea){assert(runtime.sink.displayed&&qacks==runtime.frames&&cache.displayed&&!cache.open&&!cache.prepared);retired_frames++;}''')
 tail=once(tail,'assert(qacks==i+1&&retired_frames==i+1&&!memcmp(&ref,&output,sizeof ref));', '''assert(qacks==i+1&&retired_frames==i+1&&!cache.open&&cache.active==(i&1));
  if(i==2)assert(cache.hits>0&&cache.writes<12);''')
 tail=once(tail,'assert(runtime.result==NES_RUNTIME165_IO&&runtime.frames==1&&retired_frames==1);',
 'assert(runtime.result==NES_RUNTIME165_IO&&runtime.frames==1&&retired_frames==1&&cache.fault&&!cache.open);')
 (out/'host.c').write_text(h+tail,encoding='utf8',newline='\n')
 client=BASE/'probes/nes-dirty212/test09/client/sink165.sfc';shutil.copyfile(client,out/'sink165.sfc');pins[client.relative_to(BASE).as_posix()]=sha(client)
 return pins,rtl

def lua():
 f=BASE/'probes/nes-dirty212/test09/candidate-normal/capture.lua';s=f.read_text();s=s[s.index('local CANDIDATE='):]
 s=prior.RPC_LUA+s
 s=once(s,'packet=nil;tile=nil;consumed=false;reads=0;', 'packet=nil;tile=nil;actualDescriptor=nil;consumed=false;reads=0;')
 start=s.index('local function descriptor()');end=s.index('emu.addMemoryCallback(function(a,v)return descriptor()',start)
 s=s[:start]+'''local function descriptor()
 if not actualDescriptor then actualDescriptor=rpc208(2,0x6040,12,nil,12)end
 return actualDescriptor
end
'''+s[end:]
 s=once(s,"local i=a-0x400800;assert(i<#tile,'bulk overread');assert(i==reads,'nonsequential DMA')", '''local i=a-0x400800;assert(i<#tile,'bulk overread');assert(i==reads,'nonsequential DMA')
 if i==0 then local actual=rpc208(2,0x400800,#tile,nil,#tile);assert(actual==tile,'immutable RTL bulk changed');tile=actual end''')
 s=once(s,'consumed=true;retires=retires+1;',"rpc208(3,0x604c,5,string.char(table.unpack(tokenWrites))..string.char(0xa5),0);consumed=true;retires=retires+1;")
 # Joined stream uses65534/65535/0 rather than the separate212 fixture1/2/3.
 s=once(s,"pw(8)==3 then assert(count==1", "pw(8)==0 then assert(count==1")
 s=s.replace('if st.frameCount>4000','if st.frameCount>100000')
 return s

s=inspect.getsource(prior.main)
s=once(s,"pins['repository-nes-milestone/tools/test_nes_join208.py']=sha(Path(__file__))", "pins['repository-nes-milestone/tools/test_nes_join213.py']=sha(Path(__file__))")
s=once(s,"'nes_plan191.c','nes_plan_service200.c'", "'nes_planner211.c','nes_resident211.c','nes_budget210.c','nes_plan_service200.c'")
s=once(s,'assert os.environ.get(\'SALT_LICENSE_SERVER\')',"assert str(a.out).isascii(),'ASCII simulator paths required'\n assert os.environ.get('SALT_LICENSE_SERVER')")
s=once(s,"result['same_scene_pixels']=3*256*239", """result['same_scene_pixels']=3*256*239
   baseline=BASE/'probes/nes-join208/test08/normal'
   for i in range(1,4):assert (d/f'frame-{i}.rgb').read_bytes()==(baseline/f'frame-{i}.rgb').read_bytes(),i
   result['reference208_pixels']=3*256*239""")
s=once(s,"scope=__doc__", "scope='Actual213 C/200 SPI +207 RTL source/lease/READ16/bulk +212 SNES; fixture loader/core/metadata and E0/E1 queue, not physical/FPS'")
ns=dict(prior.__dict__);ns.update(prepare=prepare,lua=lua,__file__=__file__)
exec(compile(s,'join213','exec'),ns)
if __name__=='__main__':ns['main']()
