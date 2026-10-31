# SPDX-License-Identifier: MIT
"""Actual65816 early drain against frozen input schedules; no ARM cost claim."""
import argparse,csv,json,os,re,shutil,subprocess
from pathlib import Path
from hashlib import sha256
sha=lambda p:sha256(p.read_bytes()).hexdigest()
INJECT=r'''
local early505=false
local seen505={}
local frozen505={}
local earlyCount505={}
local beamClock505=0
local maxSetup505=0
local remaining505,length505=0,0
local minLine505,maxLine505=999,0
local p505=assert(io.open(ROOT..'/early505.csv','w'));p505:write('generation,early,cursor,length,masterclock,scanline\n')
emu.addMemoryCallback(function()
 early505=true
 local g=word(0x1208)
 for cursor,bytes in pairs(frozen505[g]or{})do for i=0,5 do assert(rd(0x4000+cursor+i)==bytes[i+1],'consumed descriptor mutated')end end
end,emu.callbackType.exec,@early505@)
emu.addMemoryCallback(function()early505=false end,emu.callbackType.exec,@early_return505@)
emu.addMemoryCallback(function()beamClock505=emu.getState().masterClock end,emu.callbackType.exec,@beam505@)
emu.addMemoryCallback(function(a,v)if v==1 and early505 then
 local cost=emu.getState().masterClock-beamClock505;assert(cost<=3072,'early DMA setup budget')
 maxSetup505=math.max(maxSetup505,cost)
end end,emu.callbackType.write,0x420b)
emu.addMemoryCallback(function()if early505 then
 assert(remaining505>0,'untracked early VRAM byte')
 if remaining505==length505 or remaining505==1 then
  local line=emu.getState()['ppu.scanline'];assert(line>=225 and line<=261,'early DMA endpoint outside NTSC VBlank')
  minLine505=math.min(minLine505,line);maxLine505=math.max(maxLine505,line)
 end
 remaining505=remaining505-1
end end,emu.callbackType.write,0x2118,0x2119)
emu.addMemoryCallback(function()
 if MODE=='bad_coverage'and word(0x1208)==FAULT then
  local at=0x1320+word(0x1254)+144;emu.write(at,rd(at)&254,emu.memType.snesWorkRam)
 end
end,emu.callbackType.exec,@coverage212@)
emu.addMemoryCallback(function()
 local st=emu.getState();local cursor=word(0x1252);local g=word(0x1208);local n=word(0x4004+cursor)
 local key=g..':'..cursor;assert(not seen505[key],'descriptor replay');seen505[key]=true
 if early505 then
  assert(word(0x1228)==1 and cursor+8<word(0x1250),'mutable last descriptor consumed')
  assert(word(0x1260)==1,'tentative write unowned')
  if rd(0x1024)~=0 then assert(word(0x1034)~=word(0x1032),'active bank early write')end
  assert(st['ppu.scanline']>=225 and st['ppu.scanline']<=258,'late early DMA')
  earlyCount505[g]=(earlyCount505[g]or 0)+1
  assert(remaining505==0,'unfinished early DMA');remaining505=n;length505=n
  frozen505[g]=frozen505[g]or{};local bytes={};for i=0,5 do bytes[i+1]=rd(0x4000+cursor+i)end;frozen505[g][cursor]=bytes
 end
 p505:write(string.format('%d,%d,%d,%d,%d,%d\n',g,early505 and 1 or 0,cursor,n,st.masterClock,st['ppu.scanline']));p505:flush()
end,emu.callbackType.exec,@dma505@)
if @POISON@ then
 for i=0,303 do emu.write(0x1320+i,255,emu.memType.snesWorkRam)end
 for _,a in ipairs({0x125a,0x125b,0x1260})do emu.write(a,255,emu.memType.snesWorkRam)end
 local checked=false
 emu.addMemoryCallback(function()if not checked then
  for i=0,303 do assert(rd(0x1320+i)==0,'stale coverage survived boot')end
  assert(word(0x125a)==0x8080 and word(0x1260)==0,'boot did not rebuild zero-raw/tentative state');checked=true
 end end,emu.callbackType.exec,@poll@)
end
'''

def run(a):
    assert sha(a.input/'client.sfc')==sha(a.baseline_client/'sink165.sfc'),'fixture baseline ROM mismatch'
    a.out=a.out.resolve();assert a.out.as_posix().isascii();a.out.mkdir(parents=True,exist_ok=False)
    labels=json.loads((a.client/'labels.json').read_text());prior=json.loads((a.baseline_client/'labels.json').read_text())
    for f in a.input.iterdir():
        if f.is_file()and f.suffix=='.bin':shutil.copy2(f,a.out/f.name)
    shutil.copy2(a.client/'sink165.sfc',a.out/'client.sfc')
    lua=(a.input/'capture.lua').read_text()
    lua=re.sub(r'io.open\("[^"]+/error.txt"','io.open("'+a.out.as_posix()+'/error.txt"',lua)
    lua=re.sub(r'local ROOT="[^"]+"','local ROOT="'+a.out.as_posix()+'"',lua,count=1)
    lua=lua.replace('local MODE="normal"','local MODE="'+a.mode+'"')
    if a.start_offset:lua=lua.replace('local start=3000000','local start='+str(3000000+a.start_offset))
    if a.stall4096:
        lua=lua.replace('local function loaded()', 'local stalled505=false;local stallUntil505=0\nlocal function loaded()',1)
        lua=lua.replace('if st.masterClock<ready[index]then return end', '''if not stalled505 and word(0x1250)>=16 and word(0x1252)+8<word(0x1250) and word(0x4004+word(0x1252))==4096 then
 stalled505=true;stallUntil505=st.masterClock+2*357368
 end
 if st.masterClock<stallUntil505 then return end
 if st.masterClock<ready[index]then return end''',1)
    # Existing504 observation callbacks and any original execution hooks all
    #refer to489 labels. Rebind every exact address once, without cascades.
    address={str(v):str(labels[k])for k,v in prior.items()if k in labels}
    lua=re.sub(r'(emu.callbackType.exec,)(\d+)',lambda m:m[1]+address[m[2]],lua)
    inj=INJECT.replace('@POISON@','true'if a.poison else'false')
    for k,v in labels.items():inj=inj.replace('@'+k+'@',str(v))
    assert not re.search(r'@\w+@',inj)
    if 'local pf504='not in lua:
        phases="local pf504=assert(io.open(ROOT..'/phases504.csv','w'));pf504:write('generation,phase,masterclock,scanline\\n')\n"
        for name in ['seal','upload165_entry','wait169','final_upload212_entry']:
            phases+='emu.addMemoryCallback(function()local st=emu.getState();pf504:write(string.format("%d,'+name+',%d,%d\\n",packet and pw(8)or 0,st.masterClock,st["ppu.scanline"]));pf504:flush()end,emu.callbackType.exec,'+str(labels[name])+')\n'
        at=lua.index('emu.addMemoryCallback(function(a,v)');lua=lua[:at]+phases+lua[at:]
    at=lua.index('local pf504=');lua=lua[:at]+inj+lua[at:]
    lua=lua.replace('if a==0x6001 then','if a==0x6001 then\n if MODE=="stop_prefix" and packet and pw(8)==FAULT and pb(0)==3 and (earlyCount505[FAULT]or 0)>0 then return 128 end',1)
    lua=lua.replace("if rejected then\n", """if rejected then
   assert((earlyCount505[FAULT]or 0)>0,'fault did not cover early DMA')
   for i=0,151 do assert(rd(0x1320+word(0x1254)+i)==0,'canceled bank still certified')end
   assert(rd(0x125a+word(0x1034))==0 and word(0x1260)==0,'canceled cache published')
   assert(word(0x1248)==FAULT-905 and word(0x124a)==0,'canceled identity published')
   if MODE=='stop_prefix'then assert(lastStatus==0xe4,'STOP status')end
""",1)
    lua=lua.replace("local f=assert(io.open(ROOT..'/result.json','w'));", "assert(remaining505==0,'incomplete early DMA');local q=assert(io.open(ROOT..'/setup505.txt','w'));q:write(maxSetup505);q:close();q=assert(io.open(ROOT..'/endpoints505.json','w'));q:write(string.format('[%d,%d]',minLine505,maxLine505));q:close();local f=assert(io.open(ROOT..'/result.json','w'));",1)
    (a.out/'capture.lua').write_text(lua,encoding='utf8',newline='\n')
    env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    with(a.out/'mesen.log').open('wb')as log:
        r=subprocess.run([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.out/'client.sfc'),'--timeout=240','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=250,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0,(r.returncode,(a.out/'mesen.log').read_text(errors='replace'),(a.out/'error.txt').read_text()if(a.out/'error.txt').exists()else'no Lua error file')
    after=json.loads((a.out/'result.json').read_text());before=json.loads((a.input/'result.json').read_text());assert after['passed']
    if a.mode=='normal':
        for k in ['commits','last_status','vram_DMA_B']:assert before[k]==after[k],(k,before[k],after[k])
    else:
        assert after['commits']==1 and after['last_status']>=224
        assert sha(a.out/'retained.rgb')==sha(a.input/'frame-905.rgb'),'active display changed after rejection'
    for f in a.out.glob('frame-*.rgb'):assert sha(f)==sha(a.input/f.name),f.name
    rows=list(csv.DictReader((a.out/'early505.csv').open()));early=[r for r in rows if r['early']=='1']
    if a.stall4096:assert any(int(r['length'])==4096 for r in early),'4KiB early boundary untested'
    report=dict(passed=True,scope=__doc__,mode=a.mode,start_offset=a.start_offset,poisoned_boot=a.poison,client_SHA256=sha(a.out/'client.sfc'),input_SHA256=sha(a.input/'requests.bin'),early_descriptors=len(early),early_bytes=sum(int(r['length'])for r in early),identical_VRAM_DMA_bytes_and_RGB=a.mode=='normal',retained_active_RGB=a.mode!='normal',max_setup_masterclocks=int((a.out/'setup505.txt').read_text()),observed_stack_B=after['observed_stack_B'],frames=[dict(generation=b['generation'],baseline_ACK=a['ACK_masterclock'],candidate_ACK=b['ACK_masterclock'],ACK_delta_ms=(b['ACK_masterclock']-a['ACK_masterclock'])/21477.272,baseline_release_to_ACK_ms=(a['ACK_masterclock']-a['release_masterclock'])/21477.272,candidate_release_to_ACK_ms=(b['ACK_masterclock']-b['release_masterclock'])/21477.272)for a,b in zip(before['frames'],after['frames'])])
    report['modified_schedule_stress']=a.stall4096 or bool(a.start_offset)
    report['early_DMA_endpoint_scanlines']=json.loads((a.out/'endpoints505.json').read_text())if early else None
    if report['modified_schedule_stress']:
        for f in report['frames']:f['ACK_delta_ms']=None
    (a.out/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['input','client','baseline-client','out']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--mesen',type=Path,default=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe'))
    p.add_argument('--mode',default='normal',choices=['normal','stop_prefix','bad_coverage','bad_version','bad_count','zero_count','bad_length'])
    p.add_argument('--start-offset',type=int,default=0)
    p.add_argument('--poison',action='store_true')
    p.add_argument('--stall4096',action='store_true')
    run(p.parse_args())
