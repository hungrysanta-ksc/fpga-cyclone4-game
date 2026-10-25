# SPDX-License-Identifier: MIT
import argparse,binascii,csv,json,inspect,struct
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_prefetch359 import decoder
import probe_nes_decode280 as old
from probe_nes_arm264 import ARM

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 s=inspect.getsource(old.build).replace("shutil.copyfile(ROOT/'tools/nes_decode280.c',d/'nes_decode280.c')","(d/'nes_decode280.c').write_text(decoder(),newline='\\n')")
 ns=dict(old.__dict__);ns['decoder']=decoder;exec(compile(s,__file__,'exec'),ns);ns['build'](d)
 arm=ARM(d/'decoder.elf',None);arm.call('reset280',[]);rows=[];displayed_epoch=0;displayed_serial=0
 costs=list(csv.DictReader((BASE/'probes/nes-raw352/decoder01/blocks.csv').read_text().splitlines()));ci=0
 for f in range(905,976):
  rr=old.records(BASE/'probes/nes-raw352/decoder01'/f'frame{f}.records');bb=old.chunks(rr);packets=[];extra=0;filter_cost=0;all_before=arm.instructions
  for i,b in enumerate(bb):
   arm.uc.mem_write(0x20018000,b);before=arm.instructions
   assert arm.call('block280',[0x20010000,0x20018000,len(b),binascii.crc_hqx(b,65535)])==1
   decode=arm.instructions-before;ref=costs[ci];ci+=1;assert int(ref['frame'])==f and int(ref['block'])==i
   extra+=decode-int(ref['instructions']);before=arm.instructions;n=arm.call('prefetch359',[0x20010000,displayed_epoch,displayed_serial]);fc=arm.instructions-before;filter_cost+=fc
   if n:
    packet=bytes(arm.uc.mem_read(arm.symbols['packet359'],n));assert n==14+2*packet[1] and packet[1]<=17
    assert binascii.crc_hqx(packet[:-2],65535)==int.from_bytes(packet[-2:],'little')
    (d/f'prefetch{f}.bin').write_bytes(packet);packets.append(dict(block=i,decode_extra=decode-int(ref['instructions']),filter_instructions=fc,decode_instructions=decode,length=n,tags=list(struct.unpack('<'+'H'*packet[1],packet[12:-2]))))
  geom,raw=old.golden(f);assert bytes(arm.uc.mem_read(0x20010000,4910))==geom+raw and arm.call('complete280',[])==1
  displayed_epoch=1;displayed_serial=f-904
  rows.append(dict(frame=f,decode_extra=extra,filter_instructions=filter_cost,total_instructions=arm.instructions-all_before,packets=packets))
 assert not rows[0]['packets'] and not rows[1]['packets']
 guards=[]
 for kind in ('stale_epoch','stale_serial','STOP_reset','overflow'):
  g=ARM(d/'decoder.elf',None);g.call('reset280',[])
  for f in (905,906,907):
   bb=old.chunks(old.records(BASE/'probes/nes-raw352/decoder01'/f'frame{f}.records'))
   for b in (bb[:1] if f==907 else bb):
    g.uc.mem_write(0x20018000,b);assert g.call('block280',[0x20010000,0x20018000,len(b),binascii.crc_hqx(b,65535)])==1
  if kind=='STOP_reset':g.call('reset280',[]);assert g.call('prefetch359',[0x20010000,1,2])==0
  elif kind=='overflow':
   # Every row refers to group0; changed exceptions then select >17 tags.
   g.uc.mem_write(0x20010000+2112,bytes(224));g.uc.mem_write(0x20010000,b''.join(struct.pack('<H',i) for i in range(33)))
   assert g.call('prefetch359',[0x20010000,1,2])==0
  else:
   assert g.call('prefetch359',[0x20010000,999 if kind=='stale_epoch' else 1,1 if kind=='stale_serial' else 2])==0
   assert g.call('prefetch359',[0x20010000,1,2])==48
   assert g.call('prefetch359',[0x20010000,1,2])==0
  guards.append(kind)
 result=dict(passed=True,frames=rows,guards=guards,text_size=(d/'size.log').read_text(),stack_observed=0x2003f000-arm.low_sp,ELF_sha256=sha(d/'decoder.elf'),C_sha256=sha(d/'nes_decode280.c'),scope='Actual CortexM4 source decode+change tracking+bounded17tag filter and48B CRC packet. No integrated SPI/ROM or display permission. Failed/overflow speculation emits no packet; source decode unchanged.')
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(dict(warm907=rows[2],frames=len(rows),size=result['text_size'],stack=result['stack_observed']),indent=2))
if __name__=='__main__':main()
