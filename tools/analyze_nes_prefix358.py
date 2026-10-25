# SPDX-License-Identifier: MIT
"""Actual unchanged M4 source decoder prefix closure; no speculative ROM permission or new scheduled run."""
import argparse,binascii,csv,json,struct
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ARM
from probe_nes_decode280 import records,chunks,golden

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();d=a.out;d.mkdir(parents=True,exist_ok=False)
 src=BASE/'probes/nes-raster355/fixed01';elf=src/'source-ARM-decoder.elf';arm=ARM(elf,None);arm.call('reset280',[])
 pins={str(elf):sha(elf)};out=[]
 events={}
 for mode in ('fixed01','window01'):
  p=BASE/'probes/nes-raster355'/mode/'joint-events.csv';pins[str(p)]=sha(p);events[mode]=list(csv.reader(p.read_text().splitlines()))
 for frame in (905,906,907):
  p=src/f'frame{frame}.records';pins[str(p)]=sha(p)
  for suffix in ('expected','records'):
   truth=BASE/'probes/nes-joint278/test07'/f'frame{frame}.{suffix}';pins[str(truth)]=sha(truth)
  geom,raw=golden(frame);blocks=chunks(records(p));prior_history=bytes(arm.uc.mem_read(0x20010000,4910))
  for i,b in enumerate(blocks):
   before=arm.instructions;arm.uc.mem_write(0x20018000,b)
   assert arm.call('block280',[0x20010000,0x20018000,len(b),binascii.crc_hqx(b,65535)])==1
   instructions=arm.instructions-before;s=bytes(arm.uc.mem_read(arm.symbols['receiver280'],28));last=struct.unpack_from('<h',s,18)[0];phase=s[21];valid=s[20]
   closed=67 if phase==2 or valid else last
   history=bytes(arm.uc.mem_read(0x20010000,4910))
   end=0 if closed<0 else (closed+1)*66 if closed<32 else min(4398,2112+(closed-31)*64)
   assert history[:end]==geom[:end],(frame,i,closed)
   row=dict(frame=frame,packet=i,bytes=len(b),instructions=instructions,last=last,phase=phase,valid=valid,closed_through_block=closed,map_tags_closed=closed>=31,rows_closed=closed>=35,exceptions_closed=closed>=59,raster_and_counts_closed=closed>=67,timing={})
   for mode,ev in events.items():
    e=[x for x in ev if x[1]==str(frame)];start=int(next(x[2] for x in e if x[0]=='start319'))
    dec=[x for x in e if x[0]=='input_decode337'];assert len(dec)==len(blocks)
    assert int(dec[i][3])==instructions
    row['timing'][mode]=(int(dec[i][-1])-start)/1e9+instructions/84000
   if closed>=59:
    pool={v[0]&8191 for v in struct.iter_unpack('<H',history[:2112])}
    pool|={v[0]>>19 for v in struct.iter_unpack('<I',history[3360:3872])}
    row['unfiltered_map_exception_tag_pool']=sorted(pool)
    changed_rows=[];changed_tags=set()
    for y in range(224):
     group=history[2112+y]>>3
     if group<32 and (history[2112+y]!=prior_history[2112+y] or history[group*66:(group+1)*66]!=prior_history[group*66:(group+1)*66]):
      changed_rows.append(y);changed_tags|={v[0]&8191 for v in struct.iter_unpack('<H',history[group*66:(group+1)*66])}
    row['changed_row_prefix_rows']=changed_rows;row['changed_row_prefix_tags']=sorted(changed_tags)
    affected=set(changed_rows);changed_exception_tags=set()
    for off in range(3360,3872,4):
     if history[off:off+4]!=prior_history[off:off+4]:
      ex=struct.unpack_from('<I',history,off)[0];y=((ex>>6)&8191)//33
      if y<224:affected.add(y);changed_exception_tags.add(ex>>19)
    for y in range(min(224,max(0,(end-3872)//2))):
     if history[3872+2*y:3874+2*y]!=prior_history[3872+2*y:3874+2*y]:affected.add(y)
    joint_tags=set(changed_exception_tags)
    for y in affected:
     group=history[2112+y]>>3
     if group<32:joint_tags|={v[0]&8191 for v in struct.iter_unpack('<H',history[group*66:(group+1)*66])}
    row['changed_semantic_prefix_rows']=sorted(affected);row['changed_semantic_prefix_tags']=sorted(joint_tags)
   if end>=3888:
    first_rows=set()
    for y in range(8):
     raster=struct.unpack_from('<H',history,3872+y*2)[0]
     if raster&1024:continue
     group=history[2112+y]>>3
     assert group<32
     first_rows|={v[0]&8191 for v in struct.iter_unpack('<H',history[group*66:(group+1)*66])}
    for (ex,) in struct.iter_unpack('<I',history[3360:3872]):
     if ((ex>>6)&8191)//33<8:first_rows.add(ex>>19)
    row['first_eight_rows_tag_pool']=sorted(first_rows)
   out.append(row)
  assert history==geom+raw and arm.call('complete280',[])==1
 warm=[r for r in out if r['frame']==907];first=next(r for r in warm if r['map_tags_closed']);full=next(r for r in warm if r['raster_and_counts_closed'])
 bound=json.loads((ROOT/'analysis/arch357-verification.json').read_text())['time_budget']['continuous_previous_window_end_upper_ms']
 p=src/'actual-plans293-907.bin';pins[str(p)]=sha(p);data=p.read_bytes();at=0;batches=[];all_tags=set()
 while at<len(data):
  length,count=struct.unpack_from('<HB',data,at);at+=3;end=at+length;tags=set();kinds=[]
  for _ in range(count):
   op=data[at];kind=op&3;kinds.append(kind)
   n=(7 if op==128 else 8 if op==129 else 3) if op&128 else 16+2*data[at+1].bit_count()
   if kind==0:
    tags.add(struct.unpack_from('<H',data,at+(5 if op&128 else 6))[0])
    if not op&128:
     for j in range((n-16)//2):tags.add(struct.unpack_from('<H',data,at+16+2*j)[0])
   at+=n
  assert at==end;batches.append(dict(tags=sorted(tags),kinds=kinds));all_tags|=tags
 cache=src/'nes_chr_cache192.sv';pins[str(cache)]=sha(cache);assert 'bytes[0:15]' in cache.read_text()
 assert all_tags.issubset(set(first['unfiltered_map_exception_tag_pool']))
 prefetch=dict(actual_warm_BG_unique_tags=len(all_tags),first_BG_batch_unique_tags=len(next(x['tags'] for x in batches if x['tags'])),changed_row_prefix_tags=len(first['changed_row_prefix_tags']),actual_BG_tags_in_changed_row_pool=len(all_tags&set(first['changed_row_prefix_tags'])),early_first_eight_rows_tag_pool=len(first['first_eight_rows_tag_pool']),actual_BG_tags_in_first_eight_pool=len(all_tags&set(first['first_eight_rows_tag_pool'])),early_unfiltered_tag_pool=len(first['unfiltered_map_exception_tag_pool']),early_pool_storage_bytes=16*len(first['unfiltered_map_exception_tag_pool']),existing_cache_tiles=1,existing_cache_bytes=16,oracle_all_BG_tile_storage_bytes=16*len(all_tags),oracle_tag_wire_floor_ms=2*len(all_tags)*8/2625,
 limits='Oracle final plan tags are analysis only, not available early ARM state. Existing single-tile cache overwrites on next tag; warming one tile does not keep later BG misses out of the blocked ROM interval. Whole-prefetch bytes are a storage scenario, not allocated RAM or a proof all tags are needed simultaneously.')
 prefetch['changed_semantic_prefix_tags']=len(first['changed_semantic_prefix_tags']);prefetch['actual_BG_tags_in_semantic_pool']=len(all_tags&set(first['changed_semantic_prefix_tags']))
 result=dict(passed=True,rows=out,warm_first_tag_prefix=first,warm_full_geometry_prefix=full,cache_prefetch=prefetch,continuous_window_upper_ms=bound,tag_only_remaining_budget_ms=bound-first['timing']['window01'],full_geometry_misses_window=full['timing']['window01']>bound,
 limits='Existing block CRC and sorted-record closure checked on actual ARM decoder; final source CRC/semantic/planner/display remain required. Tag-only raw CHR cache prefetch is a candidate, not actual E9 plan/converted tile. No new ROM reads, ARM prefetch cost or cache/lease/queue area measured.',pins=pins)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('rows','pins')},indent=2))
if __name__=='__main__':main()
