# SPDX-License-Identifier: MIT
"""Actual2472 admission/receipt/RLE/STOP faults with prior display preserved."""
from pathlib import Path
import argparse,concurrent.futures,json,os,shutil,subprocess,tempfile
from nes_delta231 import once,sha

CASES=('span_zero','span_large','span_odd','span_wrap','span_end','span_overlap','span_truncated','span_mode','cold_partial','old_begin','old_seal','rle_zero_mismatch','rle_literal_mismatch','rle_overflow','rle_truncated','rle_offset','rle_mode','mixed_manifest','early_seal','map_after_manifest','stop_span','stop_manifest','stop_final_boundary')


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('normal','client','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);source=a.normal/'run'
 originals={f.name:f.read_bytes() for f in sorted(source.glob('req-*.bin')) if int.from_bytes(f.read_bytes()[8:10],'little')<=3}
 labels=json.loads((a.client/'labels.json').read_text());mesen=Path.home()/'AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe'
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 def execute(case):
  out=a.out/case;out.mkdir();d=Path(tempfile.mkdtemp(prefix='nes-jointfault247-'));generation=2 if case.startswith('span_') or case in ('cold_partial','old_begin','old_seal') else 3
  packets={n:bytearray(b) for n,b in originals.items() if int.from_bytes(b[8:10],'little')<=generation}
  names=[n for n,b in packets.items() if int.from_bytes(b[8:10],'little')==generation]
  maps=[n for n in names if packets[n][0]==9];manifests=[n for n in names if packets[n][0] in (10,11)]
  seal=next(n for n in names if packets[n][0]==3);begin=next(n for n in names if packets[n][0]==1)
  b=packets[maps[0]];mf=packets[manifests[0]]
  if case=='span_zero':b[19]=0
  elif case=='span_large':b[19]=33
  elif case=='span_odd':b[17]|=1
  elif case=='span_wrap':b[17:19]=b'\xfe\xff'
  elif case=='span_end':b[17:19]=b'\xfe\x0f'
  elif case=='span_overlap':at=20+b[19]*2;b[at:at+2]=b[17:19]
  elif case=='span_truncated':del b[-1]
  elif case=='span_mode':b[16]=2
  elif case=='cold_partial':assert b[19]==32;b[19]=31;del b[82:84];mf[19]&=127
  elif case=='old_begin':packets[begin][16]=0x71
  elif case=='old_seal':packets[seal][36]=0x71
  elif case=='rle_zero_mismatch':mf[16:]=b'\x03\xff\xff'
  elif case=='rle_literal_mismatch':
   at=17
   while mf[at]&128:at+=1
   mf[at+1]^=1
  elif case=='rle_overflow':mf.append(128)
  elif case=='rle_truncated':del mf[-1]
  elif case=='rle_offset':mf[10]=1
  elif case=='rle_mode':mf[16]=2
  elif case=='mixed_manifest':
   q=packets[seal];q[0:2]=bytes((10,2));q[10:12]=(256).to_bytes(2,'little');q[16:]=bytes(16)
  elif case=='early_seal':
   head=mf[:16];mf[:]=packets[seal];mf[2:10]=head[2:10]
  elif case=='map_after_manifest':
   q=packets[seal];head=q[:16];q[:]=b;q[2:10]=head[2:10]
  for n,b in packets.items():b[12:14]=(len(b)-16).to_bytes(2,'little');(d/n).write_bytes(b)
  for f in source.iterdir():
   if f.name.startswith(('tile-','expected-','oam-','bank-')) or f.name=='palette.bin':shutil.copyfile(f,d/f.name)
  lua='local OUT_DIR='+json.dumps(d.as_posix())+'\n'+(source/'capture.lua').read_text(encoding='utf-8').split('\n',1)[1]
  lua=once(lua,'local MODE="normal"','local MODE='+json.dumps(case))
  at=lua.index('emu.addMemoryCallback(');hook='local jointStop247=false\n'
  for key,label in [('stop_span','span_service247'),('stop_manifest','manifest_service247'),('stop_final_boundary','final212')]:
   if case==key:hook+='emu.addMemoryCallback(function() if packet and pw(8)=='+str(generation)+' then jointStop247=true end end,emu.callbackType.exec,'+str(labels[label])+')\n'
  lua=lua[:at]+hook+lua[at:]
  lua=once(lua,' if a==0x6001 then',' if a==0x6001 then\n  if jointStop247 then return 128 end')
  done=''' if rejected and not pendingAck then
  assert(commits==EXPECTED and word(0x1228)==2,'fault lifetime')
  if MODE:sub(1,5)=='stop_' then assert(rd(0x148c)==0 and rd(0x148d)==0,'STOP retained map initialization')end
  local f=assert(io.open(OUT_DIR..'/fault-result.json','w'));f:write(string.format('{"passed":true,"commits":%d,"terminal":true,"display_unchanged":true}',commits));f:close();emu.stop(0)
 end
 if not packet and not rejected then'''.replace('EXPECTED',str(generation-1))
  lua=once(lua,' if not packet and not rejected then',done)
  (d/'capture.lua').write_text(lua,encoding='utf-8',newline='\n')
  try:
   with (d/'mesen.log').open('wb') as log:run=subprocess.run([str(mesen),'--testRunner',str(d/'capture.lua'),str(a.client.resolve()/'sink165.sfc'),'--timeout=60','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=80)
   assert run.returncode==0,(case,run.returncode)
   assert not (d/'lua-error.txt').exists() or not (d/'lua-error.txt').read_text().strip(),(case,'Lua assertion')
   r=json.loads((d/'fault-result.json').read_text());assert r['passed'] and r['commits']==generation-1
   last=(d/'bus.tsv').read_text().splitlines()[-1].split('\t');assert int(last[3])==(228 if case.startswith('stop_') else 224),(case,last)
   r.update(case=case,error=int(last[3]));return r
  finally:shutil.copytree(d,out/'run',dirs_exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(execute,CASES))
 result=dict(passed=True,cases=rows,scope=__doc__,normal_sha256=sha(a.normal/'result.json'),client_sha256=sha(a.client/'sink165.sfc'),script_sha256=sha(Path(__file__)),physical=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copyfile(__file__,a.out/'test.py');print('PASS JOINTFAULT247 cases='+str(len(rows)))


if __name__=='__main__':main()
