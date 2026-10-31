# SPDX-License-Identifier: MIT
"""Observe existing493/502 65816 phase boundaries; unchanged bytes and schedule.

New PC observations of frozen file-aperture fixtures, not actual ARM/IRQ/ROM
timing or a physical502 warm replay. Never add nested dispatch/phase durations.
"""
import argparse,json,os,shutil,subprocess,csv
from pathlib import Path
from hashlib import sha256
sha=lambda p:sha256(p.read_bytes()).hexdigest()
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ['input','client','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--mesen',type=Path,default=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe'))
 a=p.parse_args();a.out=a.out.resolve();assert a.out.as_posix().isascii();a.out.mkdir(parents=True,exist_ok=False)
 expected=json.loads((ROOT/'analysis/output489-verification.json').read_text())['SNES']['client_SHA256']
 assert sha(a.input/'client.sfc')==sha(a.client/'sink165.sfc')==expected
 before=json.loads((a.input/'result.json').read_text());labels=json.loads((a.client/'labels.json').read_text())
 pins={}
 for f in a.input.iterdir():
  if f.is_file()and(f.suffix in ['.bin','.sfc']):shutil.copy2(f,a.out/f.name);pins[f.name]=sha(f)
 lua=(a.input/'capture.lua').read_text().replace(a.input.resolve().as_posix(),a.out.as_posix())
 names=['seal','coverage212','validate181','compact489','local165_entry','upload165_entry','upload_loop212','wait169','transfer212','raw_dispatch489','raw_dma489','final212','final_upload212_entry','final_upload212_return','accepted']
 injection="local pf504=assert(io.open(ROOT..'/phases504.csv','w'));pf504:write('generation,phase,masterclock,scanline\\n')\n"
 for name in names:
  assert name in labels,name
  injection+='emu.addMemoryCallback(function()local st=emu.getState();pf504:write(string.format("%d,'+name+',%d,%d\\n",packet and pw(8)or 0,st.masterClock,st["ppu.scanline"]));pf504:flush()end,emu.callbackType.exec,'+str(labels[name])+')\n'
 at=lua.index('emu.addMemoryCallback(function(a,v)');lua=lua[:at]+injection+lua[at:]
 (a.out/'capture.lua').write_text(lua,encoding='utf8',newline='\n')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with(a.out/'mesen.log').open('wb')as log:
  result=subprocess.run([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.out/'client.sfc'),'--timeout=240','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],cwd=a.out,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=250,creationflags=subprocess.CREATE_NO_WINDOW)
 assert result.returncode==0,(result.returncode,(a.out/'mesen.log').read_text())
 after=json.loads((a.out/'result.json').read_text());assert after['passed']
 for key in ['commits','last_status','vram_DMA_B','frames']:assert after[key]==before[key],key
 for f in a.input.glob('frame-*.rgb'):assert sha(f)==sha(a.out/f.name),f.name
 rows=list(csv.DictReader((a.out/'phases504.csv').open()));stages=[]
 for frame in after['frames']:
  g=frame['generation'];ev=[e for e in rows if int(e['generation'])==g]
  first=lambda name:next(int(e['masterclock'])for e in ev if e['phase']==name)
  begin,upload,end=first('seal'),first('upload165_entry'),frame['ACK_masterclock']
  stages.append(dict(generation=g,seal_pre_upload_ms=(upload-begin)/21477.272,upload_through_ACK_ms=(end-upload)/21477.272,seal_through_ACK_ms=(end-begin)/21477.272,upload_wait_calls=sum(e['phase']=='wait169' and int(e['masterclock'])>=upload for e in ev),release_through_ACK_ms=(end-frame['release_masterclock'])/21477.272))
 report=dict(passed=True,scope=__doc__,input_pins=pins,source_lua_SHA256=sha(a.input/'capture.lua'),instrumented_lua_SHA256=sha(a.out/'capture.lua'),labels_SHA256=sha(a.client/'labels.json'),phases_SHA256=sha(a.out/'phases504.csv'),result_SHA256=sha(a.out/'result.json'),identical_ACK_clocks_and_pixels=True,stages=stages,new_firmware=False,new_Quartus=False)
 (a.out/'measurement.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(stages))
