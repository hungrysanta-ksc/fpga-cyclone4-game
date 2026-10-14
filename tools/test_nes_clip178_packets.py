# SPDX-License-Identifier: MIT
"""Replay valid staging packets; real65816 must reject malformed final SEAL.

No injected ACK or WRAM state. Reuse the exact functionally tested178 client.
This checks compatibility boundaries, not physical SPI or frame throughput.
"""
from pathlib import Path
import argparse,json,os,struct,subprocess
from nes_game147 import ROOT,sha

def main():
    p=argparse.ArgumentParser()
    for n in ['prior','mesen','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    packets=[]
    for f in sorted((a.prior/'budget').glob('req-*.bin')):
        b=f.read_bytes();packets.append(b)
        if b[0]==3:break
    assert len(packets)==45 and len(packets[-1])==36 and struct.unpack_from('<H',packets[-1],12)[0]==20
    cases={'legacy18':None,'independent_left_1a':0x1a,'independent_left_1c':0x1c,'upper_byte_0118':0x118,'blank00':0,'emphasis3e':0x3e,'grayscale1f':0x1f}
    env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    results=[]
    for name,mask in cases.items():
        d=a.out/name;d.mkdir();final=bytearray(packets[-1])
        if mask is None:final=final[:-2];struct.pack_into('<H',final,12,18)
        else:struct.pack_into('<H',final,34,mask)
        for i,b in enumerate(packets[:-1]+[bytes(final)],1):(d/f'req-{i:04}.bin').write_bytes(b)
        lua=(ROOT/'snes/video_probe/capture_native_sink165.lua').read_text()
        anchor='  ackcount=ackcount+1'
        assert lua.count(anchor)==1
        lua=lua.replace(anchor,'''  if packetbyte(0)==3 then
   assert(ack[1]==0xe0 and not revealed and commits==0,'malformed SEAL displayed or accepted')
   local f=assert(io.open(OUT_DIR..'/result.json','w'))
   f:write(string.format('{"passed":true,"status":%d,"prior_acks":%d,"commits":%d}',ack[1],ackcount,commits));f:close();log:close();emu.stop(0);return
  end
'''+anchor)
        (d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE="negative"\n'+lua,encoding='utf8',newline='\n')
        with (d/'mesen.log').open('wb') as log:
            q=subprocess.run([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(a.prior/'client/sink165.sfc'),'--timeout=120','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=130,creationflags=subprocess.CREATE_NO_WINDOW)
        assert q.returncode==0,(name,(d/'mesen.log').read_text(errors='replace')[-1500:])
        r=json.loads((d/'result.json').read_bytes());assert r['passed'] and r['prior_acks']==44
        results.append(dict(case=name,**r));print(name,'PASS',flush=True)
    result=dict(passed=True,cases=results,client_sha256=sha(a.prior/'client/sink165.sfc'),prior_result_sha256=sha(a.prior/'result.json'),public_sources={n:sha(ROOT/n) for n in ['tools/test_nes_clip178_packets.py','snes/video_probe/capture_native_sink165.lua']},scope=__doc__)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
