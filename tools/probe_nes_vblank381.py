# SPDX-License-Identifier: MIT
"""Actual STOP-safe65816 commit with latchedVcounter admission in current VBlank."""
import csv,inspect,json,shutil
from pathlib import Path
import probe_nes_commit380 as prior380
from nes_delta231 import ROOT,once,sha

OLD=""" c.label('active');c.absolute(0xad,0x4212);c.branch(0x30,'active')
 c.label('blank');c.absolute(0xad,0x4212);c.branch(0x10,'blank')"""
NEW=""" c.label('active');c.absolute(0xad,0x4212);c.branch(0x10,'blank')
 # STAT78 resets counter flipflops;SLHV latches only with WRIO.7 enabled.
 # This standalone CPU fixture uses reset WRIO=$ff. Production must preserve
 # its output shadow and explicitly establish that precondition.
 c.absolute(0xad,0x213f);c.absolute(0xad,0x2137);c.absolute(0xad,0x213d);c.absolute(0x8d,0x1010)
 c.absolute(0xad,0x213d);c.emit(0x29,1);c.branch(0xf0,'low381')
 c.absolute(0xad,0x1010);c.emit(0xc9,2);c.branch(0x90,'apply381');c.jump('late381')
 c.label('low381');c.absolute(0xad,0x1010);c.emit(0xc9,225);c.branch(0xb0,'apply381');c.jump('blank')
 c.label('late381');c.absolute(0xad,0x4212);c.branch(0x30,'late381')
 c.label('blank');c.absolute(0xad,0x4212);c.branch(0x10,'blank')
 c.label('apply381')"""

def rom(d):
 s=inspect.getsource(prior380.rom);s=once(s," ns=dict(prior.__dict__);", " s=once(s,OLD381,NEW381)\n ns=dict(prior.__dict__);")
 ns=dict(prior380.__dict__,OLD381=OLD,NEW381=NEW);exec(compile(s,'vblank381-generator','exec'),ns);return ns['rom'](d)

def main():
 lua=once(prior380.LUA,'function(a,v)note(0,a,1);return 1 end',
  'function(a,v)local b=emu.getState().masterClock>=RELEASE and 1 or 0;note(0,a,b);return b end')
 lua=once(lua,'local function write(a,v)', '''emu.addMemoryCallback(function(a,v)note(0,a,v)end,emu.callbackType.read,0x4212)
emu.addMemoryCallback(function(a,v)note(0,a,v)end,emu.callbackType.read,0x2137,0x213f)
local function write(a,v)''')
 source=inspect.getsource(prior380.main)
 begin=source.index(" cases=[");end=source.index('\n for name,bank,stop,old in cases:',begin)
 cases=[('old-stop',0,1,True,0),('normal0',0,0,False,0),('normal1',1,0,False,0)]+[(f'{name}{bank}',bank,0,False,release) for name,release in [('inside',240*1364),('near',255*1364),('late',259*1364),('edge',355000)] for bank in (0,1)]+[('stopwait',0,1,False,240*1364)]
 source=source[:begin]+' cases='+repr(cases)+source[end:]
 source=once(source,'for name,bank,stop,old in cases:', 'for name,bank,stop,old,release in cases:')
 source=once(source,"script='local OUT='", "script='local RELEASE='+str(release)+'\\nlocal OUT='")
 source=source.replace('probe_nes_commit380.py','probe_nes_vblank381.py')
 ns=dict(prior380.__dict__,rom=rom,LUA=lua);exec(compile(source,'kernel381-main','exec'),ns);ns['main']()
 # main's CLI parser leaves the caller arguments unchanged.
 import sys
 d=Path(sys.argv[sys.argv.index('--out')+1]).resolve();report=json.loads((d/'result.json').read_text())
 for row,case in zip(report['cases'],cases):
  name,bank,stop,old,release=case;row['release_master']=release
  es=[list(map(int,x)) for x in csv.reader((d/name/'events.csv').read_text().splitlines())]
  if not stop:
   ack=next(x for x in es if x[:2]==[1,0x6058]);row['ACK_master']=ack[3];row['ACK_frame_index']=ack[3]//357368
   assert row['ACK_frame_index']==(1 if name.startswith(('late','edge')) else 0),(name,row)
   assert 225<=ack[4]<262
 report.update(stage=381,passed=True,current_blank_cutoff_scanline=257,scope='Actual new65816 kernel currentblank/lateblank/rollover/STOP cases with mockedview/status/token andzeroHDMAterminators;not fullCPU/PPUpixels/WCET/physical proof.')
 (d/'result.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
 capsule=d/'capsule';capsule.mkdir();selected=[]
 for bank in (0,1):
  early=d/f'normal{bank}';inside=d/f'inside{bank}';dest=capsule/f'bank{bank}';dest.mkdir()
  e=[list(map(int,x)) for x in csv.reader((early/'events.csv').read_text().splitlines())];v=[list(map(int,x)) for x in csv.reader((inside/'events.csv').read_text().splitlines())]
  first=next(x[3] for x in e if x[:2]==[0,0x6054]);poll=next(x[3] for x in e if x[1]==0x4212)
  ack=next(x[3] for x in v if x[:2]==[1,0x6058]);post=next(x[3] for x in v if x[1]==0x4212 and x[3]>ack)
  last_poll=max(x[3] for x in v if x[1]==0x4212 and x[3]<ack);latch=next(x[3] for x in v if x[1]==0x2137 and last_poll<x[3]<ack)-last_poll
  rows=[x for x in e if first<=x[3]<poll]+[x for x in v if x[3]==last_poll or last_poll<x[3]<post and not(x[0]==0 and 0x2137<=x[1]<=0x213f)]
  (dest/'events.csv').write_text('\n'.join(','.join(map(str,x)) for x in rows)+'\n',newline='\n');shutil.copyfile(early/'display.sfc',dest/'display.sfc')
  selected.append(dict(bank=bank,ROM=sha(dest/'display.sfc'),events=sha(dest/'events.csv'),head_first_master=first,first_4212_master=poll,latch_offset_clocks=latch,
   derived_head=str(early/'events.csv'),derived_head_SHA=sha(early/'events.csv'),derived_tail=str(inside/'events.csv'),derived_tail_SHA=sha(inside/'events.csv')))
 (capsule/'result.json').write_text(json.dumps(dict(passed=True,cases=selected,scope='Derived service capsule:real early head+currentblank tail;nativecounterread costs retained inoffsets,rawsource traces preserved. Observed allocation,not arbitraryphase CPU reexecution.'),indent=2)+'\n',newline='\n')
 print(json.dumps(dict(passed=True,cases=len(cases),body=report['cases'][1]['body_bytes'],capsule=selected)))
if __name__=='__main__':main()
