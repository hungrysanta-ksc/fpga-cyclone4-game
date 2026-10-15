# SPDX-License-Identifier: MIT
"""Actual C/65816/PPU raw steady-state validation; no mocked display ACK."""
import inspect
import test_nes_client181 as client
import test_nes_sinkpack181 as packed
from nes_rawsteady181 import build
from nes_clip178 import replace


def extend_lua(lua):
    lua=replace(lua,'local rejected=false','local rejected=false\nlocal lastChunks=0')
    lua=replace(lua,'  return 0\n end\n local n=', """  if packet and pb(0)==3 and pw(8)==15 then
   if MODE=='stop_steady' and rd(0x1025)==1 and word(0x40)==12 then return 128 end
   if MODE=='stop_steady_final' and rd(0x1025)==2 then return 128 end
  end
  return 0
 end
 local n=""")
    lua=replace(lua,"assert(commits==(MODE=='normal'", "assert(commits==(MODE=='steady' and 10 or MODE=='large_steady' and 6 or ((MODE=='stop_steady' or MODE=='stop_steady_final') and 3 or MODE=='normal'")
    lua=replace(lua,"and 2 or 1)))", "and 2 or 1))))")
    lua=replace(lua,"  if bytes:byte(1)==1 then", """  if bytes:byte(1)==1 then
   local f=assert(io.open(OUT_DIR..'/seal-'..pw(8)..'.txt','w'))
   f:write(string.format('%d %d %d %d %d\\n',word(0x1032),word(0x1026),word(0x1028),chunks-lastChunks,st.masterClock))
   for i=0,word(0x1026)-1 do
    f:write(string.format('%d %d %d %d\\n',word(0x1100+i*8),word(0x1102+i*8),word(0x1104+i*8),word(0x1106+i*8)))
   end
   f:close();lastChunks=chunks
""")
    return lua


def extend_host(text):
    text=text.replace('!strcmp(mode,"max")','(!strcmp(mode,"max")||!strcmp(mode,"large_steady"))')
    text=replace(text,'bg=1024;p.bg_count=1024;', '''
  if(!strcmp(mode,"large_steady") && gen>=15 && gen<=17)
   for(unsigned i=bg*16;i<16384;i++)pattern[i]^=255;
  bg=1024;p.bg_count=1024;''')
    text=replace(text,' bool raw_first=', '''
 if(!strcmp(mode,"steady")||!strcmp(mode,"large_steady")||!strcmp(mode,"stop_steady")||!strcmp(mode,"stop_steady_final")){
  assert(scene(argv[1],"rows0-phase0",12,0,0x1e));
  assert(scene(argv[1],"rows1-phase0",13,1,0x1e));
  assert(scene(argv[1],"rows7-phase0",14,7,0x1e));
  bool ok=scene(argv[1],!strcmp(mode,"stop_steady")?"rows7-phase0":"rows7-phase1",15,7,!strcmp(mode,"stop_steady")?0x1e:0x18);
  if(!strncmp(mode,"stop",4)){
   assert(!ok&&sink.state==NES_SINK165_FAULT&&sink.displayed);
   assert(nes_sink_trace168.ack[0]==0xe4);
  }else{
   assert(ok);
   assert(scene(argv[1],"rows7-phase1",16,7,0x18));
   assert(scene(argv[1],"rows7-phase2",17,7,0x18));
   if(!strcmp(mode,"large_steady"))goto done;
   assert(scene(argv[1],"rows0-phase0",18,0,0x1e));
   assert(scene(argv[1],"rows7-phase0",19,7,0x1e));
   assert(scene(argv[1],"rows7-phase1",20,7,0x18));
   assert(scene(argv[1],"rows7-phase0",21,7,0x1e));
  }
  goto done;
 }
 bool raw_first=''')
    return replace(text,' FILE *f=fopen("producer-done.txt"', ' done:;\n FILE *f=fopen("producer-done.txt"')


def main_source():
    source=inspect.getsource(client.main)
    source=replace(source,'  for i,(count,phase) in enumerate(frames,1):', '''
  if mode in ('steady','large_steady','stop_steady','stop_steady_final'):
   frames=[(0,0),(1,0),(7,0)]
   if not mode.startswith('stop'):frames += [(7,1),(7,1),(7,2),(0,0),(7,0),(7,1),(7,0)]
   if mode=='large_steady':frames=frames[:6]
  for i,(count,phase) in enumerate(frames,1):''')
    return source


def run():
    source=inspect.getsource(packed.run)
    source=replace(source,'source=inspect.getsource(original.main)','source=main_source()')
    source=replace(source,'    anchor="(ROOT/', '    lua=extend_lua(lua)\n    anchor="(ROOT/')
    source=replace(source,"host.write_text(text,encoding", "text=extend_host(text)\n host.write_text(text,encoding")
    source=replace(source,"print('PASS SINKPACK181')","print('PASS RAWSTEADY181')")
    source=replace(source,'LUA_SOURCE=lua)', 'LUA_SOURCE=lua,extend_host=extend_host)')
    ns=dict(packed.__dict__);ns.update(build=build,extend_lua=extend_lua,extend_host=extend_host,main_source=main_source)
    exec(compile(source,'rawsteady181-test','exec'),ns);ns['run']()


if __name__=='__main__':run()
