# SPDX-License-Identifier: MIT
"""Exhaustive255 nonzero masks through actual receiver after two displays.

Checks selected AND unselected map bytes, receipts, exact command spans and
full manifest. No display of synthetic graphics, WRAM injection or ACK bypass.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess,tempfile
from nes_delta231 import once,sha
from analyze_nes_batchorder247 import join


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('normal','client','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=a.normal/'run';d=Path(tempfile.mkdtemp(prefix='nes-fastmasks247-'))
    reqs=sorted(source.glob('req-*.bin'));first=[f for f in reqs if int.from_bytes(f.read_bytes()[8:10],'little')<=2]
    begin=next(f.read_bytes() for f in reqs if f.read_bytes()[0]==1 and int.from_bytes(f.read_bytes()[8:10],'little')==3)
    for f in first:shutil.copyfile(f,d/f.name)
    for f in source.iterdir():
        if f.name.startswith(('tile-','expected-','oam-','bank-')) or f.name=='palette.bin':shutil.copyfile(f,d/f.name)
    ordinal=len(first)+1;(d/f'req-{ordinal:04d}.bin').write_bytes(begin);ordinal+=1;seq=1
    want=bytearray((source/'expected-1.bin').read_bytes()[:4096]);receipt=bytearray(256);ranges=[]
    bodies=[];body=bytearray([2]);words=0
    for mask in range(1,256):
        record=bytearray([mask,mask]);receipt[mask]=mask
        for bit in range(8):
            if mask>>bit&1:
                at=mask*16+bit*2;value=(0x5a00^(mask*37)^(bit*1027)).to_bytes(2,'little')
                record+=value;want[at:at+2]=value;ranges.append((2,at,2));words+=1
        if len(body)+len(record)>240:bodies.append(body);body=bytearray([2])
        body+=record
    bodies.append(body)
    for op,at,payload in [(9,0,b) for b in bodies]+[(10,0,receipt[:240]),(10,240,receipt[240:])]:
        h=bytearray(begin[:16]);h[0:2]=bytes([op,2]);h[2:4]=seq.to_bytes(2,'little');h[10:12]=at.to_bytes(2,'little');h[12:14]=len(payload).to_bytes(2,'little');h[14:16]=bytes(2)
        (d/f'req-{ordinal:04d}.bin').write_bytes(h+payload);seq+=1;ordinal+=1
    spans=join(ranges);commands=[dict(source=0x5000+at,destination=0x6000+at,bytes=n) for k,at,n in spans]
    (d/'allmask-map.bin').write_bytes(want);(d/'allmask-receipt.bin').write_bytes(receipt)
    lua=(source/'capture.lua').read_text(encoding='utf-8').split('\n',1)[1]
    lua='local OUT_DIR='+json.dumps(d.as_posix())+'\n'+lua
    expected='{' + ','.join('{'+','.join(str(r[k]) for k in ('source','destination','bytes'))+'}' for r in commands)+'}'
    check=r'''
  if ack[1]==0 and pw(8)==3 and pb(0)==10 and word(0x1490)==256 then
   assert(commits==2 and word(0x1034)==0,'wrong lifetime')
   local f=assert(io.open(OUT_DIR..'/allmask-map.bin','rb'));local want=f:read('*a');f:close()
   for i=0,4095 do assert(rd(0x15000+i)==want:byte(i+1),'selected/unselected map mismatch '..i)end
   f=assert(io.open(OUT_DIR..'/allmask-receipt.bin','rb'));want=f:read('*a');f:close()
   for i=0,255 do assert(rd(0x1500+i)==want:byte(i+1),'receipt mismatch '..i)end
   local cmds=COMMANDS;assert(word(0x1250)==#cmds*8,'command count')
   for i,r in ipairs(cmds)do for j=1,3 do assert(word(0x4000+(i-1)*8+(j-1)*2)==r[j],'command value')end end
   f=assert(io.open(OUT_DIR..'/allmask-result.json','w'));f:write('{"passed":true,"masks":255,"words":1024,"map_bytes":4096,"receipt_bytes":256,"prior_displays":2}');f:close();emu.stop(0)
  end
'''.replace('COMMANDS',expected)
    lua=once(lua,'  if pb(0)==7 then\n',check+'  if pb(0)==7 then\n')
    (d/'capture.lua').write_text(lua,encoding='utf-8',newline='\n')
    env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    try:
        mesen=Path.home()/'AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe'
        with (d/'mesen.log').open('wb') as log:
            run=subprocess.run([str(mesen),'--testRunner',str(d/'capture.lua'),str(a.client.resolve()/'sink165.sfc'),'--timeout=60','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=80)
        assert run.returncode==0,run.returncode
        r=json.loads((d/'allmask-result.json').read_text());assert r['passed'] and r['words']==words
        r.update(scope=__doc__,commands=commands,packets=len(bodies)+2,normal_sha256=sha(a.normal/'result.json'),client_sha256=sha(a.client/'sink165.sfc'),script_sha256=sha(Path(__file__)),physical=False)
        (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS FASTMASKS247 masks=255 words=1024 exact_map=4096')
    finally:shutil.copytree(d,a.out/'run',dirs_exist_ok=True);shutil.copyfile(__file__,a.out/'test.py')


if __name__=='__main__':main()
