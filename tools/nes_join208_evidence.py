# SPDX-License-Identifier: MIT
"""Check live208 bus files, real display ACKs, reference tiles and prior archives."""
from pathlib import Path
import argparse,json
from nes_board204 import ROOT,BASE,sha
from nes_bulk194_evidence import verify_archive

FILES=['tools/test_nes_join208.py','tools/nes_join208_evidence.py',
 'tests/nes-functional/join208_rpc.c','tests/nes-functional/join208_host.inc',
 'tests/nes-functional/join208_tb.sv','docs/nes-join208-contract.ko.md']
def read(p):return json.loads(p.read_bytes())
def u16(b,n):return int.from_bytes(b[n:n+2],'little')

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-join208/test08';t=read(d/'result.json');assert t['passed']
 for n,h in t['source_pins'].items():assert sha(BASE/n)==h,n
 assert sha(d/'runner-source.py')==sha(ROOT/'tools/test_nes_join208.py')
 for n in ['join208_rpc.c','join208_tb.sv']:assert sha(d/n)==sha(ROOT/'tests/nes-functional'/n)
 rom=(d/'sink165.sfc').read_bytes();packed=bytes.fromhex((BASE/'probes/nes-board207/source02/sink-program.hex').read_text())
 assert len(packed)==4096 and packed[:0xfc0]==rom[:0xfc0] and packed[0xfc0:]==rom[0x7fc0:]
 cases=[]
 for mode,frames in [('normal',3),('partial',1)]:
  c=d/mode;requests=sorted(c.glob('req-*.bin'));seals=[];tiles=[]
  for i,f in enumerate(requests,1):
   b=f.read_bytes();ack=(c/f'ack-{i:04}.bin').read_bytes()
   assert len(ack)==12 and ack[1]==b[0] and ack[2:10]==b[2:10] and ack[10:]==bytes([0x65,0x9a])
   assert ack[0]==(1 if b[0]==3 else 0)
   if b[0]==3:seals.append(u16(b,8))
   if b[0]==7:tiles.append((b,(c/f'tile-{i:04}.bin').read_bytes()))
  assert seals==[65534,65535,0][:frames] and len(tiles)==frames*2
  sr=sorted(c.glob('S-*.req'));assert len(sr)==frames*6
  pixels=0;tokens=[]
  for i,(packet,expected) in enumerate(tiles):
   triplet=[]
   for f in sr[i*3:i*3+3]:
    b=f.read_bytes();reply=f.with_suffix('.rsp').read_bytes();triplet.append((b,reply))
   (h,desc),(b,actual),(w,done)=triplet
   assert h[0]==2 and int.from_bytes(h[1:4],'little')==0x6040 and u16(h,4)==12 and len(desc)==12
   assert desc[0]==1 and desc[1]==packet[1] and u16(desc,2)==u16(packet,14) and u16(desc,4)==u16(packet,10)
   assert u16(desc,6)==u16(packet,8) and desc[8:12]==packet[16:20]
   assert b[0]==2 and int.from_bytes(b[1:4],'little')==0x400800 and u16(b,4)==len(expected)
   assert actual==expected and len(actual)==u16(desc,2)
   assert w[0]==3 and int.from_bytes(w[1:4],'little')==0x604c and u16(w,4)==5 and w[8:]==desc[8:12]+b'\xa5' and done==b''
   pixels+=len(actual);tokens.append(int.from_bytes(desc[8:12],'little'))
  assert tokens==list(range(1,frames*2+1))
  retire=[];partial=0
  for f in sorted(c.glob('H-*.req')):
   b=f.read_bytes();reply=f.with_suffix('.rsp').read_bytes()
   if b[0]==1:
    assert len(reply)==u16(b,4) and len(b)==8+len(reply)
    if b[8]==0xea:retire.append(u16(b,9))
   elif b[0]==6:partial+=1;assert reply==b''
  assert retire==seals and partial==(mode=='partial')
  screen=(c/'frame-1.rgb').read_bytes();assert len(screen)==256*239*3 and len(set(zip(screen[::3],screen[1::3],screen[2::3])))>2
  for i in range(1,frames+1):assert (c/f'frame-{i}.rgb').read_bytes()==screen
  assert screen==(d/'normal/frame-1.rgb').read_bytes()
  cases.append(dict(mode=mode,frames=frames,display_ack_generations=seals,rtl_retire_generations=retire,
   packets=len(requests),bulk_chunks=len(tiles),actual_rtl_reference_tile_bytes=pixels,tokens=tokens,
   partial_cancel=bool(partial),screen_sha256=sha(c/'frame-1.rgb')))
 previous=read(ROOT/'analysis/board207-verification.json')
 for n,h in previous['source_pins'].items():assert sha(ROOT/n)==h,n
 archives=[verify_archive(x['name']) for x in previous['prior_archives']]+[verify_archive('nes-board207')]
 assert read(ROOT/'analysis/scroll193-measurement-plan.json')['collected_runs']==[]
 r=dict(passed=True,selected=['test08','evidence01'],source_pins={n:sha(ROOT/n) for n in FILES},prior_archives=archives,cases=cases,
  actual_c_rtl_snes_transaction_join=True,actual_snes_display_ack=True,actual_rtl_consume=True,actual_rtl_epoch_and_lease=True,
  sink_queue_model=True,archived_exporter_trace=True,capture_loader_status_fixture=True,qualified_slot_always_true=True,
  aperture_prefetch_immutable=True,shared_simulator_clock=False,full_board=False,game_cpu=False,physical=False,
  runtime203_unchanged=True,board207_rtl_unchanged=True,rom195_matches_board207=True,new_fit=False,new_arm=False,new_asm=False,new_package=False,
  actual_scroll_measured=False,meets_60fps_budget=False,
  next='Preserve207 fit/203 runtime/195 client; close exact unchanged E0/E1 queue/top mux binding by reuse or bounded trace replay, then paired ARM identity/ROM checks and FIRSTLEVELSCROLL package. Do not expand into whole-game cosimulation or repeat codec/FIT loops.')
 s=json.dumps(r,indent=2)+'\n';(a.out/'result.json').write_text(s,encoding='utf8',newline='\n');(ROOT/'analysis/join208-verification.json').write_text(s,encoding='utf8',newline='\n')
 print(json.dumps(dict(passed=True,cases=cases,prior_archives=len(archives))))
if __name__=='__main__':main()
