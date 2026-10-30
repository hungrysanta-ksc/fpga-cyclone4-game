# SPDX-License-Identifier: MIT
"""489 actual M4 packets -> actual65816 direct raw reconstruction/check/DMA/pixels, file-aperture model.

Four admission credits and2.625Mbps E1 byte time are modeled. ARM/source IRQ,
E0 polling and ROM arbitration are not on this clock. Fixed frame-release
phases isolate VBlank effects; this is not measured physical FPS.
"""
import argparse,json,os,tempfile,random,shutil,struct,subprocess
from pathlib import Path
from check_nes_game478 import sha

LUA=r'''
local ROOT=@ROOT@
local MODE=@MODE@
local COMPACT=@COMPACT@
local TOTAL=@TOTAL@
local SCHEDULE=@SCHEDULE@
local POISON=@POISON@
local FAULT=@FAULT@
local function file(name)local f=assert(io.open(ROOT..'/'..name,'rb'));local b=f:read('*a');f:close();return b end
local requests,frames,ready,retiredAt,sealIndex,frameRelease={},{},{},{},{},{}
local bundle=file('requests.bin');local pos=1
for i=1,TOTAL do local n=string.unpack('<I2',bundle,pos);pos=pos+2;requests[i]=bundle:sub(pos,pos+n-1);pos=pos+n;frames[i]=requests[i]:byte(9)+256*requests[i]:byte(10)-905 end
assert(pos==#bundle+1)
for i=1,TOTAL do if requests[i]:byte(1)==3 then sealIndex[frames[i]]=i end end
local function rd(a)return emu.read(a,emu.memType.snesWorkRam)end
local function word(a)return rd(a)+256*rd(a+1)end
local index,retired,sent,hostclock=1,0,0,@START@
local packet,tile,ack=nil,nil,{}
if POISON then for _,base in ipairs({0x5000,0x9000})do for i=0,2047 do emu.write(base+i,0xa5,emu.memType.snesVideoRam)end end;emu.write(0x125a,2,emu.memType.snesWorkRam);emu.write(0x125b,2,emu.memType.snesWorkRam)end
local reads,token,commits,rejected=0,{},0,false
local shown,captured=-100,0
local captures={};local stats={};local regs={};local decodeStart=nil;local decodeTimes={};local finalReady={};local decodePoll=nil;local decodeGap={};local minStack=0x2000
local visible=false;local vramDMA=0;local lastStatus=0;local completedFrame=0
local firstPoll=nil;local dmaRemaining=0;local dmaLength=0
local bytesToClock=8*21477272/2625000
local function fill()
 while sent<TOTAL and sent<retired+4 do
  local nextframe=frames[sent+1]
  if nextframe>0 and not retiredAt[sealIndex[nextframe-1]]then break end
  sent=sent+1
  local start=@START@
  if frames[sent]>0 then start=retiredAt[sealIndex[frames[sent]-1]]+20*bytesToClock end
  if SCHEDULE=='fixed'then start=math.max(start,@START@+frames[sent]*2147728)end
  frameRelease[frames[sent]]=frameRelease[frames[sent]]or start
  if sent>4 then start=math.max(start,(retiredAt[sent-4] or 0)+20*bytesToClock)end
  hostclock=math.max(hostclock,start)+(#requests[sent]+3)*bytesToClock;ready[sent]=hostclock
 end
end
local function pb(i)return assert(packet):byte(i+1)end
local function pw(i)return pb(i)+256*pb(i+1)end
local function loaded()
 if packet or rejected or index>TOTAL then return end
 fill();local st=emu.getState()
 if st.masterClock<ready[index]then return end
 packet=requests[index];reads=0;token={};decodeStart=nil
 if pb(0)==7 then tile=file(string.format('tile-%04d.bin',index))else tile=nil end
 if MODE~='normal' and pw(8)==FAULT then
  local b={packet:byte(1,#packet)}
  if pb(0)==3 then
   if MODE=='bad_version'then b[37]=0x71;b[38]=0x22 end
   if MODE=='bad_count'then b[39]=8 end
   if MODE=='zero_count'then b[39]=0 end
   if MODE=='bad_length'then b[27]=b[27]~2 end
  end
  if MODE=='bad_mode'and pb(0)==2 and pb(1)==5 and pw(10)==1505 then b[18]=0x7f end
  packet=string.char(table.unpack(b))
 end
end
emu.addMemoryCallback(function(a,v)
 if a==0x6000 then if not firstPoll then firstPoll=emu.getState().masterClock end;loaded();return packet and 1 or 0 end
 if a==0x6001 then
  if COMPACT and packet and decodeStart and not decodeTimes[pw(8)]then local now=emu.getState().masterClock;decodeGap[pw(8)]=math.max(decodeGap[pw(8)]or 0,now-(decodePoll or decodeStart));decodePoll=now end
  if packet and pw(8)==FAULT and pb(0)==3 then
   if MODE=='stop_decode'and decodeStart then return 128 end
   if MODE=='stop_raw'and rawTransfers>0 then return 128 end
   if MODE=='stop_clear'and clearTransfers>0 then return 128 end
   if MODE=='stop_final'and rd(0x1025)==2 then return 128 end
  end
  return 0
 end
 local n=packet and #packet or 0;return a==0x6004 and n&255 or n>>8
end,emu.callbackType.read,0x6000,0x6005)
emu.addMemoryCallback(function(a,v)assert(packet and a-0x400000<#packet,'unowned packet');return pb(a-0x400000)end,emu.callbackType.read,0x400000,0x4000ff)
emu.addMemoryCallback(function(a,v)return 0 end,emu.callbackType.read,0x4218,0x4219)
emu.addMemoryCallback(function(a,v)
 assert(tile,'unowned descriptor');local d={1,pb(1),pw(14)&255,pw(14)>>8,pb(10),pb(11),pb(8),pb(9),pb(16),pb(17),pb(18),pb(19)};return d[a-0x6040+1]
end,emu.callbackType.read,0x6040,0x604b)
emu.addMemoryCallback(function(a,v)local i=a-0x400800;assert(tile and i==reads and i<#tile,'bulk ownership');reads=reads+1;return tile:byte(i+1)end,emu.callbackType.read,0x400800,0x400fff)
emu.addMemoryCallback(function(a,v)
 if a<0x6050 then token[a-0x604c+1]=v else
  assert(v==0xa5 and #token==4 and tile and reads==#tile,'premature receipt')
  for i=1,4 do assert(token[i]==pb(15+i),'receipt token')end
 end
end,emu.callbackType.write,0x604c,0x6050)
rawTransfers=0;clearTransfers=0
local function write(a,v)
 if a==0x2118 or a==0x2119 or a==0x2122 or a==0x2104 then
  if visible then
   assert(dmaRemaining>0,'untracked visible PPU data write')
   if dmaRemaining==dmaLength or dmaRemaining==1 then assert(emu.getState()['ppu.scanline']>=225,'DMA endpoint outside VBlank')end
   dmaRemaining=dmaRemaining-1
  end
  return
 end
 local st=emu.getState()
 if COMPACT and packet and pb(0)==3 then
  if a==0x1258 and v>0 and not decodeStart then decodeStart=st.masterClock;decodePoll=decodeStart end
  if a==0x100b and v==13 and decodeStart then decodeTimes[pw(8)]=st.masterClock-decodeStart end
 end
 if a==0x1025 and v==2 and packet then finalReady[pw(8)]=st.masterClock end
 if a>=0x4300 and a<=0x4306 then regs[a]=v end
 if a==0x420b and v==1 and(regs[0x4301]==0x18 or regs[0x4301]==0x22 or regs[0x4301]==4)then
  dmaLength=(regs[0x4305]or 0)+256*(regs[0x4306]or 0);assert(dmaLength>0 and dmaLength<=4096);dmaRemaining=dmaLength
 end
 if a==0x420b and v==1 and packet and pw(8)==FAULT and pb(0)==3 and regs[0x4301]==0x18 then
  if regs[0x4304]==0x40 and regs[0x4305]==0 and regs[0x4306]==8 then clearTransfers=clearTransfers+1 end
  if regs[0x4304]==0x7f and regs[0x4305]==64 and regs[0x4306]==0 then rawTransfers=rawTransfers+1 end
 end
 if a==0x420b and v==1 and regs[0x4301]==0x18 then vramDMA=vramDMA+(regs[0x4305]or 0)+256*(regs[0x4306]or 0)end
 if a==0x2100 and v==15 then assert(st['ppu.scanline']>=225,'reveal outside VBlank');visible=true end
 if a>=0x6010 and a<=0x601b then ack[a-0x6010+1]=v end
 if a==0x601c then
  assert(v==0xa5 and packet and #ack==12,'unowned ACK')
  for i=2,9 do assert(ack[i+1]==pb(i),'ACK identity')end
  assert(ack[2]==pb(0)and ack[11]==0x65 and ack[12]==0x9a,'ACK signature')
  lastStatus=ack[1]
  if pb(0)==7 then assert(lastStatus==0 and reads==#tile,'early bulk ACK')end
  if lastStatus==1 then
   assert(pb(0)==3 and rd(0x1025)==3 and st['ppu.scanline']>=225,'early display ACK')
   local hdma=file('expected-'..pw(8)..'.bin');local base=0x10000+word(0x1020)+0x6500
   local count=pw(38)
   if COMPACT and count>0 and count<=2 then
    for i=0,1120 do assert(rd(base+i)==hdma:byte(i+1),'scroll '..i)end
    local at=0
    for plane=0,2 do for row=0,count-1 do for t=0,31 do for byte=0,1 do
     assert(rd(base+1121+at)==hdma:byte(1122+t*64+plane*16+row*2+byte),'compact raw '..at);at=at+1
    end end end end
    for i=0,248 do assert(rd(base+1121+192*count+i)==hdma:byte(3170+i),'compact table '..i)end
   else for i=0,#hdma-1 do assert(rd(base+i)==hdma:byte(i+1),'canonical HDMA '..i)end end
   if #hdma>1121 then
    local dest=word(0x1020)==0 and 0x5000 or 0x9000
    for i=0,2047 do assert(emu.read(dest+i,emu.memType.snesVideoRam)==hdma:byte(1122+i),'raw VRAM '..i)end
   end
   commits=commits+1;completedFrame=pw(8);shown=st.frameCount
   captures[#captures+1]={generation=pw(8),frame=st.frameCount}
   stats[#stats+1]={generation=pw(8),ack=st.masterClock,release=math.ceil(frameRelease[frames[index]]),decode=decodeTimes[pw(8)]or 0,ready=finalReady[pw(8)]or 0,gap=decodeGap[pw(8)]or 0}
  elseif lastStatus>=0xe0 then rejected=true;shown=st.frameCount end
  retired=index;retiredAt[index]=st.masterClock;index=index+1;packet=nil;tile=nil;ack={}
 end
end
for _,range in ipairs({{0x60,0x60},{0x1025,0x1025},{0x1258,0x1258},{0x100a,0x100b},{0x4300,0x4306},{0x2100,0x2122},{0x420b,0x420b},{0x6010,0x601c}})do emu.addMemoryCallback(write,emu.callbackType.write,range[1],range[2])end
emu.addMemoryCallback(function(a)minStack=math.min(minStack,a)end,emu.callbackType.write,0x1f00,0x1fff)
emu.addEventCallback(function()
 local st=emu.getState()
 for _,c in ipairs(captures)do if not c.done and st.frameCount>c.frame then
  local screen=emu.getScreenBuffer();local f=assert(io.open(ROOT..'/frame-'..c.generation..'.rgb','wb'))
  for y=0,238 do local row={};for x=0,255 do local b=screen[y*256+x+1];row[#row+1]=string.char((b>>16)&255,(b>>8)&255,b&255)end;f:write(table.concat(row))end
  f:close();c.done=true;captured=captured+1
 end end
 if (rejected or index>TOTAL)and not packet and st.frameCount>shown+2 then
  assert(commits==(MODE=='normal'and @FRAMES@ or (FAULT-905)),'unexpected commit count')
  assert(not rejected==(MODE=='normal'),'unexpected reject')
  if MODE=='stop_decode'or MODE=='stop_clear'or MODE=='stop_raw'or MODE=='stop_final'then assert(lastStatus==0xe4,'STOP status');if MODE=='stop_clear'or MODE=='stop_raw'then assert(rd(0x125a+(word(0x1020)==0 and 0 or 1))==0,'canceled implicit cache published')end;assert(word(0x1248)==FAULT-905 and word(0x124a)==0,'canceled display identity published')end
  assert(captured==commits)
  if rejected then
   local screen=emu.getScreenBuffer();local f=assert(io.open(ROOT..'/retained.rgb','wb'))
   for y=0,238 do local row={};for x=0,255 do local b=screen[y*256+x+1];row[#row+1]=string.char((b>>16)&255,(b>>8)&255,b&255)end;f:write(table.concat(row))end;f:close()
  end
  local f=assert(io.open(ROOT..'/result.json','w'));f:write(string.format('{"passed":true,"commits":%d,"last_status":%d,"vram_DMA_B":%d,"observed_stack_B":%d,"first_packet_poll_masterclock":%d,"frames":[',commits,lastStatus,vramDMA,0x2000-minStack,firstPoll or 0))
  for i,s in ipairs(stats)do if i>1 then f:write(',')end;f:write(string.format('{"generation":%d,"ACK_masterclock":%d,"release_masterclock":%d,"decode_masterclocks":%d,"final_ready_masterclock":%d,"decode_max_service_gap":%d}',s.generation,s.ack,s.release,s.decode,s.ready,s.gap))end
  f:write(']}');f:close();emu.stop(0)
 end
 assert(st.frameCount<360,'watchdog: index '..index..' status '..lastStatus)
end,emu.eventType.endFrame)
'''

def packet(op,section,serial,generation,offset,data,expanded=0):
    return struct.pack('<BBHIHHHH',op,section,0,serial,generation,offset,len(data),expanded)+data

def prepare(a,d,compact):
    chr=a.rom.read_bytes()[0x40010:];assert len(chr)==131072
    version=0x4891 if compact else 0x2271;ordinal=0;token=0
    for serial,frame in enumerate(range(905,905+a.frames),1):
        source=a.compact if compact else a.baseline;fd=source/f'frame{frame}'
        plans=json.loads((a.compact/f'frame{frame}/plans.json').read_text());batch=[]
        batch.append((packet(1,0,serial,frame,0,struct.pack('<HHII',version,(serial-1)&1,serial-1,1)),None))
        for bank,h in plans:
            q=bytes.fromhex(h);generation,slot,tag,kind,mask=struct.unpack_from('<HHHBB',q);size=32 if kind==1 else 16;raw=bytearray(size)
            if kind!=2:
                alt=struct.unpack_from('<8H',q,24)
                for y in range(8):
                    if mask&(1<<y):raw[y*2]=chr[(tag if alt[y]==65535 else alt[y])*16+q[8+y*2]];raw[y*2+1]=chr[tag*16+8+q[9+y*2]]
            batch.append((packet(7,int(kind==1),serial,frame,slot*size,struct.pack('<I',token),size),bytes(raw)));token+=1
        ordinary=[q.read_bytes()for q in sorted(fd.glob('packet*.bin'))]
        expected=(a.compact/f'frame{frame}/expected-hdma.bin').read_bytes()
        if a.row_counts:
            count=a.row_counts[serial-1];assert 0<=count<=7
            prefix=expected[:1121];end=0
            while prefix[end]:end+=5
            raw=bytearray(2048);rng=random.Random(frame)
            for t in range(32):
                for plane in range(3):
                    for row in range(count):raw[t*64+plane*16+row*2:t*64+plane*16+row*2+2]=rng.randbytes(2)
                for row in range(count):raw[t*64+48+row*2]=255
            descriptor=bytearray(ordinary[-1][16:]);mask=struct.unpack_from('<H',descriptor,18)[0]
            if count:
                runs=[(count,True),(127,False),(224-count-127,False)];tables=[]
                for which in range(3):
                    data=bytearray()
                    for length,israw in runs:
                        if which<2:data+=bytes([length,3 if israw else 0,0,(0x38 if israw else 0x31)+32*which,0])
                        else:data+=bytes([length,1 if israw else 17,0,0 if israw or mask!=0x18 else 17,0])
                    data+=b'\0';tables.append(bytes(data)+bytes(81-len(data)))
                tail=b''.join(tables)+struct.pack('<3H',16,16,16);expected=prefix+raw+tail
                packed=bytes(raw[t*64+plane*16+row*2+bit]for plane in range(3)for row in range(count)for t in range(32)for bit in range(2))
                wire=prefix+(packed if compact and count<=2 else raw)+tail
            else:expected=wire=prefix[:end+1]
            ordinary=[b for b in ordinary if b[0]!=3 and b[1]!=5]
            ordinary += [packet(2,5,serial,frame,at,wire[at:at+240])for at in range(0,len(wire),240)]
            struct.pack_into('<H',descriptor,10,len(wire));struct.pack_into('<H',descriptor,20,version);struct.pack_into('<H',descriptor,22,count)
            ordinary.append(packet(3,0,serial,frame,0,descriptor))
        batch.extend((b,None)for b in ordinary)
        for seq,(b,tile) in enumerate(batch):
            ordinal+=1;b=bytearray(b);struct.pack_into('<H',b,2,seq);(d/f'req-{ordinal:04d}.bin').write_bytes(b)
            if tile is not None:(d/f'tile-{ordinal:04d}.bin').write_bytes(tile)
        (d/f'expected-{frame}.bin').write_bytes(expected)
    (d/'requests.bin').write_bytes(b''.join(struct.pack('<H',len(b))+b for b in [(d/f'req-{i:04d}.bin').read_bytes()for i in range(1,ordinal+1)]))
    return ordinal

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['baseline','compact','client','rom','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--modes',nargs='+',default=['normal','bad_version','bad_count','zero_count','bad_length','bad_mode','stop_decode','stop_clear','stop_raw','stop_final'])
    p.add_argument('--frames',type=int,default=12)
    p.add_argument('--row-counts',type=int,nargs='+')
    p.add_argument('--fault-frame',type=int,default=906)
    p.add_argument('--poison-initial-raw',action='store_true')
    p.add_argument('--mesen',type=Path,default=Path(tempfile.gettempdir())/'nes-coupled165-mesen/Mesen.exe')
    p.add_argument('--dotnet',type=Path,default=Path('C:/works/dotnet'))
    p.add_argument('--start-clock',type=int,default=3000000)
    p.add_argument('--schedule',choices=['fixed','continuous'],default='continuous')
    a=p.parse_args();assert a.row_counts is None or len(a.row_counts)==a.frames;a.out=a.out.resolve();assert a.out.as_posix().isascii();a.out.mkdir(parents=True,exist_ok=False)
    assert sha(a.rom)=='dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
    mesen=a.mesen.resolve();env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']=str(a.dotnet.resolve())
    cases=[]
    for compact,mode in [(False,'normal')]+[(True,x)for x in a.modes]:
        d=a.out/(('compact-'if compact else 'baseline-')+mode);d.mkdir();total=prepare(a,d,compact)
        client=a.client/'sink165.sfc'if compact else Path(__file__).resolve().parents[2]/'probes/nes-repeat227/snes04/client/sink165.sfc'
        shutil.copyfile(client,d/'client.sfc')
        lua=LUA.replace('@ROOT@',json.dumps(d.as_posix())).replace('@MODE@',json.dumps(mode)).replace('@COMPACT@',str(compact).lower()).replace('@TOTAL@',str(total)).replace('@FRAMES@',str(a.frames)).replace('@SCHEDULE@',json.dumps(a.schedule)).replace('@START@',str(a.start_clock)).replace('@FAULT@',str(a.fault_frame)).replace('@POISON@',str(a.poison_initial_raw).lower())
        errorfile=json.dumps((d/'error.txt').as_posix())
        diagnostic="local function fatal(m)local f=io.open("+errorfile+",'a');if f then f:write(tostring(m)..'\\n'..debug.traceback()..'\\n');f:close()end;emu.stop(1)end\nlocal mem,event=emu.addMemoryCallback,emu.addEventCallback\nemu.addMemoryCallback=function(fn,...)return mem(function(a,v)local ok,r=pcall(fn,a,v);if not ok then fatal(r);return 0 end;return r end,...)end\nemu.addEventCallback=function(fn,...)return event(function(...)local ok,r=pcall(fn,...);if not ok then fatal(r)end;return r end,...)end\n"
        (d/'capture.lua').write_text(diagnostic+lua,encoding='utf8')
        (d/'bootstrap.lua').write_text('local f=assert(io.open('+json.dumps((d/'capture.lua').as_posix())+',"rb"));local s=f:read("*a");f:close();local fn,err=load(s);local ok=false;if fn then ok,err=pcall(fn)end;if not ok then local f=io.open('+json.dumps((d/'error.txt').as_posix())+',"a");f:write(tostring(err));f:close();emu.stop(1)end',encoding='utf8')
        with (d/'mesen.log').open('wb')as log:r=subprocess.run([str(mesen),'--testRunner',str(d/'bootstrap.lua'),str(d/'client.sfc'),'--timeout=240','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],env=env,cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=250,creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode==0,(r.returncode,(d/'mesen.log').read_text(errors='replace')[-1800:],(d/'error.txt').read_text()if(d/'error.txt').exists()else'')
        result=json.loads((d/'result.json').read_text());assert result['passed']
        if compact:
            for frame in range(905,905+result['commits']):assert (d/f'frame-{frame}.rgb').read_bytes()==(a.out/'baseline-normal'/f'frame-{frame}.rgb').read_bytes(),('pixels',mode,frame)
            if mode!='normal':assert (d/'retained.rgb').read_bytes()==(a.out/f'baseline-normal/frame-{a.fault_frame-1}.rgb').read_bytes(),('visible changed on failure',mode)
        result.update(compact=compact,mode=mode);cases.append(result);print(json.dumps(result),flush=True)
    (a.out/'result.json').write_text(json.dumps({'passed':True,'scope':__doc__,'schedule':a.schedule,'start_masterclock':a.start_clock,'cases':cases,'physical':False,'RTL_coupled':False,'common_ARM_IRQ_clock':False},indent=2)+'\n',encoding='utf8')
