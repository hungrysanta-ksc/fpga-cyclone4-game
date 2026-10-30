# SPDX-License-Identifier: MIT
"""Same old489 CPU/payload/start; compare compact progress wire allocations.

One ready-credit status allocation20->8B, final ready ACK20->28B. Busy polls,
ARM execution/IRQ and source/ROM are NOT on this clock: conditional schedule,
not a physical full-path bound. Packet dispatch intervals include nested work.
"""
import argparse,json,os,shutil,struct,subprocess,csv,collections
from pathlib import Path
import test_nes_output489_snes as base
from nes_status495 import once,sha
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['compact','client','rom','mesen','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--frames',type=int,default=12);a=p.parse_args();a.out=a.out.resolve();assert a.out.as_posix().isascii();a.out.mkdir(exist_ok=False)
    a.row_counts=None;a.baseline=a.compact;rows=[];env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
    for phase in [0,85909]:
        for short in [False,True]:
            d=a.out/(('short-'if short else 'full-')+str(phase));d.mkdir();total=base.prepare(a,d,True);shutil.copyfile(a.client/'sink165.sfc',d/'client.sfc')
            s=base.LUA
            if short:
                s=once(s,"start=retiredAt[sealIndex[frames[sent]-1]]+20*bytesToClock","start=retiredAt[sealIndex[frames[sent]-1]]+28*bytesToClock")
                s=once(s,"(retiredAt[sent-4] or 0)+20*bytesToClock","(retiredAt[sent-4] or 0)+8*bytesToClock")
            s=once(s,'local requests,frames,ready,retiredAt,sealIndex,frameRelease={},{},{},{},{},{}',
                "local pf495=assert(io.open(ROOT..'/packet495.csv','w'));pf495:write('generation,ordinal,op,section,dispatch_master_clocks\\n');local packet_start495=0\nlocal requests,frames,ready,retiredAt,sealIndex,frameRelease={},{},{},{},{},{}")
            s=once(s,'packet=requests[index];reads=0;token={};decodeStart=nil','packet=requests[index];packet_start495=st.masterClock;reads=0;token={};decodeStart=nil')
            s=once(s,'retired=index;retiredAt[index]=st.masterClock;',"pf495:write(string.format('%d,%d,%d,%d,%d\\n',pw(8),index,pb(0),pb(1),st.masterClock-packet_start495));pf495:flush();retired=index;retiredAt[index]=st.masterClock;")
            replacements={'ROOT':json.dumps(d.as_posix()),'MODE':'"normal"','COMPACT':'true','TOTAL':str(total),'FRAMES':str(a.frames),'SCHEDULE':'"continuous"','START':str(3000000+phase),'FAULT':'906','POISON':'false'}
            for key,value in replacements.items():s=s.replace('@'+key+'@',value)
            (d/'capture.lua').write_text(s,encoding='utf8',newline='\n')
            with (d/'mesen.log').open('wb')as f:r=subprocess.run([str(a.mesen.resolve()),'--testRunner',str(d/'capture.lua'),str(d/'client.sfc'),'--timeout=600','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=250,creationflags=subprocess.CREATE_NO_WINDOW)
            assert r.returncode==0,(d,r.returncode);q=json.loads((d/'result.json').read_text());assert q['passed']and q['commits']==a.frames
            if short:
                old=a.out/('full-'+str(phase));assert (d/'requests.bin').read_bytes()==(old/'requests.bin').read_bytes()
                for frame in range(905,905+a.frames):assert (d/f'frame-{frame}.rgb').read_bytes()==(old/f'frame-{frame}.rgb').read_bytes()
            parts=collections.Counter()
            for row in csv.DictReader((d/'packet495.csv').open()):parts[row['op']+'/'+row['section']]+=int(row['dispatch_master_clocks'])
            rows.append({'short':short,'phase_masterclocks':phase,'end_masterclock':q['frames'][-1]['ACK_masterclock'],'elapsed_ms':(q['frames'][-1]['ACK_masterclock']-3000000-phase)/21477.272,'packet_dispatch_inclusive_ms':{k:v/21477.272 for k,v in parts.items()},'requests_SHA256':sha(d/'requests.bin')})
            print(json.dumps(rows[-1]),flush=True)
    result={'passed':True,'scope':__doc__,'rows':rows,'SNES_SHA256':sha(a.client/'sink165.sfc'),'same_payload_pixels':True,'physical':False,'common_ARM_IRQ_ROM_clock':False}
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
