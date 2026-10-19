# SPDX-License-Identifier: MIT
"""Widen the replacement budget and falsify source-only area shortcuts.

No new source codec/receipt controller is synthesized by this analysis. Source
variants are independently decoded, and wire floors exclude polling/control.
"""
from pathlib import Path
import argparse,csv,inspect,json,re
from nes_delta231 import BASE,ROOT,sha
import nes_block249 as codec
from probe_nes_joint261 import packets


def hierarchy(path):
 rows={};inside=False
 for line in path.read_text().splitlines():
  if line.startswith('; Analysis & Synthesis Resource Utilization by Entity'):inside=True;continue
  if inside and line.startswith('; Analysis & Synthesis Resource Usage Summary'):break
  f=[s.strip() for s in line.split(';')]
  if inside and len(f)>10 and re.match(r'\d+ \(',f[2]):
   rows[f[1]]={k:int(re.match(r'\d+',v).group()) for k,v in zip(['comb','FF','RAM_bits'],f[2:5])}
   rows[f[1]]['own_comb']=int(re.search(r'\((\d+)\)',f[2]).group(1))
 return rows


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
 old=BASE/'probes/nes-joint268';h=hierarchy(old/'board01/output_files/board.map.rpt')
 # These six rows do not overlap. flow uses ONLY the exclusive parent count;
 # its queue, aperture, tiles and mailboxes are not counted a second time.
 blocks={n:h[n]['comb'] for n in ['|nes_core257:encoder|','|nes_transport257:transport|','|nes_queue260:queue|','|nes_plan_spi200:endpoint|','|nes_plan_batch206:transport|']}
 blocks['|nes_output260:flow| exclusive']=h['|nes_output260:flow|']['own_comb']
 region=sum(blocks.values());assert region==6494
 prior={int(r['frame']):r for r in csv.DictReader((ROOT/'analysis/joint268-costs.csv').open())}
 e1={f:0 for f in prior}
 for e in csv.reader((old/'joint-reuse01/joint-events.csv').open()):
  if e[0]=='arm267' and int(e[2])==0xe1:e1[int(e[1])]+=int(e[3])
 ns=dict(codec.__dict__);s=inspect.getsource(codec.encode).replace('if not cold and index<32','if False and index<32');exec(compile(s,'mask-only269','exec'),ns);mask_encode=ns['encode']
 previous=bytes(4398);rows=[];pins={};checks=0
 for f in range(905,976):
  path=old/f'joint-reuse01/frame{f}.records';pins[str(path.relative_to(BASE))]=sha(path)
  records=[]
  for line in path.read_text().splitlines():
   n,b=line.split();b=bytes.fromhex(b);assert len(b)==int(n);records.append(b)
  serial=f-904;generation=int.from_bytes(records[0][16:18],'little')
  new,raw=codec.decode(records,previous,serial,generation)
  masks=mask_encode(previous,new,raw,serial,generation);assert codec.decode(masks,previous,serial,generation)==(new,raw);checks+=len(new)+len(raw)
  original=sum(map(len,records));mask_bytes=sum(map(len,masks));r=prior[f]
  # Minimum full literal payload ignores framing/CRC/status and is deliberately
  # optimistic. It must still transport the same4398 canonical bytes and RAW.
  literal_floor=4398+len(raw)
  output_wire=int(r['SPI_bytes']);source_wire=int(r['source_SPI_bytes'])
  wire=float(r['shared_SPI_wire_ms']);added=mask_bytes-original
  pp=packets(BASE/f'probes/nes-joint264/arm01/frame{f}.packets')
  # 9B includes the phase flags. Full24B snapshots are still necessary for
  # token, bank, generation, range and tile identity; count one per tile plus
  # first map. Extra reads can cause additional E8 refill/poll work in reality.
  full_reads=sum(p[0]==7 for p in pp)+int(any(p[0]==9 and p[1]==2 for p in pp))
  rows.append(dict(frame=f,raw_bytes=len(raw),source_payload=original,mask_payload=mask_bytes,added_mask_payload=added,
   same_poll_mask_wire_floor_ms=wire+added*8/2625,
   literal_plus_output_wire_floor_ms=(literal_floor+output_wire)*8/2625,
   literal_plus_E1_only_wire_floor_ms=(literal_floor+e1[f])*8/2625,
   source_wire_ms=source_wire*8/2625,source_nonwire_ceiling_ms=float(r['source_ms'])-source_wire*8/2625,
   E0_polls=int(r['E0_polls']),extra_full_status_reads=full_reads,
   short9_plus_full24_frozen_saving_B=int(r['E0_polls'])*15-full_reads*24,
   short9_plus_full24_frozen_saving_ms=(int(r['E0_polls'])*15-full_reads*24)*8/2625,
   short9_frozen_net_after_extra_transfer_setup_ms=(int(r['E0_polls'])*15-full_reads*24)*8/2625-full_reads*.008,
   frontend_frozen_saving_ms=int(r['shared_envelope_frozen_transcript_wire_saving_B'])*8/2625))
  previous=new
 with (d/'source-candidates.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 result=dict(passed=True,scope=__doc__,boundary=blocks,region_comb=region,comb_deficit=2271,
  replacement_max_comb_without_margin=region-2271,required_net_reduction_percent=2271/region*100,
  whole_joint_and_plan_region=h['|nes_joint267_board:native_joint267|']['comb']+856,
  frames=71,decoded_bytes_checked=checks,worst954=rows[49],
  warm_mask_same_poll_floor_over=sum(r['same_poll_mask_wire_floor_ms']>1000/60 for r in rows[2:]),
  warm_literal_output_floor_over=sum(r['literal_plus_output_wire_floor_ms']>1000/60 for r in rows[2:]),
  warm_literal_E1_only_floor_over=sum(r['literal_plus_E1_only_wire_floor_ms']>1000/60 for r in rows[2:]),
  source_receipt_new_RTL=False,new_replacement_MAP=False,net_reclaim_proven=0,
  compact_status_implemented=False,frozen_poll_projection_is_timing=False,
  pins=pins,script_sha256=sha(Path(__file__)))
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('pins','scope')}))


if __name__=='__main__':main()
