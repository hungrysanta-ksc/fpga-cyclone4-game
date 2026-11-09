"""Execute714 fence/quiet/plan/packet on linked M4; endpoint timing is modeled."""
import argparse,json
from pathlib import Path
from check_nes_supply485_arm import ARM,crc,sha,ELFFile
from check_nes_rows713 import Peer
from test_nes_raw506_joint import member_offset

class WaitingPeer(Peer):
 def __init__(self,mode):super().__init__(mode);self.busy=0
 def exchange(self,tx,clock):
  r=super().exchange(tx,clock)
  if tx[0]==0xe8 and self.busy and not self.jobs and not self.stale_reads:
   self.busy-=1;r=bytearray(r);r[3]=0;r[19]=crc(r[1:19],8,7,0);r=bytes(r)
  return r

def case(src,mode):
 m=ARM(src,mode);m.endpoint=WaitingPeer('normal');e=m.endpoint
 with (src/'obj-nes-100/sd2snes.elf').open('rb') as f:
  for cu in ELFFile(f).get_dwarf_info().iter_CUs():
   for d in cu.iter_DIEs():
    if d.tag=='DW_TAG_structure_type' and d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value==b'nes_native_runtime165' and d.attributes.get('DW_AT_byte_size'):
     m.layout['nes_native_runtime165']={'size':d.attributes['DW_AT_byte_size'].value,**{x.attributes['DW_AT_name'].value.decode():member_offset(x) for x in d.iter_children() if x.tag=='DW_TAG_member'}}
 rt=0x20003000;L=m.layout['nes_native_runtime165'];m.p=rt+L['plan'];m.w=rt+L['transport'];m.s=rt+L['sink'];m.setup();e.mode=mode
 # Endpoint owns simulated time; reason4 input service is outside this unit.
 m.put(m.w,'nes_sink_window184','wait',m.guard485|1,4)
 for k,v in [('video',m.video),('resident',m.resident)]:m.put(rt,'nes_native_runtime165',k,v,4)
 m.put(m.s,'nes_native_sink165','plan',m.p,4)
 m.put(m.p,'nes_plan200','ctx',rt,4)
 for k,v,n in [('started',1,1),('generation',907,2),('bank_history',2,1),('early',1,1)]:m.put(m.p,'nes_plan200',k,v,n)
 mask=(1<<64)-1 if mode=='cold' else sum(1<<i for i in (0,1,2,3,4,5,32,33,34))
 m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],e.data)
 m.put(m.video,'nes_native_video165','map_dirty',mask,8)
 assert m.emit(0,1,4) and m.emit(0,2,7) # buffered, actual E9 still owed
 e.busy=2 if mode in ('busy','bad_credit') else 0
 if mode=='STOP':e.mode='STOP_after_E9';e.accepted=1
 ok=bool(m.call('offer527',[rt,1]));positive=mode in ('normal','busy','cold')
 if ok:
  assert m.get(m.p,'nes_plan200','count')==0 and e.accepted==1 and len(e.plans)==2
  assert [i for off,n in e.maps for i in range(off,off+n)]==list(range(sum(n for _,n in e.maps)))
  if mode=='busy':assert e.maps==[(0,192),(192,192)]
  if mode=='normal':assert not e.maps # E9 wins without artificial map issue
  # Existing producer must still complete real bulk receipt before final retirement.
  m.put(m.p,'nes_plan200','quiet_map',0,4)
  ok=bool(m.call('nes_plan200_end',[m.p]) and m.call('nes_plan200_progress',[m.p,1]))
 assert ok==positive,(mode,ok,m.get(m.p,'nes_plan200','error'),m.get(m.w,'nes_sink_window184','error'))
 if ok:
  assert m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,0])
  seen=[i for off,n in e.maps for i in range(off,off+n)]
  expected=[i for i in range(4096) if mask>>(i//64)&1]
  assert sorted(seen)==expected and len(set(seen))==len(seen)
  assert not m.get(m.s,'nes_native_sink165','displayed') and not m.call('nes_plan200_retire',[m.p]) and not e.rearmed
 else:
  before=len(e.calls);assert not m.emit(0,3,9) and len(e.calls)==before
 m.call('nes_sink165_reset',[m.s,m.syms['nes_window184_barrier']|1,m.w])
 assert not m.get(m.s,'nes_native_sink165','map_next') and not m.get(m.s,'nes_native_sink165','displayed')
 return dict(case=mode,passed=True,maps=e.maps,E9=e.accepted,bulk=e.bulk,operations=[int(t[:2],16) for t in e.calls])

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();rows=[case(a.arm,n) for n in ('normal','busy','cold','STOP','bad_E8_CRC','bad_credit','ambiguous_E1')]
 a.out.write_text(json.dumps(dict(stage=714,passed=True,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,scope=__doc__),indent=2)+'\n');print('PASS714',len(rows),'actual fence/queue/STOP/CRC/cold guards')
