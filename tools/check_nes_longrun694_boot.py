"""Execute selected packed reset images and detect corrupted verification bytes."""
import argparse,json,os,subprocess
from pathlib import Path
from nes_raw506 import sha

def run(a):
    a.out=a.out.resolve();assert str(a.out).isascii();a.out.mkdir(parents=True,exist_ok=False)
    rows=[]
    for name,client in [('normal',a.base),('long',a.client)]:
        info=json.loads((client/'build.json').read_text());body=(client/'body.bin').read_bytes()
        assert len(body)==info['body_bytes']
        for fault in (False,True):
            d=a.out/(name+('-corrupt' if fault else ''));d.mkdir();(d/'body.bin').write_bytes(body)
            s=r'''
local ROOT=@ROOT@;local BAD=@BAD@;local touched=false
local f=assert(io.open(ROOT..'/body.bin','rb'));local body=f:read('*a');f:close()
local function finish(kind)
 local f=assert(io.open(ROOT..'/result.json','w'))
 f:write(string.format('{"passed":true,"clock":%d,"kind":"%s","body_B":%d}',emu.getState().masterClock,kind,#body));f:close();emu.stop(0)
end
local function cb(fn,...)
 return emu.addMemoryCallback(function(...)
  local ok,v=pcall(fn,...);if not ok then local f=assert(io.open(ROOT..'/error.txt','w'));f:write(tostring(v));f:close();emu.stop(1)end;return v
 end,...)
end
cb(function()
 assert(not BAD,'corrupt image entered main')
 for i=1,#body do assert(emu.read(0x2000+i-1,emu.memType.snesWorkRam)==body:byte(i),'WRAM byte '..i)end
 finish('restored')
end,emu.callbackType.exec,0x7e2000)
if BAD then
 cb(function()
  if not touched then local p=emu.getState()['cpu.y'];emu.write(p,emu.read(p,emu.memType.snesWorkRam)~1,emu.memType.snesWorkRam);touched=true end
 end,emu.callbackType.exec,@VERIFY@)
 cb(function(a,v)if v==225 then assert(touched);finish('rejected')end end,emu.callbackType.write,0x7000)
end
emu.addEventCallback(function()if emu.getState().frameCount>50 then emu.stop(1)end end,emu.eventType.endFrame)
'''
            for k,v in dict(ROOT=json.dumps(d.as_posix()),BAD=str(fault).lower(),VERIFY=info['verify_entry']).items():s=s.replace('@'+k+'@',str(v))
            (d/'test.lua').write_text(s,encoding='utf8')
            with (d/'mesen.log').open('wb') as log:
                r=subprocess.run([str(a.mesen.resolve()),'--testRunner',str(d/'test.lua'),str((client/'sink165.sfc').resolve()),'--timeout=15','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],stdout=log,stderr=subprocess.STDOUT,timeout=30,env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),creationflags=subprocess.CREATE_NO_WINDOW)
            assert r.returncode==0,(d,(d/'error.txt').read_text() if (d/'error.txt').exists() else 'see mesen.log')
            rows.append(dict(name=name,fault=fault,ROM=sha(client/'sink165.sfc'),body=sha(client/'body.bin'),**json.loads((d/'result.json').read_text())))
    delta=(rows[2]['clock']-rows[0]['clock'])/21477.272
    result=dict(passed=True,cases=rows,long_extra_boot_ms=delta,scope='Native65816 reset/packed loader/byte verification; model ROM bus, not physical board boot')
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS694 packed boot/reject4; long boot delta_ms',delta)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
