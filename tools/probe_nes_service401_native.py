# SPDX-License-Identifier: MIT
"""401 native view and prior-display HDMA service measurements.

The installed400 kernel is unchanged. A separately identified fixture stub
establishes the prior display before the current source-job measurements.
Measured phase samples are not a resident CPU/WCET proof.
"""
import inspect,json,struct,sys
from pathlib import Path
import probe_nes_header399_native
import probe_nes_jobs394_native as old
from build_nes_trace_replay import Code
from nes_delta231 import once,sha

PHASE=0
ACTIVE='--hdma-off'not in sys.argv
if not ACTIVE:sys.argv.remove('--hdma-off')
if '--phase-line' in sys.argv:
 i=sys.argv.index('--phase-line');PHASE=int(sys.argv[i+1]);del sys.argv[i:i+2]
assert PHASE in(0,112,224)
kernel=old.rom

def rom(d):
 body,labels=kernel(d);image=bytearray((d/'spool.sfc').read_bytes())
 (d/'kernel400.sfc').write_bytes(image)
 f=int(d.name.split('-')[0]);fixture=0
 oracle,_=old.plans();previous=bytes(3418)if f<907 else(oracle/f'expected-{f-905}.bin').read_bytes()[5152:8570]
 old.LUA=fixture_lua.replace('local PRIORHDMA401=""','local PRIORHDMA401="'+previous.hex()+'"')
 if f>=907 and ACTIVE:
  prior=old.current_view(f-1);bank=1-((f-905)%2);c=Code(0x9000)
  def lda(a):c.absolute(0xad,a)
  # DP58 is a test-only one-shot, not additional target resident storage.
  lda(0x58);c.emit(0xf0,3);c.jump('run401');c.store(0x58,1)
  for a,v in((0x420c,0),(0x2100,128),(0x210b,6 if bank else 0),(0x2101,2 if bank else 1),(0x2107,0x51 if bank else 0x31),
    (0x4310,3),(0x4311,13),(0x4312,0),(0x4313,0xe5 if bank else 0x65),(0x4314,0x7f),
    (0x4320,4),(0x4321,5),(0x4322,0xb2 if bank else 0x61),(0x4323,0xf1 if bank else 0x71),(0x4324,0x7f),
    (0x4330,4),(0x4331,0x2c),(0x4332,3),(0x4333,0xf2 if bank else 0x72),(0x4334,0x7f),
    (0x420c,14 if prior[2] else 2),(0x2100,15)):c.store(a,v)
  # Enable before the next frame boundary, then release at a named line.
  c.label('blank401');lda(0x4212);c.branch(0x10,'blank401')
  c.label('active401');lda(0x4212);c.branch(0x30,'active401')
  if PHASE:
   c.label('line401');lda(0x213f);lda(0x2137);lda(0x213d);c.emit(0xc9,PHASE);c.branch(0x90,'line401')
  c.label('run401');at=labels['frame394']-0x8000
  assert image[at:at+4]==bytes.fromhex('c210c220')
  c.emit(*image[at:at+4]);c.labels['resume401']=labels['frame394']+4;c.jump('resume401')
  code=c.finish();image[0x1000:0x1000+len(code)]=code;image[at:at+4]=bytes.fromhex('4c0090ea');fixture=len(code)
  check=sum(image[:0x7fdc])+sum(image[0x7fe0:]);check&=65535;struct.pack_into('<HH',image,0x7fdc,check^65535,check)
  (d/'spool.sfc').write_bytes(image);(d/'fixture401.bin').write_bytes(code)
 (d/'fixture401.json').write_text(json.dumps(dict(kernel_body=body,kernel_SHA=sha(d/'kernel400.sfc'),fixture_bytes=fixture,phase_line=PHASE,prior_bank=bank if fixture else None,prior_HDMA_mask=(14 if prior[2]else 2)if fixture else 0,production_kernel_changed=False),indent=2)+'\n')
 return body,labels

old.rom=rom
lua=old.LUA
lua=once(lua,"local bus=assert(io.open(OUT..'/events.csv','w'));", "local PRIORHDMA401=\"\"\nlocal hdma401=assert(io.open(OUT..'/hdma401.csv','w'));local hdma_count401=0;local hdma_reads401=0;local started401=false;local fixture_begin401=nil;local fixture_end401=nil;\nlocal bus=assert(io.open(OUT..'/events.csv','w'));")
lua=once(lua,'local function note(op,a,v)local s=state();', '''local function note(op,a,v)local s=state();
 if op==1 and started401 and not COLD and not ppu_start and
   (a==0x210d or a==0x210e or a>=0x2105 and a<=0x2108 or a>=0x212c and a<=0x212f)then
  hdma401:write(string.format('%d,%d,%d,%d,%d\\n',at,a,v or 0,s.masterClock,s['ppu.scanline']));hdma401:flush();hdma_count401=hdma_count401+1;return v
 end
 ''')
lua=once(lua,'for i,b in ipairs(bytes(INITMAP))do', '''emu.write(0x58,0,emu.memType.snesWorkRam)
 local priorbytes401=bytes(PRIORHDMA401)
 if not COLD then for i,b in ipairs(priorbytes401)do emu.write(0x16500+(1-BANK)*0x8000+i-1,b,emu.memType.snesWorkRam)end end
 emu.addMemoryCallback(function(a,v)
  local off=a-0x7f6500-(1-BANK)*0x8000
  if started401 and not COLD and not ppu_start and off>=0 and off<#priorbytes401 then
   assert(emu.read(a-0x7e0000,emu.memType.snesWorkRam)==priorbytes401[off+1],'prior HDMA byte mismatch');hdma_reads401=hdma_reads401+1
  end
 end,emu.callbackType.read,0x7f0000,0x7fffff)
 emu.addMemoryCallback(function()started401=true end,emu.callbackType.exec,LABELS.new394)
 emu.addMemoryCallback(function()if not fixture_begin401 then fixture_begin401=state().masterClock end end,emu.callbackType.exec,LABELS.frame394)
 emu.addMemoryCallback(function()if not fixture_end401 then fixture_end401=state().masterClock end end,emu.callbackType.exec,LABELS.frame394+4)
 for i,b in ipairs(bytes(INITMAP))do''')
lua=lua.replace('bus:close();timings:close();emu.stop(0)', '''local h=assert(io.open(OUT..'/hdma-result401.json','w'));h:write(string.format('{"writes":%d,"reads":%d,"prior_RAM_exact":true,"fixture_begin":%d,"fixture_end":%d}',hdma_count401,hdma_reads401,fixture_begin401,fixture_end401));h:close();hdma401:close();bus:close();timings:close();emu.stop(0)''')
fixture_lua=lua;old.LUA=lua
old.__doc__=__doc__
if __name__=='__main__':old.main()
