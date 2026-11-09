"""Request user exit during native command/DMA execution, then prove the CPU parks."""
import argparse,json,os,shutil,struct,subprocess
from pathlib import Path
from test_nes_output489_snes import LUA
from test_nes_trim514_schedule import MAP_ORACLE
from nes_raw506 import once,sha

def run(a):
    a.out=a.out.resolve();assert str(a.out).isascii();a.out.mkdir(parents=True,exist_ok=False)
    labels=json.loads((a.client/'labels.json').read_text());rows=[]
    for mode in ('packet','dma'):
        d=a.out/mode;d.mkdir();packets=[]
        for line in (a.trace/'packets.jsonl').read_text().splitlines():
            _,_,h,tile=json.loads(line);b=bytes.fromhex(h)
            if int.from_bytes(b[8:10],'little')>906:break
            packets.append(b)
            if tile:(d/f'tile-{len(packets):04d}.bin').write_bytes(bytes.fromhex(tile))
        (d/'requests.bin').write_bytes(b''.join(struct.pack('<H',len(b))+b for b in packets))
        for g in (905,906):
            for stem in ('expected','map'):shutil.copyfile(a.trace/f'{stem}-{g}.bin',d/f'{stem}-{g}.bin')
        s=once(LUA,'local function loaded()',r'''local requested694=false;local requestClock694=0;local ack694=0;local dma694=0
local park694=nil;local loops694=0
local function request694()
 if not requested694 then requested694=true;requestClock694=emu.getState().masterClock end
end
emu.addMemoryCallback(function(a,v)
 if a==0x601c then ack694=ack694+1 end
 if a==0x420b then dma694=dma694+1;if @DMA@ and word(0x1226)==906 then request694()end end
 if a==0x7000 and v==126 then assert(requested694);park694={clock=emu.getState().masterClock,ack=ack694,dma=dma694}end
end,emu.callbackType.write,0x4000,0x7001)
emu.addMemoryCallback(function()
 assert(park694 and ack694==park694.ack and dma694==park694.dma,'activity after user park')
 loops694=loops694+1
 if loops694==1000 then
  local f=assert(io.open(ROOT..'/exit.json','w'))
  f:write(string.format('{"passed":true,"request_clock":%d,"park_clock":%d,"commits":%d,"ACK":%d,"DMA":%d,"park_loops":%d}',requestClock694,park694.clock,commits,ack694,dma694,loops694));f:close();emu.stop(0)
 end
end,emu.callbackType.exec,@PARK@)
local function loaded()''')
        s=once(s,'packet=requests[index];','packet=requests[index];if not @DMA@ and frames[index]==1 then request694()end;')
        s=once(s,'emu.addMemoryCallback(function(a,v)return 0 end,emu.callbackType.read,0x4218,0x4219)',
            'emu.addMemoryCallback(function(a,v)return requested694 and 0x30 or 0 end,emu.callbackType.read,0x4218,0x4219)')
        s=once(s,"   local hdma=file(",MAP_ORACLE+"   local hdma=file(")
        # Keep the actual4212 VBlank/autojoy sampling condition untouched.
        for k,v in dict(ROOT=json.dumps(d.as_posix()),MODE='"normal"',FAULT=906,COMPACT='true',POISON='false',FRAMES=2,TOTAL=len(packets),SCHEDULE='"continuous"',START=7288416,DMA=str(mode=='dma').lower(),PARK=labels['exit_wait693']).items():s=s.replace('@'+k+'@',str(v))
        # Capture assertion details at their actual Lua callback boundary.
        s=s.replace('emu.addMemoryCallback(', 'safe694(')
        s='''local function safe694(fn,...)
 return emu.addMemoryCallback(function(...)
  local ok,v=pcall(fn,...);if not ok then local f=assert(io.open('''+json.dumps((d/'error.txt').as_posix())+''','w'));f:write(tostring(v));f:close();emu.stop(1)end;return v
 end,...)
end
'''+s
        (d/'test.lua').write_text(s,encoding='utf8')
        with (d/'mesen.log').open('wb') as f:
            p=subprocess.run([str(a.mesen.resolve()),'--testRunner',str(d/'test.lua'),str((a.client/'sink165.sfc').resolve()),'--timeout=20','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],stdout=f,stderr=subprocess.STDOUT,timeout=30,env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),creationflags=subprocess.CREATE_NO_WINDOW)
        assert p.returncode==0,(mode,(d/'error.txt').read_text() if (d/'error.txt').exists() else 'see log')
        r=json.loads((d/'exit.json').read_text());assert r['passed'] and 1<=r['commits']<=2 and r['park_clock']>=r['request_clock'];rows.append(dict(mode=mode,**r))
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,CPU=sha(a.client/'sink165.sfc'),body=sha(a.client/'body.bin'),cases=rows,scope=__doc__,ARM_return_not_executed=True),indent=2)+'\n')
    print('PASS694 native packet/DMA user exit; no ACK/DMA after park')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('client','trace','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
