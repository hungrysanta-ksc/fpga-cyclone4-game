# Run and audit wholeCHR SNES replay. SPDX-License-Identifier: MIT.
from pathlib import Path
import argparse,hashlib,json,os,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(probe,out):
    manifest=json.loads((probe/'manifest.json').read_text())
    capture=json.loads((out/'capture.json').read_text())
    assert capture['exit_code']==0 and capture['rom_sha256']==manifest['rom_sha256']==sha(probe/'replay.sfc')
    frames=[];errors=[]
    rows=[tuple(map(int,s.split())) for s in (out/'frames.tsv').read_text().splitlines()]
    assert len(rows)==4
    for i,emuframe,clock,f,error,w,h in rows:
        actual=(out/f'frame-{i:03}.rgb').read_bytes()
        expected=(probe/f'expected-{f}.rgb').read_bytes()
        assert (w,h,len(actual))==(256,239,256*239*3)
        bad_positions=[j//3 for j in range(0,len(actual),3) if actual[j:j+3]!=expected[j:j+3]]
        bad=len(bad_positions)
        if bad:errors.append('pixels')
        if f!=i+1:errors.append('sequence')
        if error:errors.append('host_error')
        assert not frames or emuframe==frames[-1]['emulator_frame']+1
        frames.append(dict(index=i,frame=f,emulator_frame=emuframe,error=error,different_pixels=bad,difference_bounds=None if not bad else dict(min_x=min(j%256 for j in bad_positions),max_x=max(j%256 for j in bad_positions),min_y=min(j//256 for j in bad_positions),max_y=max(j//256 for j in bad_positions)),sha256=sha(out/f'frame-{i:03}.rgb')))
    current=None;tx=[];startup=[];published=False
    for row in (out/'trace.tsv').read_text().splitlines():
        kind,*v=row.split();value,clock,ef,line,hclock,display,attempt,error,target,size,addr,bank,src,mapbase,vmain=map(int,v)
        if kind=='brightness':
            if published:assert not value&128,'repeated forced blank'
            if value==15:published=True
        if kind=='phase' and value==1:
            assert current is None and line>=240
            current=dict(attempt=attempt,start=clock,line=line,hclock=hclock,dmas=[],bases=[],scrolls=[],chrbases=[])
        elif current and kind=='dma':
            assert 240<=line<=261
            current['dmas'].append(dict(bytes=size,target=target,address=addr,bank=bank,source=src,vmain=vmain))
        elif kind=='dma':
            assert not published
            startup.append(dict(bytes=size,target=target,address=addr,bank=bank,source=src,vmain=vmain))
        elif current and kind=='chrbase':
            current['chrbases'].append(value)
        elif current and kind=='scroll':
            current['scrolls'].append(value)
        elif current and kind=='mapbase':
            current['bases'].append(value)
        elif current and kind=='phase' and value in (3,238):
            duration=clock-current['start']
            margin=(262-current['line'])*1364-4-current['hclock']-duration
            assert margin>=0 and 240<=line<=261
            f=current['attempt'];slot=(f-1)%2
            if value==3:
                assert current['dmas']==[
                    dict(bytes=1920,target=24,address=slot*0x800,bank=1,source=0x8014+(f-1)*2048,vmain=128),
                    dict(bytes=60,target=24,address=slot*0x800+0x400,bank=1,source=0x8794+(f-1)*2048,vmain=129),
                    dict(bytes=8,target=34,address=slot*0x800+0x400,bank=1,source=0x87d0+(f-1)*2048,vmain=129)]
                fine=manifest['frames'][f-1]['fine_x']
                assert current['scrolls']==[fine,0]
                window=manifest['frames'][f-1]['chr_window']
                if manifest['fault']=='bank':window^=1
                assert current['chrbases']==[2+window*2]
                assert current['bases']==[slot*8+1] and display==f
            else:
                assert not current['dmas'] and not current['chrbases'] and not current['bases'] and not current['scrolls'] and error==226
            current.update(outcome='commit' if value==3 else 'reject',duration_master_clocks=duration,
                           deadline_margin_master_clocks=margin)
            tx.append(current);current=None
    assert current is None
    assert startup==[dict(bytes=32768,target=24,address=0x2000,bank=2,source=0x8000,vmain=128)]
    normal=not errors and len(tx)==4 and all(t['outcome']=='commit' for t in tx)
    fault=manifest['fault']
    if fault=='none':expected_outcome=normal
    elif fault=='bank':
        expected_outcome=(set(errors)=={'pixels'} and all(f['different_pixels']>0 for f in frames)
                          and len(tx)==4 and all(t['outcome']=='commit' for t in tx))
    else:
        expected_outcome=(set(errors)=={'host_error','sequence'} and [f['frame'] for f in frames]==[1]*4
                          and [t['outcome'] for t in tx]==['commit','reject'] and tx[-1]['attempt']==2)
    return dict(candidate=manifest['candidate'],normal_pass=normal,expected_outcome_verified=expected_outcome,
                fault=fault,viewport=manifest['viewport'],errors=sorted(set(errors)),frames=frames,transactions=tx,
                max_commit_master_clocks=max(t['duration_master_clocks'] for t in tx if t['outcome']=='commit'),
                min_commit_margin_master_clocks=min(t['deadline_margin_master_clocks'] for t in tx if t['outcome']=='commit'),
                source_height=240,display_height=239,live_producer_deadline_proven=False,
                manifest_sha256=sha(probe/'manifest.json'),capture_sha256=sha(out/'capture.json'),auditor_sha256=sha(__file__))
def main():
    p=argparse.ArgumentParser()
    for n in ('mesen','probe','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();out=a.out.resolve();probe=a.probe.resolve();exe=a.mesen.resolve()
    assert str(out).isascii() and not out.exists();out.mkdir(parents=True)
    script=Path(__file__).resolve().parents[1]/'snes/video_probe/capture_chr_residency.lua'
    (out/'capture.lua').write_text('local OUT_DIR='+json.dumps(out.as_posix())+'\n'+script.read_text(),encoding='utf-8',newline='\n')
    env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    with (out/'mesen.log').open('wb') as log:
        proc=subprocess.run([str(exe),'--testRunner',str(out/'capture.lua'),str(probe/'replay.sfc'),
               '--timeout=30','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true'],
               env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
    capture=dict(exit_code=proc.returncode,rom_sha256=sha(probe/'replay.sfc'),script_sha256=sha(script),
                 runner_sha256=sha(__file__),tools={n:sha(exe.parent/n) for n in ('Mesen.exe','Mesen.dll','MesenCore.dll','settings.json')})
    (out/'capture.json').write_text(json.dumps(capture,indent=2)+'\n',encoding='utf-8')
    assert proc.returncode==0,(out/'mesen.log').read_text(errors='replace')
    result=audit(probe,out)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('frames','transactions')},indent=2))
    raise SystemExit(0 if result['expected_outcome_verified'] else 1)
if __name__=='__main__':main()