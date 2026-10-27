# SPDX-License-Identifier: MIT
"""Execute cancellation and receive-boundary failures on the actual65816
output kernel. Invalid-record fixtures are CPU guards,not new ARM frames."""
import argparse,csv,json,os,struct,subprocess
from pathlib import Path
import probe_nes_jobs394_native as n
from nes_delta231 import sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--arm',required=True,type=Path);a=p.parse_args();root=a.out.resolve();root.mkdir(parents=True,exist_ok=False);base=n.fixtures(907,a.arm);oracle,_=n.plans();prior=(oracle/'expected-1.bin').read_bytes();expected=(oracle/'expected-3.bin').read_bytes();rows=[]
 cases=[('after_all_store',len(base),99999,99999,len(base),0,True),('after_view',99999,12,99999,len(base),0,True),('after_two_PPU',99999,99999,2,len(base),2,True),('bank',99999,99999,99999,0,0,False),('zero_length',99999,99999,99999,0,0,False),('job257',99999,99999,99999,256,0,False),('zero_seed',99999,99999,99999,next(i for i,j in enumerate(base)if bytes.fromhex(j['record'])[6]&64),0,False)]
 for name,stores,views,ppus,expected_stores,expected_ppu,stop in cases:
  d=root/name;d.mkdir();body,labels=n.rom(d);jobs=[dict(j)for j in base];cold=False
  if name in('bank','zero_length'):
   r=bytearray.fromhex(jobs[0]['record'])
   if name=='bank':r[7]=0x7d
   else:r[4:6]=bytes(2)
   jobs[0]['record']=r.hex()
  elif name=='zero_seed':jobs[expected_stores]['data']='0100'
  elif name=='job257':
   cold=True;jobs=[]
   for i in range(257):
    r=struct.pack('<HHHBBBBH',i*8,0x8000+i*16,16,0,0x7e,0x80,0,i)
    jobs.append(dict(record=r.hex(),data=bytes(16).hex(),offset=0,first=True,last=True,token=i+1))
  lua=n.LUA.replace("STOP and staged>=1 and 0x80","STOP and (staged>=STOP_STORES or viewreads>=STOP_VIEWS or jobdone>=STOP_PPU) and 0x80")
  lua=lua.replace("assert(STOP and v==0xee and not ppu_start and staged==1)","assert(v==0xee and staged==EXPECT_STORES and jobdone==EXPECT_PPU,'wrong abort state')")
  old="out:write('{\"passed\":true,\"STOP\":true,\"final_ACK\":false,\"PPU_jobs\":0}')"
  assert old in lua;lua=lua.replace(old,"out:write(string.format('{\"passed\":true,\"final_ACK\":false,\"PPU_jobs\":%d,\"stored\":%d}',jobdone,staged))")
  header='local OUT='+json.dumps(d.as_posix())+'\nlocal BANK=0\nlocal STOP='+str(stop).lower()+'\nlocal COLD='+str(cold).lower()+'\nlocal FINAL_TOKEN='+str(len(jobs)+1)+'\nlocal STOP_STORES='+str(stores)+'\nlocal STOP_VIEWS='+str(views)+'\nlocal STOP_PPU='+str(ppus)+'\nlocal EXPECT_STORES='+str(expected_stores)+'\nlocal EXPECT_PPU='+str(expected_ppu)+'\n'
  header+='local VIEW={'+','.join(map(str,n.current_view(907)))+'}\nlocal CONTEXT={3,0,0,0,3,0,0,'+str(int(cold))+'}\nlocal LABELS={'+','.join(k+'='+str(v)for k,v in labels.items())+'}\nlocal JOBS={'+','.join('{record="'+j['record']+'",data="'+j['data']+'",offset='+str(j['offset'])+',first='+str(j['first']).lower()+',last='+str(j['last']).lower()+',token='+str(j['token'])+'}'for j in jobs)+'}\n'
  for key,data in [('INITMAP',prior[:4096]),('INITCG',prior[4096:4608]),('INITOAM',prior[4608:5152]),('INITHDMA',prior[5152:8570]),('EXPECTMAP',expected[:4096]),('EXPECTCG',expected[4096:4608]),('EXPECTOAM',expected[4608:5152]),('EXPECTHDMA',expected[5152:8570])]:header+='local '+key+'="'+data.hex()+'"\n'
  guarded="local original_assert=assert\nfunction assert(v,msg)if not v then local e=io.open(OUT..'/error.txt','a');e:write(tostring(msg)..'\\n'..debug.traceback()..'\\n');e:close();emu.stop(1)end;return original_assert(v,msg)end\n"+lua
  (d/'capture.lua').write_text(header+guarded,newline='\n');(d/'fixture.json').write_text(json.dumps(jobs,indent=2)+'\n');env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
  with(d/'mesen.log').open('wb')as log:r=subprocess.run(['C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe','--testRunner',str(d/'capture.lua'),str(d/'spool.sfc'),'--timeout=30','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=50,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(name,(d/'mesen.log').read_text(errors='replace')[-2000:])
  result=json.loads((d/'cpu-result.json').read_text());ev=[list(map(int,x))for x in csv.reader((d/'events.csv').read_text().splitlines())];assert result['PPU_jobs']==expected_ppu and result['stored']==expected_stores and not result['final_ACK']
  for address,value in((0x2100,128),(0x420c,0)):assert[x[3]for x in ev if x[1]==1 and x[2]==address][-1]==value
  assert not any(x[1:3]==[1,0x6058]for x in ev)
  row=dict(name=name,passed=True,stored=expected_stores,PPU_jobs=expected_ppu,final_ACK=False,forcedblank=True,HDMA_off=True,ROM=sha(d/'spool.sfc'),events=sha(d/'events.csv'),fixture=sha(d/'fixture.json'));rows.append(row);print(json.dumps(row),flush=True)
 (root/'result.json').write_text(json.dumps(dict(passed=True,cases=rows,scope=__doc__),indent=2)+'\n')
if __name__=='__main__':main()
