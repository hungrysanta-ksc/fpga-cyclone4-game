# SPDX-License-Identifier: MIT
"""Pinned230 SMB3 scroll -> actual231 C -> real23265816 ACK/WRAM/VRAM.

File mailbox/source reads are fixtures. No physical FPS, FPGA producer timing,
or whole NES core emulation. Compare used VRAM and complete output metadata.
"""
from pathlib import Path
import argparse,csv,json,os,shutil,subprocess
from nes_delta231 import BASE,ROOT,sha,once
import nes_sparse232

RPC=r'''
static unsigned ordinal232;static uint32_t token232=0x23200000;
static bool cost_exchange(void *ctx,const uint8_t *p,unsigned n,uint8_t ack[12]){
 (void)ctx;packets225++;wire225+=n+3;
 uint8_t length[2]={(uint8_t)n,(uint8_t)(n>>8)};assert(packet_trace);
 assert(fwrite(length,1,2,packet_trace)==2&&fwrite(p,1,n,packet_trace)==n);
 if(p[1]==2&&(p[0]==2||p[0]==4)){mapwire225+=n+3;mapcommands225++;}
 unsigned id=++ordinal232;char tmp[80],name[80];sprintf(tmp,"req-%04u.tmp",id);sprintf(name,"req-%04u.bin",id);
 FILE *f=fopen(tmp,"wb");assert(f&&fwrite(p,1,n,f)==n);fclose(f);assert(rename(tmp,name)==0);
 sprintf(name,"ack-%04u.bin",id);DWORD start=GetTickCount();
 do{f=fopen(name,"rb");if(f){assert(fread(ack,1,12,f)==12&&fgetc(f)==EOF);fclose(f);return true;}Sleep(1);}while(GetTickCount()-start<60000);
 return false;
}
static bool bulk232(unsigned kind,unsigned slot,unsigned gen,const uint8_t *bytes,unsigned n){
 char name[80];sprintf(name,"tile-%04u.bin",ordinal232+1);FILE *f=fopen(name,"wb");assert(f&&fwrite(bytes,1,n,f)==n);fclose(f);
 unsigned at=slot*n;uint8_t d[12]={1,(uint8_t)kind,(uint8_t)n,(uint8_t)(n>>8),(uint8_t)at,(uint8_t)(at>>8),(uint8_t)gen,(uint8_t)(gen>>8)};
 for(unsigned i=0;i<4;i++)d[8+i]=(uint8_t)(token232>>(8*i));
 token232++;return nes_sink195_bulk(&real232,d);
}
static void cost225(void){
 char name[80];sprintf(name,"bank-%u.bin",r.generation);FILE *f=fopen(name,"wb");assert(f&&fwrite(&banks[cache.target],1,sizeof banks[0],f)==sizeof banks[0]);fclose(f);
 assert(nes_sink231_seal(&real232,&candidate,&cache,&dirty));
}
'''

CHECK=r'''
   local f=assert(io.open(OUT_DIR..'/expected-'..pw(8)..'.bin','rb'));local want=f:read('*a');f:close();assert(#want==8570)
   local offsets={0x5000,0x6000,0x6200,0x6500};local sizes={4096,512,544,3418};local index=0
   for region=1,4 do local base=0x10000+word(0x1020)+offsets[region]
    for i=0,sizes[region]-1 do assert(rd(base+i)==want:byte(index+i+1),'metadata mismatch '..pw(8)..' '..region..' '..i)end
    index=index+sizes[region]
   end
   f=assert(io.open(OUT_DIR..'/bank-'..pw(8)..'.bin','rb'));local bank=f:read('*a');f:close();assert(#bank==24576)
   local target=word(0x1034);local bg=target==0 and 0 or 0xc000;local obj=target==0 and 0x4000 or 0x8000
   local map=target==0 and 0x6000 or 0xa000;local raw=target==0 and 0x5000 or 0x9000
   local function vr(a)return emu.read(a,emu.memType.snesVideoRam)end
   for slot=0,1151 do if (pb(40+slot//8)&(1<<(slot%8)))~=0 then
    local n=slot<1024 and 16 or 32;local at=slot<1024 and slot*16 or (slot-1024)*32
    local dst=(slot<1024 and bg or obj)+at;local src=(slot<1024 and 0 or 16384)+at
    for i=0,n-1 do assert(vr(dst+i)==bank:byte(src+i+1),'used pattern mismatch '..pw(8)..' '..slot..' '..i)end
   end end
   for i=0,4095 do assert(vr(map+i)==want:byte(i+1),'VRAM map mismatch '..pw(8)..' '..i)end
   for i=0,2047 do assert(vr(raw+i)==want:byte(5152+1121+i+1),'VRAM raw mismatch '..pw(8)..' '..i)end
   local f=assert(io.open(OUT_DIR..'/timing-'..pw(8)..'.txt','w'));f:write(st.masterClock-sealStart232);f:close();sealStart232=nil
'''


def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--last',type=int,default=975)
 a=p.parse_args();out=a.out.resolve();assert str(out).isascii();out.mkdir(parents=True,exist_ok=False)
 src=BASE/'probes/nes-delta231/test07';common=out/'common';common.mkdir()
 for f in src.iterdir():
  if f.suffix in ('.c','.h','.inc'):shutil.copyfile(f,common/f.name)
 s=(src/'host.c').read_text();s=once(s,'static struct nes_dirty231 dirty;', '''static struct nes_dirty231 dirty;
#include "nes_native_sink165.h"
#include "nes_sink_bulk195.h"
#include <windows.h>
static struct nes_native_sink165 real232;
static bool bulk232(unsigned,unsigned,unsigned,const uint8_t *,unsigned);''')
 s=once(s,'newbytes+=unit;return true;','newbytes+=unit;return bulk232(kind,q->slot,q->generation,out,unit);')
 x=s.index('static bool cost_exchange');y=s.index('static void verify_bank',x);s=s[:x]+RPC+s[y:]
 s=once(s,'unsigned before=checksum(&banks[cache.active],sizeof banks[0]);','unsigned active_before=cache.active;unsigned before=checksum(&banks[active_before],sizeof banks[0]);')
 s=s.replace('before==checksum(&banks[cache.active],sizeof banks[0])','before==checksum(&banks[active_before],sizeof banks[0])')
 s=once(s,'assert(nes_native_video231_plan(', 'assert(nes_sink212_begin(&real232,&cache));\n assert(nes_native_video231_plan(')
 s=once(s,' assert(nes_resident211_commit(&cache,cache.serial,r.generation,cache.target,true));assert(nes_dirty231_commit(&dirty,cache.serial,r.generation,cache.target,true));','')
 s=once(s,' reset();\n for(unsigned frame=', ' reset();nes_sink165_reset(&real232,cost_exchange,NULL);\n for(unsigned frame=')
 at=s.rindex(' return 0;');s=s[:at]+' FILE *done=fopen("producer-done.txt","w");assert(done);fprintf(done,"%u",frames);fclose(done);\n'+s[at:]
 (common/'host.c').write_text(s,encoding='utf-8',newline='\n')
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');mesen=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe')
 env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 files=['host.c','reference203.c','nes_planner211.c','nes_resident211.c','nes_native165.c','nes_trace166.c','nes_native_sink165.c','nes_sink_trace168.c','nes_delta231.c']
 with (common/'gcc.log').open('wb') as f:q=subprocess.run([str(gcc),'-std=c11','-Wall','-Wextra','-Werror','-O2',*files,'-o','host.exe'],cwd=common,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(common/'gcc.log').read_text()
 build=nes_sparse232.build(out/'client');d=out/'run';d.mkdir();shutil.copyfile(src/'palette.bin',d/'palette.bin')
 for row in csv.DictReader((src/'cost.csv').open()):
  frame=int(row['frame']);gen=int(row['generation']);b=(src/f'frame{frame}.metadata').read_bytes()
  (d/f'expected-{gen}.bin').write_bytes(b);(d/f'oam-{gen}.bin').write_bytes(b[4608:5152])
 lua=(BASE/'probes/nes-repeat227/snes04/candidate-normal/capture.lua').read_text(encoding='utf-8');lua=lua.split('\n',1)[1]
 lua='local OUT_DIR='+json.dumps(d.as_posix())+'\n'+lua
 lua=once(lua,'local rejected=false','local rejected=false\nlocal sealStart232=nil')
 lua=once(lua,' if a==0x6000 then'," if a==0x6000 and packet and pb(0)==3 and not sealStart232 then sealStart232=emu.getState().masterClock end\n if a==0x6000 then")
 lua=once(lua,'  if bytes:byte(1)==1 then','  if bytes:byte(1)==1 then\n'+CHECK)
 lua=once(lua,"if st.frameCount>4000",'if st.frameCount>16000')
 (d/'capture.lua').write_text(lua,encoding='utf-8',newline='\n')
 with (d/'host.log').open('wb') as hf,(d/'mesen.log').open('wb') as mf:
  h=subprocess.Popen([str(common/'host.exe'),str(BASE/'probes/nes-geometry230/rtl02'),str(a.rom.resolve()),'905',str(a.last),str(src)],cwd=d,env=env,stdout=hf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  m=subprocess.Popen([str(mesen),'--testRunner',str(d/'capture.lua'),str(out/'client/sink165.sfc'),'--timeout=300','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  try:mr=m.wait(timeout=320);hr=h.wait(timeout=5)
  finally:
   for child in (h,m):
    if child.poll() is None:child.kill();child.wait()
 assert mr==hr==0,((d/'mesen.log').read_text(errors='replace')[-3500:],(d/'host.log').read_text(errors='replace')[-1500:])
 result=json.loads((d/'consumer-result.json').read_text());result.update(scope=__doc__,client=build,physical=False,source_rtl=False,host_output=(d/'host.log').read_text(),
  vblanks={i:int((d/f'vblank-{i}.txt').read_text()) for i in range(1,a.last-904+1)},
  seal_master_cycles={i:int((d/f'timing-{i}.txt').read_text()) for i in range(1,a.last-904+1)},
  script_sha256=sha(Path(__file__)),host_sha256=sha(common/'host.c'),mesen_sha256=sha(mesen),rom_sha256=sha(a.rom))
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('vblanks','seal_master_cycles','client')},indent=2))


if __name__=='__main__':main()
