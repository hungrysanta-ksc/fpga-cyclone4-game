# SPDX-License-Identifier: MIT
"""Actual M4 bounded hint producer from PRE-input committed resident snapshots.

Source decoder stays352 (used by355); no future geometry or final plan is read
by the hint producer. Existing actual plan bytes are an evaluation oracle only.
"""
import argparse,binascii,csv,inspect,json,shutil,struct
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_hint360 import decoder
import probe_nes_decode280 as old
from probe_nes_arm264 import ARM,ELFFile
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--batch-size',type=int,choices=(2,5),default=2);a=ap.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 for p in (BASE/'probes/nes-raster355/fixed01').glob('*.h'):shutil.copyfile(p,d/p.name)
 s=inspect.getsource(old.build).replace("shutil.copyfile(ROOT/'tools/nes_decode280.c',d/'nes_decode280.c')","(d/'nes_decode280.c').write_text(decoder(),newline='\\n')")
 ns=dict(old.__dict__);ns['decoder']=lambda:decoder(a.batch_size);exec(compile(s,'arm360-build','exec'),ns);ns['build'](d)
 ref=ARM(a.source/'output.elf',None)
 with (a.source/'output.elf').open('rb') as fp:size=ELFFile(fp).get_section_by_name('.symtab').get_symbol_by_name('resident285')[0]['st_size']
 arm=ARM(d/'decoder.elf',None);arm.call('reset280',[]);rows=[];pins={};snap=None
 costs=list(csv.DictReader((BASE/'probes/nes-raw352/decoder01/blocks.csv').read_text().splitlines()));ci=0
 for f in (905,906,907):
  p=a.source/f'prior360-{f-904}.bin';data=p.read_bytes();pins[str(p)]=sha(p)
  offset=ref.symbols['resident285']-0x20000000;r=data[offset:offset+size];arm.uc.mem_write(0x20020000,r)
  packets=[];calls=[];decode_delta=0
  for i,b in enumerate(old.chunks(old.records(BASE/f'probes/nes-raw352/decoder01/frame{f}.records'))):
   arm.uc.mem_write(0x20018000,b);before=arm.instructions;assert arm.call('block280',[0x20010000,0x20018000,len(b),binascii.crc_hqx(b,65535)])==1
   cost=arm.instructions-before;row=costs[ci];ci+=1;assert int(row['frame'])==f and int(row['block'])==i;decode_delta+=cost-int(row['instructions'])
   if i:continue
   before=arm.instructions;arm.call('hint_reset360',[]);reset_cost=arm.instructions-before
   for j in range(70 if f==907 else 1):
    before=arm.instructions;n=arm.call('hint360',[0x20020000,1,f-905,1]);cost=arm.instructions-before
    packet=bytes(arm.uc.mem_read(arm.symbols['packet360'],n)) if n else b''
    calls.append(dict(call=j,instructions=cost,packet_bytes=n))
    if n:
     assert n==14+2*packet[1] and 1<=packet[1]<=a.batch_size and binascii.crc_hqx(packet[:-2],65535)==int.from_bytes(packet[-2:],'little')
     tags=list(struct.unpack('<'+'H'*packet[1],packet[12:-2]));packets.append(dict(call=j,tags=tags,bytes=n,hex=packet.hex()))
    if f==907 and j==0:
     snap=(bytes(arm.uc.mem_read(0x20000000,0x40000)),arm.uc.context_save())
    if int.from_bytes(arm.uc.mem_read(arm.symbols['hint_done360'],4),'little'):break
   assert bytes(arm.uc.mem_read(0x20020000,size))==r
  geom,raw=old.golden(f);assert bytes(arm.uc.mem_read(0x20010000,4910))==geom+raw and arm.call('complete280',[])==1
  rows.append(dict(frame=f,calls=calls,reset_instructions=reset_cost,packets=packets,source_decode_delta=decode_delta))
 assert not rows[0]['packets'] and not rows[1]['packets']
 assert [t for p in rows[2]['packets'] for t in p['tags']]==[6525,6424,6426,6425,6427]
 guards=[]
 for label,args in [('stale_epoch',[0x20020000,2,2,1]),('stale_serial',[0x20020000,1,1,1]),('mutable_ROM',[0x20020000,1,2,0]),('STOP',[0x20020000,1,2,1])]:
  arm.uc.mem_write(0x20000000,snap[0]);arm.uc.context_restore(snap[1]);arm.call('hint_reset360',[])
  if label=='STOP':arm.call('reset280',[])
  assert arm.call('hint360',args)==0;guards.append(label)
 for p in [d/'decoder.elf',d/'nes_decode280.c',ROOT/'tools/nes_hint360.py',ROOT/'tools/probe_nes_arm360.py',a.source/'output.elf']:pins[str(p)]=sha(p)
 result=dict(passed=True,batch_size=a.batch_size,rows=rows,guards=guards,size=(d/'size.log').read_text(),stack_observed=0x2003f000-arm.low_sp,pins=pins,scope=__doc__,live_SPI=False)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
