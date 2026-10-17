# SPDX-License-Identifier: MIT
"""Pin actual C/65816 candidate evidence without approving a physical release."""
from pathlib import Path
import argparse,json,re
from nes_resident211 import ROOT,BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args();archive=a.archive.resolve()
 out=archive/'evidence01';out.mkdir(exist_ok=False)
 test=json.loads((archive/'test09/result.json').read_bytes());arm=json.loads((archive/'arm03/result.json').read_bytes())
 build=json.loads((archive/'test09/client/build.json').read_bytes())
 for name,digest in test['sources'].items():
  assert sha(ROOT/name)==digest and sha(archive/'test09/scripts'/Path(name).name)==digest,name
 for name,digest in test['generated_sources'].items():assert sha(archive/'test09'/name)==digest,name
 for name,digest in test['reference_files'].items():assert sha(archive/'test05/reference-normal'/Path(name).name)==digest,name
 for name,digest in arm['input_pins'].items():
  assert sha(archive/'test09/candidate'/name)==digest and sha(archive/'arm03'/name)==digest,name
 assert sha(ROOT/'tools/check_nes_dirty212_arm.py')==arm['script_sha256']
 assert sha(archive/'test09/client/sink165.sfc')==test['client']
 assert build['body_bytes']==3552 and build['body_free']==384 and build['program_bytes']==4096
 assert arm['layout']==dict(resident_bytes=3200,video_bytes=15912)
 assert arm['stacks']['nes_sink212_seal']['bytes']==280
 cases={c['mode']:c for c in test['cases']};assert len(cases)==14
 normal=cases['normal'];assert normal['commits']==14 and normal['single_vblank_commits']==10
 assert normal['vram_bytes']==26848 and normal['vram_commands']==45
 assert 'requests=349 packet_bytes=45985 tile_bytes=992' in normal['host']
 assert (archive/'test09/candidate-normal/vblank-3.txt').read_text()=='1'
 before=(archive/'test05/reference-normal/host.log').read_text();assert 'requests=485 packet_bytes=82877' in before
 negatives=['bad_bank','bad_base','bad_epoch','missing_slot','missing_map','old_seal','duplicate_tile','duplicate_map','bad_token','stop_dma','stop_final']
 for name in negatives:assert cases[name]['passed'] and cases[name]['commits']==1
 assert cases['pressure']['max_dma']==2048 and cases['pressure']['largest_list']==83
 assert cases['wrong_display_ack']['commits']==2 and 'commits=1 ' in cases['wrong_display_ack']['host']
 for c in cases.values():
  d=archive/'test09'/('candidate-'+c['mode'])
  assert json.loads((d/'consumer-result.json').read_bytes())['passed']
  assert (d/'host.log').read_text()==c['host']
  for i in range(1,c['commits']+1):assert sha(d/f'frame-{i}.rgb')==sha(archive/'test05/reference-normal'/f'frame-{i}.rgb')
 files=['tools/nes_dirty212.py','tools/nes_sink212.py','tools/test_nes_dirty212.py','tools/check_nes_dirty212_arm.py','tools/nes_dirty212_evidence.py','tests/nes-functional/dirty212_host.c','docs/nes-dirty212-contract.ko.md']
 result=dict(passed=True,selected=['test09','arm03'],reference='test05/reference-normal',pr=120,
  gates={n:sha(archive/n) for n in ['test09/result.json','arm03/result.json','test09/client/build.json']},
  public_sources={n:sha(ROOT/n) for n in files},cases=test['cases'],arm=arm,client=build,
  same_synthetic_input=dict(frames=14,pixels=14*256*239,packet_count_before=485,packet_count_after=349,
    packet_bytes_before=82877,packet_bytes_after=45985,packet_reduction_percent=100*(1-45985/82877),
    separate_direct_aperture_bytes=992,includes_ingress_poll_plan_audio=False,physical_fps=False),
  scope=dict(actual_c_planner=True,actual_c_sink=True,actual_65816=True,actual_ppu_dma_ack=True,
    chr_source='fixture',descriptor_bus='held file fixture',production_spi_rtl=False,production_run=False,
    preflip_old_screen_faults=11,postflip_corrupted_ack_faults=1,postflip_old_screen_preserved=False,
    complete_memory_command_capacity_stress=False,physical=False),
  next='Connect RUN/loader immutable epoch + actual200plan/193descriptor/184window to212begin/finish/seal/displayACK/retire; fullARM+IRQ and minimal board/ROM-only checks, then paired hardware video. No isolated cache/poll/FIT loop.',
  deployable=False,new_fit=False,new_package=False,save_sram_changed=False)
 text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
 (out/'verification.json').write_text(text,encoding='utf8');(ROOT/'analysis/dirty212-verification.json').write_text(text,encoding='utf8')
 manifest={str(f.relative_to(archive)):sha(f) for f in sorted(archive.rglob('*')) if f.is_file()}
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
 (archive/'progress.json').write_text(json.dumps(dict(status='C_65816_pair_verified_not_production_RUN',selected=['test09','arm03','evidence01'],next=result['next'],evidence_sha256=sha(out/'verification.json'),manifest_sha256=sha(out/'manifest.json'),files=len(manifest)),indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(passed=True,files=len(manifest),body_free=384,single_vblank_commits=10,next=result['next'])))
if __name__=='__main__':main()
