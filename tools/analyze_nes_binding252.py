# SPDX-License-Identifier: MIT
"""Recorded sparse HDMA inheritance audit and fresh-certificate policy model.

C planner certificate is executed. Receiver, refreshed packets and schedules
are Python policies, not an FPGA/SNES implementation or full ARM RUN.
"""
from pathlib import Path
from collections import defaultdict
import argparse,binascii,csv,ctypes,json,shutil,struct,subprocess
from nes_delta231 import BASE,ROOT,sha
from probe_nes_hdma251 import WRAPPER,oracle

def crc(b):return binascii.crc_hqx(b,0xffff)
def u16(b,i):return int.from_bytes(b[i:i+2],'little')
def active(b,raw):
 n=next(i+1 for i in range(0,1121,5) if b[i]==0);r=[(0,n)]
 if raw:r += [(3169,u16(b,3412)),(3250,u16(b,3414)),(3331,u16(b,3416)),(3412,6)]
 return r
def canonical(b,rr):return b''.join(b[a:a+n] for a,n in rr)

def shadow_receive(cert,scroll,hashes,context,all_consumed=True,stopped=False):
 if len(cert)!=32 or cert[:3]!=b'H2\x02' or cert[21] or crc(cert[:30])!=u16(cert,30) or stopped or not all_consumed:raise ValueError('shadow envelope')
 identity=(int.from_bytes(cert[4:8],'little'),int.from_bytes(cert[8:12],'little'),u16(cert,12),cert[3],int.from_bytes(cert[26:30],'little'))
 if identity!=context or len(scroll)!=u16(cert,14) or not 1<=len(scroll)<=1121 or cert[19] not in (0x18,0x1e) or cert[20]>7:raise ValueError('shadow identity/length')
 raw=cert[20]!=0
 if raw and (len(hashes)!=16 or any(x is None for x in hashes) or any(not 1<=n<=81 for n in cert[16:19])):raise ValueError('uninitialized shadow')
 if not raw and any(cert[16:19]):raise ValueError('normal shadow')
 b=scroll+(b''.join(struct.pack('<H',h) for h in hashes) if raw else b'')
 if u16(cert,24)!=len(scroll)+(249 if raw else 0) or crc(b)!=u16(cert,22):raise ValueError('shadow digest')
 return True

def receive(cert,parts,context,all_consumed=True,stopped=False):
 # Exact-order fresh active ranges. These are consumed bytes, not a snapshot
 # of SPI writes. There is no inherited-byte bypass in this candidate.
 if stopped or not all_consumed or len(cert)!=32 or cert[:3]!=b'H2\x01' or cert[21] or crc(cert[:30])!=u16(cert,30):raise ValueError('envelope')
 identity=(int.from_bytes(cert[4:8],'little'),int.from_bytes(cert[8:12],'little'),u16(cert,12),cert[3],int.from_bytes(cert[26:30],'little'))
 if identity!=context or cert[3]>1 or not identity[0] or not 0<identity[1]<0xffffffff or identity[4]>=identity[1] or cert[3]!=(identity[1]-1)%2:raise ValueError('identity')
 n=u16(cert,14)
 if not 1<=n<=1121 or cert[19] not in (0x18,0x1e) or cert[20]>7:raise ValueError('bounds')
 rr=[(0,n)]
 if cert[20]:
  if any(not 1<=x<=81 for x in cert[16:19]):raise ValueError('table bounds')
  rr += [(3169,cert[16]),(3250,cert[17]),(3331,cert[18]),(3412,6)]
 elif any(cert[16:19]):raise ValueError('normal lengths')
 if [(a,len(b)) for a,b in parts]!=rr:raise ValueError('receipt')
 data=b''.join(b for a,b in parts)
 if len(data)!=u16(cert,24) or crc(data)!=u16(cert,22):raise ValueError('content')
 return True

def dense_packets(missing,b):
 # Existing raw dirty granule is relative to1121, not global offset0.
 groups=sorted({(i-1121)//16 for i in missing});runs=[]
 for g in groups:
  if runs and g==runs[-1][1] and runs[-1][1]-runs[-1][0]<15:runs[-1][1]+=1
  else:runs.append([g,g+1])
 cost=0;payload=0
 for a,z in runs:
  at=1121+16*a;n=min(3418,1121+16*z)-at;v=b[at:at+n];payload+=n
  compressed=n>=4 and n%2==0 and v==v[:2]*(n//2)
  cost+=19+(2 if compressed else n)
 return cost,payload,len(runs)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True);pins={}
 def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
 def run(exe,args,label):
  q=subprocess.run([str(exe),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);(d/(label+'.log')).write_bytes(q.stdout);assert q.returncode==0,q.stdout.decode(errors='replace')[-4000:];return q.stdout.decode(errors='replace')
 for n in ('nes_native165.h','nes_native_video165.h'):shutil.copyfile(pin(BASE/'probes/nes-runtime233/arm01/src'/n),d/n)
 for n in ('nes_hdma251.c','nes_hdmabind252.c'):shutil.copyfile(pin(ROOT/'tools'/n),d/n)
 wrapper=WRAPPER+'''
bool nes_hdmabind252_prepare(const struct nes_native_video165 *,uint32_t,uint32_t,uint32_t,uint8_t,uint8_t *);
bool nes_hdmabind252_shadow(const struct nes_native_video165 *,uint32_t,uint32_t,uint32_t,uint8_t,uint8_t *);
__declspec(dllexport) int cert252(const unsigned char *b,unsigned mask,unsigned raw,unsigned size,unsigned epoch,unsigned serial,unsigned generation,unsigned base,unsigned bank,unsigned shadow,unsigned char *out){
 struct nes_native_video165 p;memset(&p,0,sizeof p);p.valid=true;p.generation=generation;
 memcpy(p.hdma,b,1121);memcpy(p.patch.mode[0],b+3169,81);memcpy(p.patch.mode[1],b+3250,81);memcpy(p.patch.enable,b+3331,81);
 for(unsigned i=0;i<3;i++)p.patch.size[i]=b[3412+i*2]|((unsigned)b[3413+i*2]<<8);
 p.display_mask=mask;p.patch_count=raw;p.hdma_size=size;
 return shadow?nes_hdmabind252_shadow(&p,epoch,serial,base,bank,out):nes_hdmabind252_prepare(&p,epoch,serial,base,bank,out);
}
'''
 (d/'wrapper.c').write_text(wrapper,newline='\n');shutil.copyfile(__file__,d/'analyzer.py')
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',['-std=c99','-O2','-Wall','-Wextra','-Werror','-shared','nes_hdma251.c','nes_hdmabind252.c','wrapper.c','-o','binding.dll'],'native')
 lib=ctypes.CDLL(str(d/'binding.dll'));f=lib.cert252;ptr=ctypes.POINTER(ctypes.c_ubyte);f.argtypes=[ptr]+[ctypes.c_uint]*9+[ptr];f.restype=ctypes.c_int
 prior=BASE/'probes/nes-wholepath247/jointdecode-test02/run';packets=defaultdict(list)
 for q in sorted(prior.glob('req-*.bin')):
  b=pin(q).read_bytes();packets[u16(b,8)].append(b)
 banks=[bytearray(3418),bytearray(3418)];shadows=[[None]*16 for _ in range(2)];rows=[];guards=0;shadow_guards=0;holes=0;negative=None
 def reject(cert,parts,ctx,**kw):
  nonlocal guards
  try:receive(cert,parts,ctx,**kw)
  except ValueError:guards+=1
  else:raise AssertionError('negative accepted')
 for g in range(1,72):
  bundle=pin(prior/f'expected-{g}.bin').read_bytes()[5152:];assert len(bundle)==3418
  bank=(g-1)%2;seal=next(b for b in packets[g] if b[0]==3);assert int.from_bytes(seal[4:8],'little')==g
  raw=u16(seal,38);mask=u16(seal,34);rr=active(bundle,raw);fresh=set();stage=banks[bank][:]
  for b in packets[g]:
   if b[1]!=5 or b[0] not in (2,4,5):continue
   at=u16(b,10);n=u16(b,12);data=b[16:];assert len(data)==n
   if b[0] in (4,5):data=data*(u16(b,14)//len(data))
   assert at+len(data)<=3418;stage[at:at+len(data)]=data;fresh.update(range(at,at+len(data)))
   for j in range(16):
    lo=3169+j*16;hi=min(3418,lo+16)
    if max(lo,at)<min(hi,at+len(data)):
     assert at<=lo and at+len(data)>=hi,'partial HDMA granule needs buffering'
     shadows[bank][j]=crc(data[lo-at:hi-at])
  assert canonical(stage,rr)==canonical(bundle,rr);banks[bank]=stage
  required={i for at,n in rr for i in range(at,at+n)};missing=required-fresh
  assert not (set(range(rr[0][1]))-fresh) # scroll is already sent every frame
  ctx=(1,g,g,bank,g-2 if g>2 else 0);cert=(ctypes.c_ubyte*32)()
  assert f((ctypes.c_ubyte*3418).from_buffer_copy(bundle),mask,raw,rr[0][1],1,g,g,ctx[4],bank,0,cert)
  cert=bytes(cert);parts=[(at,bundle[at:at+n]) for at,n in rr];assert receive(cert,parts,ctx)
  assert u16(cert,22)==crc(canonical(bundle,rr)) and oracle(bundle,mask,raw,rr[0][1])
  # A mutation in a retained active byte does not affect CRC of fresh writes.
  if missing:
   holes+=1;at=min(missing);bad=bytearray(stage);bad[at]^=1
   assert bytes(stage[i] for i in sorted(fresh))==bytes(bad[i] for i in sorted(fresh))
   assert crc(canonical(bad,rr))!=u16(cert,22)
   if negative is None:negative=dict(frame=g+904,retained_offset=at,fresh_digest_unchanged=True,active_digest_rejects=True)
  for at in range(32):
   z=bytearray(cert);z[at]^=1;reject(z,parts,ctx)
  for j,(at,data) in enumerate(parts):
   for i in range(len(data)):
    z=list(parts);v=bytearray(data);v[i]^=1;z[j]=(at,bytes(v));reject(cert,z,ctx)
  reject(cert,parts[:-1],ctx);reject(cert,parts+parts[-1:],ctx);reject(cert,list(reversed(parts)),ctx)
  reject(cert,parts,ctx,all_consumed=False);reject(cert,parts,ctx,stopped=True)
  for j in range(5):z=list(ctx);z[j]^=1;reject(cert,parts,tuple(z))
  sc=(ctypes.c_ubyte*32)();assert f((ctypes.c_ubyte*3418).from_buffer_copy(bundle),mask,raw,rr[0][1],1,g,g,ctx[4],bank,1,sc);sc=bytes(sc)
  assert shadow_receive(sc,bundle[:rr[0][1]],shadows[bank],ctx)
  assert shadows[bank]==[crc(bundle[3169+j*16:min(3418,3169+(j+1)*16)]) for j in range(16)]
  badcases=[]
  for j in range(16):
   h=list(shadows[bank]);h[j]^=1;badcases.append((sc,bundle[:rr[0][1]],h,ctx,{}))
   h=list(shadows[bank]);h[j]=None;badcases.append((sc,bundle[:rr[0][1]],h,ctx,{}))
  badcases += [(sc,bundle[:rr[0][1]],shadows[bank],ctx,dict(stopped=True)),(sc,bundle[:rr[0][1]],shadows[bank],ctx,dict(all_consumed=False))]
  for j in range(5):z=list(ctx);z[j]^=1;badcases.append((sc,bundle[:rr[0][1]],shadows[bank],tuple(z),{}))
  for c,s,h,ct,kw in badcases:
   try:shadow_receive(c,s,h,ct,**kw)
   except ValueError:shadow_guards+=1
   else:raise AssertionError('bad shadow accepted')
  dense,payload,count=dense_packets(missing,bundle)
  # Dedicated fresh receipt always supplies entire non-scroll active tables;
  # it needs new overwrite/receipt ownership (cannot reuse old duplicate rule).
  compact_payload=sum(n for at,n in rr[1:]);compact_desc=3*(len(rr)-1);compact_packets=(compact_payload+compact_desc+239)//240
  compact=compact_payload+compact_desc+19*compact_packets
  updated=len(fresh&set(range(3169,3418)));blocks=len({(i-3169)//16 for i in fresh if i>=3169})
  # Deliberately serial extra allocation:two CRC16 register contexts can use
  # one8-cycle-per-byte engine;RAM shadow writes and scan charged separately.
  shadowcycles=8*(updated+rr[0][1]+30+32)+2*blocks+32
  rows.append(dict(frame=g+904,active_bytes=len(required),fresh_active_bytes=len(required&fresh),inherited_active_bytes=len(missing),dense_added_wire_bytes=dense,dense_expanded_bytes=payload,dense_new_packets=count,compact_added_wire_bytes=compact,compact_payload_bytes=compact_payload,compact_descriptors=compact_desc,compact_packets=compact_packets,shadow_updated_bytes=updated,shadow_updated_blocks=blocks,shadow_added_wire_bytes=0,shadow_extra_allocated_cycles=shadowcycles))
 # Directed normal mode and generation wrap are accepted; bad semantic table
 # and absent/corrupt context are rejected before certificate creation.
 b=bytearray(3418);b[0]=127;b[5]=97;cert=(ctypes.c_ubyte*32)()
 assert f((ctypes.c_ubyte*3418).from_buffer_copy(b),0x18,0,11,1,65536,0,65534,1,0,cert)
 assert receive(bytes(cert),[(0,bytes(b[:11]))],(1,65536,0,1,65534))
 b[5]=96;assert not f((ctypes.c_ubyte*3418).from_buffer_copy(b),0x18,0,11,1,65536,0,65534,1,0,cert)
 # Recorded warm frames inherit every active raw-tail byte. Exercise actual
 # one-granule updates too, including last9-byte granule and different tables.
 update_checks=0
 for j in (2,7,12,15):
  changed=bytearray(bundle);changed[3169+j*16]^=1 # unused padding;semantics unchanged
  out=(ctypes.c_ubyte*32)();assert f((ctypes.c_ubyte*3418).from_buffer_copy(changed),mask,raw,rr[0][1],1,73,73,71,0,1,out)
  oldhash=[crc(bundle[3169+k*16:min(3418,3169+(k+1)*16)]) for k in range(16)]
  try:shadow_receive(bytes(out),bytes(changed[:rr[0][1]]),oldhash,(1,73,73,0,71))
  except ValueError:update_checks+=1
  else:raise AssertionError('stale granule accepted')
  oldhash[j]=crc(changed[3169+j*16:min(3418,3169+(j+1)*16)])
  assert shadow_receive(bytes(out),bytes(changed[:rr[0][1]]),oldhash,(1,73,73,0,71));update_checks+=1
 # Common STOP/raw0 invalidates both shadow banks together with validity.
 invalid=[[None]*16 for _ in range(2)]
 for h in invalid:
  try:shadow_receive(sc,bundle[:rr[0][1]],h,ctx)
  except ValueError:update_checks+=1
  else:raise AssertionError('invalidated bank accepted')
 arm=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
 for n in ('nes_hdma251','nes_hdmabind252'):run(arm/'arm-none-eabi-gcc.exe',['-Os','-std=c99','-Wall','-Wextra','-Werror','-mthumb','-mcpu=cortex-m4','-mfloat-abi=hard','-fstack-usage','-c',n+'.c','-o',n+'.o'],n+'-compile')
 sizes=run(arm/'arm-none-eabi-size.exe',['nes_hdma251.o','nes_hdmabind252.o'],'size');run(arm/'arm-none-eabi-objdump.exe',['-dr','nes_hdmabind252.o'],'disassembly')
 stack={n:(d/(n+'.su')).read_text() for n in ('nes_hdma251','nes_hdmabind252')}
 old=json.loads(pin(BASE/'probes/nes-joint251/analysis02/result.json').read_text());byframe={r['frame']:r for r in rows};schedules=[]
 for r in old['rows']:
  if r['arm_cycles_allocated']!=32000 or r['extra_binding_bytes']!=32:continue
  for mode in ('dense','compact','shadow'):
   cost=byframe[r['frame']][mode+'_added_wire_bytes'];extra=byframe[r['frame']]['shadow_extra_allocated_cycles']/22000 if mode=='shadow' else 0;total=r['total_ms']+cost*8/2625+extra
   schedules.append(dict(frame=r['frame'],setup=r['setup'],retained_policy=r['retained_policy'],binding_policy=mode,added_wire_bytes=cost,FPGA_extra_allocated_ms=extra,total_ms=total,residual_ms=1000/60-total))
 summary=[]
 for setup in (500,1000):
  for retained in ('command_tail','only_bitmap_removed'):
   for mode in ('dense','compact','shadow'):
    rr=[r for r in schedules if (r['setup'],r['retained_policy'],r['binding_policy'])==(setup,retained,mode)]
    summary.append(dict(setup=setup,retained_policy=retained,binding_policy=mode,max_ms=max(r['total_ms'] for r in rr),residual_ms=min(r['residual_ms'] for r in rr),over=[r['frame'] for r in rr if r['residual_ms']<0]))
 for n in ('tools/analyze_nes_binding252.py','tools/nes_hdmabind252.c','tools/nes_block249_rtl.py','tools/nes_receipt250.py','tools/nes_phase251.py','tools/probe_nes_hdma251.py'):pin(ROOT/n)
 for n in ('nes_source_query235.sv','nes_source_spi235.sv'):pin(BASE/'probes/nes-source240/board01'/n)
 pin(BASE/'probes/nes-runtime233/arm01/src/nes_native_sink165.c')
 result=dict(passed=True,stage=252,scope=__doc__,frames=71,frames_with_inherited_active_HDMA=holes,first_fresh_only_counterexample=negative,receiver_policy_negative_cases=guards,shadow_policy_negative_cases=shadow_guards,shadow_update_and_invalidation_checks=update_checks,arm_size=sizes,stack_usage=stack,rows=rows,schedules=schedules,summaries=summary,input_hashes=pins,
  warm_inherited_bytes=[min(r['inherited_active_bytes'] for r in rows[2:]),max(r['inherited_active_bytes'] for r in rows[2:])],
  warm_dense_added_bytes=[min(r['dense_added_wire_bytes'] for r in rows[2:]),max(r['dense_added_wire_bytes'] for r in rows[2:])],
  shadow_ram_scenario=dict(granule=16,crc_bits=16,per_bank_entries=16,both_banks_bytes=64,validity_plus_receipt_bytes=754,sum_bytes=818,persistent_bytes=396,temp_bytes=422,source_start=512,not_implemented=True,scroll_shadow_needed=False),
  no_FPGA_implementation=True,no_SNES_execution=True,no_full_ARM_RUN=True,no_MCU_timing=True,no_MAP_FIT=True,
  limitations=['CRC16 is accidental-corruption checking,not cryptographic authentication or collision-free equality.',
  'Fresh-only digest counterexample is a model of a bad proposal,not a demonstrated production corruption.',
  'Dense refresh needs an updated expected receipt manifest;new packet service/CRC/retire latency is not charged.',
  'Compact refresh requires a new typed owner/overwrite policy;no implementation area or timing measured.',
  'Added wire serialized as conservative placement within old conditional schedule;not a re-executed packet scheduler.',
  '32-byte certificate and32000ARMcycle allocations retained;MCU time and full planner cost still unknown.',
  'Shadow table64B stores only249B raw-tail hashes;scroll is already fresh every frame. New RAM offsets/CRC arbitration are unimplemented.',
  'Shadow operation bound is an explicit serial cycle allocation,not executed RTL or reclaimed area.'])
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 public={k:v for k,v in result.items() if k not in ('input_hashes','rows','schedules')};public.update(input_count=len(pins),private_result_sha256=sha(d/'result.json'))
 (d/'summary.json').write_text(json.dumps(public,indent=2)+'\n',newline='\n')
 for name,rr in [('frames.csv',rows),('schedules.csv',schedules)]:
  with (d/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
 print(json.dumps(public,indent=2))
if __name__=='__main__':main()
