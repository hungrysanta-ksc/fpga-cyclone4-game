# SPDX-License-Identifier: MIT
"""Replay only pre-hint RAM snapshots;prove selected tags have causal provenance."""
import argparse,ctypes,json,struct
from pathlib import Path
from profile_nes_prepare353 import Profile
from check_nes_compact354 import objects
from probe_nes_arm264 import crc
from nes_delta231 import BASE,sha

class Resident(ctypes.LittleEndianStructure):
 _fields_=[('bg',ctypes.c_uint16*1024),('obj',ctypes.c_uint32*128),('resident',(ctypes.c_uint8*144)*2),('used',ctypes.c_uint8*144),('dirty',ctypes.c_uint8*144),
  ('map_stale',ctypes.c_uint64*2),('map_upload',ctypes.c_uint64),('epoch',ctypes.c_uint32),('serial',ctypes.c_uint32),('writes',ctypes.c_uint32),('hits',ctypes.c_uint32),
  ('generation',ctypes.c_uint16),('bg_slots',ctypes.c_uint16),('obj_slots',ctypes.c_uint16),('active',ctypes.c_uint8),('target',ctypes.c_uint8),
  ('displayed',ctypes.c_uint8),('open',ctypes.c_uint8),('prepared',ctypes.c_uint8),('fault',ctypes.c_uint8)]

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--snapshots',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 ref=BASE/'probes/nes-context375/joint01';elf=a.candidate.resolve()/'output.elf';syms=objects(ref/'output.elf');assert syms==objects(elf)
 assert Resident.epoch.offset==3160 and Resident.fault.offset==3187
 arms=[Profile(x) for x in (ref/'output.elf',elf)];rows=[];guards=[];pins={str(x):sha(x) for x in (elf,ref/'output.elf',ref/'nes_resident211.h',Path(__file__))}
 def readobj(blob,name):at,size=syms[name];return blob[at-0x20000000:at-0x20000000+size]
 def run(arm,blob):
  arm.uc.mem_write(0x20000000,blob);arm.instructions=0;n=arm.call('source_hint367',[]);cost=arm.instructions;assert n in (0,28)
  at=arm.call('source_buffer367',[]);packet=bytes(arm.uc.mem_read(at,n))
  for name in ('resident285','receiver280','history286'):
   at,size=syms[name];assert bytes(arm.uc.mem_read(at,size))==readobj(blob,name),(name,'hint acquired authority')
  return packet,cost
 for f in range(907,917):
  for path in sorted((a.snapshots or ref).glob(f'causal368-{f-904}-*.bin')):
   pins[str(path)]=sha(path);blob=path.read_bytes();r=Resident.from_buffer_copy(readobj(blob,'resident285')[:ctypes.sizeof(Resident)])
   g=struct.unpack('<I',readobj(blob,'geometry_groups367'))[0];history=readobj(blob,'history286');allowed=set();target=1-r.active
   assert r.active in (0,1)
   bit=lambda buf,i:bool(buf[i//8]&(1<<(i%8)))
   target_tags={r.bg[i] for i in range(r.bg_slots) if bit(r.resident[target],i)}
   for group in range(32):
    if g&(1<<group):
     for col in range(33):
      word=struct.unpack_from('<H',history,66*group+2*col)[0]
      if not word&32768 and word&8191 not in target_tags:allowed.add(word&8191)
   for i in range(r.bg_slots):
    if bit(r.used,i) and bit(r.resident[r.active],i) and not bit(r.resident[target],i):allowed.add(r.bg[i])
   for i in range(r.obj_slots):
    if bit(r.used,1024+i) and bit(r.resident[r.active],1024+i) and not bit(r.resident[target],1024+i) and r.obj[i]!=0xffffffff:allowed.add(r.obj[i]&8191)
   before,bc=run(arms[0],blob);after,ac=run(arms[1],blob);tags=[]
   if after:
    assert crc(after[:26])==int.from_bytes(after[26:],'little')
    tags=list(struct.unpack('<7H',after[12:26]));assert set(tags)<=allowed,(f,tags,allowed)
    s=readobj(blob,'receiver280');epoch,serial=struct.unpack_from('<II',s);gen=struct.unpack_from('<H',s,14)[0]
    assert struct.unpack_from('<HII',after,2)==(gen,epoch,serial)
   rows.append(dict(frame=f,snapshot=path.name,before_tags=list(struct.unpack('<7H',before[12:26])) if before else [],after_tags=tags,before_instructions=bc,after_instructions=ac,causal=True))
   if f==914 and after and not guards:
    # All these states must suppress speculation;no new authority or history.
    mutations=[('STOP','source_cancel367',0,struct.pack('<I',1)),('disabled','hint_mode367',0,bytes(4)),('source_cold','receiver280',22,b'\1'),
     ('open','resident285',Resident.open.offset,b'\1'),('prepared','resident285',Resident.prepared.offset,b'\1'),('fault','resident285',Resident.fault.offset,b'\1'),
     ('epoch','resident285',Resident.epoch.offset,struct.pack('<I',r.epoch^1)),('serial','resident285',Resident.serial.offset,struct.pack('<I',r.serial+2)),
     ('generation','resident285',Resident.generation.offset,struct.pack('<H',(r.generation+2)&65535))]
    for name,obj,off,data in mutations:
     b=bytearray(blob);at=syms[obj][0]-0x20000000+off;b[at:at+len(data)]=data;packet,cost=run(arms[1],bytes(b));assert not packet,name;guards.append(name)
    assert 6136 in tags and {6554,6555}<=set(tags)
 result=dict(passed=True,rows=rows,negative_guards=guards,object_ABI_exact=True,new_cache_bytes=0,wire_bytes_per_hint=28,scope='Pre-call snapshots only,no future plan replay used as input;hint changes no resident/receiver/history authority.',pins=pins)
 a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(dict(passed=True,replays=len(rows),guards=guards,first914=next(x for x in rows if x['frame']==914 and x['after_tags'])),indent=2))
if __name__=='__main__':main()
