# SPDX-License-Identifier: MIT
"""592 measured deletion envelope and cold instruction attribution.

Replays unchanged591 ELF; no new firmware, ISA tuning or synthesized candidate.
Static DWARF line ownership is attribution, NOT independent deletion savings.
"""
import argparse,binascii,bisect,hashlib,json,math,re,struct,zipfile
from collections import Counter
from pathlib import Path
from statistics import mean
from check_nes_roles591 import Probe
from check_nes_game478 import ELFFile,encode
from nes_abi582 import canonical,crc
from analyze_nes_roles590 import old_nonmap,phase_packets
from nes_transfer512 import legacy_packets
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R3

ROOT=Path(__file__).resolve().parents[1]
PACKAGE=('nes_native165_packet','logical_record','request591','nes_native165_poll','nes_native165_prepare')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class Profile(Probe):
 def __init__(self,src):
  self.running=False;self.counts=Counter();self.context={};self.entries=Counter()
  super().__init__(src)
  native=(src/'nes_native165.c').read_text(encoding='utf8')
  lines=native.splitlines();owners={}
  for i,line in enumerate(lines):
   sig=re.match(r'^(?:static )?(?:bool|void|unsigned|uint(?:8|16|32|64)_t) (\w+)\(',line)
   if not sig:continue
   depth=0
   for j in range(i,len(lines)):
    owners[j+1]=sig[1];depth+=lines[j].count('{')-lines[j].count('}')
    if not depth:break
  line_addresses=[];line_values=[];self.pc={};self.static=Counter();self.symbols={}
  with (src/'obj-nes-100/sd2snes.elf').open('rb')as f:
   e=ELFFile(f)
   dw=e.get_dwarf_info()
   for cu in dw.iter_CUs():
    name=cu.get_top_DIE().attributes.get('DW_AT_name')
    if not name or not name.value.decode().endswith('nes_native165.c'):continue
    line=dw.line_program_for_CU(cu);assert line.header['version']==3
    for ent in line.get_entries():
     s=ent.state
     if s:
      is_native=not s.end_sequence and s.file>0 and line.header['file_entry'][s.file-1].name==b'nes_native165.c'
      line_addresses.append(s.address);line_values.append(s.line if is_native else 0)
   pairs=sorted(zip(line_addresses,line_values),key=lambda x:x[0]);line_addresses=[x[0]for x in pairs];line_values=[x[1]for x in pairs]
   funcs=[s for s in e.get_section_by_name('.symtab').iter_symbols()if s['st_info']['type']=='STT_FUNC' and s['st_size']]
   for s in funcs:
    name=s.name;start=s['st_value']&~1;size=s['st_size'];self.symbols[name]=(start,size)
    for at in range(start,start+size,2):
     category=name
     if name=='nes_native165_packet':
      pos=bisect.bisect_right(line_addresses,at)-1;ln=line_values[pos]if pos>=0 else 0
      category='packet/'+owners.get(ln,'shared_or_unmapped')
     self.pc[at]=category
     if name in PACKAGE:self.static[category]+=min(2,start+size-at)
  assert sum(self.static.values())==sum(self.symbols[n][1]for n in PACKAGE)
 def hook(self,u,at,size,user):
  if self.running and at not in (self.spi,self.end,self.writer):
   category=self.pc.get(at,'unmapped')
   for name in ('canonical591','logical_record','crc16'):
    if at==self.symbols[name][0]:
     phase=self.get('r_phase');tag=str(phase)
     if name=='logical_record':
      kind=u.reg_read(UC_ARM_REG_R1);tag='map'if kind==0 else 'nonmap'if kind<6 else 'control'+str(u.reg_read(UC_ARM_REG_R3))
     elif name=='canonical591':tag='map'if phase==1 else 'nonmap'if phase==2 else 'raw'if phase==3 else tag
     else:tag='map_rescan'if u.reg_read(UC_ARM_REG_R0)==self.state+self.layout['nes_native165']['maps']else 'wire_or_request'
     self.context[name]=tag;self.entries[name+'/'+tag]+=1
   if category in self.context:category+='/'+self.context[category]
   self.counts[category]+=1
  super().hook(u,at,size,user)
 def measured(self):
  self.counts.clear();self.entries.clear();self.running=True
  r=self.run_frame();self.running=False
  assert r['ok'] and sum(self.counts.values())==r['instructions'],(r,sum(self.counts.values()))
  r.update(exclusive_instructions=dict(self.counts),function_entries=dict(self.entries));return r


WIDTH=(2,1,7,4,7,1,1)
def raster_next(v):
 low=v&32767
 if low&0x7000!=0x7000:low+=0x1000
 else:
  low&=~0x7000;y=(low>>5)&31
  if y==29:low=(low&~0x3e0)^0x800
  elif y==31:low&=~0x3e0
  else:low+=32
 return (v&~32767)|low

def blocks(arrays,meta,raw):
 """Keep existing577 record choices. Remove tag/gen/index reinterpretation.

 One3B header=(mode<<3)|kind,count16LE, then literal/repeat/linear bytes.
 No coalescing or additional query/lookahead is credited.
 """
 cursors=[0]*7;out=[]
 for q in meta+raw:
  tag=int.from_bytes(q[:2],'big');k,idx=tag>>13,tag&8191;v=int.from_bytes(q[4:],'big');mode=0;n=1
  if k==7:
   if 0x1000<=idx<0x1700:
    k=6;n=v>>60
    if not n:mode=1;n=v>>6;v&=63
   elif idx&0x1f00==0x1c00:k=4;mode=2;n=(idx&255)+1
   else:
    k=(idx>>8)&7;n=(idx&255)+1;mode=1 if idx&0x1800==0x800 else 0
  assert 1<=k<=6 and 0<n<=256
  at=cursors[k];values=arrays[k][at:at+n];assert len(values)==n
  if mode:
   rebuilt=[v]
   for i in range(1,n):rebuilt.append(raster_next(rebuilt[-1])if mode==2 else v)
   assert rebuilt==values
   body=v.to_bytes(WIDTH[k],'little')
  else:body=b''.join(x.to_bytes(WIDTH[k],'little')for x in values)
  out.append(bytes([(mode<<3)|k])+n.to_bytes(2,'little')+body);cursors[k]+=n
 assert cursors[1:]==list(map(len,arrays))[1:]
 return out

def restore(bs,counts):
 out=[[]for _ in range(7)]
 for b in bs:
  k=b[0]&7;mode=b[0]>>3;n=int.from_bytes(b[1:3],'little')
  assert len(b)>=3 and 1<=k<=6 and mode<=2 and 0<n<=256 and len(out[k])+n<=counts[k]
  assert all(len(out[j])==counts[j] for j in range(1,k))
  assert mode!=2 or (k==4 and n>=2)
  assert mode!=1 or (k not in (1,5) and n>=(10 if k==6 else 2))
  w=WIDTH[k];assert len(b)==3+w*(n if mode==0 else 1)
  if mode==0:vals=[int.from_bytes(b[3+i*w:3+(i+1)*w],'little')for i in range(n)]
  else:
   vals=[int.from_bytes(b[3:3+w],'little')]
   for i in range(1,n):vals.append(raster_next(vals[-1])if mode==2 else vals[-1])
  for v in vals:
   assert v<1<<(0,8,49,32,53,6,6)[k]
   if k==1:assert v>>3<counts[0]//33
   if k==3:assert (v>>6)&8191<7392
   if k==4:
    if v>>49&1:assert not(v&((1<<49)-1)) and (v>>50)&7<counts[6]//256
    else:assert not(v>>49) and (v>>44)&31<counts[5]//32
  out[k]+=vals
 assert list(map(len,out))[1:]==counts[1:];return out

def check_rejects(bs,counts):
 tests={ 'missing_tail':bs[:-1], 'duplicate_tail':bs+[bs[-1]], 'raw_before_geometry':[bs[-1]]+bs[:-1],
         'section_zero':[bytes([0])+bs[0][1:]]+bs[1:],'reserved_mode':[bytes([0xf9])+bs[0][1:]]+bs[1:],
         'count_zero':[bs[0][:1]+bytes(2)+bs[0][3:]]+bs[1:],'truncated_literal':[bs[0][:-1]]+bs[1:] }
 tests['invalid_row_group']=[bs[0][:3]+b'\xff'+bs[0][4:]]+bs[1:]
 for name,seq in tests.items():
  try:restore(seq,counts)
  except AssertionError:continue
  raise AssertionError('accepted '+name)
 return list(tests)

def required(arrays):
 tags={}
 for k,usage in ((0,1),(2,2),(3,1)):
  for v in arrays[k]:
   t=(v>>19 if k==3 else v)&8191;tags[t]=tags.get(t,0)|usage
 assert len(tags)<=512
 return sorted(tags.items())

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('arm','archive','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 prior=json.loads((ROOT/'analysis/roles591-verification.json').read_text())
 assert sha(a.arm/'obj-nes-100/sd2snes.elf')==prior['linked_cost']['591']['ELF_sha256']
 assert sha(a.arm/'nes_native165.c')==prior['pins']['source_sha256']
 m=Profile(a.arm);frames=[];wire=[];guards=[];tag_count=0
 with zipfile.ZipFile(a.archive)as z:
  assert sha(a.archive)==prior['pins']['archive_sha256']
  for g in range(905,958):
   geom,raw=[z.read(f'data/frame{g}.{ext}')for ext in ('geometry','raw')]
   m.setup(geom,raw,g);r=m.measured();frames.append(r)
   assert r['instructions']==next(x['instructions']for x in prior['frames']if x['generation']==g)
   arrays=encode(geom,raw,g)[2]+[list(raw)];old,_,_=legacy_packets(geom,raw,g);meta,rawrec,_=old_nonmap(old)
   bs=blocks(arrays,meta,rawrec);counts=list(map(len,arrays));recovered=[arrays[0]]+restore(bs,counts)[1:];assert recovered==arrays
   map_crc=crc(canonical([arrays[0]]));nonmap=canonical(recovered)[2*counts[0]:]
   assert binascii.crc_hqx(nonmap,map_crc)==crc(canonical(arrays))
   tags=required(recovered);nt=m.get('ntiles',2);base=m.state+m.layout['nes_native165']['tiles']
   actual=[struct.unpack('<HB',bytes(m.u.mem_read(base+4*i,3)))for i in range(nt)]
   assert actual==tags;tag_count+=nt
   if g==905:guards=check_rejects(bs,counts)
   oldps=phase_packets(2,meta+[bytes(8)])+phase_packets(3,rawrec+[bytes(8)])
   newps=phase_packets(2,[b for b in bs if b[0]&7!=6]+[bytes(8)])+phase_packets(3,[b for b in bs if b[0]&7==6]+[bytes(8)])
   wire.append(dict(generation=g,old_nonmap_B=sum(map(len,meta+rawrec)),new_nonmap_B=sum(map(len,bs)),
                    old_packets=len(oldps),new_packets=len(newps),old_packet_B=sum(map(len,oldps)),new_packet_B=sum(map(len,newps))))
 groups={}
 for name,selected in [('cold905',frames[:1]),('warm907_957',frames[2:]),('dense951_955',[r for r in frames if 951<=r['generation']<=955])]:
  keys=set().union(*(r['exclusive_instructions']for r in selected));entries=set().union(*(r['function_entries']for r in selected))
  groups[name]=dict(instructions=mean(r['instructions']for r in selected),exclusive={k:mean(r['exclusive_instructions'].get(k,0)for r in selected)for k in sorted(keys)},entries={k:mean(r['function_entries'].get(k,0)for r in selected)for k in sorted(entries)})
 package={n:m.symbols[n][1]for n in PACKAGE};assert sum(package.values())==4796
 budgets={};driver=json.loads((ROOT/'analysis/whole580-verification.json').read_text())['phases'][0]['parameters']['driver_extra_us']
 for name,lo,hi in [('cold905',905,905),('warm907_957',907,957),('dense951_955',951,955)]:
  ws=[w for w in wire if lo<=w['generation']<=hi];delta=mean(w['new_packets']-w['old_packets']for w in ws)
  body=mean(w['new_packet_B']-w['old_packet_B']for w in ws)
  io=prior['groups'][name]['591']['IO_ms']+(body+19*delta)*8/2625000*1000+delta*sum(driver[k]for k in ('0xd0','0xd1','0xd2'))/1000
  budgets[name]=dict(nonmap_payload_delta_B=body,packet_delta=delta,conditional_IO_ms=io,
   scope='Only changed D1 bytes/packet count; retain every D4 roundtrip, D0 phase barrier and all other591 costs. No producer or decoder time credited.')
 cold=groups['cold905']['exclusive'];region=sum(cold[k]for k in ('logical_record/map','canonical591/map','crc16/map_rescan'))
 budgets['cold_limits']={}
 for cpi in (1,2):
  old=prior['groups']['cold905']['577'][f'CPI{cpi}_input_ms'];i=groups['cold905']['instructions']
  for key,io in [('unchanged591wire',prior['groups']['cold905']['591']['IO_ms']),('typed_reference',budgets['cold905']['conditional_IO_ms'])]:
   required_cut=math.ceil(i-(old-io)*84000/cpi)
   budgets['cold_limits'][key+f'_CPI{cpi}']=dict(required_instruction_cut=required_cut,
    measured_disjoint_map_region=region,new_map_region_limit_if_other_work_unchanged=region-required_cut,
    per_word_limit=(region-required_cut)/957,final_display_timing_measured=False)
 report=dict(stage=592,passed=True,frames=frames,groups=groups,wire=wire,static_attribution_B=dict(m.static),time_budgets=budgets,
  replacement=dict(measured_functions_B=package,total_old_envelope_B=sum(package.values()),required_net_reduction_B=1768,
                   new_envelope_ceiling_B=sum(package.values())-1768,packet_only_ceiling_B=m.symbols['nes_native165_packet'][1]-1768,
                   actual_deleted_B=0,new_code_cost_B=None),
  typed_reference=dict(reconstructions=53,seeded_CRC_equals_full=53,required_tag_pairs_compared=tag_count,negative_cases=guards,
   STOP_final_ACK='Retain591 checks and publication boundaries; not newly executed in a replacement binary'),
  envelope_allocation_caps_B=dict(body_and_phase=1434,semantic_and_completion=622,request_poll_prepare=972,
                                 scope='Design caps only;1434=577 packet;972 reserves actual591 D4 320 +577 poll/prepare652;622 residual.'),
  new_firmware=False,new_RTL=False,new_MAP=False,new_full_timeline=False,
  scope=__doc__,pins=dict(ELF_sha256=sha(a.arm/'obj-nes-100/sd2snes.elf'),source_sha256=sha(a.arm/'nes_native165.c'),
   archive_sha256=sha(a.archive),profiler_sha256=sha(Path(__file__)),receiver_test_sha256=sha(ROOT/'tools/check_nes_roles591.py')),
  limits=['DWARF code ownership and exclusive instruction counts are not net deletion or cycles.',
          'Typed nonmap reconstruction and CRC rollback are reference only; source/query/CDC/parser are not implemented.',
          'Map publication must wait for freshCRC; fusion needs provisional required tags and rollback, not immediate plan exposure.'])
 (a.out/'result.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
 print(json.dumps(dict(replacement=report['replacement'],static=report['static_attribution_B'],groups=groups),indent=2))

if __name__=='__main__':main()
