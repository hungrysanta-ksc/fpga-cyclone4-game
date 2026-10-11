# SPDX-License-Identifier: MIT
"""Execute native SNES client/DMA/PPU with real and all-color frame snapshots."""
from pathlib import Path
import argparse,json,os,subprocess
from nes_game147 import ROOT,sha
from test_nes_game150 import planar
from build_nes_game152 import build,palette

def main():
    p=argparse.ArgumentParser()
    for n in ['pixels','out','mesen']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--verify-existing',action='store_true')
    p.add_argument('--old-client',action='store_true')
    a=p.parse_args()
    global build
    if a.old_client:
        from build_nes_game151 import build as old_build
        def build(out):
            result=old_build(out)
            (out/'game152.sfc').write_bytes((out/'game151.sfc').read_bytes())
            return result
    if not a.verify_existing:assert not a.out.exists();a.out.mkdir(parents=True)
    first=[int(v,16) for v in a.pixels.read_text().split()];assert len(first)==61440
    second=[((x//8)+(y//8)*7)%64 for y in range(240) for x in range(256)]
    if not a.verify_existing:
        (a.out/'payload.bin').write_bytes(planar(first)+planar(second));build(a.out/'client')
    lua='local OUT_DIR='+json.dumps(a.out.as_posix())+'\nlocal PAYLOAD='+json.dumps((a.out/'payload.bin').as_posix())+'\n'
    script=lua+(ROOT/'snes/video_probe/capture_game152.lua').read_text()
    if a.verify_existing:assert (a.out/'capture.lua').read_text()==script
    else:(a.out/'capture.lua').write_text(script,encoding='utf8')
    env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    if not a.verify_existing:
      with (a.out/'mesen.log').open('wb') as f:
        r=subprocess.run([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.out/'client/game152.sfc'),
          '--timeout=90','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true',
          '--debug.scriptWindow.allowIoOsAccess=true'],env=env,stdout=f,stderr=subprocess.STDOUT,timeout=110,creationflags=subprocess.CREATE_NO_WINDOW)
      assert r.returncode==0,(a.out/'mesen.log').read_text(errors='replace')[-2500:]
    size=list(map(int,(a.out/'size.txt').read_text().split()));assert size==[256,239],size
    pal=palette();lut=[]
    for i in range(64):
        v=int.from_bytes(pal[i*2:i*2+2],'little')
        lut.append(bytes((((v>>s)&31)<<3)|(((v>>s)&31)>>2) for s in [0,5,10]))
    for i,values in enumerate([first,second],1):
        # Mesen's fixed239-row canvas pads non-overscan224 video by7/8 black rows.
        expected=bytes(7*256*3)+b''.join(lut[v&63] for v in values[8*256:232*256])+bytes(8*256*3)
        actual=(a.out/f'frame-{i}.rgb').read_bytes()
        (a.out/f'expected-{i}.rgb').write_bytes(expected)
        assert actual==expected,(i,len(actual),sum(x!=y for x,y in zip(actual,expected)))
    rows=[list(map(int,v.split())) for v in (a.out/'inputs.tsv').read_text().splitlines()]
    pulses={10:0x1000,14:0x0080,18:0x8000,22:0x0100,26:0x0200,30:0x0400,42:0x2000,46:0x0800}
    seen={f:b for f,clock,b in rows if b}
    holds=[];shown=None
    for line in (a.out/'trace.tsv').read_text().splitlines():
        address,value,clock,frame,scanline=map(int,line.split())
        if address==0x7000 and value==6:shown=frame;holds.append([frame,None])
        if address==0x2100 and value==128 and holds and holds[-1][1] is None:holds[-1][1]=frame
    if a.old_client:
        assert len(rows)==2 and not seen,(rows,seen)
    else:
        assert len(rows)==62 and seen==pulses,(len(rows),seen)
        for lo,hi in holds:
            group=[f for f,clock,b in rows if lo<f<=lo+30]
            assert len(group)==30 and all(b-a==1 for a,b in zip(group,group[1:])),group
    assert 34 not in seen,'The intentional transfer/wait gap control changed'
    (a.out/'input-result.json').write_text(json.dumps(dict(passed=True,old_control=a.old_client,polls=len(rows),short_pulses=seen,transfer_gap_pulse34_missed=True,
      scope='Injected auto-joy register snapshots through actual SNES program; not physical buttons, NES game consumption, or per-DMA polling.'),indent=2)+'\n')
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,exact_rgb_frames=2,pixels=114688,
      input_sha=sha(a.pixels),sources={n:sha(ROOT/n) for n in ['tools/build_nes_game152.py','snes/video_probe/capture_game152.lua']},
      scope='Actual SNES CPU/DMA/PPU against modeled framebuffer, including bank wrap; not physical bus or game speed.'),indent=2)+'\n')
    print('PASS GAME152 SNES client: two exact256x224 RGB frames',flush=True)
if __name__=='__main__':main()
