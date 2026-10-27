# SPDX-License-Identifier: MIT
"""Real65816 raw final-record receiver and PPU execution. Prior warm banks
remain explicit fixtures;this output kernel is not the full resident firmware."""
import argparse,csv,json,os,struct,subprocess
from pathlib import Path
from build_nes_trace_replay import Code
import probe_nes_display266 as display
import probe_nes_vblank381 as commit
from probe_nes_spool383 import current_view as recorded_view
from probe_nes_plan391 import fixtures as oldfixtures
from probe_nes_spool383 import fixtures as tilefixtures
from probe_nes_arm264 import plans,u16
from nes_delta231 import sha,BASE

def rom(d):
 c=Code(0x8000)
 def lda(a):c.absolute(0xad,a)
 def sta(a):c.absolute(0x8d,a)
 def far(op,a):c.emit(op,a&255,(a>>8)&255,a>>16)
 def cond(op,label):c.emit(op^0x20,3);c.jump(label)
 def word(a,n):c.emit(0xc2,0x20,0xa9,n&255,n>>8);sta(a);c.emit(0xe2,0x20)
 def fault():lda(0x6001);c.emit(0x29,0xc0);cond(0xd0,'abort383')
 c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20)
 for a,v in ((0x4200,0),(0x420c,0),(0x4201,255),(0x2100,128)):c.store(a,v)
 c.label('rearm394');lda(0x6001);c.emit(0x29,128);c.branch(0xd0,'rearm394')
 lda(0x6001);c.emit(0x29,64);c.branch(0xf0,'rearmed394');c.store(0x6006,0xa5);c.jump('rearm394')
 c.label('rearmed394');word(0x4c,0);word(0x4e,0)
 c.label('frame394');c.emit(0xc2,0x10);word(0x22,0xa000);word(0x24,0xa000);word(0x18,3840)
 c.label('admission394');fault();lda(0x6099);c.branch(0xf0,'admission394')
 # Read immutable frame context once;the header/raw record is never rebuilt.
 c.emit(0xa2,0,0);c.label('context394');c.absolute(0xbd,0x6091);c.absolute(0x9d,0x50);c.emit(0xe8,0xe0,8,0);c.branch(0xd0,'context394')
 c.emit(0xc2,0x20);lda(0x50);c.absolute(0xcd,0x4c);c.branch(0xd0,'new394');lda(0x52);c.absolute(0xcd,0x4e);c.branch(0xd0,'new394');c.emit(0xe2,0x20);c.jump('admission394')
 c.label('new394');lda(0x50);sta(0x4c);lda(0x52);sta(0x4e);c.emit(0xe2,0x20)
 lda(0x56);c.emit(0xc9,2);cond(0xb0,'abort383')
 lda(0x57);c.branch(0xf0,'warm394');c.store(0x420c,0);c.store(0x2100,0x80);c.label('warm394')
 c.label('next383');fault();lda(0x6054);cond(0xd0,'ready383');lda(0x6040);cond(0xf0,'next383')
 c.emit(0xa2,0,0);c.label('record394');c.absolute(0xbd,0x6080);c.absolute(0x9d,0x30);c.emit(0xe8,0xe0,17,0);c.branch(0xd0,'record394')
 # Basic receive bounds and zero/reference semantics are checked before any
 # DMA. FPGA independently binds exact canonical destinations/coverage.
 lda(0x37);c.emit(0xc9,0x7e);c.branch(0xf0,'bank394');c.emit(0xc9,0x7f);cond(0xd0,'abort383')
 c.label('bank394');lda(0x39);c.emit(0xc9,6);cond(0xb0,'abort383');c.emit(0xc2,0x20);lda(0x34);cond(0xf0,'abort16_394');lda(0x3e);c.emit(0xc9,1,8);cond(0xb0,'abort16_394');c.emit(0xe2,0x20)
 lda(0x40);c.emit(0x29,1);cond(0xf0,'copy394')
 # Store-only writes do not occupy the PPU job table. REF has no fake source
 # bytes/coverage;the accepted immutable record alone becomes a PPU job.
 lda(0x36);c.emit(0x29,3,0xc9,3);cond(0xf0,'copy394')
 c.emit(0xc2,0x20);c.absolute(0xae,0x22);c.emit(0xe0,0,0xac);cond(0xb0,'abort16_394');c.emit(0xe2,0x20)
 for i in range(12):lda(0x30+i);far(0x9f,0x7e0000+i)
 c.emit(0xc2,0x20,0x8a,0x18,0x69,12,0);sta(0x22)
 c.emit(0xe2,0x20);lda(0x57);cond(0xd0,'copy394')
 # Saturating source-stage budget replaces final scan/reconstruction.
 c.emit(0xc2,0x20);lda(0x34);c.emit(0x0a);cond(0xb0,'abort16_394');c.emit(0x0a);cond(0xb0,'abort16_394');c.emit(0x0a);cond(0xb0,'abort16_394');sta(0x46);c.emit(0xe2,0x20)
 lda(0x36);c.emit(0x29,3);c.branch(0xf0,'budget_vram394');word(0x48,1408);c.jump('budget_add394');c.label('budget_vram394');word(0x48,1200)
 c.label('budget_add394');c.emit(0xc2,0x20);lda(0x46);c.emit(0x18);c.absolute(0x6d,0x48);cond(0xb0,'abort16_394');c.emit(0x18);c.absolute(0x6d,0x18);cond(0xb0,'abort16_394');sta(0x18);c.emit(0xe2,0x20);lda(0x57);c.branch(0xd0,'copy394');c.emit(0xc2,0x20);lda(0x18);c.emit(0xc9,0xd1,0xbf);cond(0xb0,'abort16_394');c.emit(0xe2,0x20)
 c.label('copy394');fault();lda(0x36);c.emit(0x29,16);cond(0xd0,'stage_done383');lda(0x36);c.emit(0x29,64);cond(0xd0,'zero394')
 c.emit(0xc2,0x20);lda(0x32);c.emit(0x18);c.absolute(0x6d,0x3c);cond(0xb0,'abort16_394');sta(0x2181);lda(0x3e);cond(0xf0,'abort16_394');sta(0x4305);c.emit(0xe2,0x20);lda(0x37);c.emit(0x29,1);sta(0x2183)
 for a,v in ((0x4300,0),(0x4301,0x80),(0x4302,0),(0x4303,8),(0x4304,0x40),(0x420b,1)):c.store(a,v)
 c.jump('stage_done383')
 c.label('zero394');c.emit(0xc2,0x20);lda(0x39);c.emit(0x29,255,0,0xc9,5,0);cond(0xd0,'abort16_394');lda(0x34);c.emit(0xc9,0x4c,4);cond(0xd0,'abort16_394');lda(0x3a);c.emit(0xc9,21,0);cond(0xd0,'abort16_394');lda(0x3e);c.emit(0xc9,2,0);cond(0xd0,'abort16_394');c.emit(0xe2,0x20)
 for a in(0x400800,0x400801):far(0xaf,a);cond(0xd0,'abort383')
 c.emit(0xc2,0x20);lda(0x32);sta(0x2181);lda(0x34);sta(0x4305);c.emit(0xe2,0x20);c.store(0x2183,1)
 for a,v in((0x4300,8),(0x4301,0x80),(0x4304,0)):c.store(a,v)
 c.emit(0xc2,0x20,0xa9,0,0);zero_patch=len(c.data)-2;sta(0x4302);c.emit(0xe2,0x20);c.store(0x420b,1)
 c.label('stage_done383');fault()
 for i in range(4):lda(0x6048+i);sta(0x604c+i)
 c.store(0x6050,0xa5);c.jump('next383')
 c.label('ready383');fault();c.emit(0xa2,0,0);c.label('view383');c.absolute(0xbd,0x6070);c.absolute(0x9d,0x1000);c.emit(0xe8,0xe0,12,0);c.branch(0xd0,'view383')
 lda(0x1000);c.absolute(0xcd,0x56);cond(0xd0,'abort383')
 lda(0x57);cond(0xd0,'flush394')
 # No final job building,64-column scan,map cache or gather.
 c.emit(0xc2,0x20);lda(0x18);c.emit(0xc9,0x21,0x4e);c.branch(0x90,'cut246394');c.emit(0xc9,0x31,0x75);c.branch(0x90,'cut238394');c.emit(0xc9,0x41,0x9c);c.branch(0x90,'cut230394');word(0x1a,225);c.jump('window394');c.label('cut230394');word(0x1a,230);c.jump('window394');c.label('cut238394');word(0x1a,238);c.jump('window394');c.label('cut246394');word(0x1a,246)
 c.label('window394');c.emit(0xe2,0x20);fault();lda(0x4212);c.branch(0x10,'window394')
 lda(0x213f);lda(0x2137);lda(0x213d);sta(0x14);c.store(0x15,0);lda(0x213d);c.emit(0xc2,0x20,0x29,1,0,0xeb);c.absolute(0x0d,0x14);c.emit(0xc9,225,0);c.branch(0x90,'window394');c.absolute(0xcd,0x1a);c.branch(0x90,'flush394');c.branch(0xf0,'flush394')
 c.emit(0xe2,0x20);c.label('late394');fault();lda(0x4212);c.branch(0x30,'late394');c.jump('window394')
 c.label('flush394');c.emit(0xe2,0x20)
 c.label('job394');fault();c.emit(0xc2,0x20);c.absolute(0xae,0x24);c.absolute(0xec,0x22);cond(0xf0,'display_entry394')
 for offset,target in((2,0x4302),(4,0x4305)):far(0xbf,0x7e0000+offset);sta(target)
 c.emit(0xe2,0x20);far(0xbf,0x7e0007);sta(0x4304);far(0xbf,0x7e0006);c.emit(0x29,3);c.branch(0xf0,'vram394');c.emit(0xc9,1);c.branch(0xf0,'cgram394')
 c.emit(0xc2,0x20);far(0xbf,0x7e0000);sta(0x2102);c.emit(0xe2,0x20);c.store(0x4300,0);c.store(0x4301,4);c.jump('ppu383')
 c.label('cgram394');far(0xbf,0x7e0000);sta(0x2121);c.store(0x4300,2);c.store(0x4301,0x22);c.jump('ppu383')
 c.label('vram394');far(0xbf,0x7e0008);sta(0x2115);c.emit(0xc2,0x20);far(0xbf,0x7e0000);sta(0x2116);c.emit(0xe2,0x20);c.store(0x4300,1);c.store(0x4301,0x18)
 c.label('ppu383');fault();c.store(0x420b,1);c.emit(0xea)
 c.label('ppu_done383');c.emit(0xc2,0x20);lda(0x24);c.emit(0x18,0x69,12,0);sta(0x24);c.emit(0xe2,0x20);c.jump('job394')
 c.label('display_entry394');c.emit(0xe2,0x20);fault();lda(0x57);c.branch(0xf0,'warm_commit394')
 c.label('cold_commit394');fault();lda(0x4212);c.branch(0x10,'cold_commit394');c.jump('display383')
 c.label('warm_commit394');lda(0x4212);cond(0x10,'abort383');c.jump('display383')
 c.label('abort16_394');c.emit(0xe2,0x20)
 c.label('abort383');c.store(0x420c,0);c.store(0x2100,0x80);c.store(0x606f,0xee);c.jump('rearm394')
 c.label('zero394_byte');c.emit(0);c.data[zero_patch:zero_patch+2]=struct.pack('<H',c.labels['zero394_byte'])
 c.labels['display383']=0;offset=len(c.finish());original=display.Code
 try:
  display.Code=lambda origin:original(origin+offset);body=commit.rom(d);labels=json.loads((d/'labels.json').read_text())
 finally:display.Code=original
 c.labels['display383']=labels['safe380_apply'];prefix=c.finish();suffix=(d/'display.sfc').read_bytes()[:body]
 ack=suffix.index(bytes.fromhex('8d5860'));suffix=suffix[:ack+3]+bytes([0x4c,c.labels['frame394']&255,c.labels['frame394']>>8])+suffix[ack+6:]
 image=bytearray([255])*32768;image[:offset]=prefix;image[offset:offset+body]=suffix;image[0x7fc0:0x7fd5]=b'NES394 FINAL DMA ABI ';image[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
 for p in range(0x7fe0,0x8000,2):struct.pack_into('<H',image,p,0x8000)
 check=sum(image)&65535;struct.pack_into('<HH',image,0x7fdc,check^65535,check);(d/'spool.sfc').write_bytes(image)
 labels=dict(c.labels,commit383_active=labels['active']);(d/'spool-labels.json').write_text(json.dumps(labels,indent=2)+'\n');return offset+body,labels

def current_view(frame):
 if frame<=916:return recorded_view(frame)
 _,groups=plans();fields=next(p for p in groups[frame-904]if p[0]==3)[16:40]
 cert=bytes.fromhex((BASE/f'probes/nes-joint284/test04/prelude{frame}.hex').read_text())[16:48]
 return bytes([(frame-905)%2,fields[18],fields[22]])+cert[14:19]+fields[12:16]

def fixtures(frame,armdir,synthetic_tiles=False):
 jobs=json.loads((armdir/f'jobs{frame}.json').read_text());tiles={}
 groups={}
 for x in csv.reader((BASE/'probes/nes-present378/control02/joint-events.csv').read_text().splitlines()):
  if x[:2]==['read336',str(frame)]and int(x[3])==7:groups.setdefault(int(x[2]),[]).append(x)
 for rows in groups.values():
  kind=int(rows[0][4]);first=int(rows[0][5]);data=bytes(int(x[7])for x in rows)
  assert [int(x[6])for x in rows]==list(range(len(data)))
  for i,b in enumerate(data):tiles[kind,first+i]=b
 result=[];token=1
 for j in jobs:
  r=bytes.fromhex(j['record']);data=bytes.fromhex(j['payload'])
  if r[9]<2:data=bytes(u16(r,4))if synthetic_tiles else bytes(tiles[r[9],u16(r,10)*(32 if r[9]else 16)+i]for i in range(u16(r,4)))
  sizes=j['fragments']if r[9]>=2 else[len(data)]
  if not sizes:sizes=[0]
  at=0
  for size in sizes:
   result.append(dict(record=r.hex(),data=data[at:at+size].hex(),offset=at,first=at==0,last=at+size==len(data),token=token));at+=size;token+=1
  assert at==len(data)
 return result

LUA=r'''
local at,reads,staged,jobdone,viewreads=1,0,0,0,0
local ack={};local ppu_start=nil;local ppu_end=nil;local faultreads=0;local invalid=true
local bus=assert(io.open(OUT..'/events.csv','w'));local timings=assert(io.open(OUT..'/timings.csv','w'));timings:write('phase,case,clock,scanline\n')
local function state()return emu.getState()end
local function note(op,a,v)local s=state();bus:write(string.format('%d,%d,%d,%d,%d,%d\n',at,op,a,v or 0,s.masterClock,s['ppu.scanline']));bus:flush();return v end
local function mark(kind)local s=state();timings:write(string.format('%s,%d,%d,%d\n',kind,at,s.masterClock,s['ppu.scanline']));timings:flush()end
local function bytes(s)local t={};for b in s:gmatch('%x%x')do t[#t+1]=tonumber(b,16)end;return t end
for _,j in ipairs(JOBS)do j.r=bytes(j.record);j.payload=bytes(j.data)end
for _,q in ipairs({{0x16000,INITCG},{0x16200,INITOAM},{0x16500,INITHDMA}})do for i,b in ipairs(bytes(q[2]))do emu.write(q[1]+BANK*0x8000+i-1,b,emu.memType.snesWorkRam)end end
for i,b in ipairs(bytes(INITMAP))do emu.write(0x6000+BANK*0x4000+i-1,b,emu.memType.snesVideoRam)end
for i,b in ipairs(bytes(INITCG))do emu.write(i-1,b,emu.memType.snesCgRam)end
for i,b in ipairs(bytes(INITOAM))do emu.write(i-1,b,emu.memType.snesSpriteRam)end
emu.addMemoryCallback(function(a,v)
 local j=JOBS[at]
 if a==0x6001 then faultreads=faultreads+1;return note(0,a,STOP and staged>=1 and 0x80 or invalid and 0x40 or 0)end
 if a==0x6040 then return note(0,a,j and 1 or 0)end
 if a==0x6099 then return note(0,a,1)end
 if a==0x6054 then return note(0,a,j and 0 or 1)end
 if a>=0x6091 and a<=0x6098 then return note(0,a,CONTEXT[a-0x6090])end
 if a>=0x6070 and a<=0x607b then viewreads=viewreads+1;assert(a==0x6070+viewreads-1);return note(0,a,VIEW[viewreads])end
 if a>=0x6080 and a<=0x6090 then
  assert(j);local i=a-0x6080;local n=#j.payload
  return note(0,a,i<12 and j.r[i+1] or i==12 and j.offset%256 or i==13 and math.floor(j.offset/256) or i==14 and n%256 or i==15 and math.floor(n/256) or (j.first and 1 or 0)+(j.last and 2 or 0))
 end
 if a>=0x6048 and a<=0x604b then return note(0,a,math.floor((j and j.token or FINAL_TOKEN)/2^(8*(a-0x6048)))%256)end
 return v
end,emu.callbackType.read,0x6000,0x6099)
emu.addMemoryCallback(function(a,v)local j=assert(JOBS[at]);assert(a==0x400800+reads);reads=reads+1;return note(0,a,assert(j.payload[reads]))end,emu.callbackType.read,0x400800,0x4017ff)
emu.addMemoryCallback(function(a,v)
 note(1,a,v)
 if a>=0x604c and a<=0x604f then ack[a-0x604c]=v
 elseif a==0x6050 then
  local j=assert(JOBS[at]);assert(v==0xa5 and reads==#j.payload and not ppu_start)
  for i=0,3 do assert(ack[i]==math.floor(j.token/2^(8*i))%256)end
  mark('stored');at=at+1;reads=0;ack={};staged=staged+1
 elseif a==0x6058 then
  assert(v==0x5a and not STOP and staged==#JOBS and viewreads==12)
  local s=state();assert(s['ppu.scanline']>=225 and (COLD or not ppu_start or math.floor(s.masterClock/357368)==math.floor(ppu_start/357368)),'atomic display')
  for i=0,3 do assert(ack[i]==math.floor(FINAL_TOKEN/2^(8*i))%256,'fence token')end
  for i,b in ipairs(bytes(EXPECTMAP))do assert(emu.read(0x6000+BANK*0x4000+i-1,emu.memType.snesVideoRam)==b,'fullmap '..i)end
  for i,b in ipairs(bytes(EXPECTOAM))do assert(emu.read(i-1,emu.memType.snesSpriteRam)==b,'OAM '..i)end
  for i,b in ipairs(bytes(EXPECTCG))do assert(emu.read(i-1,emu.memType.snesCgRam)==b,'CGRAM '..i)end
  for i,b in ipairs(bytes(EXPECTHDMA))do assert(emu.read(0x16500+BANK*0x8000+i-1,emu.memType.snesWorkRam)==b,'HDMA '..i)end
  for _,j in ipairs(JOBS)do if j.r[10]<2 then
   local dest=j.r[1]+256*j.r[2];for i,b in ipairs(j.payload)do assert(emu.read(dest*2+j.offset+i-1,emu.memType.snesVideoRam)==b,'tile')end
  end end
  local out=assert(io.open(OUT..'/cpu-result.json','w'));out:write(string.format('{"passed":true,"staged":%d,"PPU_jobs":%d,"PPU_start":%d,"PPU_end":%d,"ACK_master":%d,"ACK_scanline":%d,"fault_reads":%d}',staged,jobdone,ppu_start or 0,ppu_end or 0,s.masterClock,s['ppu.scanline'],faultreads));out:close();bus:close();timings:close();emu.stop(0)
 elseif a==0x606f then
  assert(STOP and v==0xee and not ppu_start and staged==1);local out=assert(io.open(OUT..'/cpu-result.json','w'));out:write('{"passed":true,"STOP":true,"final_ACK":false,"PPU_jobs":0}');out:close();bus:close();timings:close();emu.stop(0)
 end
end,emu.callbackType.write,0x604c,0x606f)
emu.addMemoryCallback(function(a,v)note(1,a,v);assert(v==0xa5);invalid=false end,emu.callbackType.write,0x6006)
emu.addMemoryCallback(function(a,v)return note(0,a,v)end,emu.callbackType.read,0x4212)
emu.addMemoryCallback(function(a,v)return note(0,a,v)end,emu.callbackType.read,0x2137,0x213f)
for _,r in ipairs({{0x2100,0x2133},{0x4300,0x4334},{0x420b,0x420c}})do emu.addMemoryCallback(function(a,v)note(1,a,v)end,emu.callbackType.write,r[1],r[2])end
emu.addMemoryCallback(function()mark('stage_done')end,emu.callbackType.exec,LABELS.stage_done383)
emu.addMemoryCallback(function()local s=state();assert(COLD or s['ppu.scanline']>=225);ppu_start=ppu_start or s.masterClock;mark('PPU_trigger')end,emu.callbackType.exec,LABELS.ppu383)
emu.addMemoryCallback(function()local s=state();assert(COLD or s['ppu.scanline']>=225);ppu_end=s.masterClock;jobdone=jobdone+1;mark('PPU_done')end,emu.callbackType.exec,LABELS.ppu_done383)
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--arm',required=True,type=Path);p.add_argument('--frames',default='907,908,909,910,911,912,913,914,915,916');p.add_argument('--synthetic-tiles',action='store_true');a=p.parse_args();root=a.out.resolve();root.mkdir(parents=True,exist_ok=False);oracle,_=plans();results=[]
 for f,stop in[(int(f),False)for f in a.frames.split(',')]+[(907,True)]:
  d=root/(str(f)+('-stop'if stop else''));d.mkdir();body,labels=rom(d);jobs=fixtures(f,a.arm,a.synthetic_tiles);bank=(f-905)%2
  prior=(oracle/f'expected-{f-906}.bin').read_bytes()if f>=907 else bytes(8570);expected=(oracle/f'expected-{f-904}.bin').read_bytes();view=current_view(f)
  (d/'fixture.json').write_text(json.dumps(jobs,indent=2)+'\n')
  header='local OUT='+json.dumps(d.as_posix())+'\nlocal BANK='+str(bank)+'\nlocal STOP='+str(stop).lower()+'\nlocal FINAL_TOKEN='+str(len(jobs)+1)+'\nlocal VIEW={'+','.join(map(str,view))+'}\n'
  context=struct.pack('<IHBB',f-904,f-904,bank,int(f<907));header+='local COLD='+str(f<907).lower()+'\nlocal CONTEXT={'+','.join(map(str,context))+'}\n'
  header+='local LABELS={'+','.join(n+'='+str(v)for n,v in labels.items())+'}\nlocal JOBS={'+','.join('{record="'+j['record']+'",data="'+j['data']+'",offset='+str(j['offset'])+',first='+str(j['first']).lower()+',last='+str(j['last']).lower()+',token='+str(j['token'])+'}'for j in jobs)+'}\n'
  for name,data in [('INITMAP',prior[:4096]),('INITCG',prior[4096:4608]),('INITOAM',prior[4608:5152]),('INITHDMA',prior[5152:8570]),('EXPECTMAP',expected[:4096]),('EXPECTCG',expected[4096:4608]),('EXPECTOAM',expected[4608:5152]),('EXPECTHDMA',expected[5152:8570])]:header+='local '+name+'="'+data.hex()+'"\n'
  guarded="local original_assert=assert\nfunction assert(v,msg)if not v then local e=io.open(OUT..'/error.txt','a');e:write(tostring(msg)..'\\n'..debug.traceback()..'\\n');e:close();emu.stop(1)end;return original_assert(v,msg)end\n"+LUA
  (d/'capture.lua').write_text(header+guarded,newline='\n');env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
  with(d/'mesen.log').open('wb')as log:r=subprocess.run(['C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe','--testRunner',str(d/'capture.lua'),str(d/'spool.sfc'),'--timeout=30','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=50,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(d/'mesen.log').read_text(errors='replace')[-2000:]
  result=json.loads((d/'cpu-result.json').read_text());assert result['passed'];result.update(frame=f,body_bytes=body,synthetic_tile_bytes=a.synthetic_tiles,ROM=sha(d/'spool.sfc'),fixture=sha(d/'fixture.json'),events=sha(d/'events.csv'));results.append(result);print(json.dumps(result),flush=True)
 (root/'result.json').write_text(json.dumps(dict(passed=True,cases=results,WRAM=dict(tile=8192,jobs=3072,map=4096,total=15360),fullresident=False,cold=any(x['frame']<907 for x in results),scope=__doc__),indent=2)+'\n')
if __name__=='__main__':main()
