# SPDX-License-Identifier: MIT
"""Reconcile Lite timing using the same explicit 224 classification."""
import collections,csv,json
from nes_delta231 import BASE,ROOT,sha
from check_nes_boundary165 import measurements

d=BASE/'probes/nes-nrom419/fit01'
def rows(name):
 with (d/name).open() as f:return list(csv.DictReader(f,delimiter='\t'))
timing={}
for view in ('implementation','nominal'):
 r=rows(view+'-paths204.tsv');assert len({x['corner'] for x in r})==3
 timing[view]={}
 for kind in ('setup','hold'):
  group=[x for x in r if x['kind']==kind and ((x['from_clock']=='nes')==(x['to_clock']=='nes'))]
  timing[view][kind]=min(group,key=lambda x:float(x['slack']))
top=rows('topology206.tsv');assert len(top)==45
for x in top:
 expected=x['first'].replace('epoch_meta','epoch_sync') if 'epoch_meta' in x['first'] else x['first'][:-3]+'[1]'
 assert x['fanout']==expected
first={x['first'] for x in top};classes=collections.Counter();held=[];gray=[];other=[]
for r in rows('inventory206.tsv'):
 if ((r['from_clock']=='nes')==(r['to_clock']=='nes')):g='related'
 elif r['kind'] in ('recovery','removal'):g='inherited_reset_review'
 elif r['to'] in first:
  g='gray_first' if '|epoch_meta[' in r['to'] else 'control_first'
  if g=='gray_first' and r['kind']=='setup':gray.append(float(r['delay']))
 elif 'direct_path' in r['from'] and '|held[' in r['from'] and r['to']==r['from'].replace('|held[','|received['):
  g='held_payload'
  if r['kind']=='setup':held.append(float(r['delay']))
 elif 'direct_path' in r['from'] or 'direct_path' in r['to']:g='new_other';other.append(r)
 else:g='inherited_unmodified'
 classes[g]+=1
assert not other and held and gray
reset=rows('reset207.tsv');assert len(reset)==576 and len({x['to'] for x in reset})==96
io=measurements(d)
result={'fit_le':14751,'device_le':15408,'raw_sta_setup_ns':-6.970,'raw_sta_recovery_ns':-8.824,
 'related_paths':timing,'reset_epoch_paths':len(reset),'reset_epoch_min_slack_ns':min(float(r['slack']) for r in reset),
 'first_stage_fanout':len(top),'cdc_classes':dict(classes),'held_max_ns':max(held),'gray_max_ns':max(gray),
 'conditional_io':{k:io[k] for k in ('psram_conditional_margin_ns','snes_read_envelope_ns','spi_reply_envelope_ns','spi_half_period_ns','conditional_data_bounds_pass','native_payload_reset_pass','negative_reset_path_count','native_payload_negative_reset_path_count')},
 'inherited_unmodified_not_reaudited':True,'unconstrained_paths_remain':True,'actual_board_signoff':False,
 'input_sha256':{n:sha(d/n) for n in ('board.fit.summary','board.sta.summary','board.sta.rpt','inventory206.tsv','topology206.tsv','reset207.tsv','boundary165-paths.tsv','implementation-paths204.tsv','nominal-paths204.tsv')}}
text=json.dumps(result,indent=2)+'\n';(ROOT/'analysis/nrom420-timing.json').write_text(text);print(text)
