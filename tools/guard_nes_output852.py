"""Fault the linked 65816 at map admission or after the first prefix; restart from canceled WRAM."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from unittest.mock import patch

from nes_raw506 import once, sha
from prepare_nes_map828 import PROBES


def arm_guard(temp,kind,replay_override=None,history="tail_rows",tag_prefix="852"):
    from replay_nes_output852 import run as replay,joint
    from unicorn.arm_const import UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2
    if replay_override is not None:
        replay=replay_override
    state={}
    original=joint.Runtime.hook
    def hook(cpu,u,pc,size,ctx):
        if not cpu.live:
            return original(cpu,u,pc,size,ctx)
        def published():
            addr=cpu.rt+cpu.layout['nes_native_runtime165']['sink']+cpu.layout['nes_native_sink165'][history]
            return bytes(u.mem_read(addr,8)).hex()
        if kind=='stop' and 'armed' in state and pc==cpu.syms['nes_cf86_check094']:
            state['fired']=True
            u.reg_write(UC_ARM_REG_R0,0);u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        if pc!=cpu.spi:
            return original(cpu,u,pc,size,ctx)
        tx=u.reg_read(UC_ARM_REG_R1);rx=u.reg_read(UC_ARM_REG_R2)
        op=u.mem_read(tx,1)[0]
        first_ref=op==0xe1 and bytes(u.mem_read(tx+1,2))==bytes((9,2))
        original(cpu,u,pc,size,ctx)
        if first_ref and 'armed' not in state:
            state.update(armed=cpu.clock,generation=cpu.generation,committed=published())
        if kind=='identity' and 'armed' in state and op==0xe0:
            reply=bytearray(u.mem_read(rx,20))
            if reply[7:9]==bytes((1,3)) and int.from_bytes(reply[15:17],'little')==state['generation']:
                reply[9]^=1;reply[19]=joint.crc(reply[1:19],8,7,0)
                u.mem_write(rx,bytes(reply));state['fired']=True
    tag=tag_prefix+'-arm-'+kind
    with patch.object(joint.Runtime,'hook',hook):
        try:
            replay(temp,'demo',1,'reuse',tag,False)
        except AssertionError as exc:
            failure=exc.args[0]
            assert state.get('fired') and failure[:3]==('runtime fault',state['generation'],2 if kind=='stop' else 5),failure
        else:
            raise AssertionError('injected ARM fault was accepted')
    folder=temp/f'nes-tile821-demo-jointmirror-p1-{tag}'
    sink=json.loads((folder/'fault.json').read_bytes())['sink']
    off=sink['layout'][history]
    assert bytes.fromhex(sink['bytes'])[off:off+8].hex()==state['committed']
    events=json.loads((folder/'events.json').read_bytes())
    assert not any(e.get('opcode') in ('0xea','0xd3') for e in events if e.get('clock',-1)>state['armed'])
    return dict(generation=state['generation'],fault=failure,committed_unchanged=True,no_EA_or_D3=True)


def run(temp,trial,case,seed=None,column_client=None,edit_seal=None,adapt_lua=None,column_op=9):
    out=trial/('guard-'+case)
    out.mkdir()
    if column_client:
        client=column_client
        assert sha(client/'sink165.sfc')==sha(trial/'client.sfc')
    else:
        client,=(folder for folder in (PROBES/'nes-output852'/n for n in ('client-board','client-dma'))
             if (folder/'sink165.sfc').is_file() and sha(folder/'sink165.sfc')==sha(trial/'client.sfc'))
    labels=json.loads((client/'labels.json').read_bytes())
    rows=[]
    for line in (trial/'packets.jsonl').read_text().splitlines():
        _,target,payload,bulk=json.loads(line)
        b=bytearray.fromhex(payload)
        g=int.from_bytes(b[8:10],'little')
        if case=='restart' and g>906:
            break
        hit=b[:2]==bytes((column_op,2))
        if case=="two-stop":hit=hit and len(b)==116
        if edit_seal:
            hit=False
            if b[0]==3:
                b,hit=edit_seal(b,g,case)
        if case=='cold' and g==905 and b[1]==2 and b[0] in (2,4) and int.from_bytes(b[10:12],'little')>=2048:
            span=int.from_bytes(b[12:14] if b[0]==2 else b[14:16],'little')
            assert span in (64,128,192)
            n=4+36*(span//64)
            b=b[:12]+n.to_bytes(2,'little')+span.to_bytes(2,'little')+(1).to_bytes(4,'little')+bytes(n-4)
            if column_client:
                b[10:16]=bytes((0,8,52,0,0,0))
                b=b[:16]+bytes((1,))+bytes(51)
            if column_op==10:
                b[10:16]=bytes((0,8,54,0,0,0))
                b=b[:16]+bytes((1,0,0,0,0,8))+bytes(48)
            b[0]=column_op;hit=True
        if case=='restart':
            assert not hit
        if hit and case=='base':
            b[16]^=1
        if hit and case=='length':
            b[14:16]=(64 if b[14]!=64 else 128).to_bytes(2,'little')
        if hit and case=='range':
            b[10:12]=(4096).to_bytes(2,'little')
        if hit and case=='column':
            field=22 if column_op==10 else 20
            b[field:field+2]=bytes((63,0))
        rows.append((target,'PUSH',b.hex(),bulk))
        if case!='restart' and hit:
            break
    assert (case=='restart' and g==907) or (case=='cold' and hit and g==905) or (hit and (g>906 or edit_seal and g==906))
    commits=2 if case=='restart' else g-905
    rows.append((rows[-1][0]+1,'FINISH','',''))
    with (out/'commands.txt').open('w',encoding='ascii',newline='\n') as f:
        for i,row in enumerate(rows,1):
            f.write('\n'.join(map(str,(i,*row)))+'\n')
    lua=(trial/'capture.lua').read_text()
    lua=re.sub(r'^local ROOT=.*$',lambda _: 'local ROOT='+json.dumps(out.as_posix()),lua,count=1,flags=re.M)
    lua=re.sub(r'^local cmds=.*$',"local cmds=assert(io.open(ROOT..'/commands.txt','rb'))",lua,count=1,flags=re.M)
    lua=re.sub(r'^local replies=.*$',"local replies={write=function()end,flush=function()end}",lua,count=1,flags=re.M)
    lua=once(lua,'checkedMem527(function()rpc()end,emu.callbackType.exec,0x7e0000,0x7effff)','')
    if seed:
        assert seed.stat().st_size==8192
        lua=once(lua,'packet=requests[index];',"""if index==1 then
 local f=assert(io.open(SEED,'rb'));local data=f:read('*a');f:close()
 for bank=0,1 do for i=0,4095 do
  emu.write(0x15000+bank*32768+i,data:byte(bank*4096+i+1),emu.memType.snesWorkRam)
 end end
end
packet=requests[index];""".replace('SEED',json.dumps(seed.as_posix())))
    if case=='restart':
        lua=once(lua,"MODE=='normal'and 62","MODE=='normal'and 2")
    else:
        lua=once(lua,"local MODE='normal'","local MODE='guard852'")
        lua=once(lua,'local FAULT=905','local FAULT='+str(g))
        if case in ('damage','stop','prefix','omitted','overlap','tail-last','late-stop','two-stop'):
            action={'tail-last':"local a=0x10000+word(0x7a)+1471;emu.write(a,0x81,emu.memType.snesWorkRam);emu.write(a~32768,0x81,emu.memType.snesWorkRam)",
                    'two-stop':'stop852=true','late-stop':'stop852=true','omitted':"local a=0x10000+word(0x7a);emu.write(a,rd(a)~1,emu.memType.snesWorkRam)",
                    'overlap':"emu.write(0x1316,rd(0x1316)|0x40,emu.memType.snesWorkRam)", 'stop':'stop852=true','damage':"emu.write(0x10000+word(0x7a)+63,0x81,emu.memType.snesWorkRam)",
                    'prefix':"local a=0x10000+word(0x7a);emu.write(a,rd(a)~1,emu.memType.snesWorkRam)"}[case]
            if column_client:
                site=labels['column_service'] if case in ('stop','late-stop','two-stop') else labels['column_write']
                if case=='overlap':site=labels['column_mark']
                if case=='prefix':
                    site=labels['column_written']
                    operand=(client/"body.bin").read_bytes()[site-0x7e2000:site-0x7e2000+2]
                    assert operand in (bytes.fromhex("d1 7a"),bytes.fromhex("d1 68"))
                    action="local a=0x10000+word("+str(operand[1])+")+emu.getState()['cpu.y'];emu.write(a,rd(a)~1,emu.memType.snesWorkRam)"
            else:
                site=labels['check_tail852']
            condition="and word(0x60)==26 " if case=="late-stop" else ""
            if column_op==10:
                if case in ("late-stop","two-stop"):condition="and word(0x60)>=70 "
                condition=f"and packet and pb(0)==10 and pw(8)=={g} "+condition
                if case=="omitted":action="local a=0x10000+word(0x7a)+(pw(22)+4)%64;emu.write(a,rd(a)~1,emu.memType.snesWorkRam)"
            hooks=f"""
local stop852=false
local injected852=false
checkedMem527(function()
 if not injected852 {condition}then
  injected852=true
  {action}
 end
end,emu.callbackType.exec,{site})
"""
            lua=once(lua,'local function loaded()',hooks+'local function loaded()')
            lua=once(lua,' if a==0x6001 then',' if a==0x6001 then\n  if stop852 then return 128 end')
        lua=once(lua,'  assert(captured==commits)',"""  assert(word(0x1248)==commits and word(0x124a)==0)
  for i=0,7 do assert(rd(0x14d0+i)==0,'published bank history survived error') end
  local mem=assert(io.open(ROOT..'/canceled.bin','wb'))
  for bank=0,1 do for i=0,4095 do mem:write(string.char(rd(0x15000+bank*32768+i))) end end
  mem:close()
  assert(captured==commits)""")
    if adapt_lua:
        lua=adapt_lua(lua,labels)
    (out/'capture.lua').write_text(lua,encoding='utf8')
    for opt in ('expected-*.bin','colors636-*.bin','map-*.bin','client.sfc'):
        for file in trial.glob(opt):
            shutil.copyfile(file,out/file.name)
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([temp/'nes-bonus698-mesen/Mesen.exe','--testRunner',out/'capture.lua',out/'client.sfc',
                        '--timeout=240','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true',
                        '--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],
                       stdout=log,stderr=subprocess.STDOUT,timeout=255,check=True,creationflags=subprocess.CREATE_NO_WINDOW,
                       env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'))
    result=json.loads((out/'result.json').read_bytes())
    assert result['passed'] and result['commits']==commits
    assert result['last_status']==(1 if case=='restart' else 228 if case in ('stop','late-stop','two-stop') else 224)
    if case!='restart' and commits:
        assert sha(out/'retained.rgb')==sha(trial/f'frame-{g-1}.rgb')
    elif case=='restart':
        for g in (905,906):
            assert sha(out/f'frame-{g}.rgb')==sha(trial/f'frame-{g}.rgb')
    return dict(commits=commits,status=result['last_status'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('temp','trial','out'):p.add_argument(key,type=Path)
    p.add_argument('--arm',choices=('stop','identity'))
    a=p.parse_args()
    if a.arm:
        results=arm_guard(a.temp,a.arm)
    else:
        results={case:run(a.temp,a.trial,case) for case in ('cold','base','length','range','damage','prefix','stop')}
        results['restart']=run(a.temp,a.trial,'restart',a.trial/'guard-stop/canceled.bin')
    a.out.write_text(json.dumps(results,indent=2)+'\n')
