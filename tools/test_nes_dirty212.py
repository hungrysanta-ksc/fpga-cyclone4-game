# SPDX-License-Identifier: MIT
"""Actual211 planner/C packets -> actual65816 -> pixels vs actual186 converter.
File mailbox and physical CHR fixture, no live NES/RTL/PSRAM/FPS claim.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_resident211 import prepare,ROOT,BASE,sha,once
import nes_sink212,nes_dirty212
from test_nes_bulk194_snes import script

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--modes',nargs='+',default=['normal']);p.add_argument('--reference-run',type=Path);a=p.parse_args();out=a.out.resolve()
 assert str(out).isascii(),'Mesen Lua file paths need an ASCII run directory; archive afterwards.'
 out.mkdir(parents=True,exist_ok=False)
 tracked=[Path(__file__),ROOT/'tools/nes_dirty212.py',ROOT/'tools/nes_sink212.py',ROOT/'tests/nes-functional/dirty212_host.c']
 input_pins={str(f.relative_to(ROOT)):sha(f) for f in tracked}
 (out/'scripts').mkdir()
 for f in tracked:shutil.copyfile(f,out/'scripts'/f.name)
 common=out/'common';prepare(common)
 original=(ROOT/'tests/nes-functional/resident211_host.c').read_text()
 head=original[:original.index('static uint8_t refbg')]
 # Include only actual scene fixture and its conversion, no consumer model.
 start=original.index('bool reference203_build(');end=original.index('static bool write_slot(',start)
 head+=original[start:end]
 body=(ROOT/'tests/nes-functional/dirty212_host.c').read_text()
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
 mesen=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe')
 env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 def run(cmd,cwd,name):
  with (cwd/(name+'.log')).open('wb') as f:r=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(cwd/(name+'.log')).read_text(errors='replace')[-5000:]
 sources=['host.c','nes_resident211.c','nes_planner211.c','nes_native165.c','nes_trace166.c','reference203.c','nes_native_sink165.c','nes_sink_trace168.c']
 for typ in ['reference','candidate']:
  d=out/typ;shutil.copytree(common,d)
  nes_sink212.prepare(d)
  h=head+body
  if typ=='reference':
   for n in ['nes_native_sink165.c','nes_sink_bulk195.inc']:shutil.copyfile(BASE/'probes/nes-budget210/arm03/src'/n,d/n)
   # Unselected branch kept linkable but never executed by reference process.
   h+='\nbool nes_sink212_begin(struct nes_native_sink165 *s,struct nes_resident211 *r){(void)s;(void)r;return false;}\nbool nes_sink212_seal(struct nes_native_sink165 *s,const struct nes_native_video165 *v,struct nes_resident211 *r){(void)s;(void)v;(void)r;return false;}\n'
  (d/'host.c').write_text(h,encoding='utf8',newline='\n')
  run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2',*sources,'-o','host.exe'],d,'gcc')
 nes_dirty212.build(out/'client')
 ref=BASE/'probes/nes-copy186/evidence/coupled03/inherit';lua=script(ref)
 lua=once(lua," if not packet and (rejected or ordinal>TOTAL) then", " local done=io.open(OUT_DIR..'/producer-done.txt','r')\n if done then local expected=tonumber(done:read('*a'));done:close();")
 lua=once(lua,"assert(commits==(MODE=='normal' and 7 or 1));assert(maximumDma==2048);assert(retires>0)","assert(commits==expected)")
 lua=once(lua,"  if MODE=='normal' then assert(chunks>0 and held>0)end",'')
 lua=once(lua,'local lastChunks=0','local lastChunks=0\nlocal dmaRegs={};local vramBytes=0;local vramCommands=0;local largestList=0;local blankFrames={};local singleBlank=0')
 lua=once(lua,' local st=emu.getState()\n if a==0x2180', ''' local st=emu.getState()
 if a>=0x4300 and a<=0x4306 then dmaRegs[a]=v end
 if a==0x420b and v==1 and packet and pb(0)==3 then blankFrames[st.frameCount]=true end
 if a==0x420b and v==1 and dmaRegs[0x4301]==0x18 then
  vramBytes=vramBytes+(dmaRegs[0x4305] or 0)+256*(dmaRegs[0x4306] or 0);vramCommands=vramCommands+1
  if CANDIDATE then largestList=math.max(largestList,word(0x1250)//8)end
 end
 if a==0x2180''')
 lua=once(lua,'{{0x2180,0x2180},{0x2100,0x2122}', '{{0x4300,0x4306},{0x2180,0x2180},{0x2100,0x2122}')
 lua=once(lua,'"max_dma":%d}', '"max_dma":%d,"vram_bytes":%d,"vram_commands":%d,"largest_list":%d,"single_vblank_commits":%d}')
 lua=once(lua,'retires,maximumDma));o:close()', 'retires,maximumDma,vramBytes,vramCommands,largestList,singleBlank));o:close()')
 lua=once(lua,'  if bytes:byte(1)==1 then', '''  if bytes:byte(1)==1 then
   local count=0;for _ in pairs(blankFrames)do count=count+1 end
   if count==1 then singleBlank=singleBlank+1 end
   if CANDIDATE and pw(8)==3 then assert(count==1,'warm frame must finish in ONE VBlank')end
   local f=assert(io.open(OUT_DIR..'/vblank-'..pw(8)..'.txt','w'));f:write(count);f:close();blankFrames={}
''')
 lua=lua.replace('pw(8)==13','pw(8)==2')
 # Candidate always writes an inactive bank before final VBlank; old reference
 # has its own proven active-small-diff path and cannot use this assertion.
 lua=once(lua,"if previousScreen and packet and pb(0)==3 and (rd(0x1025)==0xe2 or rd(0x1025)==0xe3)then", "if CANDIDATE and previousScreen and packet and pb(0)==3 and rd(0x1025)~=3 then")
 # BEGIN/SEAL corruptions must be rejected before altering displayed PPU state.
 needle=" if pb(0)==7 then\n  local t=assert(io.open"
 injection=''' if CANDIDATE and pw(8)==2 then
  local b={packet:byte(1,#packet)}
  if pb(0)==1 then
   if MODE=='bad_bank' then b[19]=1-b[19] end
   if MODE=='bad_base' then b[21]=b[21]~1 end
   if MODE=='bad_epoch' then b[25]=b[25]~1 end
  end
  if pb(0)==3 and MODE=='missing_slot' then b[168]=b[168]|128 end
  if pb(0)==3 and MODE=='old_seal' then b[37]=0x41;b[38]=0x19 end
  if pb(0)==7 and MODE=='duplicate_tile' and pw(10)>0 then b[11]=0;b[12]=0 end
  if pb(1)==2 and MODE=='duplicate_map' and pw(10)>0 then b[11]=0;b[12]=0 end
  packet=string.char(table.unpack(b))
 end
'''
 lua=once(lua,needle,injection+needle)
 cases=[]
 reference_run=a.reference_run.resolve() if a.reference_run else out/'reference-normal'
 if a.reference_run:
  assert json.loads((reference_run/'consumer-result.json').read_bytes())['commits']==14
 jobs=([('reference','normal')] if not a.reference_run else [])+[('candidate',m) for m in a.modes]
 for typ,mode in jobs:
  d=out/(typ+'-'+mode);d.mkdir()
  diagnostic="\nlocal original_assert=assert\nfunction assert(v,msg) if not v then local f=io.open(OUT_DIR..'/lua-error.txt','a');if f then f:write(tostring(msg)..'\\n'..debug.traceback()..'\\n');f:close()end end;return original_assert(v,msg)end\n"
  (d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\nlocal CANDIDATE='+('true' if typ=='candidate' else 'false')+diagnostic+lua,encoding='utf8')
  rom=out/'client/sink165.sfc' if typ=='candidate' else BASE/'probes/nes-bulk195/build02/sink165.sfc'
  if not rom.exists():rom=BASE/'probes/nes-bulk195/snes01/client/sink165.sfc'
  assert rom.exists(),rom
  with (d/'host.log').open('wb') as hf,(d/'mesen.log').open('wb') as mf:
   h=subprocess.Popen([str(out/typ/'host.exe'),mode,typ],cwd=d,env=env,stdout=hf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   m=subprocess.Popen([str(mesen),'--testRunner',str(d/'capture.lua'),str(rom),'--timeout=55','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   try:mr=m.wait(timeout=60);hr=h.wait(timeout=5)
   finally:
    for child in [h,m]:
     if child.poll() is None:child.kill();child.wait()
  assert mr==hr==0,((d/'mesen.log').read_text(errors='replace')[-4500:],(d/'host.log').read_text(errors='replace')[-2000:])
  c=json.loads((d/'consumer-result.json').read_bytes());c.update(type=typ,mode=mode,host=(d/'host.log').read_text())
  if typ=='candidate':
   for i in range(1,c['commits']+1):assert (d/f'frame-{i}.rgb').read_bytes()==(reference_run/f'frame-{i}.rgb').read_bytes(),(mode,i)
  cases.append(c);print(json.dumps(c),flush=True)
 result=dict(passed=True,cases=cases,scope=__doc__,client=sha(out/'client/sink165.sfc'),physical=False,rtl_coupled=False,
             reference_files={str(f):sha(f) for f in reference_run.iterdir() if f.suffix in ['.rgb','.json','.lua','.log']},
             sources=input_pins,generated_sources={str(f.relative_to(out)):sha(f) for typ in ['reference','candidate'] for f in (out/typ).iterdir() if f.suffix in ['.c','.h','.inc']})
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
