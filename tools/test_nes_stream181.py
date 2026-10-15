# SPDX-License-Identifier: MIT
"""Paired C+actual65816 DATA5, service/STOP, staging bytes and PPU tests."""
import inspect
import test_nes_rawsteady181 as prior
from nes_stream181 import build,sink
from nes_clip178 import replace

HOST_PATCH=r'''
 if(get16(b+8)==13 && b[0]==5 && b[1]==2){
  if(!strcmp(mode,"long_full") && !get16(b+10)){b[14]=0;b[15]=16;}
  if(!strcmp(mode,"long_end") && get16(b+10)){b[14]=0;b[15]=2;}
  if(!strcmp(mode,"long_zero"))b[14]=b[15]=0;
  if(!strcmp(mode,"long_short")){b[14]=240;b[15]=0;}
  if(!strcmp(mode,"long_odd"))b[14]|=1;
  if(!strcmp(mode,"long_large")){b[14]=2;b[15]=16;}
  if(!strcmp(mode,"long_size")){b[12]=1;n=17;}
  if(!strcmp(mode,"long_section"))b[1]=6;
  if(!strcmp(mode,"long_offset")){b[10]=b[11]=255;}
  if(!strcmp(mode,"long_token"))b[2]^=1;
  if(!strcmp(mode,"short_limit")){b[0]=4;b[14]=242;b[15]=0;}
 }
'''


def extend_lua(lua):
    lua=prior.extend_lua(lua)
    lua=lua.replace('(pb(0)==2 or pb(0)==4)','(pb(0)==2 or pb(0)==4 or pb(0)==5)')
    lua=lua.replace('pb(0)==4 and','pb(0)>=4 and')
    lua=replace(lua,'local lastChunks=0','local lastChunks=0\nlocal repeatStart=nil\nlocal repeatWrites=0\nlocal maxServiceBytes=0\nlocal maxRepeat=0')
    lua=replace(lua,' if a==0x6001 then', ''' if a==0x6001 then
  if packet and pb(0)==5 then
   maxServiceBytes=math.max(maxServiceBytes,repeatWrites)
   assert(repeatWrites<=64,'long repeat service gap');repeatWrites=0
   if MODE=='stop_long' and pw(8)==13 and repeatStart then return 128 end
  end''')
    lua=replace(lua,' local st=emu.getState()\n if a==0x6003', ''' local st=emu.getState()
 if a==0x2180 and packet and pb(0)==5 then
  repeatWrites=repeatWrites+1;repeatStart=repeatStart or st.masterClock
 end
 if a==0x6003''')
    lua=replace(lua,'  if bytes:byte(1)==1 then', '''  repeatStart=nil
  if bytes:byte(1)==0 and pb(0)==5 then maxRepeat=math.max(maxRepeat,pw(14))end
  if bytes:byte(1)==1 then''')
    lua=replace(lua,'{{0x2100,0x2122}', '{{0x2180,0x2180},{0x2100,0x2122}')
    lua=replace(lua,'"held_frames":%d}', '"held_frames":%d,"max_repeat_service_bytes":%d,"max_repeat":%d}')
    lua=replace(lua,'commits,acks,pads,chunks,held));','commits,acks,pads,chunks,held,maxServiceBytes,maxRepeat));')
    return lua


def run():
    source=inspect.getsource(prior.run)
    source=replace(source,"ns=dict(packed.__dict__);ns.update(build=build,", "ns=dict(packed.__dict__);ns.update(sink=sink,HOST_PATCH=HOST_PATCH,build=build,")
    source=replace(source,"print('PASS RAWSTEADY181')","print('PASS STREAM181')")
    ns=dict(prior.__dict__);ns.update(build=build,sink=sink,extend_lua=extend_lua,HOST_PATCH=HOST_PATCH)
    exec(compile(source,'stream181-test','exec'),ns);ns['run']()


if __name__=='__main__':run()
