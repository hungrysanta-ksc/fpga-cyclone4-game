# SPDX-License-Identifier: MIT
"""Actual65816 changed-boundary rejects after one real displayed frame."""
from pathlib import Path
import argparse,concurrent.futures,json,os,shutil,subprocess,tempfile
from nes_delta231 import once,sha

CASES=('zero_mask','wrong_mode','truncated_word','duplicate_group','manifest_offset','manifest_mismatch','map_after_manifest','early_seal','cold_partial','stop_mask','stop_manifest','stop_final')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('normal','client','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 source=a.normal/'run';reqs=[f for f in sorted(source.glob('req-*.bin')) if int.from_bytes(f.read_bytes()[8:10],'little')<=2]
 originals={f.name:f.read_bytes() for f in reqs};second=[n for n,b in originals.items() if int.from_bytes(b[8:10],'little')==2]
 maps=[n for n in second if originals[n][0]==9];manifests=[n for n in second if originals[n][0]==10];seal=next(n for n in second if originals[n][0]==3)
 assert len(manifests)==2 and maps
 mesen=Path.home()/'AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe'
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 def execute(case):
  out=a.out/case;out.mkdir();d=Path(tempfile.mkdtemp(prefix='nes-maskfault247-'))
  packets={n:bytearray(b) for n,b in originals.items()};b=packets[maps[0]]
  if case=='zero_mask':b[18]=0
  elif case=='wrong_mode':b[16]=3
  elif case=='truncated_word':b.pop();b[12:14]=(len(b)-16).to_bytes(2,'little')
  elif case=='duplicate_group':b[35]=b[17]
  elif case=='manifest_offset':packets[manifests[0]][10:12]=(240).to_bytes(2,'little')
  elif case=='manifest_mismatch':packets[manifests[0]][16]^=1
  elif case=='map_after_manifest':
   b=packets[manifests[1]];b[0]=9;b[10:12]=bytes(2);b[12:14]=packets[maps[0]][12:14];b[16:]=packets[maps[0]][16:]
  elif case=='early_seal':
   b=packets[manifests[0]];header=b[:16];packets[manifests[0]]=bytearray(packets[seal]);packets[manifests[0]][2:10]=header[2:10]
  elif case=='cold_partial':
   assert b[17]==0 and b[18]==255;b[18]=254;del b[19:21];b[12:14]=(len(b)-16).to_bytes(2,'little');packets[manifests[0]][16]=254
  for n,b in packets.items():(d/n).write_bytes(b)
  for f in source.iterdir():
   if f.name.startswith(('tile-','expected-','oam-','bank-')) or f.name=='palette.bin':shutil.copyfile(f,d/f.name)
  lua=(source/'capture.lua').read_text(encoding='utf-8').split('\n',1)[1]
  lua='local OUT_DIR='+json.dumps(d.as_posix())+'\n'+lua
  lua=once(lua,'local MODE="normal"','local MODE='+json.dumps(case))
  lua=once(lua,' if a==0x6001 then', ''' if a==0x6001 then
  if packet and pw(8)==2 then
   if MODE=='stop_mask' and pb(0)==9 and word(0x148e)>0 then return 128 end
   if MODE=='stop_manifest' and pb(0)==10 and word(0x1490)>0 then return 128 end
  end''')
  lua=once(lua," if not packet and not rejected then", ''' if rejected and not pendingAck then
  assert(commits==1 and word(0x1228)==2 and rd(0x148d)==0,'fault published target or allowed next frame')
  if MODE:sub(1,5)=='stop_' then assert(rd(0x148c)==0,'STOP kept old map initialized')end
  local f=assert(io.open(OUT_DIR..'/fault-result.json','w'));f:write('{"passed":true,"commits":1,"terminal":true,"display_unchanged":true}');f:close();emu.stop(0)
 end
 if not packet and not rejected then''')
  (d/'capture.lua').write_text(lua,encoding='utf-8',newline='\n')
  try:
   with (d/'mesen.log').open('wb') as log:
    run=subprocess.run([str(mesen),'--testRunner',str(d/'capture.lua'),str(a.client.resolve()/'sink165.sfc'),'--timeout=60','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=80)
   assert run.returncode==0,(case,run.returncode)
   r=json.loads((d/'fault-result.json').read_text());assert r['passed']
   last=(d/'bus.tsv').read_text().splitlines()[-1].split('\t');assert int(last[3])==(228 if case.startswith('stop_') else 224),(case,last)
   r.update(case=case,error=int(last[3]),acks=int(last[0]));return r
  finally:shutil.copytree(d,out/'run',dirs_exist_ok=True)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(execute,CASES))
 result=dict(passed=True,cases=rows,scope=__doc__,normal_sha256=sha(a.normal/'result.json'),client_sha256=sha(a.client/'sink165.sfc'),script_sha256=sha(Path(__file__)),physical=False,full_pipeline_faults=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');shutil.copyfile(__file__,a.out/'test.py');print('PASS MASKFAULT247 cases='+str(len(rows)))

if __name__=='__main__':main()
